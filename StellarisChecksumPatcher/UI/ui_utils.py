from . import *

from PySide6 import QtWidgets
from PySide6.QtCore import QObject, QRunnable, Slot, Signal


class Capturing(list):  # Deprecated and not used, here for simply backup reasons because it was really cool to figure it out.
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio  # free up some memory
        sys.stdout = self._stdout


def prompt_user_game_install_dialog():
    directory = QtWidgets.QFileDialog().getExistingDirectory(caption='Please choose Stellaris installation Folder...')

    return directory

class WorkerSignals(QObject):
    started = Signal()
    finished = Signal()
    progress = Signal(str)
    terminal_progress = Signal(str)
    failed = Signal()


class Worker(QRunnable):
    def __init__(self, target=None, args=(), kwargs=None) -> None:
        super().__init__()
        self.signals = WorkerSignals()

        self._target = target
        self._args = args
        self._kwargs = kwargs

    @Slot()
    def run(self):
        """Start task."""
        if self._target:
            if self._kwargs is None:
                self._kwargs = {}
            self.signals.started.emit()
            self._target(*self._args, *self._kwargs)
        self.signals.finished.emit()
