import platform
import argparse

system = platform.system()
debug_commands = ("-debug", "-d")

# Argparser
_parser = argparse.ArgumentParser(description="Application Startup")

_parser.add_argument(
    "-d", "--debug",
    action="store_true",
    help="Enable debug mode and expose more debugging information"
)

_args = _parser.parse_args()

APP_VERSION = [2, 0, 0]
HOST: str = "r0fld4nc3"
APP_FOLDER: str = "Apps"
APP_NAME: str = "StellarisChecksumPatcher"
LOG_LEVEL = 1
IS_DEBUG = False
UPDATE_CHECK_COOLDOWN = 60 # seconds

# Parse debug mode and set flags related to it
if LOG_LEVEL == 0 or _args.debug:
    IS_DEBUG = True
    LOG_LEVEL = 0


class OS:
    WINDOWS = system.lower() == "windows"
    LINUX = system.lower() in ["linux", "unix"]
    LINUX_PROTON = False  # Special Case
    MACOS = system.lower() in ["darwin", "mac"]


from logger.path_helpers import win_get_localappdata
config_folder = win_get_localappdata() / HOST / APP_NAME


# Because we're using the config folder defined here, in the logger class and import
# We have to import the logger after
from logger import create_logger

log = create_logger("Globals", LOG_LEVEL)
log.info(f"[INIT] Running Stellaris-Exe-Checksum-Patcher.")
# Print flags
for action in _parser._actions:
    if action.option_strings:
        if "-h" in action.option_strings or "--help" in action.option_strings:
            continue
        log.info(f"[INIT] Run with flag {action.option_strings}: {action.help}")

from updater import Updater
updater = Updater("r0fld4nc3", "Stellaris-Exe-Checksum-Patcher")

from settings import Settings
settings = Settings()
settings.load_config()

from utils import steam_helper

steam = steam_helper.SteamHelper()

# Worker Signals hook not initialised here yet, so won't print to GUI console
log.info(f"Debug:             {IS_DEBUG}")
log.info(f"App Version:       {APP_VERSION}")
log.info(f"Target System:     {system}")
log.info(f"Config Folder:     {config_folder}")
