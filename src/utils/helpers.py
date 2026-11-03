import logging
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


def get_fpath_size(fp: Path) -> int:
    """Size of a file or folder in bytes."""
    try:
        if fp.is_dir():
            return sum(f.stat().st_size for f in fp.rglob("*") if f.is_file())
        return fp.stat().st_size
    except OSError:
        return 0


def format_size(size: int) -> str:
    """Size in bytes as a short readable string, e.g. `93 MB`."""
    for unit in ("B", "KB", "MB"):
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


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
