from PySide6.QtCore import QObject, QThread, Signal


class ThreadSignals(QObject):
    """Lifecycle of one `Threader` run. Connected slots run on the main thread, so they can update widgets."""

    started = Signal()
    finished = Signal()  # Always emitted, after `result` or `error`
    result = Signal(object)  # The target's return value. Not emitted if it raised
    error = Signal(tuple)  # (exception type, exception, formatted traceback)


class Threader(QThread):
    """Run `target(*args, **kwargs)` on a separate thread and report back through `signals`."""

    def __init__(self, target, args=(), kwargs=None) -> None:
        self.signals = ThreadSignals()

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
