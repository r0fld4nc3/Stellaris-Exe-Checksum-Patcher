import os  # isort: skip
import json  # isort: skip
import shutil  # isort: skip
import tempfile  # isort: skip
from pathlib import Path  # isort: skip
import logging
from dataclasses import asdict, dataclass, field
from typing import Optional, Union

from config.runtime import get_config

from utils.encodings import detect_file_encoding  # isort: skip


log = logging.getLogger("Settings")

_current: Optional["AppSettings"] = None


@dataclass
class AutoSaveHookedSettingsClass:
    # Manager hook to intercept attr calls in order to auto-save
    _manager: Optional["SettingsManager"] = field(default=None, init=False, repr=False, compare=False)

    def __setattr__(self, name: str, value):
        # Skip internal attributes
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return

        # Set value
        object.__setattr__(self, name, value)

        # Trigger auto-save
        if hasattr(self, "_manager") and self._manager:
            self._manager._mark_dirty()


@dataclass
class GameSettings(AutoSaveHookedSettingsClass):
    """Representation of settings for a game."""

    install_path: str = ""
    proton_install_path: str = ""
    save_games_path: str = ""
    patches: list[str] = field(default_factory=list)
    last_patched_version: str = ""
    last_patched_platform: str = ""
    last_patched_timestamp: float = 0.0


@dataclass
class AppSettings(AutoSaveHookedSettingsClass):
    """Main application settings."""

    app_version: str = ""
    accepted_welcome_dialog: bool = False
    update_last_checked: int = 0
    max_allowed_binary_backups: int = 2
    patch_patterns_update_last_checked: int = 0
    force_local_patterns: bool = False
    update_available: bool = False
    window_width: int = 800
    window_height: int = 600
    last_selected_game: str = ""
    steam_install_path: str = ""
    app_ids_update_last_checked: int = 0
    games: dict[str, GameSettings] = field(default_factory=dict)


class SettingsManager:
    """Manages application settings with automatic persistence."""

    def __init__(self, config_file_name: str = "stellaris-checksum-patcher-settings-v2.json"):
        self.config_dir = Path(get_config().config_dir)
        self.config_file = self.config_dir / config_file_name
        self.settings = AppSettings()
        self.settings._manager = self  # Link manager to class
        self._auto_save = True
        self._dirty = False

        # Kick-off migration process
        self.migrate_from_v1()

    def _mark_dirty(self):
        """Mark settings as modified and trigger auto-save."""
        self._dirty = True
        if self._auto_save:
            self.save_settings()

    def load(self) -> bool:
        """Load settings from disk."""
        if not self.config_file.exists():
            log.debug(f"Config file does not exist.")
            return False

        data = self._read_json(self.config_file)
        if data:
            self.settings = self._from_dict(data)
            self._dirty = False
            log.info(f"Loaded config from {self.config_file}")
            return True
        return False

    def save_settings(self) -> bool:
        """Save settings to dsk."""
        if not self._auto_save:
            return True

        self.config_dir.mkdir(parents=True, exist_ok=True)
        data = self._to_dict(self.settings)

        if self._write_json(self.config_file, data):
            self._dirty = False
            log.info(f"Saved config to {self.config_file}")
            return True
        return False

    def _to_dict(self, settings: AppSettings) -> dict:
        """Convert AppSettings to dict."""

        def _dict_factory(field_list):
            """Custom dict factory to filter and exclude certain attributes."""
            return {k: v for k, v in field_list if not k.startswith("_")}

        data = asdict(settings, dict_factory=_dict_factory)
        return data

    def _from_dict(self, data: dict) -> AppSettings:
        """Convert dict settings to AppSettings handling nested GameSettings."""

        # Extract nested and convert to relevant objects
        game_data: dict = data.pop("games", {})
        games: dict = {}

        for name, game_data in game_data.items():
            # Skip empty name
            if not name or not name.strip():
                log.warning(f"Skipping game with empty name: {game_data}", silent=True)
                continue

            if isinstance(game_data, dict):
                # Filter to only valid GameSettings fields
                valid_fields = {k: v for k, v in game_data.items() if k in GameSettings.__annotations__}

                game_settings = GameSettings(**valid_fields)
                game_settings._manager = self  # Link manager to class
                games[name] = game_settings
            else:
                games[name] = game_data

        # Filter valid AppSettings fields
        valid_fields = {k: v for k, v in data.items() if k in AppSettings.__annotations__}

        settings = AppSettings(**valid_fields)
        settings._manager = self  # Link manager to class
        settings.games = games

        return settings

    def _read_json(self, fp: Path) -> Optional[dict]:
        try:
            if not fp.exists():
                return None

            encoding = detect_file_encoding(fp)
            content = fp.read_text(encoding=encoding)

            if not content.strip():
                return None

            return json.loads(content)

        except json.JSONDecodeError as e:
            log.error(f"JSON Decode Error: {e}")
            backup = fp.with_suffix(fp.suffix + ".baddecode")
            shutil.copy2(fp, backup)
            log.info(f"Backed up corrupted file to: {backup}")
            return None
        except Exception as e:
            log.error(f"Error reading config: {e}")
            return None

    def _write_json(self, fp: Path, data: dict) -> bool:
        """Atomically write JSON file."""

        fp.parent.mkdir(parents=True, exist_ok=True)

        temp = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=str(fp.parent), delete=False)

        try:
            temp.write(json.dumps(data, indent=2, ensure_ascii=False))
            temp.flush()
            os.fsync(temp.fileno())
            temp.close()
            shutil.move(temp.name, fp)
            return True
        except Exception as e:
            log.error(f"Error writing config: {e}")
            try:
                os.unlink(temp.name)
            except:
                pass
            return False

    def game(self, name: str) -> GameSettings:
        """Get or create Game settings."""
        if name not in self.settings.games:
            game_settings = GameSettings()
            game_settings._manager = self  # Link manager to class
            self.settings.games[name] = game_settings
            self._mark_dirty()
        return self.settings.games[name]

    def has_game(self, name: str) -> bool:
        return name in self.settings.games

    def remove_game(self, name: str) -> bool:
        if name in self.settings.games:
            del self.settings.games[name]
            self._mark_dirty()
            return True
        return False

    def migrate_from_v1(self) -> bool:
        """
        Migrate old v1 settings to v2.
        """

        def _search_config_dir_for_file(self: "SettingsManager") -> tuple[Optional[Path], set[Path]]:
            """
            Search config directory for old settings file and return its path if found.

            It looks at recent modified and accessed times to sort for the most recent
            old save file in order to determine which file has the most up to date
            values.

            It attempts to filter out the current v2 file if it is present.

            Returns:
                Tuple of (most_recent_file, all_old_files)
            """

            log.info("Attempting to locate and migrate old settings to v2", silent=True)

            found: Optional[Path] = None
            all_old_files: set[Path] = set()

            access_sort: dict = {}

            for item in self.config_dir.iterdir():
                log.info(f"--> {item}")

                # Pass own v2 file
                if item.name == self.config_file.name:
                    log.info(f"Passing own file: {item.name}", silent=True)
                    continue

                # Pass non .json files
                if item.suffix.lower() != ".json":
                    log.info(f"Passing non .json file. {item.name}", silent=True)
                    continue

                # Test for known identifier strings
                name_split = item.stem.split("-")

                if "settings" not in name_split:
                    continue

                if "v2" in name_split and item != self.config_file:
                    all_old_files.add(item)
                    continue
                else:
                    skip = False
                    # Let's really test it, because "v2 copy" returns False
                    for kw in name_split:
                        if "v2" in kw.lower():
                            skip = True
                            break
                    if item != self.config_file:
                        all_old_files.add(item)

                    if skip:
                        continue

                log.info(f"Processing file: {item.name}")

                # Get access/modified times
                a_time = os.stat(item).st_atime
                m_time = os.stat(item).st_mtime

                log.info(f"'{item.name} a_time: {a_time}")
                log.info(f"'{item.name} m_time: {m_time}")

                most_recent = max(a_time, m_time)

                access_sort[item] = most_recent

                all_old_files.add(item)

            if access_sort:
                found = max(access_sort.items(), key=lambda x: x[1])[0]
                log.info(f"Selected most recent file for migration: {found.name}", silent=True)

            return found, all_old_files

        # Map old keys (dash-separated) to new keys (underscore-separated)
        key_mapping: dict = {
            "accepted-welcome-dialog": "accepted_welcome_dialog",
            "update-last-checked": "update_last_checked",
            "patch-patterns-update-last-checked": "patch_patterns_update_last_checked",
            "patch-patterns-force-local": "force_local_patterns",
            "window-width": "window_width",
            "window-height": "window_height",
            "last-selected-game": "last_selected_game",
            "steam-install-path": "steam_install_path",
        }

        # Map old game keys to new keys
        game_key_mapping = {
            "install-path": "install_path",
            "proton-install-path": "proton_install_path",
            "last-patched-platform": "last_patched_platform",
            "last-patched-timestamp": "last_patched_timestamp",
        }

        old_settings, all_old_files = _search_config_dir_for_file(self)

        if not old_settings:
            log.info(f"No old settings file found to migrate.", silent=True)
            return False

        with open(old_settings, "r", encoding="utf-8") as f:
            old_data = json.load(f)

        # Migrate App Settings
        with self.batch_update():
            for old_key, new_key in key_mapping.items():
                if old_key in old_data:
                    value = old_data[old_key]

                    # Need to use setattr to set the value on dataclass
                    if hasattr(self.settings, new_key):
                        setattr(self.settings, new_key, value)
                        log.info(f"Migrated {old_key} -> {new_key}: {value}", silent=True)

        # Migrate Game settings
        if "games" in old_data and isinstance(old_data["games"], dict):
            for game_name, game_data in old_data["games"].items():
                if not isinstance(game_data, dict):
                    continue

                game_settings = self.game(game_name)

                with self.batch_update():
                    for old_key, new_key in game_key_mapping.items():
                        if old_key in game_data:
                            value = game_data[old_key]
                            setattr(game_settings, new_key, value)
                            log.info(f"Migrated game '{game_name}' {old_key} -> {new_key}: {value}", silent=True)

        # Save migrated settings
        self.save_settings()
        log.info(f"Successfully migrated settings from v1 to v2.", silent=True)

        # Delete all old files
        for file in all_old_files:
            log.info(f"Delete file: {file}", silent=True)
            if file.is_file():
                file.unlink(missing_ok=True)

        return True

    def batch_update(self):
        return _BatchContext(self)


class _BatchContext:
    """Context Manager for batch updates."""

    def __init__(self, manager: SettingsManager):
        self.manager = manager

    def __enter__(self):
        log.debug(f"Batch update started, disabling auto-save", silent=True)
        self.manager._auto_save = False
        return self.manager

    def __exit__(self, *args):
        log.debug(f"Batch update ending, dirty={self.manager._dirty}", silent=True)
        self.manager._auto_save = True
        if self.manager._dirty:
            log.debug("Saving batched changes", silent=True)
            self.manager.save_settings()
        else:
            log.warning("Batch update completed without marked as dirty.", silent=True)


def init() -> SettingsManager:
    global _current

    if _current is not None:
        if isinstance(_current, SettingsManager):
            return _current
        else:
            raise RuntimeError(f"Current Settings Instance is invalid: {_current}")

    _current = SettingsManager()
    _current.load()

    return _current


def get() -> SettingsManager:
    global _current

    if not isinstance(_current, SettingsManager):
        raise RuntimeError(f"Current Settings Instance is invalid: {_current}")

    if not _current or _current is None:
        raise RuntimeError(f"Settings is not valid or uninitialised: {_current}")

    return _current
