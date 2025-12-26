import os  # isort: skip
import sys  # isort: skip
import json  # isort: skip
import shutil  # isort: skip
import tempfile  # isort: skip
from pathlib import Path  # isort: skip
from dataclasses import asdict, dataclass, field
from typing import Optional, Union

from conf_globals import config_folder, LOG_LEVEL  # isort: skip
from logger import create_logger  # isort: skip
from utils.encodings import detect_file_encoding  # isort: skip

log = create_logger("Settings", LOG_LEVEL)


@dataclass
class AutoSaveHookedSettingsClass:
    # Manager hook to intercept attr calls in order to auto-save
    _manager: Optional["SettingsManager"] = field(default=None, init=False, repr=False, compare=False)

    def __setattr__(self, name, value):
        # Skip internal attributes
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return

        # Set value
        object.__setattr__(self, name, value)

        # Trigger auto-save
        if hasattr(self, "_manager") and self._manager:
            log.info(f"Auto-saving!")
            self._manager._mark_dirty()


@dataclass
class GameSettings(AutoSaveHookedSettingsClass):
    """Representation of settings for a game."""

    install_path: str = ""
    proton_install_path: str = ""
    save_games_path: str = ""
    patches: list[str] = field(default_factory=list)
    last_patched_platform: str = ""
    last_patched_timestamp: float = 0.0


@dataclass
class AppSettings(AutoSaveHookedSettingsClass):
    """Main application settings."""

    app_version: str = ""
    accepted_welcome_dialog: bool = False
    update_last_checked: int = 0
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

    def __init__(self, config_file_name: str = "stellaris-checksum-patcher-settings.json"):
        self.config_dir = Path(config_folder)
        self.config_file = self.config_dir / config_file_name
        self.settings = AppSettings()
        self.settings._manager = self  # Link manager to class
        self._auto_save = True
        self._dirty = False

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

    def batch_update(self):
        return _BatchContext(self)


class _BatchContext:
    """Context Manager for batch updates."""

    def __init__(self, manager: SettingsManager):
        self.manager = manager

    def __enter__(self):
        self.manager._auto_save = False
        return self.manager

    def __exit__(self, *args):
        self.manager._auto_save = True
        if self.manager._dirty:
            self.manager.save_settings()
