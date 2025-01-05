import os
import sys
import time
import pathlib
import subprocess
from PySide6 import QtWidgets, QtCore, QtGui

from UI.ui_utils import Threader, get_screen_info
from utils.global_defines import updater, settings, APP_VERSION, OS, LOG_LEVEL
from logger import create_logger, reset_log_file
from UI.StellarisChecksumPatcherUI import Ui_StellarisChecksumPatcherWindow
from patchers import stellaris_patch
from patchers.save_patcher import repair_save, get_user_save_folder

# loggers to hook up to signals
from updater.updater import log as updlog
from patchers.stellaris_patch import log as patcherlog
from patchers.save_patcher import log as patchersavelog

Path = pathlib.Path

log = create_logger("UI", LOG_LEVEL)


class StellarisChecksumPatcherGUI(Ui_StellarisChecksumPatcherWindow):
    _app_version = 'v' + ".".join([str(v) for v in APP_VERSION[0:3]])
    if len(APP_VERSION) > 3:
        _app_version += "-"
        _app_version += "-".join(str(v) for v in APP_VERSION[3:])
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
        self.main_window.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowMaximizeButtonHint |
                                        QtCore.Qt.WindowMinimizeButtonHint)

        self.main_window.setWindowOpacity(0.95)

        self.grabber_filter = EventFilterGrabber()
        self.main_window.installEventFilter(self.grabber_filter)
        self.start_pos = None

        # Set App Version from HexPatcher
        self.lbl_app_version.setText(str(self._app_version))

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
        self.btn_fix_save_file.setDisabled(True) # TODO: Delete line when it is time

        # =========== Patch Executable Button ===========
        self.btn_patch_from_install.setIcon(self.patch_icon)
        self.btn_patch_from_install.setIconSize(QtCore.QSize(64, 64))
        self.btn_patch_from_install.setFlat(False)

        # =========== QTextBrowser Terminal Display ===========
        self.terminal_display.clear()  # Clear as we have preview text as default
        
        # Hook Up Patch Button
        self.btn_fix_save_file.clicked.connect(self.fix_save_achievements_thread)
        if OS.LINUX:
            # TOOD: Hacky way becase on Linux we're getting segfault after operations
            self.btn_patch_from_install.clicked.connect(self.patch_game_executable)
        else:
            self.btn_patch_from_install.clicked.connect(self.patch_game_executable_thread)
        self.btn_themed_exit_application.clicked.connect(self.app_quit)

        # Hook up Show Game Folder Button
        self.btn_show_game_folder.clicked.connect(self.show_game_folder)

        # Hook up Signals
        log.signals.progress.connect(self.terminal_display_log)
        updlog.signals.progress.connect(self.terminal_display_log)  # Could be a bit hacky. Ensure created before assign
        patcherlog.signals.progress.connect(self.terminal_display_log)  # Could be a bit hacky. Ensure created before assign
        patchersavelog.signals.progress.connect(self.terminal_display_log)  # Could be a bit hacky. Ensure created before assign

        # Worker
        self.worker = None

        # ThreadPool
        self.thread_pool = QtCore.QThreadPool()
        self.active_threads = []

        self.load_configs()

        self.check_update()

    # =============================================
    # ============== Class Functions ==============
    # =============================================

    def app_quit(self):
        try:
            log.info("Quitting Application.")
            if self.thread_pool and self.thread_pool.activeThreadCount() > 0:
                log.info("Waiting for finish.")
                self.thread_pool.waitForDone(msecs=2000) # Wait for max 2 seconds.
                log.debug("Done waiting.")

            if self.active_threads:
                for thread in self.active_threads:
                    try:
                        thread.stop()
                    except Exception as e:
                        log.error(f"Error in stopping Thread. {e}")
        except Exception as e:
            log.error(e)

        sys.exit(0)

    def set_terminal_clickable(self, is_clickable: bool):
        if is_clickable:
            self.terminal_display.setTextInteractionFlags(~QtCore.Qt.LinksAccessibleByMouse)  # the ~ negates the flag
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

        log.info("Patching from game installation.")

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

            log.error("Game installation not found.")
            self.terminal_display_log(" ")
            log.info("Patch failed.")
            self.terminal_display_log(" ")
            log.info("Please run again to manually select install directory.")
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
                log.info("System is MacOS. Appending proper path to Contents inside .app")
                log.info(f"Game Executable: {game_executable}")

            # Check if it is patched
            is_patched = stellaris_patch.is_patched(game_executable)

            if is_patched:
                log.info("File is already patched")
            else:
                # Create a backup
                if OS.MACOS:
                    stellaris_patch.create_backup(macos_app_folder)
                else:
                    stellaris_patch.create_backup(game_executable)

                log.info("Applying Patch...")

                patched = stellaris_patch.patch(game_executable)

                self.is_patching = False

                if not patched:
                    log.error(f"Unable to replace original game file.\n")

        self.terminal_display_log(' ')
        log.info("Operations finished.")

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
        log.debug(f"Thread Remove: {thread_id_remove}")

        for iter_thread in self.active_threads:
            iter_id = iter_thread.currentThread()
            log.debug(f"Iter Thread: {iter_id}")
            if iter_id == thread_id_remove:
                log.debug(f"Attempting to remove {iter_thread} ({iter_id})")
                try:
                    iter_thread.stop()
                    self.active_threads.remove(iter_thread)
                except Exception as e:
                    log.error(f"Error in attempting to stop and remove Thread: {e}")
                break

        log.debug(f"Remove thread finished ( {thread_id_remove} )")

    # ===============================================
    # ============== Regular Functions ==============
    # ===============================================
    def load_configs(self):
        self.install_dir = settings.get_install_location()
        self.game_executable_name = settings.get_executable_name()
        settings.set_app_version(f"{self._app_version}")
        updater.set_local_version(str(self._app_version))

    def reset_caches(self):
        self.replace_failed_reasons.clear()
        self.is_patching = False
        self.auto_patch_failed = False

    def terminal_display_log(self, t_log):
        self.terminal_display.insertPlainText(f"{t_log}\n")
        self.refresh_terminal_log()

    def show_game_folder(self):
        game_folder = settings.get_install_location()
        if not game_folder:
            log.info("No game folder defined.")
            return

        log.info(f"Game Folder: {game_folder}")
        if OS.WINDOWS:
            subprocess.run(["explorer.exe", "/select", os.path.normpath(game_folder)])
        elif OS.LINUX:
            subprocess.run(["xdg-open", game_folder])
        elif OS.MACOS:
            subprocess.run(["open", "-R", game_folder])
        else:
            log.warning("No known Operating System")

    def patch_game_executable_thread(self):
        if self.is_patching:
            return

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
            log.info(f"Save file: {save_file_path}")

        if not save_file_path:
            return False

        save_games_dir = pathlib.Path(save_file_path).parent.parent
        log.info(f"Save games directory: {os.path.normpath(save_games_dir)}")
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

    def adjust_app_size(self):
        screen_info = get_screen_info(self.app)

        log.debug(screen_info)

        if not self.main_window:
            return

        if screen_info[0] <= 1500 or screen_info[1] <= 1000 or screen_info[2] <= 0.7:
            self.main_window.resize(QtCore.QSize(650, 500))

    def check_update(self):
        last_checked = settings.get_update_last_checked()
        now = int(time.time())

        if now - last_checked < 60:
            self.check_update_finished()
            return

        thread_update = Threader(target=updater.check_for_update)
        thread_id = thread_update.currentThread()
        self.active_threads.append(thread_update)
        thread_update.start()
        thread_update.signals.finished.connect(self.check_update_finished)

    def check_update_finished(self):
        updater_last_checked = updater.last_checked_timestamp

        # No online check was performed
        if updater_last_checked <= 1:
            update_available = settings.get_has_update()
        else:
            settings.set_update_last_checked(updater.last_checked_timestamp)
            if updater.has_new_version:
                settings.set_has_update(True)
                update_available = True
            else:
                settings.set_has_update(False)
                update_available = False

        if update_available:
            html = self.txt_browser_project_link.toHtml().replace("</p>", '').replace("</body>", '').replace("</html>", '')
            html += "<span style=\" font-weight:700;\"> (UPDATE AVAILABLE)</span></p></body></html>"
            self.txt_browser_project_link.setHtml(html)
            self.lbl_title.setText(self.lbl_title.text() + " (UPDATE AVAILABLE)")
            settings.set_has_update(True)

    def show(self):
        reset_log_file()
        self.main_window.show()
        self.adjust_app_size()
        self.terminal_display.clear()
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
