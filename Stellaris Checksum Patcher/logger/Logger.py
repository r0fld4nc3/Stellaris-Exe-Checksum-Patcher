class Logger:
    def __init__(self) -> None:
        pass
    
    def log(self, log_text, debug=False):
        if debug:
            print(f'[DEBUG] {log_text}')
        else:
            print(f'[INFO] {log_text}')
    
    def log_error(self, log_text, debug=False):
        if debug:
            print(f'[DEBUG][ERROR] {log_text}')
        else:
            print(f'[ERROR] {log_text}')
            