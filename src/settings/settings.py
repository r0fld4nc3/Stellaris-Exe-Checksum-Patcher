import os  # isort: skip
import sys  # isort: skip
import json  # isort: skip
import shutil  # isort: skip
import tempfile  # isort: skip
from pathlib import Path  # isort: skip

from conf_globals import config_folder, LOG_LEVEL  # isort: skip
from logger import create_logger  # isort: skip
from utils.encodings import detect_file_encoding  # isort: skip

log = create_logger("Settings", LOG_LEVEL)


class Settings:
    class ENUM:
        APP_VERSION = "app-version"
        UPDATE_LAST_CHECKED = "update-last-checked"
        PATTERNS_UPDATE_LAST_CHECKED = "patch-patterns-update-last-checked"
        UPDATE_AVAILABLE = "update-available"
        WINDOW_WIDTH = "window-width"
        WINDOW_HEIGHT = "window-height"
        STELLARIS_INSTALL_PATH = "stellaris-install-path"
        STELLARIS_PROTON_INSTALL_PATH = "stellaris-proton-install-path"
        STEAM_INSTALL_PATH = "steam-install-path"
        SAVE_GAMES_PATH = "save-games-path"
        PATCHED_BLOCK = "patched-block"
        PATCHED_HASH = "patched-exe-hash"
        EXE_NAME = "exe-name"
        EXE_PROTON_NAME = "exe-proton-name"

    def __init__(self):
        self.patcher_settings = {
            self.ENUM.APP_VERSION: "",
            self.ENUM.UPDATE_LAST_CHECKED: 0,
            self.ENUM.UPDATE_AVAILABLE: False,
            self.ENUM.WINDOW_WIDTH: 0,
            self.ENUM.WINDOW_HEIGHT: 0,
            self.ENUM.STELLARIS_INSTALL_PATH: "",
            self.ENUM.STELLARIS_PROTON_INSTALL_PATH: "",
            self.ENUM.STEAM_INSTALL_PATH: "",
            self.ENUM.SAVE_GAMES_PATH: "",
            self.ENUM.PATCHED_BLOCK: "",
            self.ENUM.PATCHED_HASH: "",
            self.ENUM.EXE_NAME: "",
            self.ENUM.EXE_PROTON_NAME: "",
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
        log.info(f"Saving window width: {self.patcher_settings.get(self.ENUM.WINDOW_WIDTH)}")
        self.save_config()

    def get_window_width(self):
        # self.load_config()
        return self.patcher_settings.get(self.ENUM.WINDOW_WIDTH)

    def set_window_height(self, num: int):
        self.patcher_settings[self.ENUM.WINDOW_HEIGHT] = num
        log.info(f"Saving window height: {self.patcher_settings.get(self.ENUM.WINDOW_HEIGHT)}")
        self.save_config()

    def get_window_height(self):
        # self.load_config()
        return self.patcher_settings.get(self.ENUM.WINDOW_HEIGHT)

    def set_stellaris_install_path(self, install_path) -> None:
        self.patcher_settings[self.ENUM.STELLARIS_INSTALL_PATH] = install_path.replace("\\", "/").replace("\\\\", "/")
        log.info(
            f"Saving Stellaris install location: {self.patcher_settings.get(self.ENUM.STELLARIS_PROTON_INSTALL_PATH)}"
        )
        self.save_config()

    def get_stellaris_install_path(self) -> str:
        # self.load_config()
        return self.patcher_settings.get(self.ENUM.STELLARIS_INSTALL_PATH)

    def set_stellaris_proton_install_path(self, install_path) -> None:
        self.patcher_settings[self.ENUM.STELLARIS_PROTON_INSTALL_PATH] = install_path.replace("\\", "/").replace(
            "\\\\", "/"
        )
        log.info(
            f"Saving Stellaris (Proton) install location: {self.patcher_settings.get(self.ENUM.STELLARIS_PROTON_INSTALL_PATH)}"
        )
        self.save_config()

    def get_stellaris_proton_install_path(self) -> str:
        # self.load_config()
        return self.patcher_settings.get(self.ENUM.STELLARIS_PROTON_INSTALL_PATH)

    def set_steam_install_path(self, install_path) -> None:
        self.patcher_settings[self.ENUM.STEAM_INSTALL_PATH] = install_path.replace("\\", "/").replace("\\\\", "/")
        log.info(f"Saving Steam install path: {self.patcher_settings.get(self.ENUM.STEAM_INSTALL_PATH)}")
        self.save_config()

    def get_steam_install_path(self) -> str:
        # self.load_config()
        return self.patcher_settings.get(self.ENUM.STEAM_INSTALL_PATH)

    def set_executable_name(self, executable_name: str):
        self.patcher_settings[self.ENUM.EXE_NAME] = executable_name
        log.info(f"Saving executable name: {self.patcher_settings.get(self.ENUM.EXE_NAME)}")
        self.save_config()

    def get_executable_name(self) -> str:
        # self.load_config()
        return self.patcher_settings.get(self.ENUM.EXE_NAME)

    def set_executable_proton_name(self, executable_name: str):
        self.patcher_settings[self.ENUM.EXE_PROTON_NAME] = executable_name
        log.info(f"Saving executable (Proton) name: {self.patcher_settings.get(self.ENUM.EXE_PROTON_NAME)}")
        self.save_config()

    def get_executable_proton_name(self) -> str:
        # self.load_config()
        return self.patcher_settings.get(self.ENUM.EXE_PROTON_NAME)

    def get_save_games_dir(self) -> str:
        # self.load_config()
        return self.patcher_settings.get(self.ENUM.SAVE_GAMES_PATH)

    def set_save_games_dir(self, save_games_dir: str):
        self.patcher_settings[self.ENUM.SAVE_GAMES_PATH] = str(save_games_dir).replace("\\", "/").replace("\\\\", "/")
        log.info(f"Saving games directory: {self.patcher_settings.get(self.ENUM.SAVE_GAMES_PATH)}")
        self.save_config()

    def get_patched_block(self) -> str:
        # self.load_config()
        return self.patcher_settings.get(self.ENUM.PATCHED_BLOCK)

    def set_patched_block(self, str_to_set: str):
        self.patcher_settings[self.ENUM.PATCHED_BLOCK] = str(str_to_set)
        log.info(f"Saving patched block: {self.patcher_settings.get(self.ENUM.PATCHED_BLOCK)}")
        self.save_config()

    def get_update_last_checked(self) -> int:
        # self.load_config()
        return self.patcher_settings.get(self.ENUM.UPDATE_LAST_CHECKED, 0)

    def set_update_last_checked(self, timestamp: int):
        self.patcher_settings[self.ENUM.UPDATE_LAST_CHECKED] = int(timestamp)
        log.info(f"Saving update last checked: {self.patcher_settings.get(self.ENUM.UPDATE_LAST_CHECKED)}")
        self.save_config()

    def get_has_update(self) -> bool:
        # self.load_config()
        return self.patcher_settings.get(self.ENUM.UPDATE_AVAILABLE)

    def set_has_update(self, bool_to_set: bool):
        self.patcher_settings[self.ENUM.UPDATE_AVAILABLE] = bool(bool_to_set)
        log.info(f"Saving is update available: {self.patcher_settings.get(self.ENUM.UPDATE_AVAILABLE)}")
        self.save_config()

    def set_patched_hash(self, hash_str: str):
        self.patcher_settings[self.ENUM.PATCHED_HASH] = hash_str
        log.info(f"Saving patched hash: {hash_str}")
        self.save_config()

    def get_patched_hash(self) -> str:
        # self.load_config()
        return self.patcher_settings[self.ENUM.PATCHED_HASH]

    def get_patch_patterns_update_last_checked(self):
        # self.load_config()
        return self.patcher_settings.get(self.ENUM.PATTERNS_UPDATE_LAST_CHECKED, 0)

    def set_patch_patterns_update_last_checked(self, timestamp: int):
        self.patcher_settings[self.ENUM.PATTERNS_UPDATE_LAST_CHECKED] = int(timestamp)
        log.info(
            f"Saving patch patterns update last checked: {self.patcher_settings.get(self.ENUM.PATTERNS_UPDATE_LAST_CHECKED)}"
        )
        self.save_config()

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

        # Remove unused keys
        for setting in reversed(list(settings.keys())):
            if setting not in self.patcher_settings.keys():
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
        if settings is None:
            log.info("Generating new config file")
            self.save_config()
            return False

        # Load settings to class
        self.patcher_settings.update(settings)

        self.clean_save_file()

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

        log.info(f"Created temporary file: {temp_file.name}")

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
