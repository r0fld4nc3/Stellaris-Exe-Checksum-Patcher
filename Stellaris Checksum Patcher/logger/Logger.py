from . import * 

class Logger:
    def __init__(self, dev=False) -> None:
        self.__dev = dev
    
    def log(self, log_text):
        print(f'[INFO] {log_text}')
            
    def log_debug(self, log_text):
        if self.__dev:
            print(f'{Colours.BLUE}[DEBUG] {log_text}{Colours.DEFAULT}')
    
    def log_error(self, log_text):
        print(f'{Colours.RED}[ERROR]{Colours.DEFAULT} {log_text}')
            
    def log_debug_error(self, log_text):
        if self.__dev:
            print(f'{Colours.BLUE}[DEBUG]{Colours.RED}[ERROR]{Colours.DEFAULT} {log_text}')
