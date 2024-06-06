import logging
import pathlib
from os import makedirs

Path = pathlib.Path

from UI.ui_utils import WorkerSignals
from utils.global_defines import config_folder

LOG_FILE =  config_folder / "StellarisChecksumPatcherLog.txt"

LEVELS = {
    0: logging.DEBUG,
    1: logging.INFO,
    2: logging.WARNING,
    3: logging.ERROR
}

def create_logger(logger_name: str, level: int) -> logging.Logger:
    # Create needed folder if it doesn't exist
    if not config_folder.exists():
        makedirs(config_folder, exist_ok=True)

    logger = logging.getLogger(logger_name)

    logger.setLevel(LEVELS.get(level, 1))

    handler_stream = logging.StreamHandler()
    handler_file = logging.FileHandler(LOG_FILE)

    formatter = logging.Formatter("[%(name)s] [%(asctime)s] [%(levelname)s] %(message)s", datefmt="%d-%m-%Y %H:%M:%S")
    handler_stream.setFormatter(formatter)
    handler_file.setFormatter(formatter)

    # Add the handlers if not present already
    if not any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers):
        logger.addHandler(handler_stream)

    if not any(isinstance(handler, logging.FileHandler) and handler.baseFilename == LOG_FILE for handler in logger.handlers):
        logger.addHandler(handler_file)

    logger.signals = WorkerSignals()

    # ================================
    # Modified original methods
    # ================================
    # Add custom attributes to the logger
    # Info
    _original_info = logger.info
    def new_info(msg, *args, **kwargs):
        _original_info(msg, *args, **kwargs)
        logger.signals.progress.emit("[INFO] " + str(msg))
    logger.info = new_info

    # Warning
    _original_warning = logger.warning
    def new_warning(msg, *args, **kwargs):
        _original_warning(msg, *args, **kwargs)
        logger.signals.progress.emit("[WARN] " + str(msg))
    logger.warning = new_warning

    # Debug
    _original_debug = logger.debug
    def new_debug(msg, *args, **kwargs):
        _original_debug(msg, *args, **kwargs)
        if level <= tuple(LEVELS.keys())[0]:
            logger.signals.progress.emit("[DEBUG] " + str(msg))
    logger.debug = new_debug

    # Error
    _original_error = logger.error
    def new_error(msg, *args, **kwargs):
        _original_error(msg, *args, **kwargs)
        logger.signals.progress.emit("[ERROR] " + str(msg))
    logger.error = new_error
    # ================================

    return logger


def reset_log_file() -> None:
    if Path(LOG_FILE).exists():
        with open(LOG_FILE, 'w') as f:
            f.write('')
