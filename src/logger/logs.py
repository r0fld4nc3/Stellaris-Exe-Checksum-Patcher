import logging
from logging import FileHandler
from pathlib import Path

from config.definitions import APP_VERSION, TRACKING_BRANCH
from config.path_helpers import system
from config.runtime import get_config as get_app_cfg
from thread_utils import WorkerSignals


class LoggerWithSignals(logging.Logger):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.signals = WorkerSignals()

    def debug(self, msg, *args, silent=True, **kwargs):
        super().debug(msg, *args, **kwargs)
        if self.level < logging.INFO:
            if not silent:
                self.signals.progress.emit("[DEBUG] " + str(msg))

    def info(self, msg, *args, silent=False, **kwargs):
        super().info(msg, *args, **kwargs)
        if not silent:
            self.signals.progress.emit("[INFO] " + str(msg))

    def warning(self, msg, *args, silent=False, **kwargs):
        super().warning(msg, *args, **kwargs)
        if not silent:
            self.signals.progress.emit("[WARN] " + str(msg))

    def error(self, msg, *args, silent=False, **kwargs):
        _version_print_msg = f"System Info: '{system()} {APP_VERSION}{'-' + TRACKING_BRANCH if TRACKING_BRANCH else ''}' 'Use Local Patterns: Config={get_app_cfg().use_local_patterns}'"

        super().error(msg, *args, **kwargs)
        if not silent:
            self.signals.progress.emit("[ERROR] " + str(msg))
        super().error(_version_print_msg, *args, **kwargs)


# Replace logging.Logger Class with custom Class
print(f"Replaced Class {logging.Logger} with {LoggerWithSignals}")
logging.setLoggerClass(LoggerWithSignals)


def configure_logging(log_file: Path, level: int, console: bool = True) -> None:
    if log_file.exists() and not log_file.is_file():
        raise RuntimeError(f"Attempting to create/ensure directory when a file path has been given: '{log_file}'")

    log_file.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

    formatter = logging.Formatter(f"[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s", datefmt="%d-%m-%Y %H:%M:%S")

    # Remove any pre-existing handlers. Important when in running in dev
    root.handlers.clear()

    file_handler = FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    if console:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        root.addHandler(stream_handler)


def reset_log_file(log_file: Path) -> None:
    if Path(log_file).exists() and log_file.is_file():
        with open(log_file, "w", encoding="utf-8") as f:
            f.write("")
