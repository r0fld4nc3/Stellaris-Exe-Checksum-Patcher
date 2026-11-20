import logging
from logging import FileHandler
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal

from core.definitions import APP_REVISION_STR, APP_VERSION_STR, VISUAL_BRANCH
from core.paths import system
from core.runtime import AppConfig

# The config given to `configure_logging()`. None until then.
# Kept here rather than read from `services()`: importing `core.services` loads the settings,
# which create their logger before this module has swapped in `LoggerWithSignals` below.
_config: Optional[AppConfig] = None


class LoggerSignals(QObject):
    message = Signal(str)


class LoggerWithSignals(logging.Logger):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.signals = LoggerSignals()

    def debug(self, msg, *args, silent=True, **kwargs):
        super().debug(msg, *args, **kwargs)
        if self.level < logging.INFO:
            if not silent:
                self.signals.message.emit("[DEBUG] " + str(msg))

    def info(self, msg, *args, silent=False, **kwargs):
        super().info(msg, *args, **kwargs)
        if not silent:
            self.signals.message.emit("[INFO] " + str(msg))

    def warning(self, msg, *args, silent=False, **kwargs):
        super().warning(msg, *args, **kwargs)
        if not silent:
            self.signals.message.emit("[WARN] " + str(msg))

    def error(self, msg, *args, silent=False, **kwargs):
        super().error(msg + f"\n{_system_info()}", *args, **kwargs)
        if not silent:
            self.signals.message.emit("[ERROR] " + str(msg))


def _system_info() -> str:
    """One line written for system, version and how the app was started."""
    branch = f"-{VISUAL_BRANCH}" if VISUAL_BRANCH else ""
    use_local_patterns = str(_config.use_local_patterns) if _config else "Unknown (app not started)"
    return f"System Info: '{system()} {APP_VERSION_STR}{APP_REVISION_STR}{branch}' 'Use Local Patterns: Config={use_local_patterns}'"


# Replace logging.Logger Class with custom Class
print(f"Replaced Class {logging.Logger} with {LoggerWithSignals}")
logging.setLoggerClass(LoggerWithSignals)


def configure_logging(config: AppConfig, console: bool = True) -> None:
    """Log to `config.log_file` (and the console) at `config.log_level`."""
    global _config
    _config = config
    log_file = config.log_file
    level = config.log_level

    if log_file.exists() and not log_file.is_file():
        raise RuntimeError(f"Attempting to create/ensure directory when a file path has been given: '{log_file}'")

    log_file.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s", datefmt="%d-%m-%Y %H:%M:%S")

    # Remove any pre-existing handlers. Important when in running in dev
    root.handlers.clear()

    file_handler = FileHandler(log_file, encoding="utf-8-sig")
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    if console:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        root.addHandler(stream_handler)


def reset_log_file(log_file: Path) -> None:
    if Path(log_file).exists() and log_file.is_file():
        with open(log_file, "w", encoding="utf-8-sig") as f:
            f.write("")
