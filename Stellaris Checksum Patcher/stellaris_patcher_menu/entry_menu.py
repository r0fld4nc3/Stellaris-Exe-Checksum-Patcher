from . import *

class EntryMenu(CLI):
    def __init__(self) -> None:
        super().__init__(
            app_name='Stellaris Checksum Patcher',
            app_version=[0, 0, 3]
            )
        
        self.options =  {
            '0': 'Patch From Current Directory',
            '1': 'Patch from File Path (Unavailable)'
        }
        
        self.logger = Logger()
        
    def log(self, text) -> None:
        self.logger.log(text, debug=False)
    
    def log_debug(self, text) -> None:
        self.logger.log(f'{self.Colours.BLUE}{text}{self.Colours.DEFAULT}', debug=True)
        
    def log_error(self, text, debug=False) -> None:
        self.logger.log_error(f'{self.Colours.RED}{text}{self.Colours.DEFAULT}', debug=debug)
        
    def print_commands(self) -> None: # Extends from Base Class
        super(EntryMenu, self).print_commands()
        # Add own commands here.
        for k, v in self.options.items():
            print(f'[{k}]: {v}')
        print()
        
    def parse_input(self, user_input) -> None: # Extends from Base Class
        super(EntryMenu, self).parse_input(user_input)
        
        # Patch from Current directory
        if user_input == list(self.options.keys())[0]:
            patcher = StellarisChecksumPatcher()
            patcher.load_file_hex() # not arguments loads from current directory
            success = patcher.patch()
            if success:
                self.log(f'\nPatch {self.Colours.GREEN}successful{self.Colours.DEFAULT}.\nPress any key to resume.')
            else:
                self.log(f'\nPatch {self.Colours.RED}failed{self.Colours.DEFAULT}.\nPress any key to resume.')
            input()
            
        # Second Option
        if user_input == list(self.options.keys())[1]:
            self.log_debug('Second input')
        
        # Third Option