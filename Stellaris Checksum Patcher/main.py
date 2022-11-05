# built-ins
import os
import sys

# 3rd-party
from hex_patchers import HexPatcher
from stellaris_patcher_menu import entry_menu

sys.path.append(os.path.join(os.path.dirname(__file__), "Lib\\site-packages"))

"""
TEMP STUFF FOR UI CONVERSION

Locate pyuic5.exe either in default Python install or any virtual env.

open CMD in that folder.

Type the following into the console:
pyuic5 -x "Path\\To\Saved\\UI\Folder\\filename.ui" -o "Desired\Output\Folder\\filename.py"
"""

# https://steamcommunity.com/sharedfiles/filedetails/?id=2719382752
    
if __name__ == '__main__':
    patcher = entry_menu.EntryMenu()
    patcher.run_cli()