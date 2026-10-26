"""
Application settings, kept in memory and saved to a JSON file.

How it works:
- The file is read once at startup (init() -> SettingsManager.load()).
- Everyone reads and changes the in-memory dataclasses (AppSettings, GameSettings in models.py).
- Changing a plain field saves the whole file right away.
- Changing a `memory()` field only marks the settings as changed. It is written by the next immediate save, or by `save_if_dirty()`, which runs when the options dialog closes and when the app quits.

Safety rules:
- The file is always written and read as UTF-8, regardless of the OS language.
- Writes are atomic: we write a temp file and swap it in with `os.replace`, so the file on disk is always either the old version or the new one, never half written.
- One lock covers every change and every save, so threads can't interleave writes.
- A file we fail to read is never overwritten. It is renamed to `*.corrupt-<time>` first, and we try to recover from `*.bak` (a copy of the last file that loaded fine). If it can't even be renamed, saving is turned off for this session.
"""

import json
import logging
import os
import tempfile
import threading
import time
from dataclasses import MISSING, fields
from pathlib import Path
from typing import Optional

from config.runtime import get_config

from .models import AppSettings, GameSettings

log = logging.getLogger("Settings")

SETTINGS_FILE_NAME = "stellaris-checksum-patcher-settings-v2.json"

_current: Optional["SettingsManager"] = None


class SettingsManager:
    """Owns the in-memory settings and saves them to disk."""

    def __init__(self, config_file_name: str = SETTINGS_FILE_NAME):
        self.config_dir = Path(get_config().config_dir)
        self.config_file = self.config_dir / config_file_name
        self.backup_file = self.config_file.with_name(self.config_file.name + ".bak")

        # RLock (re-entrant) because a save can happen while the same thread already holds
        # the lock, ex.: assigning a field holds the lock and then saves.
        self.lock = threading.RLock()

        self.settings = self._attach(AppSettings())
        self._dirty = False  # Something changed in memory that isn't on disk yet

        # False when the settings file couldn't be read AND couldn't be moved aside.
        # Saving would destroy it, don't do it.
        self.can_save = True

        # Message when something went wrong while loading. Empty if all was fine.
        self.load_problem = ""

    # ---------- Loading ----------

    def load(self) -> bool:
        """
        Read settings from disk. Returns True if settings were loaded (or no file yet).

        Never Raise: on any problem we fall back to the backup, then to defaults.
        """
        with self.lock:
            if not self.config_file.exists():
                log.info(f"No settings file yet, using defaults: {self.config_file}")
                return True

            data = self._read_json(self.config_file)
            if data is not None:
                self.settings = self._from_dict(data)
                self._dirty = False
                log.info(f"Loaded settings from {self.config_file}")
                # Remember good file in case the next one gets damaged
                self._write_text_atomic(self.backup_file, json.dumps(data, indent=2, ensure_ascii=False))
                return True

            # The file exists but we can't use it. Keep it out of the way so it's not lost.
            log.error(f"Settings file could not be read: {self.config_file}")
            corrupt_copy = self._move_aside(self.config_file)
            if corrupt_copy is None:
                self.can_save = False
                self.load_problem = (
                    f"Settings file could not be read:\n{self.config_file}\n\n"
                    "Default settings will be used and changes will NOT be saved this session, "
                    "so the file is left unchanged."
                )
                return False

            data = self._read_json(self.backup_file)
            if data is not None:
                self.settings = self._from_dict(data)
                self.save_settings()
                self.load_problem = (
                    "Settings file could not be read, settings were restored from the last backup.\n\n"
                    f"The unreadable file was kept as:\n{corrupt_copy}"
                )
                log.warning(f"Restored settings from backup: {self.backup_file}")
                return True

            self.load_problem = (
                "Settings file could not be read and no usable backup was found. "
                "Default settings are used.\n\n"
                f"The unreadable file was kept as:\n{corrupt_copy}"
            )
            return False

    def _read_json(self, fp: Path) -> Optional[dict]:
        """Read a JSON object from a file. Returns None if missing, empty or invalid."""
        try:
            # "utf-8-sig" is UTF-8 that also accepts a leading BOM (some editors add one)
            content = fp.read_text(encoding="utf-8-sig")
            data = json.loads(content)
        except FileNotFoundError:
            return None
        except Exception as e:
            log.error(f"Could not read '{fp}': {e}")
            return None

        if not isinstance(data, dict):
            log.error(f"'{fp}' does not contain a JSON object.")
            return None

        return data

    def _move_aside(self, fp: Path) -> Optional[Path]:
        """Rename a bad file to '<name>.corrupt-<time>'. Returns the new path, or None on failure."""
        target = fp.with_name(f"{fp.name}.corrupt-{time.strftime('%Y%m%d-%H%M%S')}")
        try:
            os.replace(fp, target)
        except OSError as e:
            log.error(f"Could not move unreadable settings file aside: {e}")
            return None
        log.info(f"Kept unreadable settings file as: {target}")
        return target

    def _from_dict(self, data: dict) -> AppSettings:
        """Build AppSettings from a dict, one field at a time. A bad value only resets that field."""
        settings = _dataclass_from_dict(AppSettings, data)

        games_data = data.get("games", {})
        if not isinstance(games_data, dict):
            log.warning(f"Ignoring invalid 'games' value in settings: {games_data!r}")
            games_data = {}

        for name, game_data in games_data.items():
            if not name or not name.strip() or not isinstance(game_data, dict):
                log.warning(f"Skipping invalid game entry '{name}': {game_data!r}", silent=True)
                continue
            settings.games[name] = self._attach(_dataclass_from_dict(GameSettings, game_data))

        return self._attach(settings)

    # ---------- Saving ----------

    def _on_change(self, save_now: bool):
        """
        Called on every field change (with the lock held).

        save_now=True:  plain field. Save now.
        save_now=False: memory() field. Only remember that something changed.
        """
        self._dirty = True
        if save_now:
            self.save_settings()

    def save_if_dirty(self) -> bool:
        """Write the settings only if something changed since the last save. Thread-safe call."""
        with self.lock:
            if not self._dirty:
                return True
            return self.save_settings()

    def save_settings(self) -> bool:
        """Write the current settings to disk. Thread-safe call."""
        with self.lock:
            if not self.can_save:
                log.warning("Saving is disabled this session (settings file was unreadable).", silent=True)
                return False

            text = json.dumps(self._to_dict(), indent=2, ensure_ascii=False)
            if not self._write_text_atomic(self.config_file, text):
                return False

            self._dirty = False
            log.debug(f"Saved settings to {self.config_file}", silent=True)
            return True

    def _to_dict(self) -> dict:
        """Turn settings into a plain dict for JSON. Call while holding the lock."""
        data = _dataclass_to_dict(self.settings)
        data["games"] = {name: _dataclass_to_dict(game) for name, game in self.settings.games.items()}
        return data

    def _write_text_atomic(self, fp: Path, text: str) -> bool:
        """
        Write text to a file, never leaving it half-written.

        Write to a temp file in the same folder, flush to disk, then swap it into place which
        is atomic on Windows, Linux and macOS with `os.replace()`.
        """
        fp.parent.mkdir(parents=True, exist_ok=True)

        fd, temp_path = tempfile.mkstemp(dir=fp.parent, prefix=fp.name + ".", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
                f.flush()
                os.fsync(f.fileno())

            # On Windows the target can be briefly locked (antivirus, indexer).
            # Retry a few times.
            for attempt in range(3):
                try:
                    os.replace(temp_path, fp)
                    return True
                except PermissionError:
                    if attempt == 2:
                        raise
                    time.sleep(0.1)
        except Exception as e:
            log.error(f"Could not write '{fp}': {e}")
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        return False

    # ---------- Games ----------

    def game(self, name: str) -> GameSettings:
        """Get or create Game settings."""
        if not name or not name.strip():
            # Never store an entry without a name. Hand back a detached object so callers don't crash.
            log.warning("Requested game settings with an empty name; not saving it.")
            return GameSettings()

        with self.lock:
            if name not in self.settings.games:
                self.settings.games[name] = self._attach(GameSettings())
                # Empty entry isn't worth a write on its own.
                # Wait until next save to write to disk.
                self._on_change(save_now=False)
            return self.settings.games[name]

    def has_game(self, name: str) -> bool:
        return name in self.settings.games

    def remove_game(self, name: str) -> bool:
        with self.lock:
            if name in self.settings.games:
                del self.settings.games[name]
                self._on_change(save_now=True)
                return True
            return False

    def _attach(self, obj):
        """Link a settings object to this manager so changes to it get saved."""
        obj._manager = self
        return obj


# ---------- Dataclass <-> dict helpers ----------


def _dataclass_from_dict(cls, data: dict):
    """
    Create `cls` from `data`, checking each field's type against its default value.
    Missing or wrongly typed values keep the default. Unknown keys are kept in `_unknown`.
    """
    obj = cls()
    known = set()

    for f in fields(cls):
        if f.name.startswith("_"):
            continue
        known.add(f.name)

        if f.name == "games" or f.name not in data:
            continue  # games are handled by the caller

        value = data[f.name]
        default = f.default if f.default is not MISSING else f.default_factory()

        if type(value) is not type(default):
            log.warning(f"Ignoring setting '{f.name}' with unexpected value {value!r}. Using default.", silent=True)
            continue

        setattr(obj, f.name, value)

    obj._unknown = {k: v for k, v in data.items() if k not in known}
    return obj


def _dataclass_to_dict(obj) -> dict:
    """Public fields of a settings dataclass, plus any unknown keys we read from the file."""
    data = dict(obj._unknown)
    for f in fields(obj):
        if not f.name.startswith("_") and f.name != "games":
            value = getattr(obj, f.name)
            data[f.name] = list(value) if isinstance(value, list) else value
    return data


# ---------- Module access ----------


def init() -> SettingsManager:
    """Create the settings manager and load the file. Call once at startup."""
    global _current

    if _current is None:
        _current = SettingsManager()
        _current.load()

    return _current


def get() -> SettingsManager:
    if _current is None:
        raise RuntimeError("Settings are not initialised. Call settings.init() first.")
    return _current
