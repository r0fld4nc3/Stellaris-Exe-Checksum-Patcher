# built-ins
import os
import sys

# 3rd-party
from hex_patchers import HexPatcher
from stellaris_patcher_menu import entry_menu
from UI import stellaris_checksum_patcher_gui
from PySide6.QtWidgets import QApplication, QMainWindow

sys.path.append(os.path.join(os.path.dirname(__file__), "Lib\\site-packages"))

# https://steamcommunity.com/sharedfiles/filedetails/?id=2719382752
    
if __name__ == '__main__':
    # patcher = entry_menu.EntryMenu()
    # patcher.run_cli()
    
    w = stellaris_checksum_patcher_gui.StellarisChecksumPatcherGUI()
    w.show()