# built-ins
import json
import logging
from pathlib import Path
from typing import Optional, Union

import vdf

from core.paths import os_darwin, os_linux, os_windows
from core.services import services
from utils import registry_helper
from utils.encodings import safe_read_file_encode

from .base import StoreHelperBase
from .definitions import GameStore, SteamInstallInfo

log = logging.getLogger("Steam Helper")

# KEY_LOCAL_MACHINE
STEAM_REGISTRY_PATH_32 = r"SOFTWARE\Valve\Steam"
STEAM_REGISTRY_PATH_64 = r"SOFTWARE\WOW6432Node\Valve\Steam"

# Constants for Steam Paths and Folders
STEAM_INSTALL_LOCATION_KEY = "InstallPath"
STEAM_STEAMAPPS_FOLDER = "steamapps"
STEAM_APP_ID_FILE_NAME = "steam_appid.txt"
STEAM_EXECUTABLE_WINDOWS = "steam.exe"

# Constants for common folder names
STEAM_CONFIG_FOLDER = "config"
STEAM_COMMON_FOLDER = "common"
STEAM_APP_MANIFEST_FILE_PREFIX = "appmanifest"
LIBRARY_FOLDERS_VDF_FILE = "libraryfolders.vdf"
STEAM_COMPATDATA_FOLDER = "compatdata"  # Proton prefixes. One folder per AppId in each library.
PROTON_DOCUMENTS_PATH = Path("pfx") / "drive_c" / "users" / "steamuser" / "Documents"  # Inside a game prefix.

# Constants for VDF Keys
VDF_APPID_KEY = "appid"
VDF_NAME_KEY = "name"
VDF_PATH_KEY = "path"

# Constants for Direct Steam Client Invokation
STEAM_CLIENT_INVOKE_URL = "steam://"
STEAM_CLIENT_INVOKE_VALIDATE = "validate"
STEAM_CLIENT_INVOKE_RUN = "rungameid"

LINUX_DISTRO_PATHS = [
    # Standard locations
    Path.home() / ".steam" / "steam",
    Path.home() / ".local" / "share" / "Steam",
    # Flatpak
    Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam",
    # Snap
    Path.home() / "snap" / "steam" / "common" / ".local" / "share" / "Steam",
]

MACOS_DISTRO_PATHS = [Path.home() / "Library" / "Application Support" / "Steam"]


class SteamHelper(StoreHelperBase):
    def _game_install_info_in_library(self, library: Path, game_name: str) -> Optional[SteamInstallInfo]:
        """
        `game_name`'s install info from the appmanifests in `library` (a `steamapps` folder).
        None if it isn't there.
        """

        log.info(f"Checking Library '{library}'")

        for file in library.iterdir():
            # prefer 'startswith' over 'in' to skip some macOS "._appmanifest_*.acf" metadata files on non-Apple drives.
            if not file.is_file() or not file.name.lower().startswith(STEAM_APP_MANIFEST_FILE_PREFIX):
                continue

            app_ids = self.get_from_vdf_file(file, VDF_APPID_KEY)
            titles = self.get_from_vdf_file(file, VDF_NAME_KEY)

            if not app_ids or not titles:
                log.warning(f"Could not find required keys 'appid' or 'name' in {file.name}")
                continue

            app_id = app_ids[0]
            title = titles[0]

            log.debug(f"{app_id}: {title}", silent=True)
            if title == game_name:
                log.info(f"Found {title} (App Id {app_id} in Library {library}).")
                return SteamInstallInfo(title=title, app_id=app_id, library=library)

        return None

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

    def _find_library_folders_vdf(self, steam_folder: Path) -> Optional[Path]:
        """Checks potential locations for libraryfolders.vdf and returns the path if foind"""
        potential_paths = [
            steam_folder / STEAM_STEAMAPPS_FOLDER / LIBRARY_FOLDERS_VDF_FILE,
            steam_folder / STEAM_CONFIG_FOLDER / LIBRARY_FOLDERS_VDF_FILE,
        ]

        for path in potential_paths:
            if path.exists():
                log.info(f"Found library folders file at: {path}")
                return path

        log.warning(f"Unable to locate {LIBRARY_FOLDERS_VDF_FILE}.")
        return None

    def get_steam_libraries(self) -> list[Path]:
        """Every Steam library (its `steamapps` folder) of every Steam folder found, without duplicates."""
        log.info("Getting available Steam Libraries...")

        libraries: list[Path] = []
        for steam_folder in self.get_steam_install_paths():
            for library in self._libraries_of(steam_folder):
                if library not in libraries:
                    libraries.append(library)

        log.info(f"Final known library paths: {libraries}", silent=True)
        return libraries

    def _libraries_of(self, steam_folder: Path) -> list[Path]:
        """
        The libraries of one Steam folder, its own `steamapps` folder, and those listed in its libraryfolders.vdf.
        """
        libraries: list[Path] = []

        default_library = (steam_folder / STEAM_STEAMAPPS_FOLDER).resolve()
        if default_library.is_dir():
            libraries.append(default_library)

        library_file = self._find_library_folders_vdf(steam_folder)
        if not library_file:
            return libraries

        for path_str in self.get_from_vdf_file(library_file, VDF_PATH_KEY):
            library = (Path(path_str) / STEAM_STEAMAPPS_FOLDER).resolve()
            if library.is_dir() and library not in libraries:
                libraries.append(library)

        return libraries

    def get_game_install_paths(self, game_name: str) -> list[Path]:
        """
        Every folder `game_name` is installed in, across all Steam folders and libraries.

        Empty if none.
        """
        log.info(f"Acquiring {game_name} installation(s)...")

        install_paths: list[Path] = []
        for library in self.get_steam_libraries():
            install_info = self._game_install_info_in_library(library, game_name)
            if install_info:
                install_paths.append(Path(install_info.library) / STEAM_COMMON_FOLDER / install_info.title)

        if not install_paths:
            log.error(f"Unable to determine installation information for {game_name}")

        return install_paths

    def get_game_install_path(self, game_name) -> Optional[Path]:
        """
        The first folder `game_name` is installed in.
        """
        install_paths = self.get_game_install_paths(game_name)
        if not install_paths:
            return None
        return install_paths[0]

    def get_steam_install_paths(self) -> list[Path]:
        """
        Every Steam folder to search, without duplicates, the one set in General Utilities first (if it exists),
        then every Steam folder found on this system.

        Empty if none.
        """
        log.info("Acquiring Steam installation(s)...")

        candidates: list[Path] = []

        saved_path_str = services().settings.app_settings.steam_install_path
        if saved_path_str:
            candidates.append(Path(saved_path_str))

        candidates.extend(self._steam_folder_candidates())

        steam_folders: list[Path] = []
        for candidate in candidates:
            if not candidate.is_dir():
                continue

            # Different paths can be the same folder (~/.steam/steam links to ~/.local/share/Steam)
            steam_folder = candidate.resolve()
            if steam_folder not in steam_folders:
                steam_folders.append(steam_folder)

        if not steam_folders:
            log.error("Unable to acquire Steam installation.")
            return []

        log.info(f"Steam folder(s): {steam_folders}")
        return steam_folders

    def _steam_folder_candidates(self) -> list[Path]:
        """Where Steam may be installed on the system. Can not exist."""
        if os_windows():
            candidates: list[Path] = []
            for registry_path in (STEAM_REGISTRY_PATH_64, STEAM_REGISTRY_PATH_32):
                steam_path_str = registry_helper.read_key(registry_path, STEAM_INSTALL_LOCATION_KEY)
                if steam_path_str:
                    candidates.append(Path(steam_path_str))
            return candidates

        if os_linux():
            return LINUX_DISTRO_PATHS

        if os_darwin():
            return MACOS_DISTRO_PATHS

        return []

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
        with open(app_id_file, "r", encoding="utf-8-sig") as f:
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

    def get_app_id(self, game_name: str, binary_path: Optional[Path]) -> Optional[str]:
        """Steam App ID from the game's install folder, falling back to the known App IDs."""
        app_id = self.get_app_id_from_install_path(binary_path) if binary_path else None

        if not app_id or app_id == "-1":
            app_id = self.get_known_app_id(game_name)

        return app_id

    def get_known_app_id(self, game_name: str) -> Optional[str]:
        """Steam App ID for `game_name` from the known game IDs. None if unknown."""
        steam_info = GameStore.STEAM.game_info(game_name)
        if not steam_info:
            return None

        return str(steam_info.id)

    def get_proton_documents_folders(self, game_name: str) -> list[Path]:
        """
        The Windows Documents folder inside `game_name` Proton prefix, in every Steam library that has one.
        Empty on Windows (no Proton), or when the game was never run through Proton.
        """
        if os_windows():
            return []

        app_id = self.get_known_app_id(game_name)
        if not app_id:
            return []

        documents_folders = []
        for library in self.get_steam_libraries():
            documents_folder = library / STEAM_COMPATDATA_FOLDER / app_id / PROTON_DOCUMENTS_PATH
            if documents_folder.is_dir():
                documents_folders.append(documents_folder)

        return documents_folders

    def launch_game(self, game_name: str, binary_path: Optional[Path]) -> None:
        # Known store starts its own install of the game, so binary_path isn't needed
        app_id = self.get_known_app_id(game_name)

        if not app_id:
            log.error(f"Unable to find Steam App ID for: {game_name}")
            return

        self.launch_app_id(app_id)

    def validate_game_files(self, game_name: str, binary_path: Optional[Path]) -> bool:
        app_id = self.get_app_id(game_name, binary_path)

        # Don't touch any files unless Steam can actually restore them
        if not app_id:
            log.error(f"Unable to determine Steam App ID for '{game_name}'. Validation aborted.")
            return False

        # Remove the binary file before verifying, so Steam restores an unmodified copy
        if binary_path and binary_path.is_file():
            log.info(f"Removing game binary before verifying: {binary_path}")
            try:
                binary_path.unlink()
            except Exception as e:
                log.error(f"Failed to unlink game binary: {e}")

        self.validate_app_id(app_id)
        return True

    def validate_app_id(self, app_id: int | str) -> None:
        steam_cmd_url = f"{STEAM_CLIENT_INVOKE_URL}{STEAM_CLIENT_INVOKE_VALIDATE}/{app_id}"

        log.info(f"Calling Verify Game Files for App ID: {app_id}")
        log.info(f"Steam Validate Integrity Command: {steam_cmd_url}", silent=True)

        try:
            self.open_steam_url(steam_cmd_url)
        except Exception as e:
            log.error(f"Error calling game files verification: {e}")

    def launch_app_id(self, app_id: int | str) -> None:
        steam_cmd_url = f"{STEAM_CLIENT_INVOKE_URL}{STEAM_CLIENT_INVOKE_RUN}/{app_id}"

        log.info(f"Launching game with App ID: {app_id}")
        log.info(f"Steam Launch Command: {steam_cmd_url}", silent=True)

        try:
            self.open_steam_url(steam_cmd_url)
        except Exception as e:
            log.error(f"Error launching game: {e}")

    def open_steam_url(self, steam_cmd_url: str) -> None:
        """Open a steam:// URL: through steam.exe on Windows when it's found, otherwise with the system URL handler."""
        steam_exe = self.get_windows_steam_executable()

        if steam_exe:
            log.info(f"Attempting with Steam binary: {steam_exe} {steam_cmd_url}", silent=True)
            self.run_detached([str(steam_exe), steam_cmd_url])
            return

        # Let the OS handle the steam:// protocol
        log.info(f"Attempting with the system URL handler: {steam_cmd_url}", silent=True)
        self.open_url(steam_cmd_url)

    def get_windows_steam_executable(self) -> Optional[Path]:
        """steam.exe in the first Steam folder that has one. None when not on Windows, or when none is found."""
        if not os_windows():
            return None

        for steam_folder in self.get_steam_install_paths():
            steam_exe = steam_folder / STEAM_EXECUTABLE_WINDOWS
            if steam_exe.is_file():
                return steam_exe

        log.warning("Steam executable not found.")
        return None
