from . import *
from typing import Union

# 3rd Party
from utils.global_defines import system
import vdf

# KEY_LOCAL_MACHINE
GAME_INSTALL_LOCATION_KEY = "InstallLocation"

# KEY_LOCAL_MACHINE
STEAM_REGISTRY_PATH_32 = "SOFTWARE\Valve\Steam"
STEAM_REGISTRY_PATH_64 = "SOFTWARE\WOW6432Node\Valve\Steam"
STEAM_INSTALL_LOCATION_KEY ="InstallPath"
STEAM_STEAMAPPS_FOLDER = "steamapps"
STEAM_APP_MANIFEST_FILE_PREFIX = "appmanifest"
STEAM_LIBRARY_FOLDERS_FILE_TRAIL = "config\libraryfolders.vdf" # Trail to join to steam install main path

LINUX_DISTRO_PATHS = [
    os.path.join(os.path.expanduser('~'), ".steam"),
    os.path.join(os.path.expanduser('~'), ".local/share/Steam"),
    os.path.join(os.path.expanduser('~'), ".var/app/com.valvesoftware.Steam/.local/share/Steam"),
]

class SteamHelper:
    def __init__(self):
        self.steam_install = None
        self.steam_library_paths = []

    @staticmethod
    def _vdf_line_contains(vdf_line, argument_to_check) -> list:
        vdf_line = str(vdf_line).lstrip().rstrip()
        logger.debug(f"{vdf_line} contains {argument_to_check}")
        # logger.log_debug(f"{str(argument_to_check).upper()} in {vdf_line.upper()} = {str(argument_to_check).upper() in vdf_line.upper()}")
        if str(argument_to_check).upper() in vdf_line.upper():
            return vdf_line.split('"')

        return []

    def get_game_install_info_from_name(self, game_name) -> dict:
        # Parse Steam appmanifests (.acf files)

        logger.info(f"Getting installation details for game: {game_name}")

        if not self.steam_install:
            self.steam_install = self.get_steam_install_path()
            if not self.steam_install:
                return {}

        logger.debug(f"Steam install path: {self.steam_install}")

        if not self.steam_library_paths:
            self.steam_library_paths = self.get_steam_libraries()
            if not self.steam_library_paths or self.steam_library_paths == []:
                logger.error("No Steam Libraries found.")
                return {}

        logger.debug(f"Steam library paths: {self.steam_library_paths}")

        for lib in self.steam_library_paths:
            logger.write_to_log_file('')
            logger.debug(f"Checking Library \"{lib}\"")
            for file in os.listdir(lib):
                fname = file
                file = os.path.join(lib, fname)

                if not os.path.isfile(file):
                    logger.debug(f"{file} is not a file.")
                    continue

                if not STEAM_APP_MANIFEST_FILE_PREFIX in fname:
                    continue

                app_id = self.get_from_vdf_file(file, "appid")[0] # List of AppIDs
                title = self.get_from_vdf_file(file, "name")[0] # 1 Name

                # Value to look for seems to always be in index 3
                # title = line_name[3]
                # app_id = line_app_id[3]
                logger.debug(f"{app_id}: {title}")
                if title == game_name:
                    logger.debug(f"Found title match: {title} with App Id {app_id} in {fname} in library {lib}")
                    logger.info(f'Found game install in {os.path.join(lib, f"common/{title}")}'.replace('/', '\\'))
                    logger.write_to_log_file('')
                    return {
                        "title": title,
                        "app-id": app_id,
                        "steam-library": lib
                    }

        logger.error(f"Unable to determine installation information for {game_name}")
        logger.write_to_log_file('')
        return {}

    def recursive_dict_find_value(self, dict_to_find, key_to_find, stop_on_find=False):
        matches = []
        for key, val in dict_to_find.items():
            # if isinstance(val, dict):
            #     logger.debug(f"\n{key}: {json.dumps(val, indent=2)}")
            # else:
            #     logger.debug(f"{key}: {val}")
            if key == key_to_find:
                matches.append(val)
                logger.debug(f"Found {val} in {key}")
                if stop_on_find:
                    return matches
            elif isinstance(val, dict):
                recurse_matches = self.recursive_dict_find_value(val, key_to_find)
                if recurse_matches is not None:
                    matches.extend([f"{k_value}" for k_value in recurse_matches])
        return matches

    def get_from_vdf_file(self, vdf_file, key, stop_on_find=False) -> list:
        """
        Retrieve values from Steam's .vdf and .acf files.

        :param vdf_file:
        :param key:
        :param stop_on_find:
        :return: A list of matching parameters.
        """

        logger.debug(f"From {pathlib.Path(vdf_file).name} getting values of {key}")

        vdf_fh = vdf.load(open(vdf_file))
        values_out = self.recursive_dict_find_value(vdf_fh, key, stop_on_find)

        # for k, v in vdf_fh.items():
        #     print(f"{k=}: {v=}")
        #
        # values_out = []
        #
        # for line in vdf_fh:
        #     line = line.lstrip().rstrip()
        #
        #     value = self._vdf_line_contains(line, key)
        #
        #     if value:
        #         for v in value:
        #             values_out.append(v)

        logger.debug(f"Out values: {values_out}")
        logger.write_to_log_file('')
        return values_out

    def get_steam_libraries(self) -> Union[list, bool]:
        logger.info("Getting available Steam Libraries...")

        if not self.steam_install:
            self.steam_install = self.get_steam_install_path()
            if not self.steam_install:
                return False

        library_file = os.path.join(self.steam_install, STEAM_LIBRARY_FOLDERS_FILE_TRAIL)

        if not os.path.exists(library_file):
            logger.error("Could not locate Steam Library file.")
            return False

        path_list = self.get_from_vdf_file(library_file, "path")

        if not path_list:
            return False

        # So far, path seems to be in the 2nd index of the list but let's iterate over list and check for valid path
        for item in path_list:
            if os.path.isdir(item):
                item = os.path.join(item, STEAM_STEAMAPPS_FOLDER)
                if item not in self.steam_library_paths:
                    self.steam_library_paths.append(os.path.abspath(item))

        logger.debug(f"Known paths: {self.steam_library_paths}")

        return self.steam_library_paths

    def get_game_install_path(self, game_name) -> Union[str, bool]:
        logger.info("Acquiring Stellaris installation...")

        install_details = self.get_game_install_info_from_name(game_name)

        if not install_details:
            return False

        title_name = install_details.get("title")
        install_folder = os.path.join(install_details.get("steam-library"), f"common\\{title_name}")

        return install_folder

    def get_steam_install_path(self) -> str:
        logger.info("Acquiring Steam installation...")

        if system == "Windows":
            # Try 64-bit first
            steam = registry_helper.read_key(STEAM_REGISTRY_PATH_64, STEAM_INSTALL_LOCATION_KEY)

            # Try 32-bit if 64 failed.
            if not steam:
                steam = registry_helper.read_key(STEAM_REGISTRY_PATH_32, STEAM_INSTALL_LOCATION_KEY)
        elif system == "Linux" or system == "Darwin":
            home_steam = ''
            steam = None
            libraryfolders_vdf_file = "libraryfolders.vdf"

            for distro_path in LINUX_DISTRO_PATHS:
                if pathlib.Path(distro_path).exists():
                    home_steam = distro_path
                    print(f"Found: {home_steam}")
                    break

            if not home_steam:
                print("Count not find Steam install.")
                return ''

            print("Locating for Linux\\Unix\\Darwin system. Please be patient, could take a bit.")
            for root, dirs, files in os.walk(home_steam):
                root += 1
                os.system("clear")
                if libraryfolders_vdf_file in files:
                    steam = pathlib.Path(root) / libraryfolders_vdf_file
        else:
            steam = None

        if steam:
            self.steam_install = steam
        else:
            logger.error("Unable to acquire Steam installation.")
        
        return steam
        