import logging
import sys
from pathlib import Path
from typing import Optional

from .definitions import AppConfig
from .path_helpers import get_os_env_config_folder

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
