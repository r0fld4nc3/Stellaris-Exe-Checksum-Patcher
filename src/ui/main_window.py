import os  # isort: skip
import sys  # isort: skip
import time  # isort: skip

from pathlib import Path  # isort: skip
import subprocess  # isort: skip
from PySide6.QtWidgets import (  # isort: skip
    QAbstractScrollArea,
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
    QCheckBox,
    QMessageBox,
    QMainWindow,
)
from PySide6.QtCore import Qt, QUrl  # isort: skip

from patchers import (  # isort: skip
    pdx_patchers,
)

from typing import List, Optional, Union

from patchers import models as patcher_models

from .configure_patch_window import ConfigurePatchOptionsDialog

from PySide6.QtCore import Qt, QSize, QThreadPool, Slot  # isort: skip
from PySide6.QtGui import QIcon, QFont, QFontDatabase  # isort: skip


from conf_globals import (  # isort: skip
    APP_VERSION,
    BRANCH,
    IS_DEBUG,
    LOG_LEVEL,
    UPDATE_CHECK_COOLDOWN,
    USE_LOCAL_PATTERNS,
    SETTINGS,
    OS,
    updater,
)

from .ui_utils import WorkerSignals, Threader, EventFilterMoveResize, get_screen_info, set_icon_gray  # isort: skip
from logger import create_logger  # isort: skip
from patchers.save_patcher import repair_save, get_user_save_folder  # isort: skip

# loggers to hook up to signals
from updater.updater import log as updater_log  # isort: skip
from patchers.pdx_patchers import log as patcher_log  # isort: skip
from patchers.save_patcher import log as patcher_save_log  # isort: skip
from utils.steam_helper import log as steam_log  # isort: skip
from utils.registry_helper import log as registry_log  # isort: skip

# Patch Patterns
from patch_patterns.patterns import PATTERNS_LOCAL, get_patterns_config_remote  # isort: skip

log = create_logger("UI", LOG_LEVEL)


class StellarisChecksumPatcherGUI(QMainWindow):
    _APP_VERSION = "v" + ".".join([str(v) for v in APP_VERSION[0:3]])
    if len(APP_VERSION) > 3:
        _APP_VERSION += "-"
        _APP_VERSION += "-".join(str(v) for v in APP_VERSION[3:])
    icons = Path(__file__).parent / "icons"
    fonts = Path(__file__).parent / "fonts"
    styles_path = Path(__file__).parent / "styles"

    def __init__(self):
        if not QApplication.instance():
            self.app = QApplication(sys.argv)
        else:
            self.app = QApplication.instance()

        super().__init__()

        self.setObjectName("MainWindow")

        self.signals = WorkerSignals()

        # --- Get size settings ---
        width = SETTINGS.get_window_width()
        height = SETTINGS.get_window_height()

        # --- Failsafes ---
        if width < 1:
            width = 966
        if height < 1:
            height = 821

        # --- Base Size---
        self.resize(width, height)

        # --- Styles---
        self.load_stylesheet(f"{self.styles_path}/stellaris.qss")

        self.setWindowOpacity(0.95)

        self.is_patching = False

        self.window_title = "Stellaris Checksum Patcher"

        self._prev_app_version = ""

        self.window_title_with_app_version = f"{self.window_title} ({self._APP_VERSION}){'-debug' if IS_DEBUG else ''}"

        # --- Icons and Fonts---
        window_icon_win = QIcon(str(self.icons / "stellaris_checksum_patcher_icon.ico"))
        window_icon_unix = QIcon(str(self.icons / "stellaris_checksum_patcher_icon.png"))
        patch_icon = QIcon(str(self.icons / "patch_icon.png"))
        save_patch_icon = QIcon(str(self.icons / "save_patch_icon.png"))
        configure_icon = QIcon(str(self.icons / "configure_icon_big.png"))

        orbitron_bold_font_id = QFontDatabase.addApplicationFont(str(self.fonts / "Orbitron-Bold.ttf"))
        self.orbitron_bold_font = QFontDatabase.applicationFontFamilies(orbitron_bold_font_id)[0]

        # --- Instance icon assignment ---
        self.stellaris_patch_icon = patch_icon
        self.stellaris_save_patch_icon = set_icon_gray(save_patch_icon)

        # --- Set App Constraints ---
        self.setWindowTitle(self.window_title_with_app_version)
        if OS.WINDOWS:
            self.setWindowIcon(window_icon_win)
        else:
            self.setWindowIcon(window_icon_unix)
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

        # --- Frame Layout---
        self.frame_layout = QVBoxLayout()

        # --- Window Functions Container & Layout---
        self.window_functions_container_handle = QWidget(self)
        self.window_functions_container_handle.setObjectName("WindowFunctionsContainer")
        self.window_functions_container_handle.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.hlayout_window_functions = QHBoxLayout(self.window_functions_container_handle)

        # --- Layout After Terminal ---
        self.hlayout_after_terminal_display = QHBoxLayout()

        # --- Patch Buttons Laytout ---
        self.hlayout_patch_buttons = QHBoxLayout()
        # self.hlayout_patch_buttons.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignHCenter)

        # --- Layout for Miscellaneous functions
        self.hlayout_misc_functions = QHBoxLayout()
        self.hlayout_misc_functions.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # ---Widgets---
        # --- Main Frame---
        self.main_frame = QFrame()
        self.main_frame.setMinimumSize(QSize(650, 500))
        self.main_frame.setFrameShape(QFrame.WinPanel)
        self.main_frame.setFrameShadow(QFrame.Plain)
        self.main_frame.setContentsMargins(10, 10, 10, 10)
        self.main_frame.setLineWidth(5)
        self.main_frame.setMidLineWidth(0)

        self.lbl_title = QLabel(self.window_title)
        self.lbl_title.setObjectName("TitleLabel")
        self.lbl_title.setFont(QFont(self.orbitron_bold_font, 24))
        self.lbl_title.setSizePolicy(size_policy_app_version_label)
        self.lbl_title.setMinimumSize(QSize(24, 36))
        self.lbl_title.setMaximumSize(QSize(16777215, 36))
        self.lbl_title.setContentsMargins(5, 2, 5, 2)

        self.lbl_app_version = QLabel(f"{self._APP_VERSION}-{BRANCH}{'-debug' if IS_DEBUG else ''}")
        self.lbl_app_version.setSizePolicy(size_policy_app_version_label)

        # --- Themed Exit Application---
        self.btn_themed_exit_app = QPushButton("X")
        self.btn_themed_exit_app.setObjectName("ExitButton")
        self.btn_themed_exit_app.setFont(self.orbitron_bold_font)
        self.btn_themed_exit_app.setSizePolicy(size_policy_button)
        self.btn_themed_exit_app.setMinimumSize(QSize(32, 32))
        self.btn_themed_exit_app.clicked.connect(self.app_quit)

        # --- Terminal Display---
        self.terminal_display = QTextBrowser()
        self.terminal_display.setObjectName("TerminalDisplay")
        self.terminal_display.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored))
        self.terminal_display.setFrameShape(QFrame.Box)
        self.terminal_display.setFrameShadow(QFrame.Sunken)
        self.terminal_display.setLineWidth(2)
        self.terminal_display.setOpenExternalLinks(True)
        # --- Terminal Display- Size Policy---
        size_policy_terminal_display = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        size_policy_terminal_display.setHorizontalStretch(0)
        size_policy_terminal_display.setVerticalStretch(0)
        size_policy_terminal_display.setHeightForWidth(self.terminal_display.sizePolicy().hasHeightForWidth())
        self.terminal_display.setSizePolicy(size_policy_terminal_display)

        # --- Project Browser Link---
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
        self.btn_fix_save_file = QPushButton("Fix Save Achievements\n(Coming soon..)")
        self.btn_fix_save_file.setIcon(self.stellaris_save_patch_icon)
        self.btn_fix_save_file.setIconSize(QSize(64, 64))
        self.btn_fix_save_file.setFont(QFont(self.orbitron_bold_font, 12))
        self.btn_fix_save_file.setFlat(False)
        self.btn_fix_save_file.clicked.connect(self.fix_save_achievements_thread)
        self.btn_fix_save_file.setDisabled(True)  # TODO: Delete line when it is time

        # --- Patch Button---
        self.btn_patch_executable = QPushButton("Patch Executable")
        self.btn_patch_executable.setIcon(self.stellaris_patch_icon)
        self.btn_patch_executable.setIconSize(QSize(64, 64))
        self.btn_patch_executable.setFont(QFont(self.orbitron_bold_font, 14))
        self.btn_patch_executable.clicked.connect(self.start_patch_game_executable_thread)
        self.btn_patch_executable.setFlat(False)

        # --- Configure Button---
        self.btn_configure_patch_options = QPushButton()
        self.btn_configure_patch_options.setObjectName("ConfigureButton")
        self.btn_configure_patch_options.setIcon(configure_icon)
        self.btn_configure_patch_options.setIconSize(QSize(64, 64))
        self.btn_configure_patch_options.setFixedSize(QSize(64, 64))
        self.btn_configure_patch_options.clicked.connect(self.open_configure_patch_options_window)

        # --- Show Game Folder Button---
        self.btn_show_game_folder = QPushButton("Show Game Folder")
        self.btn_show_game_folder.setFlat(False)
        self.btn_show_game_folder.setSizePolicy(size_policy_button)
        self.btn_show_game_folder.setMinimumSize(QSize(100, 48))
        self.btn_show_game_folder.setMaximumSize(QSize(16777215, 64))
        self.btn_show_game_folder.setFont(QFont(self.orbitron_bold_font, 14))
        self.btn_show_game_folder.clicked.connect(self.show_game_folder)

        # --- Open Config Directory Button---
        self.btn_show_app_config_dir = QPushButton("Show Config Folder")
        self.btn_show_app_config_dir.setFlat(False)
        self.btn_show_app_config_dir.setSizePolicy(size_policy_button)
        self.btn_show_app_config_dir.setMinimumSize(QSize(100, 48))
        self.btn_show_app_config_dir.setMaximumSize(QSize(16777215, 64))
        self.btn_show_app_config_dir.setFont(QFont(self.orbitron_bold_font, 14))
        self.btn_show_app_config_dir.clicked.connect(self.show_app_config_folder)

        # ---Add Widgets to Layouts---
        # --- Window Functions---
        self.hlayout_window_functions.addWidget(self.lbl_title, 0, Qt.AlignmentFlag.AlignLeft)
        self.hlayout_window_functions.addWidget(self.btn_themed_exit_app, 0, Qt.AlignmentFlag.AlignRight)

        # --- After Terminal Layout---
        self.hlayout_after_terminal_display.addWidget(self.txt_browser_project_link)

        # --- Patch Buttons Layout---
        self.hlayout_patch_buttons.addWidget(self.btn_fix_save_file)
        self.hlayout_patch_buttons.addWidget(self.btn_patch_executable)
        self.hlayout_patch_buttons.addWidget(self.btn_configure_patch_options)

        # --- Misc Layout---
        self.hlayout_misc_functions.addWidget(self.btn_show_app_config_dir)
        self.hlayout_misc_functions.addWidget(self.btn_show_game_folder)

        # --- Main Layout---
        self.setCentralWidget(self.main_frame)
        self.main_frame.setLayout(self.frame_layout)

        # --- Main Frame Layout---
        self.frame_layout.addWidget(self.window_functions_container_handle)
        self.frame_layout.addWidget(self.lbl_app_version)
        self.frame_layout.addWidget(self.terminal_display)
        self.frame_layout.addLayout(self.hlayout_after_terminal_display)
        self.frame_layout.addLayout(self.hlayout_patch_buttons)
        self.frame_layout.addLayout(self.hlayout_misc_functions)

        # --- Add frame_layout to main_frame---
        self.main_frame.setLayout(self.frame_layout)

        # --- Hook up Signals---
        # Could be a bit hacky. Ensure created before assign
        log.signals.progress.connect(self.terminal_display_log, Qt.QueuedConnection)
        updater_log.signals.progress.connect(self.terminal_display_log, Qt.QueuedConnection)
        patcher_log.signals.progress.connect(self.terminal_display_log, Qt.QueuedConnection)
        patcher_save_log.signals.progress.connect(self.terminal_display_log, Qt.QueuedConnection)
        steam_log.signals.progress.connect(self.terminal_display_log, Qt.QueuedConnection)
        registry_log.signals.progress.connect(self.terminal_display_log, Qt.QueuedConnection)
        self.signals.terminal_progress.connect(self.terminal_display_log, Qt.QueuedConnection)

        # --- Worker---
        self.worker = None  # Currently unusued, possibly to deprecate

        # --- Threads---
        self.thread_pool = QThreadPool()  # Currently unusued, possibly to deprecate
        self.active_threads = []

        # --- Patch info---
        if not PATTERNS_LOCAL.exists():
            # Download patch patterns once
            # This allows us to store it when they don't exist and use local only if required
            log.info("Downloading remote patch patterns to local storage.", silent=True)
            get_patterns_config_remote()
        else:
            # Patterns exists, pull only if not forced local
            if not SETTINGS.get_force_use_local_patterns() or USE_LOCAL_PATTERNS:
                log.info(
                    "Force local patterns is off. Downloading remote patch patterns to local storage.", silent=True
                )
                get_patterns_config_remote()

        self.patcher = pdx_patchers.MultiGamePatcher(PATTERNS_LOCAL)

        # TODO: Defaults, turn into dynamic?
        self.game_to_patch = "Stellaris"
        self.selected_version = patcher_models.CONST_VERSION_LATEST_KEY
        self.available_versions: List[str] = self.patcher.get_available_versions(self.game_to_patch)

        # --- Cache available patches to display---
        self.available_patches: dict = self.patcher.get_available_patches_for_game(
            self.game_to_patch, version=self.selected_version
        )

        self.configuration = patcher_models.PatchConfiguration(
            game=self.game_to_patch, version=patcher_models.CONST_VERSION_LATEST_KEY, is_proton=OS.WINDOWS
        )

        self.load_settings()

        self.check_update()

    def load_stylesheet(self, qss_filepath: Union[str, Path]):
        """Read QSS file and apply style to the application"""

        log.info(f"Loading Stylesheet: {qss_filepath}", silent=True)

        qss_path = Path(qss_filepath)
        if not qss_path.exists() or not qss_path.is_file():
            log.error(f"QSS style path is invalid: {qss_path}", silent=True)
            return False

        if not isinstance(qss_filepath, str):
            qss_str = str(qss_filepath)
        else:
            qss_str = qss_filepath

        try:
            with open(qss_str, "r") as f:
                style = f.read()
                self.setStyleSheet(style)
                log.info(f"Loaded Stylesheet: {qss_str}", silent=True)
        except Exception as e:
            log.error(f"Error setting Style for path: {qss_str}: {e}", silent=True)

    def load_settings(self):
        self._prev_app_version = SETTINGS.get_app_version()
        SETTINGS.set_app_version(f"{self._APP_VERSION}")
        updater.set_local_version(str(self._APP_VERSION))

    @Slot(str)
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
        self.btn_show_app_config_dir.setDisabled(False)
        self.btn_configure_patch_options.setDisabled(False)
        self.btn_show_game_folder.setDisabled(False)
        self.set_terminal_clickable(True)

    def disable_ui_elements(self):
        self.btn_patch_executable.setDisabled(True)
        self.btn_fix_save_file.setDisabled(True)
        self.btn_show_app_config_dir.setDisabled(True)
        self.btn_configure_patch_options.setDisabled(True)
        self.btn_show_game_folder.setDisabled(True)
        self.set_terminal_clickable(False)

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

        log.info(f"Proceeding to patch executable: {game_binary_path}")

        # Get patcher
        patcher: pdx_patchers.GamePatcher = self.patcher.get_game_patcher(
            self.configuration.game, self.configuration.version
        )

        if not patcher:
            log.error(f"Failed to initialise patcher for {self.game_to_patch}")
            return False

        patches_to_apply = [patch_name for patch_name in self.configuration.selected_patches]

        if not patches_to_apply:
            log.warning(
                f"Aborting Patch process. No patches selected for configuration: {self.configuration}", silent=True
            )
            log.warning(
                f"No patches selected or available. Applying all available patches corresponding to 'latest' version.\nUse the configuration window to select patches to apply."
            )
            patches_to_apply = [
                patch_name
                for patch_name in self.patcher.get_available_patches_for_game(
                    self.configuration.game, self.configuration.version
                )
            ]

        platform = None
        if OS.LINUX:
            if self.configuration.is_proton:
                platform = patcher_models.Platform.WINDOWS
            else:
                platform = patcher_models.Platform.LINUX_NATIVE

        log.info(f"Patches to apply: {patches_to_apply}", silent=True)

        results = patcher.patch_file_multiple(game_binary_path, patches_to_apply, platform=platform)

        self.signals.terminal_progress.emit(" ")

        all_patches_success = True

        applied = []
        for patch, success in results.items():
            if success:
                applied.append(patch)
            else:
                if all_patches_success:
                    all_patches_success = False
                log.warning(f"Failed patch: {patch}")

        SETTINGS.set_patches_applied_to_game(self.game_to_patch, applied)

        if all_patches_success:
            log.info("Finished. Close the patcher and go play!")

        return all_patches_success

    def start_patch_game_executable_thread(self):
        if self.is_patching:
            return

        self.terminal_display.clear()
        self.is_patching = True
        self.disable_ui_elements()

        self.active_threads.clear()

        # STEP: Attempt to find and establish paths
        self.path_finder_thread = Threader(target=self._find_game_path_worker_thread)
        self.path_finder_thread.signals.result.connect(self._path_found_or_failed)
        self.active_threads.append(self.path_finder_thread)
        self.path_finder_thread.start()

    def _find_game_path_worker_thread(self) -> Optional[Path]:
        """
        WORKER FUNCTION: Tries to find the game path automatically.
        Returns the path if found, otherwise None.
        """

        patcher = self.patcher.get_game_patcher(self.game_to_patch)
        if not patcher:
            return None

        is_proton = self.configuration.is_proton

        if is_proton:
            exe_info = patcher.get_executable_info(patcher_models.Platform.WINDOWS)
        else:
            # Get native exe info
            exe_info = patcher.get_executable_info()

        log.info(f"{exe_info=}", silent=True)

        # Check for saved path in settings first
        saved_install_path_str: str = SETTINGS.get_install_path(self.game_to_patch)
        if saved_install_path_str:
            game_install_dir = Path(saved_install_path_str)
            if game_install_dir.exists() and game_install_dir.is_file():
                log.info(f"Retrieved game executable from settings: {game_install_dir}")
                return game_install_dir
            else:
                log.warning(f"Saved game path found, but executable is invalid.")

        # Auto-locate
        log.info("Attempting to auto-locate game installation...")
        game_install_dir = patcher.locate_game_install()

        if game_install_dir:
            game_install_dir = game_install_dir.resolve() / exe_info.filename
            if game_install_dir.exists() and game_install_dir.is_file():
                log.info(f"Auto-located path: {game_install_dir}")
                return game_install_dir
            else:
                log.warning(f"Unable to auto-locate game binary: {game_install_dir}")

        log.warning(f"Automatic path detection failed")
        return None  # Signal failure

    def _path_found_or_failed(self, found_path: Optional[Path]):
        """
        SLOT FUNCTION: Runs on the main thread after _find_game_path_worker_thread
        """

        game_binary_path = found_path

        if not game_binary_path:
            # Automatic search failed
            log.info("Asking for user-provided game executable path.")

            user_selected_path = self.prompt_install_dir()

            if user_selected_path:
                game_binary_path = user_selected_path
            else:
                # User cancelled
                log.warning(f"User cancelled location. Aborting patch")
                self.enable_ui_elements()
                return

        if game_binary_path:
            SETTINGS.set_install_path(self.game_to_patch, game_binary_path)
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

    def show_game_folder(self):
        # Trying out setting platform specific logic and binding it
        # to variables to call, to reduce code duplication

        # TODO: In future, ensure we get the `self.game_to_patch` from settings

        if OS.LINUX_PROTON:
            get_path = SETTINGS.get_proton_install_path
            set_path = SETTINGS.set_proton_install_path
        else:
            get_path = SETTINGS.get_install_path
            set_path = SETTINGS.set_install_path

        executable_path = None

        # Attempt to find a valid executable from settings
        saved_path_str: str = get_path(self.game_to_patch)
        if saved_path_str:
            log.debug(f"Saved path str: {saved_path_str}")
            # Path can be file or folder (due to older versions of the app)
            # Only trust a file
            saved_path = Path(saved_path_str)
            if saved_path.is_file():
                executable_path = saved_path
                log.info(f"Saved path is file: {executable_path}", silent=True)

        # No valid exe found from settings. Auto-search
        if not executable_path:
            log.info(f"No valid executable path: {executable_path}", silent=True)
            found_exe = False
            if found_exe:
                log.debug(f"{found_exe=}")
                executable_path = Path(found_exe)
                # Save the path
                set_path(self.game_to_patch, str(executable_path))

        # If valid exe was found
        log.debug(f"{executable_path=}")
        if executable_path and executable_path.is_file():
            game_folder = executable_path.parent
            log.info(f"Derived Game Folder: {game_folder}", silent=True)

            # Save if mismatch
            if Path(get_path(self.game_to_patch)) != executable_path:
                set_path(self.game_to_patch, str(executable_path))

            try:
                if OS.WINDOWS:
                    subprocess.run(["explorer.exe", "/select,", os.path.normpath(game_folder)])
                elif OS.LINUX:
                    subprocess.run(["xdg-open", game_folder])
                elif OS.MACOS:
                    subprocess.run(["open", "-R", game_folder])
                else:
                    log.warning("No known Operating System")
            except Exception as e:
                log.error(f"Failed to open game folder: {e}")
        else:
            log.warning(f"Unable to determine game folder.")

    @staticmethod
    def show_app_config_folder():
        config_dir = SETTINGS.get_config_dir()

        if config_dir.exists() and config_dir.is_dir():
            log.info(f"App Config Folder: {config_dir}", silent=True)

            if OS.WINDOWS:
                subprocess.run(["explorer.exe", "/select,", os.path.normpath(config_dir)])
            elif OS.LINUX:
                subprocess.run(["xdg-open", config_dir])
            elif OS.MACOS:
                subprocess.run(["open", "-R", config_dir])
            else:
                log.warning("No known Operating System")

    @staticmethod
    def prompt_install_dir():
        qurl_install_dir: tuple[QUrl, str] = QFileDialog().getOpenFileUrl(
            caption="Please choose Stellaris installation Folder..."
        )
        install_dir = qurl_install_dir[0].path()
        log.info(f"{install_dir=}")
        if install_dir:
            install_dir = Path(install_dir).absolute().resolve()

        return install_dir

    def fix_save_achievements_thread(self):
        if self.is_patching:
            return

        self.terminal_display.clear()

        # Before starting the thread, ask which save file the user wants to repair.
        # Simply point to the .sav file and we will do the rest.
        # Usually located in user Documents. Attempt to grab that directory on open

        # Windows
        documents_dir = get_user_save_folder()

        save_file_path = QFileDialog().getOpenFileName(caption="Save file to repair...", dir=documents_dir)[0]

        if save_file_path or save_file_path != "":
            log.info(f"Save file: {save_file_path}")

        if not save_file_path:
            return False

        save_games_dir = Path(save_file_path).parent.parent
        log.info(f"Save games directory: {os.path.normpath(save_games_dir)}")
        SETTINGS.set_save_games_dir(self.game_to_patch, save_games_dir)

        thread_repair_save = Threader(target=lambda save_file=save_file_path: repair_save(save_file))
        thread_id = thread_repair_save.currentThread()
        thread_repair_save.setTerminationEnabled(True)
        # self.threader.signals.failed.connect() # TODO
        thread_repair_save.signals.started.connect(self.disable_ui_elements)
        thread_repair_save.signals.finished.connect(self.enable_ui_elements)
        thread_repair_save.signals.finished.connect(lambda: self.remove_thread(thread_id))  # Removes thead by ID
        self.active_threads.append(thread_repair_save)
        thread_repair_save.start()

    def open_configure_patch_options_window(self):
        log.info("Opening patch configuration window", silent=True)

        dialog = ConfigurePatchOptionsDialog(
            patcher=self.patcher,
            current_config=self.configuration,
            font=QFont(self.orbitron_bold_font, 10),
            window_icon=self.windowIcon(),
            parent=self,
        )

        if dialog.exec_() == QFileDialog.DialogCode.Accepted:
            self.configuration = dialog.get_configuration()
            log.info(f"Configuration updated: {self.configuration}", silent=True)
            selected_patches_str = ", ".join(self.configuration.selected_patches)
            log.info(f"Selected patches: {selected_patches_str}")
        else:
            log.info("Configuration unchanged.", silent=True)

    def check_update(self):
        last_checked = SETTINGS.get_update_last_checked()
        now = int(time.time())

        log.debug(
            f"{self._APP_VERSION} == {self._prev_app_version} = {self._APP_VERSION == self._prev_app_version}",
            silent=True,
        )
        log.debug(
            f"{now} - {last_checked} < {UPDATE_CHECK_COOLDOWN} = {now - last_checked < UPDATE_CHECK_COOLDOWN}",
            silent=True,
        )

        if self._APP_VERSION == self._prev_app_version:
            if now - last_checked < UPDATE_CHECK_COOLDOWN:
                self.check_update_finished()
                return

        thread_update = Threader(target=updater.check_for_update)
        # thread_id = thread_update.currentThread()
        self.active_threads.append(thread_update)
        thread_update.start()
        thread_update.signals.finished.connect(self.check_update_finished)

    def check_update_finished(self):
        updater_last_checked = updater.last_checked_timestamp

        # No online check was performed
        if updater_last_checked <= 1:
            update_available = SETTINGS.get_has_update()
        else:
            SETTINGS.set_update_last_checked(updater.last_checked_timestamp)
            if updater.has_new_version:
                SETTINGS.set_has_update(True)
                update_available = True
            else:
                SETTINGS.set_has_update(False)
                update_available = False

        if update_available:
            html = (
                self.txt_browser_project_link.toHtml().replace("</p>", "").replace("</body>", "").replace("</html>", "")
            )
            html += '<span style=" font-weight:700;"> (UPDATE AVAILABLE)</span></p></body></html>'
            self.txt_browser_project_link.setHtml(html)
            self.lbl_title.setFont(QFont(self.orbitron_bold_font, 20))
            self.lbl_title.setText(self.lbl_title.text() + " (UPDATE AVAILABLE)")
            SETTINGS.set_has_update(True)

    def show(self):
        super().show()
        self._adjust_app_size()
        self.terminal_display.clear()
        sys.exit(self.app.exec_())

    def closeEvent(self, event):
        log.info("Application is closing. Shutting down procedure")

        log.info("Shutdown")
        event.accept()
        self.app_quit()

    def app_quit(self):
        log.info("Quitting Application. Performing graceful shutdown procedure.")

        SETTINGS.set_app_version(f"{self._APP_VERSION}")
        SETTINGS.set_window_width(self.width())
        SETTINGS.set_window_height(self.height())

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

    def _adjust_app_size(self):
        screen_info = get_screen_info(self.app)

        log.debug(f"{screen_info=}")

        if not self:
            log.warning("Not self")
            return

        if screen_info[0] <= 1500 or screen_info[1] <= 1000 or screen_info[2] <= 0.7:
            log.info("Resizing application")
            self.resize(QSize(650, 500))
