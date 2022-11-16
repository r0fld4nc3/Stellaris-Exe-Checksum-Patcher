from . import *

from PySide6 import QtWidgets, QtCore, QtGui
from .ui_utils import prompt_user_game_install_dialog, Worker
from UI.StellarisChecksumPatcherUI import Ui_MainWindow
from hex_patchers.HexPatcher import StellarisChecksumPatcher

class StellarisChecksumPatcherGUI(Ui_MainWindow):
    _app_version = ('.'.join([str(v) for v in StellarisChecksumPatcher.app_version]))
    UI_ICONS_FOLDER = os.path.join(os.path.dirname(__file__), 'ui_icons')

    def __init__(self) -> None:
        super(StellarisChecksumPatcherGUI, self).__init__()

        # Required constructor definitions
        self.app = QtWidgets.QApplication(sys.argv)
        self.main_window = QtWidgets.QMainWindow()
        Ui_MainWindow.setupUi(self, self.main_window)

        self.patch_icon = QtGui.QIcon(os.path.join(self.UI_ICONS_FOLDER, 'patch_icon.png'))

        # Add additional main_window stuff here
        self.main_window.setWindowTitle(f'Stellaris Checksum Patcher v{self._app_version}')
        self.main_window.setWindowIcon(self.patch_icon)
        # self.main_window.setWindowFlags(QtCore.Qt.FramelessWindowHint) # Needs implementation of event filters and draggable events but cannot seem to get it working as of now.

        self.__set_app_id() # Setting App ID on Windows

        # Set App Version from HexPatcher
        self.lbl_app_version.setText(f'Version {self._app_version}')

        # Patcher Service Class
        self.stellaris_patcher = StellarisChecksumPatcher()

        self._has_run_once = False
        self._patch_successful = False
        self.is_patching = False

        self._manual_install_dir = ''
        self._replace_failed_reasons = []

        # =========== Patch From Directory Button ===========
        self.btn_patch_from_dir.setIcon(self.patch_icon)
        self.btn_patch_from_dir.setIconSize(QtCore.QSize(64, 64))
        self.btn_patch_from_dir.setFlat(False)

        # =========== Patch From Installation Button ===========
        self.btn_patch_from_install.setIcon(self.patch_icon)
        self.btn_patch_from_install.setIconSize(QtCore.QSize(64, 64))
        self.btn_patch_from_install.setFlat(False)

        # =========== QTextBrowser Terminal Display ===========
        self.terminal_display.clear() # Clear as we have preview text as default
        
        # Handle initial connects
        self.btn_patch_from_dir.clicked.connect(self.patch_from_directory_thread)
        self.btn_patch_from_install.clicked.connect(self.patch_from_game_install_thread)
        self.btn_themed_exit_application.clicked.connect(self._app_quit)
        logger.signals.progress.connect(self.terminal_display_log)
        
        # Worker
        self.worker = None

        # ThreadPool
        self.thread_pool = QtCore.QThreadPool()

    # ===============================================
    # ============== Protected methods ==============
    # ===============================================

    @staticmethod
    def __set_app_id():
        lpBuffer = wintypes.LPWSTR()
        AppUserModelID = ctypes.windll.shell32.GetCurrentProcessExplicitAppUserModelID
        AppUserModelID(ctypes.cast(ctypes.byref(lpBuffer), wintypes.LPWSTR))
        appid = lpBuffer.value
        ctypes.windll.kernel32.LocalFree(lpBuffer)
        if appid is not None:
            print(appid)
    
    # =============================================
    # ============== Class Functions ==============
    # =============================================

    def _app_quit(self):
        try:
            logger.log('Quitting Application.')
            if self.thread_pool and self.thread_pool.activeThreadCount() > 0:
                logger.log('Waiting for finish.')
                self.thread_pool.waitForDone(msecs=15000) # Wait for max 15 seconds.
                self.thread_pool.clear()
        except Exception as e:
            logger.log_error(e)
            
        sys.exit()

    def _set_terminal_clickable(self, is_clickable: bool):
        if is_clickable:
            self.terminal_display.setTextInteractionFlags(~QtCore.Qt.LinksAccessibleByMouse) # the ~ negates the flag
        else:
            self.terminal_display.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse)
        
    def _refresh_terminal_log(self):
        # Could potentially not be useful anymore. Here to force redraw of elements in the QTextBrowser.
        self.terminal_display.update()

    def _operations_finished_report(self):
        self.terminal_display_log(' ')
        logger.log('Operations finished.')
        
    def _patch_from_game_install(self) -> bool:
        """
        Attempts to find the Steam game installation and performing all the necessary steps to patch the exe.

        To be called from Worker Thread.
        :return: bool
        """
        self.reset_caches()
        self._has_run_once = True
        self.is_patching = True

        self._set_terminal_clickable(False)
        
        logger.log('Patching from game installation.')
        game_executable = self.stellaris_patcher.locate_game_install()
        
        if not game_executable:
            self.is_patching = False
            logger.log_error('Game installation not found.')
            self.terminal_display_log(' ')
            logger.log('Patch failed.')
            self.terminal_display_log(' ')
            logger.log('Please run again to manually select install directory.')
            self._set_terminal_clickable(True)
            return False
        
        self.stellaris_patcher.load_file_hex(file_path=game_executable)
        
        logger.log('Applying Patch...')
        
        self.terminal_display_log(' ')
        
        self.stellaris_patcher.patch() # Here if the file IS patched, there is the "is_patched" flag
            
        replaced = self.replace_with_patched_file()

        self._patch_successful = True
        self.is_patching = False

        # Handle feedback if replacing failed
        if not replaced and not self.stellaris_patcher.is_patched:
            logger.log(f'Unable to replace original game file. Please attempt to do so manually.\n')

        self._operations_finished_report()

        self._set_terminal_clickable(True)

        return True
        
    def _patch_from_manual_game_install(self) -> bool:
        """
        Attempts to patch the executable located in the current application's directory. Will prompt for a directory
        in the event that the executable is not found.

        To be called from Worker Thread.
        :return: True if patched succesfully.
        """

        self.reset_caches()
        self._has_run_once = True
        self.is_patching = True

        dir_to_look = os.path.join(self._manual_install_dir, self.stellaris_patcher.exe_default_filename)

        self._set_terminal_clickable(False)
        
        logger.log('Patching from directory.')
        loaded = self.stellaris_patcher.load_file_hex(dir_to_look)
        
        if not loaded:
            self.is_patching = False
            self.terminal_display_log(' ')
            if not self._manual_install_dir or self._manual_install_dir == '':
                logger.log_error('Game executable not found in current directory.')
            else:
                logger.log_error(f'Game executable not found in {dir_to_look}.')
            logger.log('Patch failed.')
            self.worker.signals.failed.emit()
            self._set_terminal_clickable(True)
            return False
        
        logger.log('Applying Patch...')
        
        self.terminal_display_log(' ')

        self.stellaris_patcher.patch()  # Here if the file IS patched, there is the "is_patched" flag

        replaced = self.replace_with_patched_file()

        self._patch_successful = True
        self.is_patching = False

        # Handle feedback if replacing failed
        if not replaced and not self.stellaris_patcher.is_patched:
            logger.log(f'Unable to replace original game file. Please attempt to do so manually.')

        self._operations_finished_report()

        self._set_terminal_clickable(True)

        return True
        
    def _patch_from_directory(self):
        self.reset_caches()
        self.is_patching = True
        
        logger.log('Patching from current directory.')
        loaded = self.stellaris_patcher.load_file_hex()
        
        if not loaded:
            self.is_patching = False
            self.terminal_display_log(' ')
            logger.log_error('Game executable not found.')
            logger.log('Patch failed.')
            return False
        
        logger.log('Applying Patch...')
        
        self.stellaris_patcher.patch()
        
        self._patch_successful = True
        self.is_patching = False
        
    def _enable_ui_elements(self):
        self.btn_patch_from_install.setDisabled(False)
        self.btn_patch_from_dir.setDisabled(False)
    
    def _disable_ui_elements(self):
        self.btn_patch_from_install.setDisabled(True)
        self.btn_patch_from_dir.setDisabled(True)
        
    # ===============================================
    # ============== Regular Functions ==============
    # ===============================================
    
    def reset_caches(self):
        self._replace_failed_reasons.clear()
        self._patch_successful = False
        self.is_patching = False
        
    def terminal_display_log(self, t_log):
        self.terminal_display.insertPlainText(f'{t_log}\n')
        self._refresh_terminal_log()
        
    def get_patched_file(self) -> str:
        """
        Returns path to patched file BUT does NOT CHECK if file exists.

        :return: Path to file
        """
        return os.path.join(self.stellaris_patcher.exe_out_directory, self.stellaris_patcher.exe_modified_filename + '.exe')
        
    def replace_with_patched_file(self) -> bool:
        # Do nothing if file is already patched.
        if self.stellaris_patcher.is_patched:
            return False
        
        self.terminal_display_log(' ')
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
            
        try:
            os.remove(patched_file)
        except Exception:
            self.terminal_display_log(' ')
            logger.log_error('Unable to delete patched file.')
        
        return True
        
    def patch_from_game_install_thread(self):
        if self.is_patching:
            return
        
        logger.restart_log_file()
        
        self.terminal_display.clear()
        
        self.worker = Worker(target=self._patch_from_game_install)
        self.worker.signals.started.connect(self._disable_ui_elements)
        self.worker.signals.finished.connect(self._enable_ui_elements)
        self.thread_pool.start(self.worker)
        
    def patch_from_prompt(self):
        self._manual_install_dir = prompt_user_game_install_dialog()
        self.stellaris_patcher._manual_install_dir = self._manual_install_dir
        if self._manual_install_dir and self._manual_install_dir != '':
            self._has_run_once = False
            self.patch_from_directory_thread()
            
    def patch_from_directory_thread(self):
        if self.is_patching:
            return
        
        logger.restart_log_file()
        
        self.terminal_display.clear()
        
        self.worker = Worker(target=self._patch_from_manual_game_install)
        self.worker.signals.failed.connect(self.patch_from_prompt)
        self.worker.signals.started.connect(self._disable_ui_elements)
        self.worker.signals.finished.connect(self._enable_ui_elements)
        self.thread_pool.start(self.worker)
    
    def show(self):
        self.main_window.show()
        sys.exit(self.app.exec_())
