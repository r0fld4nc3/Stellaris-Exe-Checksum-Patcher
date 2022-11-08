from . import *

# 3rd-party
from PySide6 import QtCore, QtGui, QtWidgets
from UI.StellarisChecksumPatcherUI import Ui_MainWindow
from hex_patchers.HexPatcher import StellarisChecksumPatcher

UI_ICONS_FOLDER = os.path.join(os.path.dirname(__file__), 'ui_icons')

DEV = False
EXE = True

logger = Logger(dev=DEV, exe=EXE)

def prompt_user_game_install_dialog():
    directory = QtWidgets.QFileDialog().getExistingDirectory(caption='Please choose Stellaris installation Folder...')
    
    return os.path.abspath(directory)

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
        
        self.__has_run_once = False
        self.__patch_successful = False
        
        self.__manual_install_dir = ''
        
        self.app = QtWidgets.QApplication(sys.argv)
        self.main_window = QtWidgets.QMainWindow()
        Ui_MainWindow.setupUi(self, self.main_window)
        self.main_window.setWindowTitle("Stellaris Checksum Patcher")
        
        self.patch_icon = QtGui.QIcon(os.path.join(UI_ICONS_FOLDER, 'patch_icon.png'))
        
        self.main_window.setWindowIcon(self.patch_icon)
        
        self.btn_patch_from_dir.setIcon(self.patch_icon)
        self.btn_patch_from_dir.setIconSize(QtCore.QSize(64, 64))
        self.btn_patch_from_dir.setFlat(False)
        
        self.btn_patch_from_install.setIcon(self.patch_icon)
        self.btn_patch_from_install.setIconSize(QtCore.QSize(64, 64))
        self.btn_patch_from_install.setFlat(False)
        
        self.terminal_display.clear()
        
        self.stellaris_patcher = StellarisChecksumPatcher()
        
        self.lbl_app_version.setText(f'Version {(".".join([str(v) for v in self.stellaris_patcher.app_version]))}')
        
        self.btn_patch_from_dir.clicked.connect(self.patch_from_directory_thread)
        self.btn_patch_from_install.clicked.connect(self.patch_from_install_thread)
        
    def __refresh_onscreen_log(self):
        QtCore.QCoreApplication.processEvents()
        
    def reset_caches(self):
        self.__patch_successful = False
        
    def patch_from_game_install(self):
        self.reset_caches()
        self.__has_run_once = True
        
        with Capturing() as output:
            logger.log('Patching from game installation.')
            game_executable = self.stellaris_patcher.locate_game_install()
        for o in output:
            self.terminal_display.insertPlainText(f'{o}\n')
        
        if not game_executable:
            with Capturing() as output:
                logger.log_error('Game installation not found.')
                print('')
                logger.log('Patch failed.')
                print('')
                logger.log('Please run again to manually select install directory.')
            
            for o in output:
                self.terminal_display.insertPlainText(f'{o}\n')
            self.__refresh_onscreen_log()
            return False
        
        with Capturing() as output:
            self.stellaris_patcher.load_file_hex(file_path=game_executable)
            logger.log('Applying Patch...')
        for o in output:
            self.terminal_display.insertPlainText(f'{o}\n')
        
        with Capturing() as output:
            self.stellaris_patcher.patch()
        for o in output:
            self.terminal_display.insertPlainText(f'{o}\n')
            
        self.__refresh_onscreen_log()
            
        self.__patch_successful = True
        
    def patch_from_manual_game_install(self):
        self.reset_caches()
        self.__has_run_once = True
        
        with Capturing() as output:
            logger.log('Patching from user submitted directory.')
            loaded = self.stellaris_patcher.load_file_hex(os.path.join(self.__manual_install_dir, self.stellaris_patcher.exe_default_filename))
        for o in output:
            self.terminal_display.insertPlainText(f'{o}\n')
        
        if not loaded:
            with Capturing() as output:
                logger.log_error('Game executable not found.')
                print('')
                logger.log('Patch failed.')
           
            for o in output:
                self.terminal_display.insertPlainText(f'{o}\n')
            self.__refresh_onscreen_log()
            return False
        
        with Capturing() as output:
            logger.log('Applying Patch...')
        for o in output:
            self.terminal_display.insertPlainText(f'{o}\n')
        
        with Capturing() as output:
            self.stellaris_patcher.patch()
        
        for o in output:
            self.terminal_display.insertPlainText(f'{o}\n')
        
        self.__refresh_onscreen_log()
        
        self.__patch_successful = True
        
    def patch_from_directory(self):
        self.reset_caches()
        self.__has_run_once = True
        
        with Capturing() as output:
            logger.log('Patching from current directory.')
            loaded = self.stellaris_patcher.load_file_hex()
        for o in output:
            self.terminal_display.insertPlainText(f'{o}\n')
        
        if not loaded:
            with Capturing() as output:
                logger.log_error('Game executable not found.')
                print('')
                logger.log('Patch failed.')
           
            for o in output:
                self.terminal_display.insertPlainText(f'{o}\n')
            self.__refresh_onscreen_log()
            return False
        
        with Capturing() as output:
            logger.log('Applying Patch...')
        for o in output:
            self.terminal_display.insertPlainText(f'{o}\n')
        
        with Capturing() as output:
            self.stellaris_patcher.patch()
        
        for o in output:
            self.terminal_display.insertPlainText(f'{o}\n')
        
        self.__refresh_onscreen_log()
        
        self.__patch_successful = True
        
    def patch_from_install_thread(self):
        if not self.__has_run_once:
            thread_do_install_patch = threading.Thread(
                target=self.patch_from_game_install
            )
            thread_do_install_patch.start()
        else:
            if not self.__patch_successful:
                self.__manual_install_dir = prompt_user_game_install_dialog()
                self.patch_from_directory_thread()
            
    def patch_from_directory_thread(self):
        thread_do_dir_patch = threading.Thread(
            target=self.patch_from_manual_game_install
        )
        thread_do_dir_patch.start()
        
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