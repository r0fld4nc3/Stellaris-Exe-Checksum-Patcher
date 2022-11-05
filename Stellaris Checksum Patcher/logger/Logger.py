from . import * 

class Logger:
    def __init__(self, dev=False, exe=False) -> None:
        self.__dev = dev
        self.__exe = exe
    
    def log(self, log_text):
        print(f'[INFO] {log_text}')
            
    def log_debug(self, log_text):
        if self.__dev:
            if self.__exe:
                print(f'[DEBUG] {log_text}')
            else:
                print(f'{Colours.BLUE}[DEBUG] {log_text}{Colours.DEFAULT}')
    
    def log_error(self, log_text):
        if self.__exe:
            print(f'[ERROR] {log_text}')
        else:
            print(f'{Colours.RED}[ERROR]{Colours.DEFAULT} {log_text}')
            
    def log_debug_error(self, log_text):
        if self.__dev:
            if self.__exe:
                print(f'[DEBUG][ERROR] {log_text}')
            else:
                print(f'{Colours.BLUE}[DEBUG]{Colours.RED}[ERROR]{Colours.DEFAULT} {log_text}')
