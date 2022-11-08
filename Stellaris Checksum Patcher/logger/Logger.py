from . import *

SYS_DRIVE = os.getenv('SystemDrive')
LOG_FOLDER = os.path.join(SYS_DRIVE, 'ProgramData\\r0fld4nc3\\Apps\\Stellaris\\ChecksumPatcher')
LOG_FILE = 'StellarisChecksumPatcherLog.txt'

class Logger:
    def __init__(self, dev=False, exe=False) -> None:
        self.__dev = dev
        self.__exe = exe
        
        self.log_file = os.path.join(LOG_FOLDER, LOG_FILE)
        
        self.__create_log_file()
    
    def __create_log_file(self):
        if not os.path.exists(LOG_FOLDER):
            os.makedirs(LOG_FOLDER)
                
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
        print(f'[INFO] {log_text}')
        self.write_to_log_file(f'[INFO] {log_text}')
            
    def log_debug(self, log_text):
        if self.__dev:
            if self.__exe:
                print(f'[DEBUG] {log_text}')
            else:
                print(f'{Colours.BLUE}[DEBUG] {log_text}{Colours.DEFAULT}')

        self.write_to_log_file(f'[DEBUG] {log_text}')
    
    def log_error(self, log_text):
        if self.__exe:
            print(f'[ERROR] {log_text}')
        else:
            print(f'{Colours.RED}[ERROR]{Colours.DEFAULT} {log_text}')
            
        self.write_to_log_file(f'[ERROR] {log_text}')
            
    def log_debug_error(self, log_text):
        if self.__dev:
            if self.__exe:
                print(f'[DEBUG][ERROR] {log_text}')
            else:
                print(f'{Colours.BLUE}[DEBUG]{Colours.RED}[ERROR]{Colours.DEFAULT} {log_text}')
        
        self.write_to_log_file(f'[DEBUG][ERROR] {log_text}')
