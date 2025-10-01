# 3rd-party
from UI import StellarisChecksumPatcherGUI  # isort: skip
from patchers import update_patcher_globals  # isort: skip

if __name__ == "__main__":
    update_patcher_globals()
    app = StellarisChecksumPatcherGUI()
    app.show()
