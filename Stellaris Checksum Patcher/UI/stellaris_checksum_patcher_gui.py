from . import *

# 3rd-party
from PySide6.QtGui import QIcon
from PySide6 import QtCore, QtGui, QtWidgets
from UI.StellarisChecksumPatcherUI import Ui_MainWindow
from hex_patchers.HexPatcher import StellarisChecksumPatcher

logger = Logger(dev=False, exe=True)

class Capturing(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self
    
    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio    # free up some memory
        sys.stdout = self._stdout
        
class StellarisChecksumPatcherGUI(Ui_MainWindow):
    def __init__(self) -> None:
        
        super(StellarisChecksumPatcherGUI, self).__init__()
        
        self.set_app_id()
        
        self.app = QtWidgets.QApplication(sys.argv)
        self.main_window = QtWidgets.QMainWindow()
        Ui_MainWindow.setupUi(self, self.main_window)
        self.main_window.setWindowTitle("Stellaris Checksum Patcher")
        self.main_window.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), "ui_icons/patch_icon.png")))
        
        self.terminal_display.clear()
        
        self.stellaris_patcher = StellarisChecksumPatcher()
        
        self.lbl_app_version.setText(f'Version {(".".join([str(v) for v in self.stellaris_patcher.app_version]))}')
        
        self.btn_patch_from_install.clicked.connect(self.patch_from_install_thread)
        
    def patch_from_install(self):
        with Capturing() as output:
            logger.log('Patching from game installation.')
            game_executable = self.stellaris_patcher.locate_game_install()
        for o in output:
            self.terminal_display.insertPlainText(f'{o}\n')
        
        
        with Capturing() as output:
            self.stellaris_patcher.load_file_hex(file_path=game_executable)
            logger.log('Applying Patch...')
        for o in output:
            self.terminal_display.insertPlainText(f'{o}\n')
        
        with Capturing() as output:
            self.stellaris_patcher.patch()
        for o in output:
            self.terminal_display.insertPlainText(f'{o}\n')
        
    def patch_from_directory(self):
        print("Patching")
        with Capturing() as output:
            self.stellaris_patcher.locate_game_install()
        
        for o in output:
            self.terminal_display.insertPlainText(f'{o}\n')
        
    def patch_from_install_thread(self):
        thread_do_install = threading.Thread(
            target=self.patch_from_install
        )
        thread_do_install.start()
        
    def set_app_id(self):
        lpBuffer = wintypes.LPWSTR()
        AppUserModelID = ctypes.windll.shell32.GetCurrentProcessExplicitAppUserModelID
        AppUserModelID(ctypes.cast(ctypes.byref(lpBuffer), wintypes.LPWSTR))
        appid = lpBuffer.value
        ctypes.windll.kernel32.LocalFree(lpBuffer)
        if appid is not None:
            print(appid)
    
    def show(self):
        self.main_window.show()
        sys.exit(self.app.exec_())