from . import *

logger = Logger(dev=True)

# KEY_LOCAL_MACHINE
# STELLARIS_STEAM_APP_REGISTRY_PATH = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Steam App 281990'
GAME_INSTALL_LOCATION_KEY = 'InstallLocation'

# KEY_LOCAL_MACHINE
STEAM_REGISTRY_PATH_32 = 'SOFTWARE\Valve\Steam'
STEAM_REGISTRY_PATH_64 = 'SOFTWARE\WOW6432Node\Valve\Steam'
STEAM_INSTALL_LOCATION_KEY ='InstallPath'
STEAM_STEAMAPPS_FOLDER = 'steamapps'
STEAM_APP_MANIFEST_FILE_PREFIX = 'appmanifest'
STEAM_LIBRARY_FOLDERS_FILE_TRAIL = 'config\libraryfolders.vdf' # Trail to join to steam install main path

# IN ORDER TO GET A MORE ACCURATE INSTALL PATH FOR GAMES, A FEW STEPS MUST BE COMPLETED FIRST
# https://stackoverflow.com/questions/34090258/find-steam-games-folder

# 1. VIA REGISTRY LOCATE STEAM INSTALL FOLDER
# 2. GET THE STEAM LIBRARIES TO KNOW WHERE steamapps IS AND TO BE ABLE TO PARSE EVERY MANIFEST
# 2. IF YOU DON'T KNOW HOW THE APP ID, SEARCH IN steamapps FOLDER, EVERY MANIFEST, AND THERE IS A name PARAMETER.
# 3. KNOWING THE APP ID, PARSE libraryfolders.vdf FOR EACH USER LIBRARY AND CHECK IF THE APP ID IS IN THE LIST OF GAMES OF THAT LIBRARY
# 4. KNOWING THE LIBRARY PATH WE CAN WITH MORE CONFIDENCE NAVIGATE TO ...path\to\library\steamapps\common\Game Folder Name (installdir parameter in the game's appmanifest)
# 5. THEN SIMPLY GRAB THE EXE FROM THERE.

class SteamHelper:
    def __init__(self):
        self.steam_install = None
        self.steam_library_paths = []

    def get_steam_install_path(self):
        logger.log('Acquiring Steam installation...')
        
        # Try 64-bit first
        steam = registry_helper.read_key(STEAM_REGISTRY_PATH_64, STEAM_INSTALL_LOCATION_KEY)
        
        # Try 32-bit if 64 failed.
        if not steam:
            steam = registry_helper.read_key(STEAM_REGISTRY_PATH_32, STEAM_INSTALL_LOCATION_KEY)
        
        if steam:
            self.steam_install = steam
        else:
            logger.log_error('Unable to acquire Steam installation.')
        
        return steam
    
    def __vdf_line_contains(self, vdf_line, argument_to_check) -> list:
        vdf_line = str(vdf_line).lstrip().rstrip()
        # logger.log_debug(f'{str(argument_to_check).upper()} in {vdf_line.upper()} = {str(argument_to_check).upper() in vdf_line.upper()}')
        if str(argument_to_check).upper() in vdf_line.upper():
            return vdf_line.split('"')
        
        return None
    
    def get_from_vdf_file(self, vdf_file, key) -> list:
        with open(vdf_file, 'r') as f:
            lines = f.readlines()
            
        values_out = []
            
        for line in lines:
            line = line.lstrip().rstrip()
            
            value = self.__vdf_line_contains(line, key)
            
            if value:
                for v in value:
                    values_out.append(v)
        
        return values_out
    
    def get_steam_libraries(self):
        logger.log('Getting available Steam Libraries...')
        
        if not self.steam_install:
            self.steam_install = self.get_steam_install_path()
            if not self.steam_install:
                return False
    
        library_file = os.path.join(self.steam_install, STEAM_LIBRARY_FOLDERS_FILE_TRAIL)
        
        if not os.path.exists(library_file):
            logger.log_error('Could not locate Steam Library file.')
            return False
        
        path_list = self.get_from_vdf_file(library_file, '"PATH"')
        if path_list:
            # So far, path seems to be in the 2nd index of the list but let's iterate over list and check for valid path
            for item in path_list:
                if os.path.isdir(item):
                    item = os.path.join(item, STEAM_STEAMAPPS_FOLDER)
                    if item not in self.steam_library_paths:
                        self.steam_library_paths.append(os.path.abspath(item))
        
        logger.log_debug(f'Known paths: {self.steam_library_paths}')
            
        return self.steam_library_paths
    
    def __get_game_install_info_from_name(self, game_name) -> dict:
        # Parse Steam appmanifests
        
        logger.log(f'Getting installation details for game: {game_name}')
        
        if not self.steam_install:
            self.steam_install = self.get_steam_install_path()
            if not self.steam_install:
                return False
        
        if not self.steam_library_paths:
            self.steam_library_paths = self.get_steam_libraries()
            if not self.steam_library_paths or self.steam_library_paths == []:
                logger.log_error('No Steam Libraries found.')
                return False
        
        for lib in self.steam_library_paths:
            for file in os.listdir(lib):
                fname = file
                file = os.path.join(lib, fname)
                
                if not os.path.isfile(file):
                    continue
                
                if not STEAM_APP_MANIFEST_FILE_PREFIX in fname:
                    continue
                
                line_app_id = self.get_from_vdf_file(file, '"appid"')
                line_name = self.get_from_vdf_file(file, '"name"')
                    
                # Value to look for seems to always be in index 3
                title = line_name[3]
                app_id = line_app_id[3]
                if title == game_name:
                    logger.log_debug(f'Found title match: {title} with App Id {app_id} in {fname} in library {lib}')
                    logger.log(f'Found game install in {os.path.join(lib, f"common/{title}")}'.replace('/', '\\'))
                    return {
                        'title': title,
                        'app-id': app_id,
                        'steam-library': lib
                    }
        
        logger.log_error(f'Unable to determine installation information for {game_name}')
        return {}
        
    def get_game_install_path(self, game_name) -> os.path:
        logger.log('Acquiring Stellaris installation...')
        
        install_details = self.__get_game_install_info_from_name(game_name)
        
        if not install_details:
            return False
        
        title_name = install_details.get('title')
        install_folder = os.path.join(install_details.get('steam-library'), f'common/{title_name}')
        
        logger.log
        
        return install_folder
        