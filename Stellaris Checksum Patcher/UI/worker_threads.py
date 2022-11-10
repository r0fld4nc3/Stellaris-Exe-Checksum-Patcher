from PySide6.QtCore import QObject, QRunnable, Slot, Signal

class WorkerSignals(QObject):
    finished_signal = Signal()
    progress_signal = Signal(str)
    terminal_progress = Signal(str)
    fail_signal = Signal()

class Worker(QRunnable):
    def __init__(self, target=None, args=(), kwargs=None) -> None:
        super().__init__()
        self.signals = WorkerSignals()
        
        self._target = target
        self._args = args
        self._kwargs = kwargs

    @Slot()
    def run(self):
        """Long-running task."""
        if self._target:
            if self._kwargs is None:
                self._kwargs = {}
            self._target(*self._args, *self._kwargs)
        self.signals.finished_signal.emit()