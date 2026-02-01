import copy
import logging
import re
import sys
import time
from pathlib import Path
from typing import List, Optional, Union

from PySide6.QtCore import QSize, Qt, QThreadPool, Slot
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app_services import services
from config.definitions import APP_VERSION, SUPPORTED_GAMES, TRACKING_BRANCH
from config.path_helpers import os_darwin, os_linux, os_windows, system

# Patch Patterns
from patch_patterns.patterns import (
    PATTERNS_LOCAL,
    get_patterns_config_local,
    get_patterns_config_remote,
)
from patchers import models as patcher_models
from patchers import pdx_patchers, save_patcher
from thread_utils import Threader, WorkerSignals
from ui.utils import get_qt_platform
from utils.platform import (
    WAYLAND,
    X11,
    get_file_access_time,
    get_file_modified_time,
    set_file_access_time,
)

from .resources import AppFont, AppIcon, AppStyle, IconAchievementState, ResourceManager
from .utils import (
    EventFilterMoveResize,
    find_game_path,
    get_screen_info,
    prompt_install_dir,
)
from .windows import (
    ConfigurePatchOptionsDialog,
    ConfigureSavePatchDialog,
    WelcomeDialog,
)

# loggers to hook up to signals
from updater.updater import log as updater_log  # isort: skip
from patchers.pdx_patchers import log as patcher_log  # isort: skip
from patchers.save_patcher import log as patcher_save_log  # isort: skip
from utils.steam_helper import log as steam_log  # isort: skip
from utils.registry_helper import log as registry_log  # isort: skip


log = logging.getLogger("UI")


class StellarisChecksumPatcherGUI(QMainWindow):
    _APP_VERSION = "v" + ".".join([str(v) for v in APP_VERSION[0:3]])
    if len(APP_VERSION) > 3:
        _APP_VERSION += "-"
        _APP_VERSION += "-".join(str(v) for v in APP_VERSION[3:])

    svc = services()
    app_config = svc.config
    settings = svc.settings
    updater = svc.updater

    def __init__(self):
        if not QApplication.instance():
            self.app = QApplication(sys.argv)
        else:
            self.app = QApplication.instance()

        super().__init__()
        self.setObjectName("MainWindow")

        qt_platform = get_qt_platform()
        log.info(f"Qt Platform: {qt_platform}")
        if os_linux():
            if qt_platform not in {WAYLAND, X11}:
                log.warning(f"Unknown Qt plaform on Linux: '{qt_platform}'. Moving/Resizing might behave oddly.")

        self.resources = ResourceManager()
        self.signals = WorkerSignals()

        # --- Get size settings ---
        width, height = self.settings.settings.window_width, self.settings.settings.window_height

        # --- Failsafes ---
        width = 966 if width < 1 else width
        height = 821 if height < 1 else height

        # Pre-compiled regex patterns for terminal log
        self._log_pattern = re.compile(r"(\[(DEBUG|INFO|WARN|ERROR)\])(.*)")

        # Pre-compiled colour map
        self._colour_map = {
            "ERROR": QColor("#E20000"),
            "WARN": QColor("#EAA353"),
            "INFO": QColor("#FFFFFF"),
            "DEBUG": QColor("#888888"),
        }

        # Pre-create text formats (is good performance)
        self._formats = {}
        for level, colour in self._colour_map.items():
            bold_fmt = QTextCharFormat()
            bold_fmt.setForeground(colour)
            bold_fmt.setFontWeight(QFont.Bold)

            # Normal message
            normal_fmt = QTextCharFormat()
            normal_fmt.setForeground(colour)

            self._formats[level] = (bold_fmt, normal_fmt)

        # Set a default format
        self._default_format = QTextCharFormat()
        self._default_format.setForeground(self._colour_map["INFO"])

        # --- Base Size---
        self.resize(width, height)

        self.setWindowOpacity(0.95)
        self.is_patching = False
        self._prev_app_version = ""

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        self.resize_move_filter = EventFilterMoveResize(self)
        self.installEventFilter(self.resize_move_filter)

        # --- Size Policies---
        size_policy_button = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Maximum)
        size_policy_button.setHorizontalStretch(0)
        size_policy_button.setVerticalStretch(0)

        size_policy_project_browser_link = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        size_policy_project_browser_link.setHorizontalStretch(0)
        size_policy_project_browser_link.setVerticalStretch(0)

        size_policy_app_version_label = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        size_policy_app_version_label.setHorizontalStretch(0)
        size_policy_app_version_label.setVerticalStretch(0)

        # ------------------------------------

        self.load_app_styles()

        # --- Frame Layout ---
        self.frame_layout = QVBoxLayout()

        # --- Window Functions Container & Layout q---
        self.window_functions_container_handle = QWidget(self)
        self.window_functions_container_handle.setObjectName("WindowFunctionsContainer")
        self.window_functions_container_handle.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.hlayout_window_functions = QHBoxLayout(self.window_functions_container_handle)
        self.window_functions_container_handle.setProperty("windowDragHandle", True)

        # --- Layout After Terminal ---
        self.hlayout_after_terminal_display = QHBoxLayout()

        # --- Patch Buttons Layout ---
        self.hlayout_patch_buttons = QHBoxLayout()
        # self.hlayout_patch_buttons.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignHCenter)

        # --- Layout for Miscellaneous functions ---
        self.hlayout_misc_functions = QHBoxLayout()
        self.hlayout_misc_functions.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # --- Widgets ---
        # --- Main Frame ---
        self.main_frame = QFrame()
        # self.main_frame.setMinimumSize(QSize(650, 500))
        self.main_frame.setFrameShape(QFrame.WinPanel)
        self.main_frame.setFrameShadow(QFrame.Plain)
        self.main_frame.setContentsMargins(10, 10, 10, 10)
        self.main_frame.setLineWidth(5)
        self.main_frame.setMidLineWidth(0)
        self.main_frame.setProperty("windowDragHandle", True)

        self.lbl_title = QLabel("Patcher")
        self.lbl_title.setObjectName("TitleLabel")
        self.lbl_title.setSizePolicy(size_policy_app_version_label)
        self.lbl_title.setProperty("windowDragHandle", True)

        self.lbl_app_version = QLabel(
            f"{self._APP_VERSION}-{TRACKING_BRANCH}{'-debug' if self.app_config.debug else ''}"
        )
        self.lbl_app_version.setSizePolicy(size_policy_app_version_label)
        self.lbl_app_version.setProperty("windowDragHandle", True)

        # --- Themed Exit Button ---
        self.btn_themed_exit_app = QPushButton("X")
        self.btn_themed_exit_app.setObjectName("ExitButton")
        # self.btn_themed_exit_app.setSizePolicy(size_policy_button)
        self.btn_themed_exit_app.clicked.connect(self.app_quit)

        # --- Terminal Display ---
        self.terminal_display = QPlainTextEdit()
        self.terminal_display.setObjectName("TerminalDisplay")
        self.terminal_display.setReadOnly(True)
        self.terminal_display.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored))
        self.terminal_display.setFrameShape(QFrame.Box)
        self.terminal_display.setFrameShadow(QFrame.Sunken)
        self.terminal_display.setLineWidth(2)
        # self.terminal_display.setOpenExternalLinks(True)

        # --- Terminal Display Size Policy ---
        size_policy_terminal_display = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        size_policy_terminal_display.setHorizontalStretch(0)
        size_policy_terminal_display.setVerticalStretch(0)
        size_policy_terminal_display.setHeightForWidth(self.terminal_display.sizePolicy().hasHeightForWidth())
        self.terminal_display.setSizePolicy(size_policy_terminal_display)

        # --- Project Browser Link ---
        self.project_link_html = """
                <p>Project link: <a href="https://github.com/r0fld4nc3/Stellaris-Exe-Checksum-Patcher">https://github.com/r0fld4nc3/Stellaris-Exe-Checksum-Patcher</a></p>
                """
        self.txt_browser_project_link = QTextBrowser()
        self.txt_browser_project_link.setObjectName("ProjectLink")
        self.txt_browser_project_link.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.txt_browser_project_link.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.txt_browser_project_link.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.txt_browser_project_link.setOpenExternalLinks(True)
        self.txt_browser_project_link.setHtml(self.project_link_html)
        self.txt_browser_project_link.setSizePolicy(size_policy_project_browser_link)
        self.txt_browser_project_link.setMaximumSize(QSize(16777215, 36))

        # --- Fix Save Button---
        self.btn_fix_save_file = QPushButton("Fix Save")
        self.btn_fix_save_file.setFlat(False)
        self.btn_fix_save_file.clicked.connect(self.fix_save_achievements_thread)

        # --- Patch Button ---
        self.btn_patch_executable = QPushButton()
        self.btn_patch_executable.clicked.connect(self.start_patch_game_executable_thread)
        self.btn_patch_executable.setFlat(False)

        # --- Configure Button ---
        self.btn_configure_patch_options = QPushButton()
        self.btn_configure_patch_options.setObjectName("ConfigureButton")
        self.btn_configure_patch_options.setToolTip("Configure patch options and access general utilities.")
        self.btn_configure_patch_options.clicked.connect(self.open_configure_patch_options_window)

        # --- FAQ & Tips Button ---
        self.btn_faq_dialog = QPushButton()
        self.btn_faq_dialog.setObjectName("FAQButton")
        self.btn_faq_dialog.setToolTip("Frequently asked questions and workarounds.")
        self.btn_faq_dialog.clicked.connect(self.open_faq_window)

        # ---Add Widgets to Layouts ---
        # --- Window Functions ---
        self.hlayout_window_functions.addWidget(self.lbl_title, 1, Qt.AlignmentFlag.AlignLeft)
        self.hlayout_window_functions.addWidget(self.btn_configure_patch_options, 0, Qt.AlignmentFlag.AlignRight)
        self.hlayout_window_functions.addWidget(self.btn_faq_dialog, 0, Qt.AlignmentFlag.AlignRight)
        self.hlayout_window_functions.addWidget(self.btn_themed_exit_app, 0, Qt.AlignmentFlag.AlignRight)

        # --- After Terminal Layout ---
        self.hlayout_after_terminal_display.addWidget(self.txt_browser_project_link)

        # --- Patch Buttons Layout ---
        # Add with stretch. The second argument is the "stretch factor".
        # The layout will be divided into 1 + 3 = 4 parts or 25 + 75 = 100 parts
        self.hlayout_patch_buttons.addWidget(self.btn_fix_save_file, 30)
        self.hlayout_patch_buttons.addWidget(self.btn_patch_executable, 70)

        # --- Main Layout ---
        self.setCentralWidget(self.main_frame)
        self.main_frame.setLayout(self.frame_layout)

        # --- Main Frame Layout---
        self.frame_layout.addWidget(self.window_functions_container_handle)
        self.frame_layout.addWidget(self.lbl_app_version)
        self.frame_layout.addWidget(self.terminal_display)
        self.frame_layout.addLayout(self.hlayout_after_terminal_display)
        self.frame_layout.addLayout(self.hlayout_patch_buttons)
        self.frame_layout.addLayout(self.hlayout_misc_functions)

        # --- Add frame_layout to main_frame ---
        self.main_frame.setLayout(self.frame_layout)

        # --- Hook up Signals ---
        # Could be a bit hacky. Ensure created before assign
        log.signals.progress.connect(self.terminal_display_log, Qt.QueuedConnection)
        updater_log.signals.progress.connect(self.terminal_display_log, Qt.QueuedConnection)
        patcher_log.signals.progress.connect(self.terminal_display_log, Qt.QueuedConnection)
        patcher_save_log.signals.progress.connect(self.terminal_display_log, Qt.QueuedConnection)
        steam_log.signals.progress.connect(self.terminal_display_log, Qt.QueuedConnection)
        registry_log.signals.progress.connect(self.terminal_display_log, Qt.QueuedConnection)
        self.signals.terminal_progress.connect(self.terminal_display_log, Qt.QueuedConnection)

        # --- Worker ---
        self.worker = None  # Currently unusued, possibly to deprecate

        # --- Threads ---
        self.thread_pool = QThreadPool()  # Currently unusued, possibly to deprecate
        self.active_threads = []

        # --- Track if Configure Patch Dialog Opened ---
        self.patch_config_dialog: ConfigurePatchOptionsDialog | None = None

        # --- Cache Configuration ---
        self.multi_game_patcher = pdx_patchers.MultiGamePatcher(PATTERNS_LOCAL)

        self.selected_version = patcher_models.KEY_VERSION_LATEST

        self.configuration = patcher_models.PatchConfiguration(
            game="",
            version=patcher_models.KEY_VERSION_LATEST,
            is_proton=(os_windows() or (self.app_config.use_proton)),
        )
        self.save_configuration: patcher_models.GameSavePatchConfig = None
        self.last_conf_game = ""

        # --- Cache available patches to display ---
        self.available_patches: dict = {}
        self.available_versions: List[str] = []

        self.load_settings()

        self.apply_app_style()

        # --- Load Patterns Fetch ---
        self.fetch_patterns_thread = Threader(self.fetch_patterns)
        self.active_threads.append(self.fetch_patterns_thread)
        self.fetch_patterns_thread.signals.started.connect(self.disable_ui_elements)
        self.fetch_patterns_thread.signals.result.connect(self.enable_ui_elements)
        self.fetch_patterns_thread.signals.result.connect(self.apply_app_style)  # Also ensure style is updated
        self.fetch_patterns_thread.signals.result.connect(self.check_file_already_patched)
        self.fetch_patterns_thread.start()

        self.check_update()

    def load_settings(self):
        self._prev_app_version = self.settings.settings.app_version
        self.settings.settings.app_version = self._APP_VERSION
        self.updater.set_local_version(str(self._APP_VERSION))

        if self.configuration.game:
            _last_platform = self.settings.game(self.configuration.game).last_patched_platform
            if _last_platform:
                if os_linux() or os_darwin():
                    self.configuration.is_proton = _last_platform.lower() == patcher_models.Platform.WINDOWS

    def load_app_styles(self):
        """Loads Styles, Icons and Fonts"""
        # --- Icons ---
        self.window_icon_win = self.resources.get_icon(AppIcon.WINDOW_WIN)
        self.window_icon_unix = self.resources.get_icon(AppIcon.WINDOW_UNIX)

        self.save_patch_icon = self.resources.get_icon(AppIcon.SAVE_PATCH_ICON)
        self.configure_icon = self.resources.get_icon(AppIcon.CONFIGURE_ICON)

        # --- Fonts ---
        self.app_font_bold = self.resources.load_font(AppFont.ORBITRON_BOLD)

    def apply_app_style(self):
        # --- Set App Constraints ---
        conf_game = self.configuration.game

        self.window_title = f"{conf_game} Patcher"
        self.window_title_update_available = self.window_title + " (UPDATE AVAILABLE)"
        self.window_title_with_app_version = (
            f"{self.window_title} ({self._APP_VERSION}){'-debug' if self.app_config.debug else ''}"
        )

        self.setWindowTitle(self.window_title_with_app_version)
        if os_windows():
            self.setWindowIcon(self.window_icon_win)
        else:
            self.setWindowIcon(self.window_icon_unix)

        # --- Styles---
        stylesheet_content = self.resources.get_stylesheet(conf_game)
        self.setStyleSheet(stylesheet_content)

        # --- Label Title ---
        self.lbl_title.setText(self.window_title)
        if self.settings.settings.update_available:
            self.lbl_title.setText(self.window_title_update_available)
        self.lbl_title.setFont(QFont(self.app_font_bold, 24))
        self.lbl_title.setMinimumSize(QSize(24, 36))
        self.lbl_title.setMaximumSize(QSize(16777215, 36))
        self.lbl_title.setContentsMargins(5, 2, 5, 2)

        # --- Themed Exit Button ---
        self.btn_themed_exit_app.setFont(self.app_font_bold)
        self.btn_themed_exit_app.setFont(QFont(self.app_font_bold, 20))
        self.btn_themed_exit_app.setFixedSize(QSize(48, 48))

        # --- FAQ & Tips Button ---
        self.btn_faq_dialog.setText("?")
        self.btn_faq_dialog.setFont(QFont(self.app_font_bold, 20))
        self.btn_faq_dialog.setFixedSize(QSize(48, 48))

        # --- Fix Save Button ---
        self.btn_fix_save_file.setIcon(self.save_patch_icon)
        self.btn_fix_save_file.setIconSize(QSize(64, 64))
        self.btn_fix_save_file.setFont(QFont(self.app_font_bold, 12))
        # Allow/Block save patching for supported games
        self.btn_fix_save_file.setEnabled(self.configuration.game in SUPPORTED_GAMES)

        # --- Patch Icon ---
        # Only update if we're in __init__ or games differ
        if not hasattr(self, "patch_icon") or conf_game != self.last_conf_game:
            self.random_achievement = self.resources.get_random_achievement_icon(conf_game)
            self.patch_icon = self.random_achievement.get(IconAchievementState.LOCKED)

        # --- Patch Button ---
        # self.btn_patch_executable.setText("Patch Executable")
        self.btn_patch_executable.setIcon(self.patch_icon)
        self.btn_patch_executable.setIconSize(QSize(64, 64))
        self.btn_patch_executable.setFont(QFont(self.app_font_bold, 14))
        self.btn_patch_executable.setToolTip("Start Patch Game Binary")
        # self.btn_patch_executable.setMaximumSize(QSize(80, 80))

        # --- Configure Button ---
        self.btn_configure_patch_options.setIcon(self.configure_icon)
        self.btn_configure_patch_options.setIconSize(QSize(48, 48))
        self.btn_configure_patch_options.setFixedSize(QSize(48, 48))

    @Slot(str)
    def terminal_display_log(self, t_log: str):
        cursor = self.terminal_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.terminal_display.setTextCursor(cursor)

        match = self._log_pattern.match(t_log)

        if match:
            level_tag = match.group(1)
            level_name = match.group(2)
            msg = match.group(3)

            bold_fmt, normal_fmt = self._formats[level_name]

            cursor.insertText(level_tag, bold_fmt)
            cursor.insertText(msg + "\n", normal_fmt)
        else:
            cursor.insertText(t_log + "\n", self._default_format)

        self.terminal_display.ensureCursorVisible()

    def set_terminal_clickable(self, is_clickable: bool):
        if is_clickable:
            self.terminal_display.setTextInteractionFlags(~Qt.LinksAccessibleByMouse)  # the ~ negates the flag
        else:
            self.terminal_display.setTextInteractionFlags(Qt.LinksAccessibleByMouse)

    def enable_ui_elements(self):
        self.btn_patch_executable.setEnabled(True)
        self.btn_fix_save_file.setEnabled(self.configuration.game in SUPPORTED_GAMES)
        self.btn_configure_patch_options.setEnabled(True)
        self.terminal_display.setEnabled(True)

    def disable_ui_elements(self):
        self.btn_patch_executable.setDisabled(True)
        self.btn_fix_save_file.setDisabled(True)
        self.btn_configure_patch_options.setDisabled(True)
        self.terminal_display.setDisabled(True)

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

    def patch_game_executable(self, game_binary_path: Path) -> bool:
        """
        Attemps to perform all necessary steps to patch the given game binary.
        """

        self.is_patching = True

        log.info(f"Proceeding to patch executable: {game_binary_path}")

        # Configuration
        if not self.configuration:
            log.error(f"No configuration available.")
            return False

        log.info(f"Using configuration: {self.configuration}", silent=True)

        # Check for empty game
        if not self.configuration.game:
            log.error(f"Configuration game is empty")
            return False

        # Get patcher
        patcher: pdx_patchers.GamePatcher = self.multi_game_patcher.get_game_patcher(
            self.configuration.game, self.configuration.version
        )

        if not patcher:
            log.error(f"Failed to initialise patcher for {self.configuration.game}")
            return False

        patches_to_apply = [patch_name for patch_name in self.configuration.selected_patches]

        # --- Determine platform ---
        platform = (
            patcher_models.Platform.detect_current()
            if not self.configuration.is_proton
            else patcher_models.Platform.WINDOWS
        )

        if self.patch_config_dialog and not patches_to_apply:
            log.warning(f"Aborting Patch process. No patches selected for configuration: {self.configuration}")
            return False

        if not patches_to_apply:
            log.warning(
                f"No patches selected or available. Applying all available patches corresponding to '{self.selected_version}' version.\nUse the configuration window to select patches to apply."
            )
            patches_to_apply = [
                patch_name
                for patch_name, config in self.multi_game_patcher.get_available_patches_for_game(
                    self.configuration.game, self.configuration.version, platform=platform
                ).items()
                if config.enabled or config.required
            ]

        with self.settings.batch_update():
            self.settings.game(self.configuration.game).last_patched_platform = platform
            self.settings.game(self.configuration.game).last_patched_version = self.configuration.version

        log.info(f"Patches to apply: {patches_to_apply}", silent=True)

        results = patcher.patch_file_multiple(game_binary_path, patches_to_apply, platform=platform)

        self.signals.terminal_progress.emit(" ")

        all_patches_success = True

        applied: list = []
        for patch, success in results.items():
            if success:
                applied.append(patch)
            else:
                if all_patches_success:
                    all_patches_success = False
                log.warning(f"Failed patch: {patch}")

        if all_patches_success:
            # Unlock (colour) achievement icon to signify all patches were successful.
            # Leave uncoloured to signify some have failed.
            self.btn_patch_executable.setIcon(self.random_achievement.get(IconAchievementState.UNLOCKED))
            log.info("Finished. Close the patcher and go play!")

        if all_patches_success or applied:
            # Get times to save
            original_mtime = get_file_modified_time(game_binary_path)
            access_ts = set_file_access_time(game_binary_path, None, original_mtime)

            with self.settings.batch_update():
                # Save applied patches
                self.settings.game(self.configuration.game).patches = applied
                # Save last access time to track if already patched
                self.settings.game(self.configuration.game).last_patched_timestamp = access_ts

        self.swap_btn_patch_to_launch_game()

        return all_patches_success

    def _find_game_path_worker_thread(self) -> Optional[Path]:
        """
        WORKER FUNCTION: Tries to find the game path automatically.
        Returns the path if found, otherwise None.
        """

        return find_game_path(self.multi_game_patcher, self.configuration)

    def start_patch_game_executable_thread(self):
        if self.is_patching:
            return

        self.terminal_display.clear()
        self.disable_ui_elements()

        self.active_threads.clear()

        # Configuration
        msgbox = QMessageBox(self)
        if not self.configuration:
            log.error(f"No configuration available.")
            msgbox.setWindowTitle("No Configuration")
            msgbox.setText("Please choose a configuration.")
            msgbox.exec_()
            self.enable_ui_elements()
            return False
        elif not self.configuration.game:
            log.error(f"Configuration does not provide a game.")
            msgbox.setWindowTitle("No Game Selected")
            msgbox.setText("Please select a game to patch.")
            msgbox.exec_()
            self.enable_ui_elements()
            return False

        # Attempt to find and establish paths
        self.path_finder_thread = Threader(target=self._find_game_path_worker_thread)
        self.path_finder_thread.signals.result.connect(self._path_found_or_failed)
        self.active_threads.append(self.path_finder_thread)
        self.path_finder_thread.start()

    def _path_found_or_failed(self, found_path: Optional[Path]):
        """
        SLOT FUNCTION: Runs on the main thread after _find_game_path_worker_thread
        """

        game_binary_path = found_path

        if not game_binary_path:
            # Automatic search failed
            log.info("Asking for user-provided game executable path.")

            user_selected_path = prompt_install_dir(game_name=self.configuration.game)

            if user_selected_path:
                game_binary_path = user_selected_path
            else:
                # User cancelled
                log.warning(f"User cancelled location picker. Aborting patch.")
                self.enable_ui_elements()
                return

        game_binary_path_posix = game_binary_path.resolve().as_posix()

        if game_binary_path:
            if (os_linux() or self.app_config.use_proton) and self.configuration.is_proton:
                self.settings.game(self.configuration.game).proton_install_path = game_binary_path_posix
            elif os_darwin() and self.configuration.is_proton:
                self.settings.game(self.configuration.game).proton_install_path = game_binary_path_posix
            else:
                self.settings.game(self.configuration.game).install_path = game_binary_path_posix
            self._run_patcher_worker_thread(game_binary_path)

    def _run_patcher_worker_thread(self, game_binary_path: Path):
        """
        Starts the final worker thread to perform the patch
        """

        patch_thread = Threader(target=self.patch_game_executable, args=(game_binary_path,))
        patch_thread.signals.finished.connect(self._patching_finished)
        self.active_threads.append(patch_thread)
        patch_thread.start()

    def _patching_finished(self):
        """
        SLOT: Runs on the main thread
        """

        log.info("Patching process finished.")
        self.is_patching = False
        self.enable_ui_elements()

        self.active_threads.clear()

    def fix_save_achievements_thread(self):
        if self.is_patching:
            return

        self.terminal_display.clear()

        saver = save_patcher.StellarisSavePatcher(self.configuration.game, self.save_configuration)

        # --- Ask for save path ---
        # Hack for empty save games folder List. Otherwise won't open dialog
        save_games_folders: list = saver.save_games_folders
        if not save_games_folders:
            save_games_folders.append("")
        # ---

        initial_open_folder = ""
        if save_games_folders:
            for p in save_games_folders:
                if Path(p).exists():
                    initial_open_folder = p
                    break

        save_file_path = QFileDialog().getOpenFileName(
            caption="Save file to repair...",
            dir=str(initial_open_folder),
            filter=(f"Save File (*{saver.save_extension})"),
        )[0]

        if save_file_path or save_file_path != "":
            log.info(f"Save file: {save_file_path}")

        if not save_file_path:
            return False

        # --- Configure Fixes
        fixes_config = self.open_configure_save_patch_options_window()

        if not fixes_config:
            log.info(f"No fixes: {fixes_config}", silent=True)
            return False

        log.info(f"Fixes: {fixes_config}", silent=True)

        saver.set_config(fixes_config)

        thread_repair_save = Threader(target=lambda save_file=save_file_path: saver.repair_save(save_file))
        thread_id = thread_repair_save.currentThread()
        thread_repair_save.setTerminationEnabled(True)
        # self.threader.signals.failed.connect() # TODO
        thread_repair_save.signals.started.connect(self.disable_ui_elements)
        thread_repair_save.signals.finished.connect(self.enable_ui_elements)
        thread_repair_save.signals.finished.connect(self.on_finished_save_repair)
        thread_repair_save.signals.finished.connect(lambda: self.remove_thread(thread_id))  # Removes thead by ID
        self.active_threads.append(thread_repair_save)
        thread_repair_save.start()

    def on_finished_save_repair(self) -> None:
        if self.app_config.is_cheated_save:
            msgbox = QMessageBox(self)
            msgbox.setWindowTitle("Cheated Save")
            msgbox.setText("WARNING: Save is a cheated save and the fixes might not work.")
            msgbox.setStyleSheet("QLabel{ color: white}")
            msgbox.exec_()

        # Reset the variable
        self.app_config.is_cheated_save = False

    def open_configure_patch_options_window(self):
        log.info("Opening patch configuration window", silent=True)

        # Important: Work in a copy of the configuration to retain
        # selections whether user clicks Cancel or Ok in the
        # configuration window.
        # This gives us flexibility of only applying the new config
        # when the user accepts the dialog.
        _is_new_dialog = self.patch_config_dialog is None

        if not self.patch_config_dialog:
            # Pass a copy of the config
            config_copy = copy.deepcopy(self.configuration)

            self.patch_config_dialog = ConfigurePatchOptionsDialog(
                patcher=self.multi_game_patcher,
                configuration=config_copy,
                font=QFont(self.app_font_bold, 12),
                window_icon=self.windowIcon(),
                parent=self,
            )
        else:
            # Refresh with a new copy if it exists
            config_copy = copy.deepcopy(self.configuration)
            self.patch_config_dialog.patch_options_configuration = config_copy
            self.patch_config_dialog._populate_options()  # Refresh UI

        # Set current game as last selected
        self.last_conf_game = self.configuration.game

        # Show Configure Dialog and handle returns
        if self.patch_config_dialog.exec() == QFileDialog.DialogCode.Accepted:
            # Only apply the changes to the configuration now
            self.configuration = self.patch_config_dialog.get_configuration()

            # Also update app style
            self.apply_app_style()

            self.settings.settings.last_selected_game = self.configuration.game

            log.info(f"Configuration updated: {self.configuration}", silent=True)

            # --- Determine platform ---
            platform = (
                patcher_models.Platform.detect_current()
                if not self.configuration.is_proton
                else patcher_models.Platform.WINDOWS
            )

            available_patches = self.multi_game_patcher.get_available_patches_for_game(
                self.configuration.game, self.configuration.version, platform=platform
            )
            selected_patches_str = ", ".join(
                [v.display_name for k, v in available_patches.items() if k in self.configuration.selected_patches]
            )

            log.info(f"Selected patches: {selected_patches_str}")

            if (
                self.last_conf_game != self.configuration.game
                or self.configuration.selected_patches != config_copy.selected_patches
            ):
                self.swap_btn_patch_to_patch_binary()
        else:
            # If first open and user cancelled, still populate with defaults
            # This should ensure patching works even if the user never
            # accepts the dialog.
            if _is_new_dialog and not self.configuration.selected_patches:
                self.configuration.selected_patches = (
                    self.patch_config_dialog.patch_options_configuration.selected_patches.copy()
                )
            log.info("Configuration unchanged.", silent=True)

    def open_configure_save_patch_options_window(self):
        log.info("Opening save patch configuration window", silent=True)

        dialog = ConfigureSavePatchDialog(
            self.configuration.game,
            font=QFont(self.app_font_bold, 10),
            window_icon=self.windowIcon(),
            parent=self,
        )

        # Show Configure Dialog and handle returns
        if dialog.exec_() == QFileDialog.DialogCode.Accepted:
            self.save_configuration = dialog.get_configuration()

            log.info(
                f"Selected save patches: {[opt.display_name for opt in self.save_configuration.get_enabled_options()]}"
            )
        else:
            log.info("Configuration unchanged.", silent=True)

        return self.save_configuration

    def check_update(self):
        last_checked = self.settings.settings.update_last_checked
        now = int(time.time())

        log.debug("Trigger update check.")
        log.debug(
            f"{self._APP_VERSION} == {self._prev_app_version} = {self._APP_VERSION == self._prev_app_version}",
            silent=True,
        )
        log.debug(
            f"{now} - {last_checked} < {self.app_config.update_check_cooldown} = {now - last_checked < self.app_config.update_check_cooldown}",
            silent=True,
        )

        if self._APP_VERSION == self._prev_app_version:
            if now - last_checked < self.app_config.update_check_cooldown:
                self.check_update_finished()
                return

        thread_update = Threader(target=self.updater.check_for_update)
        # thread_id = thread_update.currentThread()
        self.active_threads.append(thread_update)
        thread_update.start()
        thread_update.signals.finished.connect(self.check_update_finished)

    def check_update_finished(self):
        updater_last_checked = self.updater.last_checked_timestamp

        # No online check was performed
        if updater_last_checked <= 1:
            update_available = self.settings.settings.update_available
        else:
            self.settings.settings.update_last_checked = self.updater.last_checked_timestamp
            if self.updater.has_new_version:
                self.settings.settings.update_available = True
                update_available = True
            else:
                self.settings.settings.update_available = False
                update_available = False

        if update_available:
            html = (
                self.txt_browser_project_link.toHtml().replace("</p>", "").replace("</body>", "").replace("</html>", "")
            )
            html += '<span style=" font-weight:700;"> (UPDATE AVAILABLE)</span></p></body></html>'
            self.txt_browser_project_link.setHtml(html)
            self.lbl_title.setText(self.window_title_update_available)
            self.settings.settings.update_available = True
        else:
            self.lbl_title.setText(self.window_title)

    def open_faq_window(self):
        msgbox = QMessageBox(self)
        msgbox.setStyleSheet("QLabel{ color: white; font-size: 18px}")
        msgbox.setWindowTitle("Quick Tips & FAQs")
        msgbox.setMaximumWidth(800)
        msg = """Patch Failed?
        * After a game update, that typically changes the checksum, it is
            advised to delete both executables and validate Game Files with 
            Steam in order for it to redownload the correct one.
            Go to Utilities Tab and validate Integrity of Game Files.
            After this, apply the patch and it should work.

        * The overall patterns may have changed. If this is the case, open
        an Issue over on GitHub (or look for an existing one) so we can
        fix and update the patterns file as soon as possible.
        
        * It is possible that you're patching an already patched game,
            but due to some pattern recognition changes, it could be that
            the already patched pattern was not recognised as it is
            looking for a different one. This makes it seem like the patch
            failed when in reality the file is already patched.
            Delete and validate files with Steam.

        * After a game update, if you notice things acting up, ALWAYS delete
        the existing executable and validate integrity of files on Steam before
        patching again. This can be quickly accessed via the cogwheel and the
        dedicated button in General Utilities tab to validate game files.
        """
        msgbox.setInformativeText(msg)
        msgbox.exec_()

    def fetch_patterns(self):
        can_fetch_remote = all(
            [
                not self.app_config.prevent_conn,
                not self.app_config.use_local_patterns,
                not self.settings.settings.force_local_patterns,
            ]
        )

        log.info(f"Can fetch remote: {can_fetch_remote}", silent=True)

        # --- Patch info---
        if can_fetch_remote:
            # Download patch patterns once
            # This allows us to store it when they don't exist and use local only if required
            log.info("Downloading remote patch patterns to local storage.")
            get_patterns_config_remote()
        else:
            # We are preventing a connection or forcing the usage of local patterns

            if not PATTERNS_LOCAL.exists() and not self.app_config.prevent_conn:
                # Local patterns don't exist, pull remote first, we allow connections
                log.info(
                    "Force local patterns is off. Downloading remote patch patterns to local storage.", silent=True
                )
                get_patterns_config_remote()
            else:
                get_patterns_config_local()

        precached_game = self.settings.settings.last_selected_game  # Can be None or "" or pre-set with a game name
        if not precached_game:
            log.info(
                f"Pre-cached game is empty. Inserting with entry at index 0 of {SUPPORTED_GAMES}: {SUPPORTED_GAMES[0]}",
                silent=True,
            )
            precached_game = SUPPORTED_GAMES[0]

        self.multi_game_patcher.reload_patterns()

        # Determine platform
        last_platform_str = self.settings.game(precached_game).last_patched_platform
        if last_platform_str:
            try:
                platform = patcher_models.Platform(last_platform_str.lower())
                log.info(f"Using saved platform for {precached_game}: {platform}", silent=True)
            except ValueError:
                log.warning(f"Invalid saved platform '{last_platform_str}', auto-detecting", silent=True)
                platform = system() if not self.configuration.is_proton else patcher_models.Platform.WINDOWS
        else:
            platform = system()
            log.info(f"No saved platform, auto-detected: {platform}", silent=True)

        # Get available version and find first one with patches available
        all_versions = self.multi_game_patcher.get_available_versions(precached_game)
        last_patched_version = self.settings.game(precached_game).last_patched_version
        log.info(f"Last patched version: {last_patched_version}", silent=True)
        selected_version = patcher_models.KEY_VERSION_LATEST  # Default fallback

        for version in all_versions:
            patches = self.multi_game_patcher.get_available_patches_for_game(precached_game, version, platform)
            if patches:
                selected_version = version
                log.info(
                    f"Selected version '{version}' for {precached_game} on {platform} ({len(patches)}) patches available.",
                    silent=True,
                )
                break
        else:
            log.warning(
                f"No version with patches found for {precached_game} on {platform}, using fallback '{selected_version}'",
                silent=True,
            )

        # Update selection version cache
        self.selected_version = selected_version

        # --- Cache Configuration ---
        self.configuration = patcher_models.PatchConfiguration(
            game=precached_game,
            version=self.selected_version,
            is_proton=(os_windows() or (os_linux() and self.app_config.use_proton)),
        )
        self.last_conf_game = self.configuration.game

        if self.configuration.game:
            self.available_patches = self.multi_game_patcher.get_available_patches_for_game(
                self.configuration.game, version=self.selected_version
            )
            self.available_versions = self.multi_game_patcher.get_available_versions(self.configuration.game)

    def check_file_already_patched(self):
        game = self.configuration.game

        log.info(f"Checking if {game} is already patched.")

        if self.configuration.is_proton:
            install_path = self.settings.game(self.configuration.game).proton_install_path
        else:
            install_path = self.settings.game(self.configuration.game).install_path

        if not Path(install_path).exists():
            log.error(f"File does not exist: {install_path}")
            return False

        # Check if file already patched
        file_access_time = get_file_access_time(install_path)
        last_access_time = self.settings.game(game).last_patched_timestamp

        if file_access_time == last_access_time:
            log.info("File already patched.")
            return True

        log.info(f"{game} has not been patched yet.")

        return False

    def swap_btn_patch_to_patch_binary(self):
        log.info(
            f"Want to connect new signal to Patch Executable Button: self.start_patch_game_executable_thread",
            silent=True,
        )

        try:
            log.info(f"Disconnecting all signals from patch executable button", silent=True)
            self.btn_patch_executable.clicked.disconnect()
        except Exception as e:
            # No signals exist
            pass

        self.btn_patch_executable.clicked.connect(self.start_patch_game_executable_thread)
        self.btn_patch_executable.setText("")
        self.btn_patch_executable.setToolTip("Start Patch Game Binary")
        self.btn_patch_executable.setIcon(self.random_achievement.get(IconAchievementState.LOCKED))

        log.info(
            f"Connected new signal to Patch Game Executable Button: self.start_patch_game_executable_thread",
            silent=True,
        )

    def swap_btn_patch_to_launch_game(self):
        log.info(
            f"Want to connect new signal to Patch Executable Button: lambda: STEAM.launch_game_app_name({self.configuration.game.lower()})",
            silent=True,
        )

        try:
            log.info(f"Disconnecting all signals from patch executable button", silent=True)
            self.btn_patch_executable.clicked.disconnect()
        except Exception as e:
            # No signals exist
            pass

        self.btn_patch_executable.clicked.connect(
            lambda: self.svc.steam_helper.launch_game_app_name(self.configuration.game.lower())
        )

        self.btn_patch_executable.setText(f"Launch {self.configuration.game}")
        self.btn_patch_executable.setToolTip("Launch the game through Steam.")

        log.info(
            f"Connected new signal to Patch Game Executable Button: lambda: STEAM.launch_game_app_name({self.configuration.game.lower()})",
            silent=True,
        )

    def show_welcome_dialog(self):
        has_accepted_dialog = self.settings.settings.accepted_welcome_dialog
        if not has_accepted_dialog:
            # --- Show welcome dialog ---
            welcome_dialog = WelcomeDialog(QFont(self.app_font_bold, 8), window_icon=self.windowIcon(), parent=self)
            welcome_dialog.show()

    def show(self):
        super().show()
        self.adapt_to_screen_size()
        self.terminal_display.clear()

        self.show_welcome_dialog()

        sys.exit(self.app.exec_())

    def closeEvent(self, event):
        log.info("Application is closing. Shutting down procedure")

        self.settings.save_settings()

        log.info("Shutdown")
        event.accept()
        self.app_quit()

    def app_quit(self):
        log.info("Quitting Application. Performing graceful shutdown procedure.")

        with self.settings.batch_update():
            self.settings.settings.app_version = self._APP_VERSION
            self.settings.settings.window_width = self.width()
            self.settings.settings.window_height = self.height()

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

        log.info("Application shutdown.")

        sys.exit(0)

    def adapt_to_screen_size(self, parent=None, width_pct: int = 40, height_pct: int = 60):
        screen_info = get_screen_info(self.app)

        saved_w = self.settings.settings.window_width
        saved_h = self.settings.settings.window_height

        if parent:
            screen = parent.screen()
        else:
            screen = QApplication.primaryScreen()

        screen_geometry = screen.availableGeometry()

        if screen_info[0] <= 1500 or screen_info[1] <= 1000 or screen_info[2] <= 0.7:
            width = int(screen_geometry.width() * (width_pct * 0.01))
            height = int(screen_geometry.height() * (height_pct * 0.01))
        elif not saved_h or not saved_w:
            width = int(screen_geometry.width() * (width_pct * 0.01))
            height = int(screen_geometry.height() * (height_pct * 0.01))
        elif saved_w and saved_h:
            width = saved_w
            height = saved_h
        else:
            width = int(screen_geometry.width() * (width_pct * 0.01))
            height = int(screen_geometry.height() * (height_pct * 0.01))

        # Set minimum size to screen percentage
        min_w = int(screen_geometry.width() * (30 * 0.01))
        min_h = int(screen_geometry.height() * (45 * 0.01))
        log.info(f"Set Minimum Size: ({min_w=}, {min_h})", silent=True)
        self.setMinimumSize(min_w, min_h)

        # Set initial size
        self.resize(width, height)

        # Center the window on the screen
        self.move(screen_geometry.center().x() - self.width() // 2, screen_geometry.center().y() - self.height() // 2)
