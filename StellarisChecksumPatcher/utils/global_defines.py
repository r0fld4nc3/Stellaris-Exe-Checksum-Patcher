import sys
import os
import pathlib
import platform
from threading import Lock

# To add more arguments after the rX.Y.Z, always have the '-' suffix before. Example ['r', 0, 0, 1, "-dev", "-nightly"]
APP_VERSION = ['r', 1, 1, 0]

system = platform.system()
debug_commands = ("-debug", "-d")

class SingletonMetaClass(type):
    """
        Thread-safe Singleton class
        """
    _instances = {}
    _lock = Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
            return cls._instances[cls]

# Probably overengineered way to have this display as a persistent thingy
# We don't actually call/initialise this class, but have it as a singleton just in case
class OS(metaclass=SingletonMetaClass):
    WINDOWS = False
    LINUX = False
    MACOS = False

def is_windows():
    if system == "Windows":
        OS.WINDOWS = True
        OS.LINUX = False
        OS.MACOS = False
        return True
    OS.WINDOWS = False
    return False

def is_linux():
    if system in ["Linux", "Unix"]:
        OS.WINDOWS = False
        OS.LINUX = True
        OS.MACOS = False
        return True
    OS.LINUX = False
    return False

def is_macos():
    if system == "Darwin":
        OS.WINDOWS = False
        OS.LINUX = False
        OS.MACOS = True
        return True
    OS.MACOS = False
    return False

if is_windows():
    print("Target System Windows")
    program_data_path = os.getenv("LOCALAPPDATA")
    config_folder = pathlib.Path(program_data_path + "\\r0fld4nc3\\Apps\\Stellaris\\ChecksumPatcher")
elif is_linux():
    print("Target System Linux/Unix")
    program_data_path = pathlib.Path("/usr/local/var/")
    config_folder = pathlib.Path(program_data_path) / "r0fld4nc3" / "Apps" / "Stellaris" / "ChecksumPatcher"
elif is_macos():
    # Write to user-writable locations, like ~/Applications
    program_data_path = pathlib.Path(pathlib.Path.home() / "Applications")
    config_folder = pathlib.Path(program_data_path) / "r0fld4nc3" / "Apps" / "Stellaris" / "ChecksumPatcher"
else:
    print("Target System Other")
    print(system)
    program_data_path = pathlib.Path.cwd()
    config_folder = pathlib.Path(program_data_path) / r"\r0fld4nc3" / "Apps" / "Stellaris" / "ChecksumPatcher"

if len(sys.argv) > 1 and str(sys.argv[1]).lower() in debug_commands:
    is_debug = True
    APP_VERSION.append("-debug") # Yes, I allow changing of the CONST here, since it's a one time startup change
else:
    is_debug = False

# Because we're using the config folder defined here, in the logger class and import
# We have to import the logger after
from logger.Logger import Logger
logger = Logger(is_debug=is_debug, logger_name="StellarisChecksumPatcherLogger")

from updater.updater import Updater
updater = Updater()

from settings.settings import Settings
settings = Settings()

from utils import steam_helper
steam = steam_helper.SteamHelper()

# Worker Signals hook not initialised here yet, so won't print to GUI console
logger.info(f"Debug:             {is_debug}")
logger.info(f"App Version:       {APP_VERSION}")
logger.info(f"Target System:     {system}")
logger.info(f"Program Data Path: {program_data_path}")
logger.info(f"Config Folder:     {config_folder}")
