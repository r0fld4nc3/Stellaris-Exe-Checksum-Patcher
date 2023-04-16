import json
import os
import pathlib

from utils.global_defines import logger, config_folder

class Settings:
    def __init__(self):
        self.patcher_settings = {
                "app-version": "",
                "install-dir": "",
                "save-games-dir": "",
        }
        self._config_file_name = "stellaris-checksum-patcher-settings.json"
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

    def save_config(self):
        if config_folder == '' or not pathlib.Path(config_folder).exists():
            os.makedirs(config_folder)
            logger.debug(f"Generated config folder {config_folder}")

        with open(self.config_file, 'w') as config_file:
            config_file.write(json.dumps(self.patcher_settings, indent=2))
            logger.debug(f"Saved config to {self.config_file}")

    def load_config(self):
        if config_folder == '' or not pathlib.Path(config_folder).exists()\
                or not pathlib.Path(self.config_file).exists():
            logger.debug(f"Config does not exists.")
            return False

        logger.debug(f"Loading config from {config_folder}")
        config_error = False
        with open(self.config_file, 'r') as config_file:
            try:
                self.patcher_settings = json.load(config_file)
            except Exception as e:
                logger.error("An error occurred trying to read config file.")
                logger.error(e)
                config_error = True

        if config_error:
            logger.info("Generating new config file.")
            with open(self.config_file, 'w') as config_file:
                config_file.write(json.dumps(self.patcher_settings, indent=2))
        logger.debug(self.patcher_settings)