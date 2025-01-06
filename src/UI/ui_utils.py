import sys
from io import StringIO

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, QRunnable, QThread, Slot, Signal, QCoreApplication


class Capturing(list):  # Deprecated, here for simply backup reasons because it was really cool to figure it out.
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio  # free up some memory
        sys.stdout = self._stdout


class WorkerSignals(QObject):
    started = Signal()
    finished = Signal()
    progress = Signal(str)
    terminal_progress = Signal(str)
    failed = Signal()
    sig_quit = Signal()


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


class Threader(QThread):
    def __init__(self, target, args=(), kwargs=None) -> None:
        self.signals = WorkerSignals()

        QThread.__init__(self)
        self._target = target
        self._args = args
        self._kwargs = kwargs

    def run(self):
        """Start Thread."""
        if self._target:
            if self._kwargs is None:
                self._kwargs = {}
            self.signals.started.emit()
            self._target(*self._args, *self._kwargs)
        self.signals.finished.emit()

    def stop(self):
        self.signals.sig_quit.emit()
        self.exit(0)


def get_screen_info(app: QApplication | QCoreApplication) -> tuple:
    # Get the primary screen
    screen = app.primaryScreen()

    # Screen resolution
    size = screen.size()
    width = size.width()
    height = size.height()

    # Scaling factor
    scale_f = screen.devicePixelRatio()

    return width, height, scale_f
