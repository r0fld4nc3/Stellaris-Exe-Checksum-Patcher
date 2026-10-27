from collections.abc import Generator
from contextlib import contextmanager

from PySide6.QtCore import QObject


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
