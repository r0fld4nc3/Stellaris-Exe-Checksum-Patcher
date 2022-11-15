from . import *

from UI.worker_threads import WorkerSignals

SYS_DRIVE = os.getenv('SystemDrive')
LOG_FOLDER = os.path.join(SYS_DRIVE, '\\ProgramData\\r0fld4nc3\\Apps\\Stellaris\\ChecksumPatcher')
LOG_FILE = 'StellarisChecksumPatcherLog.txt'

print(f'LOG PATH: {LOG_FOLDER}')

class Logger:
    def __init__(self, dev=False) -> None:
        self._dev = dev
        
        self.signals = WorkerSignals()
        
        self.log_file = os.path.join(LOG_FOLDER, LOG_FILE)
        
        self.create_log_folder()

    @staticmethod
    def create_log_folder():
        if not os.path.exists(LOG_FOLDER):
            os.makedirs(LOG_FOLDER)
            
    def restart_log_file(self):
        if not os.path.exists(LOG_FOLDER):
            os.makedirs(LOG_FOLDER)
            
        with open(self.log_file, 'w') as f:
            f.write('')
                
    def write_to_log_file(self, log_text):
        if not log_text:
            log_text = ''
            
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                f.write(log_text + '\n')
        else:
            with open(self.log_file, 'a') as f:
                f.write(log_text + '\n')
    
    def log(self, log_text):
        log = f'[INFO] {log_text}'
        print(log)
        self.signals.progress.emit(log)
        self.write_to_log_file(log)
            
    def log_debug(self, log_text):
        log = f'[DEBUG] {log_text}'
        if self._dev:
            print(log)
            self.signals.progress.emit(log)

        self.write_to_log_file(log)
    
    def log_error(self, log_text):
        log = f'[ERROR] {log_text}'
        print(log)
        self.signals.progress.emit(log)
            
        self.write_to_log_file(log)
            
    def log_debug_error(self, log_text):
        log = f'[DEBUG][ERROR] {log_text}'
        if self._dev:
            print(log)
            self.signals.progress.emit(log)
        
        self.write_to_log_file(log)
