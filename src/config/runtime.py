import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .definitions import APP_NAME, HOST
from .path_helpers import get_os_env_config_folder


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


_current_app_config: Optional[AppConfig] = None


def build(
    app_name: str,
    app_author: str = "",
    working_dir: Optional[Path] = None,
    log_level: int = logging.INFO,
    debug: bool = False,
) -> AppConfig:
    config_dir = Path(get_os_env_config_folder() / app_author / app_name)
    saves_backup_dir = Path(get_os_env_config_folder() / app_author / app_name / "saves_backup")

    # App Frozen? (Compiled)
    is_frozen: bool = getattr(sys, "frozen", False) or "__compiled__" in globals()

    # Ensure dirs exist early (or do it lazily when writing)
    config_dir.mkdir(parents=True, exist_ok=True)

    return AppConfig(
        config_dir, saves_backup_dir, working_dir=working_dir, log_level=log_level, debug=debug, frozen=is_frozen
    )


def init(cfg: AppConfig) -> Optional[AppConfig]:
    global _current_app_config

    if _current_app_config is not None:
        if not isinstance(_current_app_config, AppConfig):
            return _current_app_config
        else:
            # Intentionally Raise if mismatched type
            raise RuntimeError(f"Configuration instance is invalid: {_current_app_config}")
    _current_app_config = cfg

    return _current_app_config


def get_config() -> Optional[AppConfig]:
    if _current_app_config is None:
        raise RuntimeError("Configuration not initialised.")

    if not isinstance(_current_app_config, AppConfig):
        # Intentionally Raise if mismatched type
        raise RuntimeError(f"Configuration instance is invalid: {_current_app_config}")

    return _current_app_config
