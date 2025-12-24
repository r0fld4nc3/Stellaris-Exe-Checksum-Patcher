from PySide6.QtCore import QObject, QThread, Signal


class WorkerSignals(QObject):
    started = Signal()
    finished = Signal()
    progress = Signal(str)
    terminal_progress = Signal(str)
    request_file_path = Signal()
    result = Signal(object)
    failed = Signal()
    sig_quit = Signal()
    error = Signal(tuple)


class Threader(QThread):
    def __init__(self, target, args=(), kwargs=None) -> None:
        self.signals = WorkerSignals()

        QThread.__init__(self)
        self._target = target
        self._args = args
        self._kwargs = kwargs if kwargs is not None else {}

    def run(self):
        """Start Thread."""

        try:
            if self._target:
                self.signals.started.emit()
                return_value = self._target(*self._args, **self._kwargs)

                self.signals.result.emit(return_value)
        except Exception as e:
            import traceback

            traceback.print_exc()
            err_info = (type(e), e, traceback.format_exc())
            self.signals.error.emit(err_info)
        finally:
            self.signals.finished.emit()

    def stop(self):
        if self.isRunning():
            self.requestInterruption()
            self.wait()
