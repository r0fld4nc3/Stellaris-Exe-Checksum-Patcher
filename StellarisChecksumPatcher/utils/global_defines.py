import sys
import os
import pathlib
import platform

_system = platform.system()
debug_commands = ("-debug", "-d")

if _system == "Windows":
    sys_drive = os.getenv("SystemDrive")
    config_folder = pathlib.Path(sys_drive) / r"\ProgramData" / "r0fld4nc3" / "Apps" / "Stellaris" / "ChecksumPatcher"
elif _system == "Linux" or _system == "Darwin":
    sys_drive = pathlib.Path("usr/bin/r0fld4nc3")
    config_folder = pathlib.Path(sys_drive) / "Apps" / "Stellaris" / "ChecksumPatcher"
else:
    sys_drive = pathlib.Path.cwd()
    config_folder = pathlib.Path(sys_drive) / r"\r0fld4nc3" / "Apps" / "Stellaris" / "ChecksumPatcher"

from logger.Logger import Logger

if len(sys.argv) > 1 and str(sys.argv[1]).lower() in debug_commands:
    is_debug = True
else:
    is_debug = False
logger = Logger(is_debug=is_debug, logger_name="StellarisChecksumPatcherLogger")

from updater.updater import Updater
updater = Updater()

from settings.settings import Settings
settings = Settings()
