"""
Backups of a game executable.

A backup sits next to what was backed up and is named after it:
`<name>-<timestamp>.orig` now, `<name>_<timestamp>.orig` or `<name>.orig` in older versions.

On macOS the executable is inside a bundle (a `.app` folder), and the whole bundle is backed up.
"""

import datetime
import logging
import re
import shutil
from pathlib import Path
from typing import List, Optional, Union

log = logging.getLogger("Backups")

DEFAULT_MAX_BACKUPS = 1


def find_backups(binary_path: Union[Path, str], bundle_root: Optional[Path] = None) -> List[Path]:
    """
    Backups made of the game binary at `binary_path`, oldest first.

    `bundle_root` is the bundle (ex.: macOS .app) containing the binary, if inside one.

    The whole bundle is backed up.
    """
    binary_path = Path(binary_path)

    targets = [binary_path]
    if bundle_root:
        targets.append(bundle_root)

    backups: List[Path] = []
    for target in targets:
        folder = target.parent
        if not folder.is_dir():
            continue

        pattern = re.compile(rf"^{re.escape(target.name)}([-_].+)?\.orig$", re.IGNORECASE)
        try:
            for item in folder.iterdir():
                if pattern.match(item.name):
                    backups.append(item)
        except OSError as e:
            log.warning(f"Unable to list backups in '{folder}': {e}")

    backups = sorted(set(backups), key=lambda item: item.stat().st_mtime)
    log.debug(f"Binary backups of '{binary_path}': {backups}")
    return backups


def create_backup(target: Path, max_allowed_backups: int) -> bool:
    """
    Create a timestamped backup next to `target`.
    Removing the oldest backups over `max_allowed_backups`.
    Returns False if the backup couldn't be made.
    """
    # If max is 0, don't create or delete any backups
    if max_allowed_backups <= 0:
        log.info(f"Backup creation disabled (max_allowed_binary_backups = {max_allowed_backups})", silent=True)
        return True

    _delete_old_backups(target, max_allowed_backups)

    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    backup_path = Path(f"{target}-{timestamp_str}.orig")

    try:
        # macOS .app bundles are folders
        if target.is_dir():
            if backup_path.exists():
                shutil.rmtree(backup_path)
            shutil.copytree(target, backup_path)
        else:
            shutil.copy2(target, backup_path)

        log.info(f"Create backup: {backup_path}")
        return True
    except Exception as e:
        log.error(f"Failed to create backup: {e}")
        return False


def _delete_old_backups(target: Path, max_allowed_backups: int) -> None:
    """Delete the oldest backups of `target`."""
    log.info(f"Deleting backups if reached or over max allowed: {max_allowed_backups}", silent=True)
    log.info(f"Processing backups of: {target}", silent=True)

    # Only backups of this target, so backups of other files in the folder keep their own limit
    backups = find_backups(target)

    if len(backups) < max_allowed_backups:
        log.info(f"No backups to delete, found {len(backups)}/{max_allowed_backups}")
        return

    log.info(f"Sorted backups: {backups}", silent=True)

    num_to_keep = max_allowed_backups - 1
    num_to_delete = len(backups) - num_to_keep
    log.info(f"Keep {num_to_keep}, Delete {num_to_delete}", silent=True)

    for backup_item in backups[:num_to_delete]:
        log.info(f"Remove: '{backup_item}", silent=True)
        try:
            # macOS .app backups are folders
            if backup_item.is_dir():
                shutil.rmtree(backup_item)
            else:
                backup_item.unlink()
        except Exception as e:
            log.warning(f"Failed to delete backup: '{backup_item}': {e}")
