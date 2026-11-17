"""
This run of the app: how it was started (folders, build type, command line flags)
and what it learns while running.

Kept in memory only, never saved, lost on quit. For the user's choices, use settings.
Built by `app.bootstrap.start()`. Reach it through `services().config`.

State of one window or dialog doesn't belong here, it belongs to that window (ex.: `OptionsContext.store_paths`).
"""

import json
import logging
import sys
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Optional

from .paths import get_os_env_config_folder


@dataclass
class AppConfig:
    config_dir: Path
    log_file: Path

    working_dir: Path = None
    frozen: bool = False

    debug: bool = False
    prevent_conn: bool = False
    prevent_settings_save: bool = False
    log_level: int = logging.INFO
    update_check_cooldown: int = 60
    use_local_patterns: bool = False  # Force use of only local patterns file. If True will override user choice.

    def dump(self) -> dict:
        values = {}

        for class_field in fields(self):
            if class_field.name.startswith("_"):
                continue

            values[class_field.name] = getattr(self, class_field.name)

        return values

    def dump_json(self) -> str:
        """`dump()` as indented JSON text."""
        return json.dumps(self.dump(), indent=2, default=str)


def build(app_name: str, app_author: str = "", working_dir: Optional[Path] = None) -> AppConfig:
    config_dir = Path(get_os_env_config_folder() / app_author / app_name)
    log_file = config_dir / f"{app_name}.log"

    # App Frozen? (Compiled)
    is_frozen: bool = getattr(sys, "frozen", False) or "__compiled__" in globals()

    # Ensure dirs exist early (or do it lazily when writing)
    config_dir.mkdir(parents=True, exist_ok=True)

    return AppConfig(config_dir, log_file, working_dir=working_dir, frozen=is_frozen)
