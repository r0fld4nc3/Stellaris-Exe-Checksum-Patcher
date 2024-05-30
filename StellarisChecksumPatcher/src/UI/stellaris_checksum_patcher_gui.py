import os
import pathlib
import sys
from PySide6 import QtWidgets, QtCore, QtGui

from src.UI.ui_utils import Threader
from src.utils.global_defines import logger, updater, settings, APP_VERSION, OS
from src.UI.StellarisChecksumPatcherUI import Ui_StellarisChecksumPatcherWindow
from src.patchers import stellaris_patch
from src.patchers.save_patcher import repair_save, get_user_save_folder

Path = pathlib.Path

class StellarisChecksumPatcherGUI(Ui_StellarisChecksumPatcherWindow):
    _app_version = (".".join([str(v) for v in APP_VERSION]))
    ui_icons_folder = str(Path(__file__).parent / "ui_icons")

    def __init__(self) -> None:
        super(StellarisChecksumPatcherGUI, self).__init__()

        # Required constructor definitions
        self.app = QtWidgets.QApplication(sys.argv)
        self.main_window = QtWidgets.QMainWindow()
        Ui_StellarisChecksumPatcherWindow.setupUi(self, self.main_window)

        self.window_icon = QtGui.QIcon(str(Path(self.ui_icons_folder) / "stellaris_checksum_patcher_icon.ico"))
        self.patch_icon = QtGui.QIcon(str(Path(self.ui_icons_folder) / "patch_icon.png"))
        self.save_patch_icon = QtGui.QIcon(str(Path(self.ui_icons_folder) / "save_patch_icon.png"))
        self.app.setWindowIcon(self.window_icon)

        # Add additional main_window stuff here
        self.main_window.setWindowTitle(f"Stellaris Checksum Patcher v{self._app_version}")
        self.main_window.setWindowIcon(self.patch_icon)
        # Needs implementation of event filters and draggable events.
        self.main_window.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowMaximizeButtonHint |
                                        QtCore.Qt.WindowMinimizeButtonHint)

        self.main_window.setWindowOpacity(0.95)

        self.grabber_filter = EventFilterGrabber()
        self.main_window.installEventFilter(self.grabber_filter)
        self.start_pos = None

        # Set App Version from HexPatcher
        self.lbl_app_version.setText(f"Version {self._app_version}")

        self.has_run_once = False
        self.is_patching = False
        self.auto_patch_failed = False

        self.install_dir = ''
        self.game_executable_name = ''
        self.replace_failed_reasons = []

        # =========== Patch Save File Button ===========
        self.btn_fix_save_file.setIcon(self.save_patch_icon)
        self.btn_fix_save_file.setIconSize(QtCore.QSize(64, 64))
        self.btn_fix_save_file.setFlat(False)
        self.btn_fix_save_file.setDisabled(True) # TODO: Uncomment when it is time

        # =========== Patch Executable Button ===========
        self.btn_patch_from_install.setIcon(self.patch_icon)
        self.btn_patch_from_install.setIconSize(QtCore.QSize(64, 64))
        self.btn_patch_from_install.setFlat(False)

        # =========== QTextBrowser Terminal Display ===========
        self.terminal_display.clear() # Clear as we have preview text as default
        
        # Handle initial connects
        self.btn_fix_save_file.clicked.connect(self.fix_save_achievements_thread)
        self.btn_patch_from_install.clicked.connect(self.patch_game_executable_thread)
        self.btn_themed_exit_application.clicked.connect(self.app_quit)
        logger.signals.progress.connect(self.terminal_display_log)
        
        # Worker
        self.worker = None

        # ThreadPool
        self.thread_pool = QtCore.QThreadPool()
        self.active_threads = []

        self.load_configs()
    
    # =============================================
    # ============== Class Functions ==============
    # =============================================

    def app_quit(self):
        try:
            logger.info("Quitting Application.")
            if self.thread_pool and self.thread_pool.activeThreadCount() > 0:
                logger.info("Waiting for finish.")
                self.thread_pool.waitForDone(msecs=2000) # Wait for max 2 seconds.
                logger.debug("Done waiting.")

            if self.active_threads:
                for thread in self.active_threads:
                    try:
                        thread.stop()
                    except Exception as e:
                        logger.error(f"Error in stopping Thread. {e}")
        except Exception as e:
            logger.error(e)

        sys.exit(0)

    def set_terminal_clickable(self, is_clickable: bool):
        if is_clickable:
            self.terminal_display.setTextInteractionFlags(~QtCore.Qt.LinksAccessibleByMouse) # the ~ negates the flag
        else:
            self.terminal_display.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse)
        
    def refresh_terminal_log(self):
        # Could potentially not be useful anymore. Here to force redraw of elements in the QTextBrowser.
        self.terminal_display.update()
        
    def patch_game_executable(self) -> bool:
        """
        Attempts to find the Steam game installation and performing all the necessary steps to patch the exe.

        To be called from Worker Thread.
        :return: bool
        """
        self.reset_caches()
        self.has_run_once = True # Set for the runtime lifetime
        self.is_patching = True # Because this is triggered when the button to patch was clicked

        self.set_terminal_clickable(False)

        logger.info("Patching from game installation.")

        # Test settings for install location
        settings_install_dir = settings.get_install_location()

        if self.install_dir or settings_install_dir:
            game_executable = Path(self.install_dir) / stellaris_patch.EXE_DEFAULT_FILENAME
            # Make sure the file exists
            if not Path(game_executable).exists():
                game_executable = stellaris_patch.locate_game_executable()
        else:
            game_executable = stellaris_patch.locate_game_executable()

        if not game_executable:
            self.auto_patch_failed = True
            self.is_patching = False

            logger.error("Game installation not found.")
            self.terminal_display_log(" ")
            logger.info("Patch failed.")
            self.terminal_display_log(" ")
            logger.info("Please run again to manually select install directory.")
            self.set_terminal_clickable(True)

            # TODO: Could we not make it run again calling own function? So it doesn't have to be user driven?
            # self.patch_game_executable()
            return False

        self.install_dir = game_executable.parent # executable's directory
        exe_name = game_executable.name

        # Update game executable name in settings
        if exe_name != self.game_executable_name:
            self.game_executable_name = exe_name
            settings.set_executable_name(self.game_executable_name)

        if game_executable:
            # Patch can proceed, therefore save game install location
            settings.set_install_location(str(game_executable))

            # MacOS exception, as it will return a .app, and is a dir
            # Append the postpend filepath to inside the .app
            macos_app_folder = None
            if OS.MACOS:
                macos_app_folder = game_executable
                game_executable = macos_app_folder / stellaris_patch.EXE_PATH_POSTPEND
                logger.info("System is MacOS. Appending proper path to Contents inside .app")
                logger.info(f"Game Executable: {game_executable}")

            # Check if it is patched
            is_patched = stellaris_patch.is_patched(game_executable)

            if is_patched:
                logger.info("File is already patched")
            else:
                # Create a backup
                if OS.MACOS:
                    stellaris_patch.create_backup(macos_app_folder)
                else:
                    stellaris_patch.create_backup(game_executable)

                logger.info("Applying Patch...")

                patched = stellaris_patch.patch(game_executable)

                self.is_patching = False

                if not patched:
                    logger.error(f"Unable to replace original game file.\n")

        self.terminal_display_log(' ')
        logger.info("Operations finished.")

        self.set_terminal_clickable(True)

        return True
        
    def enable_ui_elements(self):
        self.btn_patch_from_install.setDisabled(False)
        # self.btn_fix_save_file.setDisabled(False) # TODO: Uncomment when it is time
    
    def disable_ui_elements(self):
        self.btn_patch_from_install.setDisabled(True)
        self.btn_fix_save_file.setDisabled(True)

    def remove_thread(self, thread_id_remove):
        # Iterates through active threads, checks for ID and stops then removes thread
        logger.debug(f"Thread Remove: {thread_id_remove}")

        for iter_thread in self.active_threads:
            iter_id = iter_thread.currentThread()
            logger.debug(f"Iter Thread: {iter_id}")
            if iter_id == thread_id_remove:
                logger.debug(f"Attempting to remove {iter_thread} ({iter_id})")
                try:
                    iter_thread.stop()
                    self.active_threads.remove(iter_thread)
                except Exception as e:
                    logger.error(f"Error in attempting to stop and remove Thread: {e}")
                break

        logger.debug(f"Remove thread finished ( {thread_id_remove} )")

    # ===============================================
    # ============== Regular Functions ==============
    # ===============================================
    def load_configs(self):
        self.install_dir = settings.get_install_location()
        self.game_executable_name = settings.get_executable_name()
        settings.set_app_version(f"{self._app_version[2:]}")
        updater.local_version = str(self._app_version)[2:]
        self.check_update()

    def reset_caches(self):
        self.replace_failed_reasons.clear()
        self.is_patching = False
        self.auto_patch_failed = False
        
    def terminal_display_log(self, t_log):
        self.terminal_display.insertPlainText(f"{t_log}\n")
        self.refresh_terminal_log()
        
    def patch_game_executable_thread(self):
        if self.is_patching:
            return
        
        logger.restart_log_file()
        
        self.terminal_display.clear()

        # If install failed, ask for directory and then perform the normal patching operation
        if self.has_run_once and self.auto_patch_failed:
            self.install_dir = self.prompt_install_dir()

        # self.worker = Worker(target=self.patch_from_game_install)
        thread_patch_exe = Threader(target=self.patch_game_executable)
        thread_id = thread_patch_exe.currentThread()
        thread_patch_exe.signals.started.connect(self.disable_ui_elements)
        thread_patch_exe.signals.finished.connect(self.enable_ui_elements)
        thread_patch_exe.signals.finished.connect(lambda: self.remove_thread(thread_id))
        self.active_threads.append(thread_patch_exe)
        thread_patch_exe.start()
        # self.thread_pool.start(self.worker)

    @staticmethod
    def prompt_install_dir():
        _install_dir = QtWidgets.QFileDialog().getExistingDirectory(
                caption="Please choose Stellaris installation Folder...")
        if _install_dir:
            _install_dir = Path(_install_dir).absolute().resolve()

        return _install_dir

    def fix_save_achievements_thread(self):
        if self.is_patching:
            return

        logger.restart_log_file()

        self.terminal_display.clear()

        # Before starting the thread, ask which save file the user wants to repair.
        # Simply point to the .sav file and we will do the rest.
        # Usually located in user Documents. Attempt to grab that directory on open

        # Windows
        documents_dir = get_user_save_folder()

        save_file_path = QtWidgets.QFileDialog().getOpenFileName(
                caption="Save file to repair...",
                dir=documents_dir
        )[0]

        if save_file_path or save_file_path != '':
            logger.info(f"Save file: {save_file_path}")

        if not save_file_path:
            return False

        save_games_dir = pathlib.Path(save_file_path).parent.parent
        logger.info(f"Save games directory: {os.path.normpath(save_games_dir)}")
        settings.set_save_games_dir(save_games_dir)

        thread_repair_save = Threader(target=lambda save_file=save_file_path: repair_save(save_file))
        thread_id = thread_repair_save.currentThread()
        thread_repair_save.setTerminationEnabled(True)
        # self.threader.signals.failed.connect() # TODO
        thread_repair_save.signals.started.connect(self.disable_ui_elements)
        thread_repair_save.signals.finished.connect(self.enable_ui_elements)
        thread_repair_save.signals.finished.connect(lambda: self.remove_thread(thread_id))  # Removes thead by ID
        self.active_threads.append(thread_repair_save)
        thread_repair_save.start()

    def check_update(self):
        thread_update = Threader(target=updater.check_for_update)
        thread_id = thread_update.currentThread()
        thread_update.signals.finished.connect(lambda: self.remove_thread(thread_id))
        self.active_threads.append(thread_update)
        thread_update.start()
        # self.thread_pool.start(self.worker)
    
    def show(self):
        self.main_window.show()
        sys.exit(self.app.exec_())


class EventFilterOvr(QtCore.QObject):
    def eventFilter(self, obj, event):
        return False


class EventFilterGrabber(EventFilterOvr):
    def eventFilter(self, obj, event):
        if obj.underMouse() and event.type() == QtCore.QEvent.Type.MouseButtonPress:
            obj.start_pos = event.pos()
            return True
        elif obj.underMouse() and event.type() == QtCore.QEvent.Type.MouseMove and obj.start_pos is not None:
            obj.move(obj.pos() + event.pos() - obj.start_pos)
            return True
        elif obj.underMouse() and event.type() == QtCore.QEvent.Type.MouseButtonRelease and obj.start_pos is not None:
            obj.start_pos = None
            return True
        return False
