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
class GameSettings:
    """Representation of settings for a game."""

    install_path: str = ""
    proton_install_path: str = ""
    save_games_path: str = ""
    patches: list[str] = field(default_factory=list)
    last_selected_platform: str = ""
    last_accessed_timestamp: float = 0.0


@dataclass
class AppSettings:
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

        data = asdict(settings)
        return data

    def _from_dict(self, data: dict) -> AppSettings:
        """Convert dict settings to AppSettings handling nested GameSettings."""

        # Extract nested and convert to relevant objects
        game_data: dict = data.pop("games", {})
        games: dict = {}

        for name, game_data in game_data.items():
            if isinstance(game_data, dict):
                # Filter to only valid GameSettings fields
                valid_fields = {k: v for k, v in game_data.items() if k in GameSettings.__annotations__}

                games[name] = GameSettings(**valid_fields)
            else:
                games[name] = game_data

        # Filter valid AppSettings fields
        valid_fields = {k: v for k, v in data.items() if k in AppSettings.__annotations__}

        settings = AppSettings(**valid_fields)
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
            self.settings.games[name] = GameSettings()
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


class Settings:
    class ENUM:
        APP_VERSION = "app-version"
        ACCEPTED_WELCOME_DIALOG = "accepted-welcome-dialog"
        UPDATE_LAST_CHECKED = "update-last-checked"
        PATTERNS_UPDATE_LAST_CHECKED = "patch-patterns-update-last-checked"
        FORCE_LOCAL_PATTERNS = "patch-patterns-force-local"
        UPDATE_AVAILABLE = "update-available"
        WINDOW_WIDTH = "window-width"
        WINDOW_HEIGHT = "window-height"
        LAST_SELECTED_GAME = "last-selected-game"
        STEAM_INSTALL_PATH = "steam-install-path"
        GAMES = "games"

        APP_IDS_UPDATE_LAST_CHECKED = "app-ids-update-last-checked"

        # --- GAME SPECIFIC INFO ---
        INSTALL_PATH = "install-path"
        PROTON_INSTALL_PATH = "proton-install-path"
        PATCHES = "patches"
        SAVE_GAMES_PATH = "save-games-path"
        PATCHED_BLOCK = "patched-block"
        PATCHED_HASH = "patched-exe-hash"
        EXE_NAME = "exe-name"
        EXE_PROTON_NAME = "exe-proton-name"
        LAST_PATCHED_PLATFORM = "last-patched-platform"
        LAST_PATCHED_TIMESTAMP = "last-patched-ts"

        _DICT_DEFAULT_GAME_SETTINGS = {
            LAST_PATCHED_PLATFORM: "",
            LAST_PATCHED_TIMESTAMP: 0,
            INSTALL_PATH: "",
            PROTON_INSTALL_PATH: "",
            SAVE_GAMES_PATH: "",
            PATCHES: [],
        }

    def __init__(self):
        self.patcher_settings: dict = {
            self.ENUM.APP_VERSION: "",
            self.ENUM.ACCEPTED_WELCOME_DIALOG: False,
            self.ENUM.UPDATE_LAST_CHECKED: 0,
            self.ENUM.PATTERNS_UPDATE_LAST_CHECKED: 0,
            self.ENUM.FORCE_LOCAL_PATTERNS: False,
            self.ENUM.UPDATE_AVAILABLE: False,
            self.ENUM.WINDOW_WIDTH: 0,
            self.ENUM.WINDOW_HEIGHT: 0,
            self.ENUM.LAST_SELECTED_GAME: "",
            self.ENUM.STEAM_INSTALL_PATH: "",
            self.ENUM.GAMES: {},
        }
        self._config_file_name = "stellaris-checksum-patcher-settings.json"
        self.config_dir = Path(config_folder)
        self.config_file = Path(config_folder) / self._config_file_name

    def set_app_version(self, version: str):
        self.patcher_settings[self.ENUM.APP_VERSION] = version
        log.info(f"Saving app version: {version}")
        self.save_config()

    def get_app_version(self):
        # self.load_config()
        return self.patcher_settings.get(self.ENUM.APP_VERSION)

    def set_window_width(self, num: int):
        self.patcher_settings[self.ENUM.WINDOW_WIDTH] = num
        log.info(f"Saving window width: {num}")
        self.save_config()

    def get_window_width(self):
        # self.load_config()
        return self.patcher_settings.get(self.ENUM.WINDOW_WIDTH)

    def set_window_height(self, num: int):
        self.patcher_settings[self.ENUM.WINDOW_HEIGHT] = num
        log.info(f"Saving window height: {num}")
        self.save_config()

    def get_window_height(self):
        # self.load_config()
        return self.patcher_settings.get(self.ENUM.WINDOW_HEIGHT)

    def set_install_path(self, game_name: str, install_path: Union[Path, str]):
        game = self.patcher_settings[self.ENUM.GAMES].get(game_name, None)

        if not game:
            self.patcher_settings[self.ENUM.GAMES][game_name] = self.ENUM._DICT_DEFAULT_GAME_SETTINGS

        # Enforce install_path type
        if not isinstance(install_path, Path):
            install_path = Path(install_path).resolve().as_posix()

        self.patcher_settings[self.ENUM.GAMES][game_name][self.ENUM.INSTALL_PATH] = str(install_path)

        log.info(f"Saving {game_name} install location: {install_path}")
        self.save_config()

        return True

    def get_install_path(self, game_name: str) -> str:
        # self.load_config()

        game = self.patcher_settings[self.ENUM.GAMES].get(game_name, None)

        if not game:
            return ""

        return self.patcher_settings[self.ENUM.GAMES][game_name].get(self.ENUM.INSTALL_PATH)

    def set_proton_install_path(self, game_name: str, install_path):
        game = self.patcher_settings[self.ENUM.GAMES].get(game_name, None)

        if not game:
            self.patcher_settings[self.ENUM.GAMES][game_name] = self.ENUM._DICT_DEFAULT_GAME_SETTINGS

        # Enforce install_path type
        if not isinstance(install_path, Path):
            install_path = Path(install_path).resolve().as_posix()

        self.patcher_settings[self.ENUM.GAMES][game_name][self.ENUM.PROTON_INSTALL_PATH] = install_path

        log.info(f"Saving {game_name} Proton install location: {install_path}")
        self.save_config()

        return True

    def get_proton_install_path(self, game_name: str) -> str:
        # self.load_config()

        game = self.patcher_settings[self.ENUM.GAMES].get(game_name, None)

        if not game:
            return ""

        return self.patcher_settings[self.ENUM.GAMES][game_name].get(self.ENUM.PROTON_INSTALL_PATH)

    def set_steam_install_path(self, install_path) -> None:
        posix_path = Path(install_path).as_posix()
        self.patcher_settings[self.ENUM.STEAM_INSTALL_PATH] = posix_path
        log.info(f"Saving Steam install path: {posix_path}")
        self.save_config()

    def get_steam_install_path(self) -> str:
        # self.load_config()
        return self.patcher_settings.get(self.ENUM.STEAM_INSTALL_PATH)

    def set_save_games_dir(self, game_name: str, save_games_dir: str):
        game = self.patcher_settings[self.ENUM.GAMES].get(game_name, None)

        if not game:
            self.patcher_settings[self.ENUM.GAMES][game_name] = self.ENUM._DICT_DEFAULT_GAME_SETTINGS

        posix_path = Path(save_games_dir).as_posix()

        self.patcher_settings[self.ENUM.GAMES][game_name][self.ENUM.SAVE_GAMES_PATH] = posix_path

        log.info(f"Saving {game_name} save games directory: {posix_path}")
        self.save_config()

        return True

    def get_save_games_dir(self, game_name: str) -> Optional[Path]:
        # self.load_config()

        game = self.patcher_settings[self.ENUM.GAMES].get(game_name, None)

        if not game:
            return None

        return self.patcher_settings[self.ENUM.GAMES][game_name].get(self.ENUM.SAVE_GAMES_PATH)

    def set_patches_applied_to_game(self, game_name: str, patches: list[str]):
        game = self.patcher_settings[self.ENUM.GAMES].get(game_name, None)

        if not game:
            self.patcher_settings[self.ENUM.GAMES][game_name] = self.ENUM._DICT_DEFAULT_GAME_SETTINGS

        self.patcher_settings[self.ENUM.GAMES][game_name][self.ENUM.PATCHES] = patches

        log.info(f"Saving {game_name} patches: {patches}")
        self.save_config()

        return True

    def get_patches_applied_to_game(self, game_name: str) -> list[str]:
        # self.load_config()

        game = self.patcher_settings[self.ENUM.GAMES].get(game_name, None)

        if not game:
            return []

        return self.patcher_settings[self.ENUM.GAMES][game_name].get(self.ENUM.PATCHES, [])

    def get_update_last_checked(self) -> int:
        # self.load_config()
        return self.patcher_settings.get(self.ENUM.UPDATE_LAST_CHECKED, 0)

    def set_update_last_checked(self, timestamp: int):
        self.patcher_settings[self.ENUM.UPDATE_LAST_CHECKED] = int(timestamp)
        log.info(f"Saving update last checked: {timestamp}")
        self.save_config()

    def get_has_update(self) -> bool:
        # self.load_config()
        return self.patcher_settings.get(self.ENUM.UPDATE_AVAILABLE)

    def set_has_update(self, has_update_bool: bool):
        self.patcher_settings[self.ENUM.UPDATE_AVAILABLE] = bool(has_update_bool)
        log.info(f"Saving is update available: {has_update_bool}")
        self.save_config()

    def get_patch_patterns_update_last_checked(self):
        # self.load_config()
        return self.patcher_settings.get(self.ENUM.PATTERNS_UPDATE_LAST_CHECKED, 0)

    def set_patch_patterns_update_last_checked(self, timestamp: int):
        self.patcher_settings[self.ENUM.PATTERNS_UPDATE_LAST_CHECKED] = int(timestamp)
        log.info(f"Saving patch patterns update last checked: {int(timestamp)}")
        self.save_config()

    def set_force_use_local_patterns(self, state: bool):
        self.patcher_settings[self.ENUM.FORCE_LOCAL_PATTERNS] = state
        log.info(f"Saving force local patterns to: {state}")
        self.save_config()

    def get_force_use_local_patterns(self):
        # self.load_config()
        return self.patcher_settings.get(self.ENUM.FORCE_LOCAL_PATTERNS, False)

    def get_app_ids_file_update_last_checked(self):
        # self.load_config()
        return self.patcher_settings.get(self.ENUM.APP_IDS_UPDATE_LAST_CHECKED, 0)

    def set_app_ids_file_update_last_checked(self, timestamp: int):
        self.patcher_settings[self.ENUM.APP_IDS_UPDATE_LAST_CHECKED] = int(timestamp)
        log.info(f"Saving App IDs file update last checked: {int(timestamp)}")
        self.save_config()

    def set_last_selected_platform(self, game: str, platform: str):
        game_config = self.patcher_settings[self.ENUM.GAMES].get(game, None)

        if not game_config:
            return

        log.info(f"Saving '{game}' last used platform: {platform}", silent=True)
        self.patcher_settings[self.ENUM.GAMES][game][self.ENUM.LAST_PATCHED_PLATFORM] = platform

    def get_last_selected_platorm(self, game_name: str) -> str:
        games: dict = self.patcher_settings.get(self.ENUM.GAMES)
        game_config: dict = games.get(game_name, None)

        if not game_config:
            return ""

        return game_config.get(self.ENUM.LAST_PATCHED_PLATFORM, "")

    def set_last_accessed_timestamp(self, game: str, ts: int | float):
        game_config = self.patcher_settings[self.ENUM.GAMES].get(game, None)

        if not game_config:
            return

        log.info(f"Saving '{game}' last accessed time: {ts}", silent=True)
        self.patcher_settings[self.ENUM.GAMES][game][self.ENUM.LAST_PATCHED_TIMESTAMP] = ts

    def get_last_accessed_timestamp(self, game_name: str) -> int | float:
        games: dict = self.patcher_settings.get(self.ENUM.GAMES)
        game_config: dict = games.get(game_name, None)

        if not game_config:
            return ""

        return game_config.get(self.ENUM.LAST_PATCHED_TIMESTAMP, 0)

    def set_last_selected_game(self, game_name: str):
        self.patcher_settings[self.ENUM.LAST_SELECTED_GAME] = game_name
        log.info(f"Saving last selected game: {game_name}")
        self.save_config()

    def get_last_selected_game(self) -> str:
        """Return name of last selected game"""
        return self.patcher_settings.get(self.ENUM.LAST_SELECTED_GAME, "")

    def set_accepted_welcome_dialog(self, acceptance: bool):
        log.info(f"Set welcome dialog acceptance: {acceptance}")
        self.patcher_settings[self.ENUM.ACCEPTED_WELCOME_DIALOG] = acceptance
        self.save_config()

    def get_accepted_welcome_dialog(self) -> bool:
        return self.patcher_settings.get(self.ENUM.ACCEPTED_WELCOME_DIALOG, False)

    def clean_save_file(self):
        """
        Removes unused keys from the save file.
        :return: `bool`
        """

        if not self.config_dir or not Path(self.config_dir).exists():
            log.info("No config folder found.")
            return False

        if not Path(self.config_file).exists():
            log.info("Config file does not exist. Creating.")
            return self._safe_write_json(self.config_file, self.patcher_settings)

        settings: dict = self._safe_read_json(self.config_file)
        if settings is None:
            log.info(f"Unable to read config file {self.config_file}. Creating new one")
            return self._safe_write_json(self.config_file, self.patcher_settings)

        # Get all valid keys from ENUM
        valid_main_keys = {
            getattr(self.ENUM, attr)
            for attr in dir(self.ENUM)
            if not attr.startswith("_") and isinstance(getattr(self.ENUM, attr), str)
        }

        log.debug(f"{valid_main_keys=}")

        # Remove unused keys
        for setting in reversed(list(settings.keys())):
            if setting not in valid_main_keys:
                settings.pop(setting)
                log.debug(f"Cleared unused settings key: {setting}")

        # Add missing settings
        for k, v in self.patcher_settings.items():
            if k not in settings:
                settings[k] = v
                log.info(f"Added {k}: {v}")

        return self._safe_write_json(self.config_file, settings)

    def save_config(self):
        if not self.config_dir:
            self.config_dir = self.get_config_dir()

        os.makedirs(str(self.config_dir), exist_ok=True)
        result = self._safe_write_json(self.config_file, self.patcher_settings)
        if result:
            log.debug(f"Saved config to {self.config_file}")
        return result

    def load_config(self):
        if self.config_dir == "" or not Path(self.config_dir).exists() or not Path(self.config_file).exists():
            log.debug(f"Config does not exist.")
            return False

        self.clean_save_file()

        log.debug(f"Loading config from {self.config_dir}")
        log.debug(f"Config file: {self.config_file}")

        settings = self._safe_read_json(self.config_file)

        log.debug(json.dumps(settings, indent=2))

        if settings is None:
            log.info("Generating new config file")
            self.save_config()
            return False

        # Load settings to class
        self.patcher_settings.update(settings)

        log.debug(f"Loaded config: {self.patcher_settings}")
        return True

    def get_config_dir(self) -> Path:
        if not self.config_dir or not Path(self.config_dir).exists():
            return Path(os.path.dirname(sys.executable))

        return self.config_dir

    def _safe_read_json(self, fp):
        try:
            if not Path(fp).exists():
                return None

            _encoding = detect_file_encoding(fp)

            with open(fp, "r", encoding=_encoding) as file:
                content = file.read()
                if not content.strip():
                    return None
                return json.loads(content)
        except json.JSONDecodeError as e:
            log.error(f"Json decode error reading file: {e}")

            backup_path = f"{fp}.baddecode"
            shutil.copy2(fp, backup_path)
            log.info(f"Backed up bad file to {backup_path}")
            return None
        except Exception as e:
            log.error(f"Error reading config file: {e}")
            return None

    def _safe_write_json(self, fp: Path, data):
        if not isinstance(fp, Path):
            fp = Path(fp)

        # Ensure directory exists
        if not fp.parent.exists():
            fp.parent.mkdir(parents=True, exist_ok=True)

        # Write to temporary first
        temp_file = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=str(fp.parent), delete=False)

        log.debug(f"Created temporary file: {temp_file.name}")

        try:
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            temp_file.write(json_str)
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_file.close()

            # Rename the temp file to the target file (atomic)
            shutil.move(temp_file.name, fp)
            return True
        except Exception as e:
            log.error(f"Error writing config file: {e}")
            try:
                os.unlink(temp_file.name)
                log.info(f"Unlink: {temp_file.name}")
            except:
                pass
            return False
