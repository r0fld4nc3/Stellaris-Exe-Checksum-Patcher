# built-ins
import os
import sys

# 3rd-party
from hex_patchers import HexData
from stellaris_patcher_menu import entry_menu

sys.path.append(os.path.join(os.path.dirname(__file__), "Lib\\site-packages"))

# https://steamcommunity.com/sharedfiles/filedetails/?id=2719382752
    
if __name__ == '__main__':
    patcher = entry_menu.EntryMenu()
    patcher.run_cli()