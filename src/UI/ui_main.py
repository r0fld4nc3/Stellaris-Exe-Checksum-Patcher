import os
import sys
import time
import pathlib
import subprocess
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSizePolicy, QInputDialog, QDialog, QFileDialog, QTextBrowser,
    QFrame, QAbstractScrollArea
)
from PySide6.QtCore import QSize, QDateTime, QRunnable, Qt, QThreadPool, QObject, QEvent
from PySide6.QtGui import QIcon, QFont, QFontDatabase

from UI.ui_utils import Threader, get_screen_info
from utils.global_defines import updater, settings, APP_VERSION, OS, LOG_LEVEL
from logger import create_logger, reset_log_file
from patchers import stellaris_patch
from patchers.save_patcher import repair_save, get_user_save_folder

# loggers to hook up to signals
from updater.updater import log as updlog
from patchers.stellaris_patch import log as patcherlog
from patchers.save_patcher import log as patchersavelog

Path = pathlib.Path

log = create_logger("UI", LOG_LEVEL)

class STYLES:
    BACKGROUND = """
        background-color: rgb(35, 55, 50);
        color: rgb(35, 75, 70);
        """
    BUTTONS = """
    QPushButton {
    color: rgb(255, 255, 255);
    background-color: rgba(22, 59, 56, 100);
    border: 4px solid rgb(35, 75, 70);
    }
    QPushButton:hover {
    background-color: rgba(255, 179, 25, 100);
    border-color: rgba(255, 151, 33, 175);
    }
    QPushButton:pressed {
    background-color: rgba(30, 80, 70, 100);
    border-color: rgb(67, 144, 134);
    }"""
    TITLE = """
        color: rgb(255, 255, 255);
        background-color: rgb(35, 75, 70);
        border-radius: 5px;
        """
    TERMINAL_DISPLAY = """
        color: rgb(255, 255, 255);
        background-color: rgba(22, 59, 56, 100);
        border: 4px solid rgb(35, 75, 70);
        """
    EXIT_APP = """
    QPushButton {
    color: rgb(25, 255, 236);
    background-color: rgba(22, 59, 56, 100);
    border: 2px solid rgb(67, 144, 134);
    }
    QPushButton:hover {
    background-color: rgba(255, 179, 25, 100);
    border-color: rgba(255, 151, 33, 175);
    }
    QPushButton:pressed {
    background-color: rgba(30, 80, 70, 100);
    border-color: rgb(67, 144, 134);
    }"""
    FRAME = """
    color: rgb(67, 144, 134);
    background-color: rgb(35, 55, 50);  
    """


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

        self.window_title = "Stellaris Checksum Patcher"
        self.window_title_with_app_version = f"{self.window_title} ({self._APP_VERSION})"

        # Icons and Fonts
        orbitron_bold_font_id = QFontDatabase.addApplicationFont(str(self.fonts / "Orbitron-Bold.ttf"))
        self.orbitron_bold_font = QFontDatabase.applicationFontFamilies(orbitron_bold_font_id)[0]
        window_icon = QIcon(str(self.icons / "stellaris_checksum_patcher_icon.ico"))
        self.stellaris_patch_icon = QIcon(str(self.icons / "patch_icon.png"))
        self.stellaris_save_patch_icon = QIcon(str(self.icons / "save_patch_icon.png"))

        # Set app constraints
        self.setWindowTitle(self.window_title_with_app_version)
        self.setWindowIcon(window_icon)
        self.setWindowIcon(self.stellaris_patch_icon)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        self.grabber_filter = EventFilterGrabber()
        self.installEventFilter(self.grabber_filter)
        self.start_pos = None
        self.setWindowOpacity(0.95)
        self.setStyleSheet(STYLES.BACKGROUND)

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
        self.main_frame.setStyleSheet(STYLES.FRAME)
        self.main_frame.setMinimumSize(QSize(650, 500))
        self.main_frame.setFrameShape(QFrame.WinPanel)
        self.main_frame.setFrameShadow(QFrame.Plain)
        self.main_frame.setLineWidth(5)
        self.main_frame.setMidLineWidth(0)

        self.lbl_title = QLabel(self.window_title)
        self.lbl_title.setStyleSheet(STYLES.TITLE)
        self.lbl_title.setFont(QFont(self.orbitron_bold_font, 24))
        self.lbl_title.setSizePolicy(size_policy_app_version_label)
        self.lbl_title.setMinimumSize(QSize(24, 36))
        self.lbl_title.setMaximumSize(QSize(16777215, 36))

        self.lbl_app_version = QLabel(self._APP_VERSION)
        self.lbl_app_version.setSizePolicy(size_policy_app_version_label)

        # Themed Exit Application
        self.btn_themed_exit_app = QPushButton("X")
        self.btn_themed_exit_app.setStyleSheet(STYLES.EXIT_APP)
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
        self.terminal_display.setStyleSheet(STYLES.TERMINAL_DISPLAY)
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
        self.btn_fix_save_file.setStyleSheet(STYLES.BUTTONS)
        self.btn_fix_save_file.setIcon(self.stellaris_save_patch_icon)
        self.btn_fix_save_file.setIconSize(QSize(64, 64))
        self.btn_fix_save_file.setFont(QFont(self.orbitron_bold_font, 14))
        self.btn_fix_save_file.setFlat(False)
        self.btn_fix_save_file.setDisabled(True)  # TODO: Delete line when it is time

        # Patch Button
        self.btn_patch_executable = QPushButton("Patch Executable")
        self.btn_patch_executable.setStyleSheet(STYLES.BUTTONS)
        self.btn_patch_executable.setIcon(self.stellaris_patch_icon)
        self.btn_patch_executable.setIconSize(QSize(64, 64))
        self.btn_patch_executable.setFont(QFont(self.orbitron_bold_font, 14))
        self.btn_patch_executable.setFlat(False)

        # Show Game Folder Button
        self.btn_show_game_folder = QPushButton("Show Game Folder")
        self.btn_show_game_folder.setStyleSheet(STYLES.BUTTONS)
        self.btn_show_game_folder.setFlat(False)
        self.btn_show_game_folder.setSizePolicy(btn_size_policy)
        self.btn_show_game_folder.setMinimumSize(QSize(12, 24))
        self.btn_show_game_folder.setMaximumSize(QSize(16777215, 75))
        self.btn_show_game_folder.setBaseSize(QSize(12, 24))
        self.btn_show_game_folder.setFont(QFont(self.orbitron_bold_font, 14))
        self.btn_show_game_folder.setMouseTracking(True)

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

    def show(self):
        super().show()
        self._adjust_app_size()
        sys.exit(self.app.exec())

    def closeEvent(self, event):
        log.info("Application is closing. Shutting down procedure")

        log.info("Shutdown")
        event.accept()
        self.app_quit()

    def app_quit(self):
        log.info("Application is closing. Shutting down procedure")

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