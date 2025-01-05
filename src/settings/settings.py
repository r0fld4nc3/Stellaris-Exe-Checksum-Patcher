import json
import os
import pathlib
import sys

from utils.global_defines import config_folder, LOG_LEVEL
from logger import create_logger

log = create_logger("Settings", LOG_LEVEL)

class Settings:
    def __init__(self):
        self.patcher_settings = {
            "app-version": "",
            "update-last-checked": 0,
            "update-available": False,
            "install-dir": "",
            "save-games-dir": "",
            "patched-block": "",
            "exe-name": ""
        }
        self._config_file_name = "stellaris-checksum-patcher-settings.json"
        self.config_dir = pathlib.Path(config_folder)
        self.config_file = pathlib.Path(config_folder) / self._config_file_name

    def set_app_version(self, version: str):
        self.patcher_settings["app-version"] = version
        self.save_config()

    def get_app_version(self):
        self.load_config()
        return self.patcher_settings.get("app-version")

    def set_install_location(self, install_path) -> None:
        self.patcher_settings["install-dir"] = install_path.replace('\\', '/').replace('\\\\', '/')
        self.save_config()

    def get_install_location(self) -> str:
        self.load_config()
        return self.patcher_settings.get("install-dir")

    def set_executable_name(self, executable_name: str):
        self.patcher_settings["exe-name"] = executable_name
        self.save_config()

    def get_executable_name(self) -> str:
        self.load_config()
        return self.patcher_settings.get("exe-name")

    def get_save_games_dir(self) -> str:
        self.load_config()
        return self.patcher_settings.get("save-games-dir")

    def set_save_games_dir(self, save_games_dir: str):
        self.patcher_settings["save-games-dir"] = str(save_games_dir).replace('\\', '/').replace('\\\\', '/')
        self.save_config()

    def get_patched_block(self) -> str:
        self.load_config()
        return self.patcher_settings.get("patched-block")

    def set_patched_block(self, str_to_set: str):
        self.patcher_settings["patched-block"] = str(str_to_set)
        self.save_config()

    def get_update_last_checked(self) -> int:
        self.load_config()
        return self.patcher_settings.get("update-last-checked")

    def set_update_last_checked(self, timestamp: int):
        self.patcher_settings["update-last-checked"] = int(timestamp)
        self.save_config()

    def get_has_update(self) -> bool:
        self.load_config()
        return self.patcher_settings.get("update-available")

    def set_has_update(self, bool_to_set: bool):
        self.patcher_settings["update-available"] = bool(bool_to_set)
        self.save_config()

    def clean_save_file(self):
        """
        Removes unused keys from the save file.
        :return: `bool`
        """

        if not self.config_dir or not pathlib.Path(self.config_dir).exists():
            log.info("No config folder found.")
            return False

        with open(self.config_file, 'r', encoding="utf-8") as config_file:
            settings = dict(json.load(config_file))

        for setting in reversed(list(settings.keys())):
            if setting not in self.patcher_settings.keys():
                settings.pop(setting)
                log.debug(f"Cleared unused settings key: {setting}")

        # Add non existant settings
        for k, v in self.patcher_settings.items():
            if k not in settings:
                settings[k] = v
                log.info(f"Added {k}: {v}")

        with open(self.config_file, 'w', encoding="utf-8") as config_file:
            config_file.write(json.dumps(settings, indent=2))
            log.debug(f"Saved cleaned config: {self.config_file}")

        return True

    def save_config(self):
        if self.config_dir == '' or not pathlib.Path(self.config_dir).exists():
            os.makedirs(self.config_dir)
            log.debug(f"Generated config folder {self.config_dir}")

        with open(self.config_file, 'w', encoding="utf-8") as config_file:
            config_file.write(json.dumps(self.patcher_settings, indent=2))
            log.debug(f"Saved config to {self.config_file}")

    def load_config(self):
        if self.config_dir == '' or not pathlib.Path(self.config_dir).exists()\
                or not pathlib.Path(self.config_file).exists():
            log.debug(f"Config does not exist.")
            return False

        self.clean_save_file()

        log.debug(f"Loading config from {self.config_dir}")
        config_error = False
        with open(self.config_file, 'r', encoding="utf-8") as config_file:
            try:
                self.patcher_settings = json.load(config_file)
            except Exception as e:
                log.error("An error occurred trying to read config file.")
                log.error(e)
                config_error = True

        if config_error:
            log.info("Generating new config file.")
            with open(self.config_file, 'w', encoding="utf-8") as config_file:
                config_file.write(json.dumps(self.patcher_settings, indent=2))
        log.debug(self.patcher_settings)

    def get_config_dir(self) -> pathlib.Path:
        if not self.config_dir or not pathlib.Path(self.config_dir).exists:
            return pathlib.Path(os.path.dirname(sys.executable))

        return self.config_dir
