# 3rd-party
from UI import stellaris_checksum_patcher_gui
from logger.Logger import Logger

DEV = False
EXE = True
logger = Logger(dev=DEV, exe=EXE)
    
if __name__ == '__main__':
    w = stellaris_checksum_patcher_gui.StellarisChecksumPatcherGUI()
    w.show()
