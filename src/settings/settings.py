import json
import os
from pathlib import Path
import sys

from conf_globals import config_folder, LOG_LEVEL
from logger import create_logger

log = create_logger("Settings", LOG_LEVEL)


class Settings:
    class ENUM:
        APP_VERSION = "app-version"
        UPDATE_LAST_CHECKED = "update-last-checked"
        UPDATE_AVAILABLE = "update-available"
        WINDOW_WIDTH = "window-width"
        WINDOW_HEIGHT = "window-height"
        STELLARIS_INSTALL_PATH = "stellaris-install-path"
        STELLARIS_PROTON_INSTALL_PATH = "stellaris-proton-install-path"
        STEAM_INSTALL_PATH = "steam-install-path"
        SAVE_GAMES_PATH = "save-games-path"
        PATCHED_BLOCK = "patched-block"
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
        self.patcher_settings[self.ENUM.STELLARIS_INSTALL_PATH] = install_path.replace('\\', '/').replace('\\\\', '/')
        log.info(f"Saving Stellaris install location: {self.patcher_settings.get(self.ENUM.STELLARIS_PROTON_INSTALL_PATH)}")
        self.save_config()

    def get_stellaris_install_path(self) -> str:
        # self.load_config()
        return self.patcher_settings.get(self.ENUM.STELLARIS_INSTALL_PATH)

    def set_stellaris_proton_install_path(self, install_path) -> None:
        self.patcher_settings[self.ENUM.STELLARIS_PROTON_INSTALL_PATH] = install_path.replace('\\', '/').replace('\\\\', '/')
        log.info(f"Saving Stellaris (Proton) install location: {self.patcher_settings.get(self.ENUM.STELLARIS_PROTON_INSTALL_PATH)}")
        self.save_config()

    def get_stellaris_proton_install_path(self) -> str:
        # self.load_config()
        return self.patcher_settings.get(self.ENUM.STELLARIS_PROTON_INSTALL_PATH)

    def set_steam_install_path(self, install_path) -> None:
        self.patcher_settings[self.ENUM.STEAM_INSTALL_PATH] = install_path.replace('\\', '/').replace('\\\\', '/')
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
        self.patcher_settings[self.ENUM.SAVE_GAMES_PATH] = str(save_games_dir).replace('\\', '/').replace('\\\\', '/')
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
        return self.patcher_settings.get(self.ENUM.UPDATE_LAST_CHECKED)

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

    def clean_save_file(self):
        """
        Removes unused keys from the save file.
        :return: `bool`
        """

        if not self.config_dir or not Path(self.config_dir).exists():
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
        if self.config_dir == '' or not Path(self.config_dir).exists():
            os.makedirs(self.config_dir)
            log.debug(f"Generated config folder {self.config_dir}")

        with open(self.config_file, 'w', encoding="utf-8") as config_file:
            config_file.write(json.dumps(self.patcher_settings, indent=2))
            log.debug(f"Saved config to {self.config_file}")

    def load_config(self):
        if self.config_dir == '' or not Path(self.config_dir).exists()\
                or not Path(self.config_file).exists():
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

    def get_config_dir(self) -> Path:
        if not self.config_dir or not Path(self.config_dir).exists:
            return Path(os.path.dirname(sys.executable))

        return self.config_dir
