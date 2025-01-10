import sys
from io import StringIO

from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, QRunnable, QThread, Slot, Signal, QCoreApplication

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


def set_icon_gray(icon: QIcon, size=(32, 32)):
    """
    Converts a QIcon to a grayed out version by applying a grayscale filter.

    :param icon: QIcon to be grayed out.
    :param size: Tuple (width, height) for the size of the QPixmap
    :return: QIcon with a grayscale effect
    """

    pixmap = icon.pixmap(size[0], size[1])

    gray_pixmap = QPixmap(pixmap.size())
    gray_pixmap.fill(QColor("transparent")) # Background is transparent

    # QPainter to apply the filter
    painter = QPainter(gray_pixmap)
    painter.drawPixmap(0, 0, pixmap) # Draw original
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(gray_pixmap.rect(), QColor("gray")) # Apply the colour filter
    painter.end()

    return QIcon(gray_pixmap)


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
