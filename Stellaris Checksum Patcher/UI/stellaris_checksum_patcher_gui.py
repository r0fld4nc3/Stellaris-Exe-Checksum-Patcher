from . import *

# 3rd-party
from main import logger

from PySide6 import QtWidgets, QtCore, QtGui
from .ui_utils import prompt_user_game_install_dialog, do_something_when_thread_ended
from .worker_threads import Worker, WorkerSignals
from UI.StellarisChecksumPatcherUI import Ui_MainWindow
from hex_patchers.HexPatcher import StellarisChecksumPatcher

UI_ICONS_FOLDER = os.path.join(os.path.dirname(__file__), 'ui_icons')

class StellarisChecksumPatcherGUI(Ui_MainWindow):
    def __init__(self) -> None:
        
        super(StellarisChecksumPatcherGUI, self).__init__()
        
        self.set_app_id()
        
        self._has_run_once = False
        self._patch_successful = False
        self.is_patching = False
        
        self._manual_install_dir = ''
        
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
        
        # Set App Version from HexPatcher
        self.lbl_app_version.setText(f'Version {(".".join([str(v) for v in self.stellaris_patcher.app_version]))}')
        
        # Perhaps add a GUI Version as well? Hmm
        
        self.btn_patch_from_dir.clicked.connect(self.patch_from_directory_thread)
        self.btn_patch_from_install.clicked.connect(self.patch_from_game_install_thread)
        logger.signals.progress_signal.connect(self._terminal_display_log)
        
    def _refresh_onscreen_log(self):
        self.terminal_display.update()
        
    def _terminal_display_log(self, t_log):
        self.terminal_display.insertPlainText(f'{t_log}\n')
        self._refresh_onscreen_log()
        
    def get_patched_file(self):
        return os.path.join(self.stellaris_patcher.exe_out_directory, self.stellaris_patcher.exe_modified_filename + '.exe')
        
    def reset_caches(self):
        self._patch_successful = False
        self.is_patching = False
        
    def replace_with_patched_file(self):
        self._terminal_display_log(' ')
        patched_file = self.get_patched_file()
        original_file = self.stellaris_patcher.locate_game_install()
        
        # Rename original file
        renamed = False
        logger.log('Backing up original file.')
        try:
            backup_file = f'{original_file}.orig'
            if not os.path.exists(backup_file):
                logger.log_debug(f'Renaming {original_file} -> {backup_file}')
                os.rename(original_file, original_file + '.orig')
            else:
                logger.log('Backed up file already exists.')
            renamed = True
        except Exception as e:
            logger.log_error('Failed to rename original file.')
            logger.log_debug_error(e)
            
        if not renamed:
            return False
        
        # Copy patched file and rename
        copied = False
        logger.log('Moving patched file.')
        try:
            logger.log_debug(f'{patched_file} -> {original_file}')
            shutil.copy(patched_file, original_file)
            copied = True
        except Exception as e:
            logger.log_error('Failed to move patched file.')
            logger.log_debug_error(e)
            
        if not copied:
            return False
        
        self._terminal_display_log(' ')
        logger.log('Operations finished.')
            
        try:
            os.remove(patched_file)
        except Exception as e:
            self._terminal_display_log(' ')
            logger.log_error('Unable to delete patched file.')
        
        return True
        
    def patch_from_game_install(self):
        self.reset_caches()
        self._has_run_once = True
        self.is_patching = True
        
        logger.log('Patching from game installation.')
        game_executable = self.stellaris_patcher.locate_game_install()
        
        if not game_executable:
            self.is_patching = False
            logger.log_error('Game installation not found.')
            self._terminal_display_log(' ')
            logger.log('Patch failed.')
            self._terminal_display_log(' ')
            logger.log('Please run again to manually select install directory.')
            self._refresh_onscreen_log()
            return False
        
        self.stellaris_patcher.load_file_hex(file_path=game_executable)
        
        logger.log('Applying Patch...')
        
        self._terminal_display_log(' ')
        
        self.stellaris_patcher.patch()
            
        self.replace_with_patched_file()
        
        self._refresh_onscreen_log()
            
        self._patch_successful = True
        self.is_patching = False
        
    def patch_from_manual_game_install(self):
        self.reset_caches()
        self._has_run_once = True
        self.is_patching = True
        dir_to_look = os.path.join(self._manual_install_dir, self.stellaris_patcher.exe_default_filename)
        
        logger.log('Patching from directory.')
        loaded = self.stellaris_patcher.load_file_hex(dir_to_look)
        
        if not loaded:
            self.is_patching = False
            self._terminal_display_log(' ')
            if not self._manual_install_dir or self._manual_install_dir == '':
                logger.log_error('Game executable not found in current directory.')
            else:
                logger.log_error(f'Game executable not found in {dir_to_look}.')
            logger.log('Patch failed.')
            self.worker.signals.fail_signal.emit()
            return False
        
        logger.log('Applying Patch...')
        
        self._terminal_display_log(' ')
        
        self.stellaris_patcher.patch()
        
        self.replace_with_patched_file()
        
        self._refresh_onscreen_log()
        
        self._patch_successful = True
        self.is_patching = False
        
    def patch_from_directory(self):
        self.reset_caches()
        self.is_patching = True
        
        logger.log('Patching from current directory.')
        loaded = self.stellaris_patcher.load_file_hex()
        
        if not loaded:
            self.is_patching = False
            self._terminal_display_log(' ')
            logger.log_error('Game executable not found.')
            logger.log('Patch failed.')
            return False
        
        logger.log('Applying Patch...')
        
        self.stellaris_patcher.patch()
        
        self._refresh_onscreen_log()
        
        self._patch_successful = True
        self.is_patching = False
        
    def patch_from_game_install_thread(self):
        if self.is_patching:
            return False
        
        logger.restart_log_file()
        
        self.terminal_display.clear()
        
        # Not run once OR (has run once and patch was successful)
        self.thread_pool = QtCore.QThreadPool()
        self.worker = Worker(target=self.patch_from_game_install)
        self.thread_pool.start(self.worker)
        
    def patch_from_prompt(self):
        self._manual_install_dir = prompt_user_game_install_dialog()
        if self._manual_install_dir and self._manual_install_dir != '':
            self._has_run_once = False
            self.patch_from_directory_thread()
            
    def patch_from_directory_thread(self):
        if self.is_patching:
            return False
        
        logger.restart_log_file()
        
        self.terminal_display.clear()
        
        self.thread_pool = QtCore.QThreadPool()
        self.worker = Worker(target=self.patch_from_manual_game_install)
        self.worker.signals.fail_signal.connect(self.patch_from_prompt)
        self.thread_pool.start(self.worker)
                
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