import logging
import re
import shutil
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from PySide6.QtCore import QObject

log = logging.getLogger("Helpers")


@contextmanager
def block_signals(*objects: QObject) -> Generator[None]:
    """
    Block Qt signals of one or more objects for the duration of the `with` block.

    Each object returns to the state it had before, so nesting or an already-blocked object stays blocked.
    Restored even if the block raises.
    """
    previous = [obj.blockSignals(True) for obj in objects]
    try:
        yield
    finally:
        for obj, was_blocked in zip(objects, previous):
            obj.blockSignals(was_blocked)


def find_binary_backups(binary_path: Path | str) -> list[Path]:
    """
    Backups the Patcher made of the game binary at `binary_path`, oldest first.

    Backups sit next to what was backed up and are named after it:
    `<name>-<timestamp>.orig` now, `<name>_<timestamp>.orig` or `<name>.orig` in older versions.
    On macOS the whole `.app` bundle is backed up, so backups of the bundle are included too.
    """
    binary_path = Path(binary_path)

    targets = [binary_path]
    # .../Game.app/Contents/MacOS/binary -> Game.app
    app_bundle = binary_path.parent.parent.parent
    if app_bundle.suffix.lower() == ".app":
        targets.append(app_bundle)

    backups: list[Path] = []
    for target in targets:
        folder = target.parent
        if not folder.is_dir():
            continue

        pattern = re.compile(rf"^{re.escape(target.name)}([-_].+)?\.orig$", re.IGNORECASE)
        try:
            backups.extend(item for item in folder.iterdir() if pattern.match(item.name))
        except OSError as e:
            log.warning(f"Unable to list backups in '{folder}': {e}")

    backups = sorted(set(backups), key=lambda item: item.stat().st_mtime)
    log.debug(f"Binary backups of '{binary_path}': {backups}")
    return backups


def get_fpath_size(fp: Path) -> int:
    """Size of a file or folder in bytes."""
    try:
        if fp.is_dir():
            return sum(f.stat().st_size for f in fp.rglob("*") if f.is_file())
        return fp.stat().st_size
    except OSError:
        return 0


def delete_fpaths(fpaths: list[Path]) -> tuple[list[Path], list[Path]]:
    """Delete file(s) and/or folder(s). Returns (deleted, failed)."""
    deleted: list[Path] = []
    failed: list[Path] = []

    for fp in fpaths:
        try:
            if fp.is_dir() and not fp.is_symlink():
                shutil.rmtree(fp)
            else:
                fp.unlink()
            log.info(f"Deleted: '{fp}'")
            deleted.append(fp)
        except OSError as e:
            log.error(f"Failed to delete '{fp}': {e}")
            failed.append(fp)

    return deleted, failed
