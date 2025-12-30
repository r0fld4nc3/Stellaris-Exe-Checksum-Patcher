# built-ins
import json
import os
import subprocess
from pathlib import Path
from typing import Optional, Union

import vdf

from app_ids import APP_IDS
from conf_globals import LOG_LEVEL, OS, SETTINGS
from logger import create_logger
from utils import registry_helper
from utils.encodings import safe_read_file_encode

log = create_logger("Steam Helper", LOG_LEVEL)

# KEY_LOCAL_MACHINE
STEAM_REGISTRY_PATH_32 = r"SOFTWARE\Valve\Steam"
STEAM_REGISTRY_PATH_64 = r"SOFTWARE\WOW6432Node\Valve\Steam"

# Constants for Steam Paths and Folders
STEAM_INSTALL_LOCATION_KEY = "InstallPath"
STEAM_STEAMAPPS_FOLDER = "steamapps"
STEAM_APP_ID_FILE_NAME = "steam_appid.txt"

# Constants for common folder names
STEAM_CONFIG_FOLDER = "config"
STEAM_COMMON_FOLDER = "common"
STEAM_APP_MANIFEST_FILE_PREFIX = "appmanifest"
LIBRARY_FOLDERS_VDF_FILE = "libraryfolders.vdf"

# Constants for VDF Keys
VDF_APPID_KEY = "appid"
VDF_NAME_KEY = "name"
VDF_PATH_KEY = "path"

# Constants for Direct Steam Client Invokation
STEAM_CLIENT_INVOKE_URL = "steam://"
STEAM_CLIENT_INVOKE_VALIDATE = "validate"
STEAM_CLIENT_INVOKE_RUN = "rungameid"
STEAM_CLIENT_INVOKE_RUN_DIALOG = "launch"

LINUX_DISTRO_PATHS = [
    # Standard location
    Path.home() / ".steam" / "steam",
    Path.home() / ".steam" / "steam" / "steamapps",
    Path.home() / ".local" / "share" / "Steam",
    Path.home() / ".local" / "share" / "Steam" / "config",
    # Flatpak
    Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam",
]

MACOS_DISTRO_PATHS = [Path.home() / "Library" / "Application Support" / "Steam"]


class SteamHelper:
    def __init__(self):
        self.steam_install: Optional[Path] = None
        self.steam_library_paths: list[Path] = []

    def get_game_install_info_from_name(self, game_name) -> dict:
        # Parse Steam appmanifests (.acf files) in case of windows
        # For linux, get libraries and find the installation folder

        log.info(f"Getting installation details for game: {game_name}")

        if not self.steam_install:
            self.steam_install = self.get_steam_install_path()
            if not self.steam_install:
                return {}

        log.info(f"Steam install path: {self.steam_install}")

        if not self.steam_library_paths:
            self.steam_library_paths = self.get_steam_libraries()
            if not self.steam_library_paths or self.steam_library_paths == []:
                log.error("No Steam Libraries found.")
                return {}

        if not self.steam_library_paths:
            self.steam_library_paths = self.get_steam_libraries()
            if not self.steam_library_paths:
                log.error(f"No Steam Libraries found.")
                return {}

        log.info(f"Steam Library paths: {self.steam_library_paths}", silent=True)

        for lib in self.steam_library_paths:
            log.info(f'Checking Library "{lib}"')
            for file in lib.iterdir():
                if not file.is_file() or STEAM_APP_MANIFEST_FILE_PREFIX not in file.name:
                    continue

                app_ids = self.get_from_vdf_file(file, VDF_APPID_KEY)
                titles = self.get_from_vdf_file(file, VDF_NAME_KEY)

                if not app_ids or not titles:
                    log.debug(f"Could not find required keys 'appid' or 'name' in {file.name}")
                    continue

                app_id = app_ids[0]  # List of AppIDs
                title = titles[0]  # 1 Name

                # Value to look for seems to always be in index 3
                # title = line_name[3]
                # app_id = line_app_id[3]
                log.debug(f"{app_id}: {title}", silent=True)
                if title == game_name:
                    log.debug(f"Found title match: {title} with App Id {app_id} in {file.name} in library {lib}")
                    game_path: Path = lib / STEAM_COMMON_FOLDER / title
                    log.info(f"Found game install in {game_path.as_posix()}")
                    return {"title": title, "app-id": app_id, "steam-library": lib}

        log.error(f"Unable to determine installation information for {game_name}")
        return {}

    def get_from_vdf_file(self, vdf_file: Union[str, Path], key: str, stop_on_find: bool = False) -> list:
        """
        Retrieve values from Steam's .vdf and .acf files.

        :param vdf_file:
        :param key:
        :param stop_on_find:
        :return: A list of matching parameters.
        """

        # Enforce vdf_file type
        if not isinstance(vdf_file, Path):
            vdf_file = Path(vdf_file)

        log.debug(f'From {vdf_file.name} getting values of key "{key}"')

        try:
            file_content = safe_read_file_encode(vdf_file)
            if file_content is None:
                log.error(f"Could not read VDF file: {vdf_file}")
                return []

            try:
                vdf_data = vdf.loads(file_content)
            except Exception as e:
                log.error(f"Error parsing VDF content: {e}")
                # Try binary mode as fallback
                try:
                    vdf_data = vdf.load(open(vdf_file, "rb"))
                except Exception as e2:
                    log.error(f"Failed binary fallback for VDF parsing: {e2}")
                    return []

            values_out = self._recursive_dict_find_value(vdf_data, key, stop_on_find)
            log.info(f"Gathered: {values_out}", silent=True)
            return values_out

        except Exception as e:
            log.error(f"Unexpected error processing VDF file {vdf_file}: {e}")
            return []

    def _recursive_dict_find_value(self, dict_to_find, key_to_find, stop_on_find=False):
        matches = []
        for key, val in dict_to_find.items():
            if isinstance(val, dict):
                log.debug(f"\n{key}: {json.dumps(val, indent=2)}")
            else:
                log.debug(f"{key}: {val}")

            if key == key_to_find:
                matches.append(val)
                log.debug(f"Found {val} in {key}")
                if stop_on_find:
                    return matches
            elif isinstance(val, dict):
                recurse_matches = self._recursive_dict_find_value(val, key_to_find)
                if recurse_matches is not None:
                    matches.extend([f"{k_value}" for k_value in recurse_matches])
        return matches

    def _find_library_folders_vdf(self) -> Optional[Path]:
        """Checks potential locations for libraryfolders.vdf and returns the path if foind"""
        if not self.steam_install:
            return None

        potential_paths = [
            self.steam_install / STEAM_STEAMAPPS_FOLDER / LIBRARY_FOLDERS_VDF_FILE,
            self.steam_install / STEAM_CONFIG_FOLDER / LIBRARY_FOLDERS_VDF_FILE,
        ]

        for path in potential_paths:
            if path.exists():
                log.info(f"Found library folders file at: {path}")
                return path

        log.warning(f"Unable to locate {LIBRARY_FOLDERS_VDF_FILE}.")
        return None

    def get_steam_libraries(self) -> list[Path]:
        log.info("Getting available Steam Libraries...")

        if not self.steam_install:
            self.steam_install = self.get_steam_install_path()
            if not self.steam_install:
                return []

        # Always fallback to default steamapps folder
        default_library_path = (self.steam_install / STEAM_STEAMAPPS_FOLDER).resolve()
        if default_library_path.is_dir() and default_library_path not in self.steam_library_paths:
            resolved_path = default_library_path.resolve()
            self.steam_library_paths.append(resolved_path)
            log.info(f"Added default Steam library: {resolved_path}", silent=True)

        # Find and parse libraryfolders.vdf
        library_file = self._find_library_folders_vdf()
        if not library_file:
            return self.steam_library_paths

        path_list = self.get_from_vdf_file(library_file, VDF_PATH_KEY)
        if not path_list:
            log.warning(f"No additional library paths found in {library_file}.", silent=True)
            return self.steam_library_paths

        for item_str in path_list:
            item = Path(item_str)
            if item.is_dir():
                library_path = (item / STEAM_STEAMAPPS_FOLDER).resolve()
                if library_path not in self.steam_library_paths:
                    self.steam_library_paths.append(library_path)

        log.info(f"Final known library paths: {self.steam_library_paths}", silent=True)
        return self.steam_library_paths

    def get_game_install_path(self, game_name) -> Optional[Path]:
        log.info(f"Acquiring {game_name} installation...")

        install_details = self.get_game_install_info_from_name(game_name)

        if not install_details:
            return None

        log.info(f"{install_details=}", silent=True)

        title_name = install_details.get("title")
        library = install_details.get("steam-library")

        return Path(library) / STEAM_COMMON_FOLDER / title_name

    def get_steam_install_path(self) -> Optional[Path]:
        log.info("Acquiring Steam installation...")

        saved_path_str = SETTINGS.settings.steam_install_path
        if saved_path_str:
            saved_path = Path(saved_path_str)
            if saved_path.exists():
                self.steam_install = saved_path
                log.info(f"Got Steam install path from Settings")
                return self.steam_install

        steam_path_str: Optional[str] = None

        if OS.WINDOWS:
            # Try 64-bit first
            steam_path_str = registry_helper.read_key(STEAM_REGISTRY_PATH_64, STEAM_INSTALL_LOCATION_KEY)

            # Try 32-bit if 64 failed.
            if not steam_path_str:
                steam_path_str = registry_helper.read_key(STEAM_REGISTRY_PATH_32, STEAM_INSTALL_LOCATION_KEY)
        elif OS.LINUX:
            search_paths = LINUX_DISTRO_PATHS
            for distro_path in search_paths:
                if Path(distro_path).exists():
                    steam_path_str = str(distro_path)
                    break
        elif OS.MACOS:
            search_paths = MACOS_DISTRO_PATHS
            for distro_path in search_paths:
                if Path(distro_path).exists():
                    steam_path_str = str(distro_path)
                    break

        if steam_path_str:
            self.steam_install = Path(steam_path_str)
            SETTINGS.settings.steam_install_path = self.steam_install.resolve().as_posix()
            return self.steam_install
        else:
            log.error("Unable to acquire Steam installation.")
            return Path().home()

    def get_app_id_from_install_path(self, install_path: str | Path) -> str:
        if not isinstance(install_path, Path):
            log.info(f"Convert install path to Path instance: '{install_path}'", silent=True)
            install_path = Path(install_path)

        if install_path.exists() and install_path.is_file():
            log.info(f"Convert to directory: '{install_path}'", silent=True)
            install_path = install_path.parent  # Make it a dir
            log.info(f"Install path: '{install_path}'")
        else:
            path_attempt = install_path

            if not path_attempt.exists():
                log.warning(f"Path '{path_attempt}' does not exist. Is it a file that's missing?")

                path_attempt = path_attempt.parent
                if path_attempt.exists():
                    log.info(f"Path '{path_attempt}' converted to directory that exists.")
                    install_path = path_attempt

        if not install_path.exists() and not install_path.is_dir():
            log.error(f"Install path does not exist: {install_path}")
            return

        app_id_file = install_path / STEAM_APP_ID_FILE_NAME
        log.info(f"App ID File: {app_id_file}", silent=True)

        if not app_id_file.exists():
            log.error(f"App ID file does not exist: {app_id_file}")
            return

        log.info(f"Reading file: '{app_id_file}", silent=True)
        with open(app_id_file, "r", encoding="utf-8") as f:
            try:
                data = f.readline()
                log.info(data, silent=True)
            except Exception as e:
                log.error(f'Error reading file "{app_id_file}": {e}')
                data = None

        if data:
            app_id = data.strip()
        else:
            app_id = "-1"

        return app_id

    def validate_game_files_app_name(self, app_name: str) -> None:
        # Wrapper
        verify_game_files_app_name(app_name)

    def validate_game_files_app_id(self, app_id: int | str) -> None:
        # Wrapper
        validate_game_files_app_id(app_id)

    def launch_game_app_name(self, app_name: str) -> None:
        # Wrapper
        launch_game_app_name(app_name)

    def launch_game_app_id(self, app_id: int | str) -> None:
        # Wrapper
        launch_game_app_id(app_id)


def validate_game_files_app_id(app_id: int | str) -> None:
    steam_bin_win = SETTINGS.settings.steam_install_path + "/steam.exe"

    steam_cmd_url = f"{STEAM_CLIENT_INVOKE_URL}{STEAM_CLIENT_INVOKE_VALIDATE}/{app_id}"

    log.info(f"Calling Verify Game Files for App ID: {app_id}")
    log.info(f"Steam Validate Integrity Command: {steam_cmd_url}", silent=True)

    try:
        if OS.WINDOWS:
            # Windows specific flags for process detachment
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200

            if Path(steam_bin_win).exists():
                log.info(f"Attempting with Steam binary: {steam_bin_win} {steam_cmd_url}", silent=True)
                subprocess.Popen(
                    [steam_bin_win, steam_cmd_url],
                    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                    close_fds=True,
                )
            else:
                log.info(f"Attempting with os.startfile({steam_cmd_url})", silent=True)
                # Fallback: Let OS handle the protocol
                os.startfile(steam_cmd_url)
        elif OS.LINUX:
            subprocess.Popen(
                ["xdg-open", steam_cmd_url],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
        elif OS.MACOS:
            subprocess.Popen(
                ["open", steam_cmd_url],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )

    except Exception as e:
        log.error(f"Error calling game files verification: {e}")


def verify_game_files_app_name(app_name: str) -> None:
    app_id = APP_IDS.get(app_name, -1)

    if app_id == -1:
        log.error(f"Unable to find App ID for app name: {app_name} -> {app_id}")
        return

    validate_game_files_app_id(app_id)


def launch_game_app_id(app_id: int | str) -> None:
    steam_bin = SETTINGS.settings.steam_install_path
    steam_cmd_url = f"{STEAM_CLIENT_INVOKE_URL}{STEAM_CLIENT_INVOKE_RUN}/{app_id}"

    log.info(f"Launching game with App ID: {app_id}")
    log.info(f"Steam Launch Command: {steam_cmd_url}", silent=True)

    try:
        if OS.WINDOWS:
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200

            if steam_bin:
                subprocess.Popen(
                    [steam_bin, steam_cmd_url],
                    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                    close_fds=True,
                )
            else:
                os.startfile(steam_cmd_url)
        elif OS.LINUX:
            subprocess.Popen(
                ["xdg-open", steam_cmd_url],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
        elif OS.MACOS:
            subprocess.Popen(
                ["open", steam_cmd_url],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )

    except Exception as e:
        log.error(f"Error launching game: {e}")


def launch_game_app_name(app_name: str) -> None:
    app_id = APP_IDS.get(app_name, -1)

    if app_id == -1:
        log.error(f"Unable to find App ID for app name: {app_name} -> {app_id}")
        return

    launch_game_app_id(app_id)
