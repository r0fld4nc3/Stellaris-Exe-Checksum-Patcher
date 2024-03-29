import sys
import os
import pathlib
import platform

_system = platform.system()
debug_commands = ("-debug", "-d")

if _system == "Windows":
    print("Target System Windows")
    sys_drive = os.getenv("LOCALAPPDATA")
    config_folder = pathlib.Path(sys_drive + "\\r0fld4nc3\\Apps\\Stellaris\\ChecksumPatcher")
elif _system == "Linux" or _system == "Darwin":
    print("Target System Linux")
    sys_drive = pathlib.Path("usr/bin/r0fld4nc3")
    config_folder = pathlib.Path(sys_drive) / "Apps" / "Stellaris" / "ChecksumPatcher"
else:
    print("Target System Other")
    print(_system)
    sys_drive = pathlib.Path.cwd()
    config_folder = pathlib.Path(sys_drive) / r"\r0fld4nc3" / "Apps" / "Stellaris" / "ChecksumPatcher"

from logger.Logger import Logger

if len(sys.argv) > 1 and str(sys.argv[1]).lower() in debug_commands:
    is_debug = True
    print(f"Sys Drive: {sys_drive}")
    print(f"Config Folder: {config_folder}")
else:
    is_debug = False

logger = Logger(is_debug=is_debug, logger_name="StellarisChecksumPatcherLogger")

from updater.updater import Updater
updater = Updater()

from settings.settings import Settings
settings = Settings()
