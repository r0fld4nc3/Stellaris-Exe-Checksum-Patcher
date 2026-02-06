import logging
from dataclasses import dataclass
from pathlib import Path

APP_VERSION = [2, 1, 1]
HOST: str = "r0fld4nc3"
APP_FOLDER: str = "Apps"
APP_NAME: str = "StellarisChecksumPatcher"

REPO_BRANCH: str = "dev"
TRACKING_BRANCH: str = "pyinstaller"

SUPPORTED_GAMES = ("Stellaris",)

# --- Updater ---
REPO_OWNER = HOST
REPO_NAME = "Stellaris-Exe-Checksum-Patcher"


class OS_TYPE:
    WINDOWS = "Windows"
    LINUX = "Linux"
    DARWIN = "Darwin"


@dataclass
class AppConfig:
    config_dir: Path
    saves_backup_dir: Path

    # runtime
    use_proton: bool = False
    working_dir: Path = None
    frozen: bool = False

    is_cheated_save: bool = False

    debug: bool = False
    prevent_conn: bool = False
    log_file: Path = Path.home() / HOST / APP_NAME / f"{APP_NAME}.log"
    log_level: int = logging.INFO
    update_check_cooldown: int = 60
    use_local_patterns: bool = False  # Force use of only local patterns file. If True will override user choice.
