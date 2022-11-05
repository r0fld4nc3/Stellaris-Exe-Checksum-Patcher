from . import *

class EntryMenu(CLI):
    def __init__(self) -> None:
        super().__init__(
            app_name='Stellaris Checksum Patcher',
            app_version=[0, 0, 6]
            )
        
        self.options =  {
            '0': 'Patch From Current Directory  (Must have \'stellaris.exe\' in same folder as patcher executable)',
            '1': 'Patch From Install Location   (Automatically detect installation and create patch)'
        }
        
        self.logger = Logger()
        self.patcher = StellarisChecksumPatcher()
        
    def print_commands(self) -> None: # Extends from Base Class
        super(EntryMenu, self).print_commands()
        # Add own commands here.
        for k, v in self.options.items():
            print(f'{k}: {v}')
        print()
        
    def parse_input(self, user_input) -> None: # Extends from Base Class
        super(EntryMenu, self).parse_input(user_input)
        
        # Patch from Current directory
        if user_input == list(self.options.keys())[0]:
            self.patcher.load_file_hex() # not arguments loads from current directory
            self.patcher.patch()
            input("Press any key to resume.")
            
        # Second Option
        if user_input == list(self.options.keys())[1]:
            game_executable = self.patcher.locate_game_install()
            self.patcher.load_file_hex(file_path=game_executable)
            self.patcher.patch()
            input("Press any key to resume.")
