import logging
from dataclasses import dataclass
from pathlib import Path

APP_VERSION = [3, 0, 0]

# Display form of APP_VERSION, ex.:
# [3, 0, 0] -> "v3.0.0"
# [3, 0, 0, "beta", 1] -> "v3.0.0-beta-1"
APP_VERSION_STR: str = "v" + ".".join(str(v) for v in APP_VERSION[0:3])
if len(APP_VERSION) > 3:
    APP_VERSION_STR += "-" + "-".join(str(v) for v in APP_VERSION[3:])

HOST: str = "r0fld4nc3"
APP_FOLDER: str = "Apps"
APP_NAME: str = "StellarisChecksumPatcher"

REPO_BRANCH: str = "v3"  # Used for APIs and remote requests
TRACKING_BRANCH: str = "v3-dev"  # Used for local tracking and visual indicators. No remote impact.

SUPPORTED_GAMES = ("Stellaris",)

# --- Updater ---
REPO_OWNER = HOST
REPO_NAME = "Stellaris-Exe-Checksum-Patcher"


class OS_TYPE:
    WINDOWS: str = "Windows"
    LINUX: str = "Linux"
    DARWIN: str = "Darwin"


class FILE_FORMAT:
    PE: str = "pe"
    ELF: str = "elf"
    MACHO: str = "macho"


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
