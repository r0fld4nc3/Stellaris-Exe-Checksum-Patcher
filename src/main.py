# 3rd-party
from UI import StellarisChecksumPatcherGUI
from patchers import update_patcher_globals

if __name__ == '__main__':
    update_patcher_globals()
    app = StellarisChecksumPatcherGUI()
    app.show()
