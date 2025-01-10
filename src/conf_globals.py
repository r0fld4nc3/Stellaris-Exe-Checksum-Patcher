import sys
import pathlib
import platform

APP_VERSION = [1, 1, 0, "pre"]

system = platform.system()
debug_commands = ("-debug", "-d")

Path = pathlib.Path
HOST: str = "r0fld4nc3"
APP_FOLDER: str = "Apps"
APP_NAME: str = "StellarisChecksumPatcher"


class OS:
    WINDOWS = system.lower() == "windows"
    LINUX = system.lower() in ["linux", "unix"]
    MACOS = system.lower() in ["darwin", "mac"]

from logger.path_helpers import win_get_localappdata
config_folder = win_get_localappdata() / HOST / APP_NAME

LOG_LEVEL = 0
if len(sys.argv) > 1 and str(sys.argv[1]).lower() in debug_commands:
    is_debug = True
    LOG_LEVEL = 0
    APP_VERSION.append("debug") # Yes, I allow changing of the CONST here, since it's a one time startup change
else:
    is_debug = False

# Because we're using the config folder defined here, in the logger class and import
# We have to import the logger after
from logger import create_logger

log = create_logger("Globals", LOG_LEVEL)

from updater import Updater
updater = Updater("r0fld4nc3", "Stellaris-Exe-Checksum-Patcher")

from settings import Settings
settings = Settings()
settings.load_config()

from utils import steam_helper

steam = steam_helper.SteamHelper()

# Worker Signals hook not initialised here yet, so won't print to GUI console
log.info(f"Debug:             {is_debug}")
log.info(f"App Version:       {APP_VERSION}")
log.info(f"Target System:     {system}")
log.info(f"Config Folder:     {config_folder}")
