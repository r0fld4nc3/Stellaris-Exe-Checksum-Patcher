import os
import sys
import time
import pathlib
import subprocess
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSizePolicy, QFileDialog, QTextBrowser, QFrame, QAbstractScrollArea
)
from PySide6.QtCore import Qt, QSize, QThreadPool, QObject, QEvent
from PySide6.QtGui import QIcon, QFont, QFontDatabase

from .Styles import STYLES
from conf_globals import updater, settings, APP_VERSION, OS, LOG_LEVEL, IS_DEBUG
from .ui_utils import Threader, get_screen_info, set_icon_gray
from logger import create_logger, reset_log_file
from patchers import stellaris_patch
from patchers.save_patcher import repair_save, get_user_save_folder

# loggers to hook up to signals
from updater.updater import log as updater_log
from patchers.stellaris_patch import log as patcher_log
from patchers.save_patcher import log as patcher_save_log

Path = pathlib.Path

log = create_logger("UI", LOG_LEVEL)


class StellarisChecksumPatcherGUI(QWidget):
    _APP_VERSION = 'v' + ".".join([str(v) for v in APP_VERSION[0:3]])
    if len(APP_VERSION) > 3:
        _APP_VERSION += "-"
        _APP_VERSION += "-".join(str(v) for v in APP_VERSION[3:])
    icons = Path(__file__).parent / "ui_icons"
    fonts = Path(__file__).parent / "fonts"

    def __init__(self):
        if not QApplication.instance():
            self.app = QApplication(sys.argv)
        else:
            self.app = QApplication.instance()

        super().__init__()

        self.style = STYLES.Stellaris # Default pick

        if self.style == STYLES.Stellaris:
            self.window_title = "Stellaris Checksum Patcher"
        elif self.style == STYLES.CK:
            self.window_title = "Crusader Kings Checksum Patcher"

        self.has_run_once = False
        self.is_patching = False
        self.auto_patch_failed = False

        self.install_dir = ''
        self.game_executable_name = ''
        self.replace_failed_reasons = []

        self.window_title_with_app_version = f"{self.window_title} ({self._APP_VERSION}){'-debug' if IS_DEBUG else ''}"

        # Icons and Fonts
        window_icon = QIcon(str(self.icons / "stellaris_checksum_patcher_icon.ico"))
        patch_icon = QIcon(str(self.icons / "patch_icon.png"))
        save_patch_icon = QIcon(str(self.icons / "save_patch_icon.png"))
        orbitron_bold_font_id = QFontDatabase.addApplicationFont(str(self.fonts / "Orbitron-Bold.ttf"))
        self.orbitron_bold_font = QFontDatabase.applicationFontFamilies(orbitron_bold_font_id)[0]
        self.stellaris_patch_icon = patch_icon
        self.stellaris_save_patch_icon = set_icon_gray(save_patch_icon)

        # Set app constraints
        self.setWindowTitle(self.window_title_with_app_version)
        self.setWindowIcon(window_icon)
        self.setWindowIcon(self.stellaris_patch_icon)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        self.grabber_filter = EventFilterGrabber()
        self.installEventFilter(self.grabber_filter)
        self.start_pos = None
        self.setWindowOpacity(0.95)
        self.setStyleSheet(self.style.BACKGROUND)

        # Main layout
        self.main_layout = QVBoxLayout()

        # Frame Layout
        self.frame_layout = QVBoxLayout()

        # Window Functions Layout
        self.hlayout_window_functions = QHBoxLayout()

        self.hlayout_after_terminal_display = QHBoxLayout()

        self.hlayout_patch_buttons = QHBoxLayout()

        self.hlayout_misc_functions = QHBoxLayout()

        # ========== Size Policies ==========
        btn_size_policy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Maximum)
        btn_size_policy.setHorizontalStretch(0)
        btn_size_policy.setVerticalStretch(0)

        size_policy_project_browser_link = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        size_policy_project_browser_link.setHorizontalStretch(0)
        size_policy_project_browser_link.setVerticalStretch(0)

        size_policy_app_version_label = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        size_policy_app_version_label.setHorizontalStretch(0)
        size_policy_app_version_label.setVerticalStretch(0)

        # ========== Widgets ==========
        # Main Frame
        self.main_frame = QFrame()
        self.main_frame.setStyleSheet(self.style.FRAME)
        self.main_frame.setMinimumSize(QSize(650, 500))
        self.main_frame.setFrameShape(QFrame.WinPanel)
        self.main_frame.setFrameShadow(QFrame.Plain)
        self.main_frame.setLineWidth(5)
        self.main_frame.setMidLineWidth(0)

        self.lbl_title = QLabel(self.window_title)
        self.lbl_title.setStyleSheet(self.style.TITLE)
        self.lbl_title.setFont(QFont(self.orbitron_bold_font, 24))
        self.lbl_title.setSizePolicy(size_policy_app_version_label)
        self.lbl_title.setMinimumSize(QSize(24, 36))
        self.lbl_title.setMaximumSize(QSize(16777215, 36))
        self.lbl_title.setContentsMargins(5, 2, 5, 2)

        self.lbl_app_version = QLabel(f"{self._APP_VERSION}{'-debug' if IS_DEBUG else ''}")
        self.lbl_app_version.setSizePolicy(size_policy_app_version_label)

        # Themed Exit Application
        self.btn_themed_exit_app = QPushButton("X")
        self.btn_themed_exit_app.setStyleSheet(self.style.EXIT_APP)
        self.btn_themed_exit_app.setFont(self.orbitron_bold_font)
        self.btn_themed_exit_app.setSizePolicy(btn_size_policy)
        self.btn_themed_exit_app.setMinimumSize(QSize(32, 24))
        self.btn_themed_exit_app.setMaximumSize(QSize(32, 32))
        self.btn_themed_exit_app.setBaseSize(QSize(32, 32))
        self.btn_themed_exit_app.clicked.connect(self.app_quit)

        # Terminal Display
        self.terminal_display = QTextBrowser()
        self.terminal_display.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored))
        self.terminal_display.setFrameShape(QFrame.Box)
        self.terminal_display.setFrameShadow(QFrame.Sunken)
        self.terminal_display.setStyleSheet(self.style.TERMINAL_DISPLAY)
        self.terminal_display.setLineWidth(2)
        self.terminal_display.setOpenExternalLinks(True)
        # Size Policy
        size_policy_terminal_display = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        size_policy_terminal_display.setHorizontalStretch(0)
        size_policy_terminal_display.setVerticalStretch(0)
        size_policy_terminal_display.setHeightForWidth(self.terminal_display.sizePolicy().hasHeightForWidth())
        self.terminal_display.setSizePolicy(size_policy_terminal_display)

        # Project Browser Link
        self.project_link_html = '''
                <p>Project link: <a href="https://github.com/r0fld4nc3/Stellaris-Exe-Checksum-Patcher">https://github.com/r0fld4nc3/Stellaris-Exe-Checksum-Patcher</a></p>
                '''
        self.txt_browser_project_link = QTextBrowser()
        self.txt_browser_project_link.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.txt_browser_project_link.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.txt_browser_project_link.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.txt_browser_project_link.setOpenExternalLinks(True)
        self.txt_browser_project_link.setHtml(self.project_link_html)
        self.txt_browser_project_link.setStyleSheet("""border: 4px solid rgb(35, 75, 70);""")
        self.txt_browser_project_link.setSizePolicy(size_policy_project_browser_link)
        self.txt_browser_project_link.setMaximumSize(QSize(16777215, 36))

        # Fix Save Button
        self.btn_fix_save_file = QPushButton("Fix Save Achievements")
        self.btn_fix_save_file.setStyleSheet(STYLES.GRAYED_OUT)
        self.btn_fix_save_file.setIcon(self.stellaris_save_patch_icon)
        self.btn_fix_save_file.setIconSize(QSize(64, 64))
        self.btn_fix_save_file.setFont(QFont(self.orbitron_bold_font, 14))
        self.btn_fix_save_file.setFlat(False)
        self.btn_fix_save_file.clicked.connect(self.fix_save_achievements_thread)
        self.btn_fix_save_file.setDisabled(True)  # TODO: Delete line when it is time

        # Patch Button
        self.btn_patch_executable = QPushButton("Patch Executable")
        self.btn_patch_executable.setStyleSheet(self.style.BUTTONS)
        self.btn_patch_executable.setIcon(self.stellaris_patch_icon)
        self.btn_patch_executable.setIconSize(QSize(64, 64))
        self.btn_patch_executable.setFont(QFont(self.orbitron_bold_font, 14))
        if OS.LINUX:
            # TOOD: Hacky way becase on Linux we're getting segfault after operations
            self.btn_patch_executable.clicked.connect(self.patch_game_executable)
        else:
            self.btn_patch_executable.clicked.connect(self.patch_game_executable_thread)
        self.btn_patch_executable.setFlat(False)

        # Show Game Folder Button
        self.btn_show_game_folder = QPushButton("Show Game Folder")
        self.btn_show_game_folder.setStyleSheet(self.style.BUTTONS)
        self.btn_show_game_folder.setFlat(False)
        self.btn_show_game_folder.setSizePolicy(btn_size_policy)
        self.btn_show_game_folder.setMinimumSize(QSize(12, 24))
        self.btn_show_game_folder.setMaximumSize(QSize(16777215, 75))
        self.btn_show_game_folder.setBaseSize(QSize(12, 24))
        self.btn_show_game_folder.setFont(QFont(self.orbitron_bold_font, 14))
        self.btn_show_game_folder.setMouseTracking(True)
        self.btn_show_game_folder.clicked.connect(self.show_game_folder)

        # Add Widgets to Layouts
        # Window Functions
        self.hlayout_window_functions.addWidget(self.btn_themed_exit_app, 0, Qt.AlignRight)

        # After Terminal Layout
        self.hlayout_after_terminal_display.addWidget(self.txt_browser_project_link)

        # Patch Buttons Layout
        self.hlayout_patch_buttons.addWidget(self.btn_fix_save_file)
        self.hlayout_patch_buttons.addWidget(self.btn_patch_executable)

        # Misc Layout
        self.hlayout_misc_functions.addWidget(self.btn_show_game_folder)

        # Main Layout
        self.main_layout.addWidget(self.main_frame)

        # Main Frame Layout
        self.frame_layout.addLayout(self.hlayout_window_functions)
        self.frame_layout.addWidget(self.lbl_title)
        self.frame_layout.addWidget(self.lbl_app_version)
        self.frame_layout.addWidget(self.terminal_display)
        self.frame_layout.addLayout(self.hlayout_after_terminal_display)
        self.frame_layout.addLayout(self.hlayout_patch_buttons)
        self.frame_layout.addLayout(self.hlayout_misc_functions)

        self.setLayout(self.main_layout)
        self.main_frame.setLayout(self.frame_layout)

        # Hook up Signals
        # Could be a bit hacky. Ensure created before assign
        log.signals.progress.connect(self.terminal_display_log)
        updater_log.signals.progress.connect(self.terminal_display_log)
        patcher_log.signals.progress.connect(self.terminal_display_log)
        patcher_save_log.signals.progress.connect(self.terminal_display_log)

        # Worker
        self.worker = None  # Currently unusued, possibly to deprecate

        # Threads
        self.thread_pool = QThreadPool()  # Currently unusued, possibly to deprecate
        self.active_threads = []

        self.load_configs()

        self.check_update()

    def load_configs(self):
        self.install_dir = settings.get_install_location()
        self.game_executable_name = settings.get_executable_name()
        settings.set_app_version(f"{self._APP_VERSION}")
        updater.set_local_version(str(self._APP_VERSION))

    def reset_caches(self):
        self.replace_failed_reasons.clear()
        self.is_patching = False
        self.auto_patch_failed = False

    def terminal_display_log(self, t_log):
        self.terminal_display.insertPlainText(f"{t_log}\n")
        self.refresh_terminal_log()

    def set_terminal_clickable(self, is_clickable: bool):
        if is_clickable:
            self.terminal_display.setTextInteractionFlags(~Qt.LinksAccessibleByMouse)  # the ~ negates the flag
        else:
            self.terminal_display.setTextInteractionFlags(Qt.LinksAccessibleByMouse)

    def refresh_terminal_log(self):
        # Could potentially not be useful anymore. Here to force redraw of elements in the QTextBrowser.
        self.terminal_display.update()

    def enable_ui_elements(self):
        self.btn_patch_executable.setDisabled(False)
        # self.btn_fix_save_file.setDisabled(False) # TODO: Uncomment when it is time

    def disable_ui_elements(self):
        self.btn_patch_executable.setDisabled(True)
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

    @staticmethod
    def prompt_install_dir():
        _install_dir = QFileDialog().getExistingDirectory(
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

        save_file_path = QFileDialog().getOpenFileName(
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

    def check_update(self):
        last_checked = settings.get_update_last_checked()
        now = int(time.time())

        if now - last_checked < 60: # seconds
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
        super().show()
        self._adjust_app_size()
        self.terminal_display.clear()
        sys.exit(self.app.exec())

    def closeEvent(self, event):
        log.info("Application is closing. Shutting down procedure")

        log.info("Shutdown")
        event.accept()
        self.app_quit()

    def app_quit(self):
        log.info("Quitting Application. Performing graceful shutdown procedure.")
        try:
            if self.thread_pool and self.thread_pool.activeThreadCount() > 0:
                log.info("Waiting for thread pool finish.")
                self.thread_pool.waitForDone(msecs=2000)  # Wait for max 2 seconds.
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

    def _adjust_app_size(self):
        screen_info = get_screen_info(self.app)

        log.debug(f"{screen_info=}")

        if not self:
            log.warning("Not self")
            return

        if screen_info[0] <= 1500 or screen_info[1] <= 1000 or screen_info[2] <= 0.7:
            log.info("Resizing application")
            self.resize(QSize(650, 500))
        else:
            self.resize(966, 821)


class EventFilterOvr(QObject):
    def eventFilter(self, obj, event):
        return False


class EventFilterGrabber(EventFilterOvr):
    def eventFilter(self, obj, event):
        if obj.underMouse() and event.type() == QEvent.Type.MouseButtonPress:
            obj.start_pos = event.pos()
            return True
        elif obj.underMouse() and event.type() == QEvent.Type.MouseMove and obj.start_pos is not None:
            obj.move(obj.pos() + event.pos() - obj.start_pos)
            return True
        elif obj.underMouse() and event.type() == QEvent.Type.MouseButtonRelease and obj.start_pos is not None:
            obj.start_pos = None
            return True
        return False