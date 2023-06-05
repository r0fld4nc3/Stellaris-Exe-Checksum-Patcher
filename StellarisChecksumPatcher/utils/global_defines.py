import sys
import os
import pathlib
import platform

APP_VERSION = ['r', 1, 1, 0] # To add more arguments after the rX.Y.Z, always have the '-' suffix before. Example ['r', 0, 0, 1, "-dev", "-nightly"]

system = platform.system()
debug_commands = ("-debug", "-d")

if system == "Windows":
    print("Target System Windows")
    sys_drive = os.getenv("LOCALAPPDATA")
    config_folder = pathlib.Path(sys_drive + "\\r0fld4nc3\\Apps\\Stellaris\\ChecksumPatcher")
elif system == "Linux" or system == "Darwin":
    print("Target System Linux")
    sys_drive = pathlib.Path("/var/log")
    config_folder = pathlib.Path(sys_drive) / "StellarisChecksumPatcher"
else:
    print("Target System Other")
    print(system)
    sys_drive = pathlib.Path.cwd()
    config_folder = pathlib.Path(sys_drive) / r"\r0fld4nc3" / "Apps" / "Stellaris" / "ChecksumPatcher"

from logger.Logger import Logger

if len(sys.argv) > 1 and str(sys.argv[1]).lower() in debug_commands:
    is_debug = True
    APP_VERSION.append("-debug") # Yes, I allow changing of the CONST here, since it's a one time startup change
    print(f"Sys Drive: {sys_drive}")
    print(f"Config Folder: {config_folder}")
else:
    is_debug = False

logger = Logger(is_debug=is_debug, logger_name="StellarisChecksumPatcherLogger")

from updater.updater import Updater
updater = Updater()

from settings.settings import Settings
settings = Settings()
