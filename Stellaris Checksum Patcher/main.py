# built-ins
import os
import sys

# 3rd-party
from UI import stellaris_checksum_patcher_gui

sys.path.append(os.path.join(os.path.dirname(__file__), "Lib\\site-packages"))
    
if __name__ == '__main__':
    # patcher = entry_menu.EntryMenu()
    # patcher.run_cli()
    
    w = stellaris_checksum_patcher_gui.StellarisChecksumPatcherGUI()
    w.show()