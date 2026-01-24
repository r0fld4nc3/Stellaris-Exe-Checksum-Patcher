import platform

from utils.argument_parse import ARGUMENTS, PARSER

APP_VERSION = [2, 1, 0]
HOST: str = "r0fld4nc3"
APP_FOLDER: str = "Apps"
APP_NAME: str = "StellarisChecksumPatcher"
REPO_BRANCH: str = "dev"
TRACKING_BRANCH: str = f"more-save-options"
LOG_LEVEL = 1
IS_DEBUG = False
UPDATE_CHECK_COOLDOWN = 60  # seconds
USE_LOCAL_PATTERNS = False  # Force use of only local patterns file. If True will override user choice.
SUPPORTED_GAMES = ("Stellaris",)

# --- Connections ---
PREVENT_CONN = False
if ARGUMENTS.no_conn:
    PREVENT_CONN = True
    USE_LOCAL_PATTERNS = True

# --- Updater ---
REPO_OWNER = HOST
REPO_NAME = "Stellaris-Exe-Checksum-Patcher"

# Parse debug mode and set flags related to it
if LOG_LEVEL == 0 or ARGUMENTS.debug:
    IS_DEBUG = True
    LOG_LEVEL = 0

system = platform.system()


class OS:
    WINDOWS = system.lower() == "windows"
    LINUX = system.lower() in ["linux", "unix"]
    LINUX_PROTON = False  # Special Case
    MACOS = system.lower() in ["darwin", "mac"]


from logger.path_helpers import win_get_localappdata

CONFIG_FOLDER = win_get_localappdata() / HOST / APP_NAME


log = None
updater = None
SETTINGS = None
STEAM = None


def __init_logging():
    """
    Jaaaaaaaank
    """
    global log
    from logger import create_logger, reset_log_file

    log = create_logger("Globals", LOG_LEVEL)

    if not IS_DEBUG:
        reset_log_file()

    log.info(f"[INIT] Running Application.")

    log.info(f"Debug:                  {IS_DEBUG}")
    log.info(f"App Version:            {APP_VERSION}")
    log.info(f"Target System:          {system}")
    log.info(f"Config Folder:          {CONFIG_FOLDER}")
    log.info(f"Prevent Connections:    {PREVENT_CONN}")
    log.info(f"Use Local Patterns:     {USE_LOCAL_PATTERNS}")

    # Print flags
    for action in PARSER._actions:
        if action.option_strings:
            if "-h" in action.option_strings or "--help" in action.option_strings:
                continue
            log.info(f"[INIT] Run with flag {action.option_strings}: {action.help}")


def __init_updater():
    global updater
    from updater import Updater

    updater = Updater(REPO_OWNER, REPO_NAME)


def __init_settings():
    global SETTINGS
    from settings import SettingsManager

    SETTINGS = SettingsManager()
    SETTINGS.load()


def __init_steam_helper():
    global STEAM
    from utils import steam_helper

    STEAM = steam_helper.SteamHelper()


def init_globals():
    __init_updater()
    __init_settings()
    __init_steam_helper()
    __init_logging()
