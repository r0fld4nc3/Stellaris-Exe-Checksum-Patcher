import json
import os
import pathlib
import sys

from utils.global_defines import logger, config_folder


class Settings:
    def __init__(self):
        self.patcher_settings = {
                "app-version": "",
                "install-dir": "",
                "save-games-dir": "",
                "patched-block": "",
        }
        self._config_file_name = "stellaris-checksum-patcher-settings.json"
        self.config_dir = pathlib.Path(config_folder)
        self.config_file = pathlib.Path(config_folder) / self._config_file_name

    def set_app_version(self, version: str):
        self.patcher_settings["app-version"] = version
        self.save_config()

    def get_app_version(self):
        self.load_config()
        v = self.patcher_settings.get("app-version")
        return v

    def set_install_location(self, install_path) -> None:
        self.patcher_settings["install-dir"] = install_path
        self.save_config()

    def get_install_location(self) -> str:
        self.load_config()
        i = self.patcher_settings.get("install-dir")
        return i

    def set_executable_name(self, executable_name: str):
        self.patcher_settings["exe-name"] = executable_name
        self.save_config()

    def get_executable_name(self) -> str:
        self.load_config()
        name = self.patcher_settings.get("exe-name")

        return name

    def get_save_games_dir(self) -> str:
        self.load_config()
        s = self.patcher_settings.get("save-games-dir")
        return s

    def set_save_games_dir(self, save_games_dir: str):
        self.patcher_settings["save-games-dir"] = str(save_games_dir)
        self.save_config()

    def get_patched_block(self) -> str:
        self.load_config()
        s = self.patcher_settings.get("patched-block")
        return s

    def set_patched_block(self, str_to_set: str):
        self.patcher_settings["patched-block"] = str(str_to_set)
        self.save_config()

    def clean_save_file(self):
        """
        Removes unused keys from the save file.
        :return: `bool`
        """

        if not self.config_dir or not pathlib.Path(self.config_dir).exists():
            logger.info("No config folder found.")
            return False

        with open(self.config_file, 'r', encoding="utf-8") as config_file:
            settings = dict(json.load(config_file))

        for setting in reversed(list(settings.keys())):
            if setting not in self.patcher_settings.keys():
                settings.pop(setting)
                logger.debug(f"Cleared unused settings key: {setting}")

        with open(self.config_file, 'w', encoding="utf-8") as config_file:
            config_file.write(json.dumps(settings, indent=2))
            logger.debug(f"Saved cleaned config: {self.config_file}")

        return True

    def save_config(self):
        if self.config_dir == '' or not pathlib.Path(self.config_dir).exists():
            os.makedirs(self.config_dir)
            logger.debug(f"Generated config folder {self.config_dir}")

        with open(self.config_file, 'w', encoding="utf-8") as config_file:
            config_file.write(json.dumps(self.patcher_settings, indent=2))
            logger.debug(f"Saved config to {self.config_file}")

    def load_config(self):
        if self.config_dir == '' or not pathlib.Path(self.config_dir).exists()\
                or not pathlib.Path(self.config_file).exists():
            logger.debug(f"Config does not exist.")
            return False

        self.clean_save_file()

        logger.debug(f"Loading config from {self.config_dir}")
        config_error = False
        with open(self.config_file, 'r', encoding="utf-8") as config_file:
            try:
                self.patcher_settings = json.load(config_file)
            except Exception as e:
                logger.error("An error occurred trying to read config file.")
                logger.error(e)
                config_error = True

        if config_error:
            logger.info("Generating new config file.")
            with open(self.config_file, 'w', encoding="utf-8") as config_file:
                config_file.write(json.dumps(self.patcher_settings, indent=2))
        logger.debug(self.patcher_settings)

    def get_config_dir(self) -> pathlib.Path:
        if not self.config_dir or not pathlib.Path(self.config_dir).exists:
            return pathlib.Path(os.path.dirname(sys.executable))

        return self.config_dir
