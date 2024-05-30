import os
import pathlib
import logging
from time import localtime, strftime

from src.UI.ui_utils import WorkerSignals
from src.utils.global_defines import config_folder

LOG_FOLDER = config_folder
LOG_FILE = "StellarisChecksumPatcherLog.txt"

print(f"LOG PATH: {LOG_FOLDER}")

class Logger:
    # Attempt at Singleton pattern
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__init__(*args, **kwargs)
        return cls._instance

    def __init__(self,
                 is_debug=False,
                 logger_name: str = "DefaultAppLogger",
                 filepath: str = None,
                 filename: str = None,
                 log_level: int = 1
                 ) -> None:

        self.is_debug = is_debug

        """
        LOG LEVELS:

        0 - DEBUG

        1 - INFO

        2 - WARNING

        3 - ERROR

        4 - CRITICAL

        :param log_level: 0 to 4
        """
        
        self.signals = WorkerSignals()

        ##############################################################
        
        self.log_file = pathlib.Path(LOG_FOLDER) / LOG_FILE

        # Modify if initialised with custom parameters
        if filepath:
            self.log_file = pathlib.Path(filepath) / LOG_FILE
        elif filepath and filename:
            self.log_file = pathlib.Path(filepath) /filename

        self.create_log_folder()

        self.DEBUG = logging.DEBUG
        self.INFO = logging.INFO
        self.WARNING = logging.WARNING
        self.ERROR = logging.ERROR
        self.CRITICAL = logging.CRITICAL

        if log_level == 0:
            self.log_level = self.DEBUG
        elif log_level == 1:
            self.log_level = self.INFO
        elif log_level == 2:
            self.log_level = self.WARNING
        elif log_level == 3:
            self.log_level = self.ERROR
        elif log_level == 4:
            self.log_level = self.CRITICAL
        else:
            self.log_level = self.DEBUG

        if self.is_debug:
            self.log_level = self.DEBUG

        self.logger = logging.getLogger(logger_name)
        print(f"logger: {self.logger}")
        self.logger.setLevel(self.log_level)

        if not self.logger.handlers:
            formatter = logging.Formatter("[%(asctime)s] [%(levelname)-4s]: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
            file_handler = logging.FileHandler(self.log_file)
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(self.log_level)

            stream_handler.setFormatter(formatter)
            file_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)
            self.logger.addHandler(stream_handler)

    def create_log_folder(self):
        if not os.path.exists(LOG_FOLDER):
            os.makedirs(LOG_FOLDER)

        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', encoding="utf-8") as f:
                f.write("")
            
    def restart_log_file(self):
        if not os.path.exists(LOG_FOLDER):
            os.makedirs(LOG_FOLDER)
            
        with open(self.log_file, 'w', encoding="utf-8") as f:
            f.write('')
                
    def write_to_log_file(self, log_input):
        if not log_input:
            log_input = ""
            
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', encoding="utf-8") as f:
                f.write(log_input + '\n')
        else:
            with open(self.log_file, 'a', encoding="utf-8") as f:
                f.write(log_input + '\n')
    
    def info(self, log_input):
        console_log = f"[INFO] {log_input}"
        self.signals.progress.emit(console_log)
        self.logger.info(f"{log_input}")

    def warning(self, log_input):
        console_log = f"[WARNING] {log_input}"
        self.signals.progress.emit(console_log)
        self.logger.warning(f"{log_input}")
            
    def debug(self, log_input):
        console_log = f"[DEBUG] {log_input}"
        if self.is_debug:
            self.signals.progress.emit(console_log)

        self.logger.debug(f"{log_input}")
    
    def error(self, log_input):
        console_log = f"[ERROR] {log_input}"
        self.signals.progress.emit(console_log)
            
        self.logger.error(f"{log_input}")
            
    def debug_error(self, log_input):
        console_log = f"[DEBUG][ERROR] {log_input}"
        if self.is_debug:
            self.signals.progress.emit(console_log)
        
        self.logger.debug(f"[ERROR]: {log_input}")

    @staticmethod
    def _time_now():
        now_time = strftime("%H:%M:%S", localtime())

        return now_time

    @staticmethod
    def _date_now():
        now_date = strftime("%Y-%m-%d", localtime())

        return now_date
