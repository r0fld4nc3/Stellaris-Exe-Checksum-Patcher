from . import *

from PySide6 import QtWidgets

class Capturing(list): # Deprecated and not used, here for simply backup reasons because it was really cool to figure it out.
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self
    
    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio    # free up some memory
        sys.stdout = self._stdout

def prompt_user_game_install_dialog():
    directory = QtWidgets.QFileDialog().getExistingDirectory(caption='Please choose Stellaris installation Folder...')
    
    return directory