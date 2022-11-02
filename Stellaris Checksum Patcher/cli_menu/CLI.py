# built-ins
import os
import sys

# 3rd Party
from . import colours

class CLI:
    def __init__(self, app_name:str='CLI Base Class Interface', app_version:list=[0, 0, 0]) -> None:
        self.Colours = colours.Colours
        self.app_version = app_version
        self.app_name = app_name
        self.app_version_label = f'{self.Colours.GREEN}{self.app_name}{self.Colours.DEFAULT} {self.Colours.YELLOW}[Version d-{".".join([str(x) for x in self.app_version])}]{self.Colours.DEFAULT}'
        self.do_quit = False
        self.quit_arguments = ['q', 'quit', 'exit']
        self.clear_cli_arguments = ['cls', 'clear']
    
    def is_base_class(self) -> bool:
        return type(self) == CLI
        
    def get_exe_path(self) -> os.path:
        return os.path.dirname(sys.executable)
    
    def get_sys_path(self) -> os.path:
        return os.path.dirname(__file__)
    
    def clear_cli(self) -> None:
        os.system('cls')
        
    def print_commands(self) -> None:
        print(f'-- Exit Application:       {", ".join(self.quit_arguments)}')
        print(f'-- To clear the interface: {", ".join(self.clear_cli_arguments)}')
        print()
        
    def await_input(self) -> str:
        user_input = input('>: ').lower()
        
        return user_input
    
    def parse_input(self, user_input) -> None:
        if user_input in self.quit_arguments:
            self.clear_cli()
            # sys.exit(0)
            self.do_quit = True
                
        if user_input in self.clear_cli_arguments:
            self.clear_cli()
            return True
        
    def print_options(self) -> None:
        pass
        
    def run_cli(self) -> None:
        while not self.do_quit:
            self.clear_cli()
            print(self.app_version_label)
            print()
            self.print_commands()
            user_input = self.await_input()
            self.parse_input(user_input)
            print()