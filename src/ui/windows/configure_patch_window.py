from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from conf_globals import (
    IS_DEBUG,
    LOG_LEVEL,
    OS,
    PREVENT_CONN,
    SETTINGS,
    STEAM,
    USE_LOCAL_PATTERNS,
)
from logger import create_logger
from patchers import MultiGamePatcher, PatchConfiguration
from patchers import models as patcher_models
from utils.platform import open_in_file_manager

from ..utils import Threader, restore_window_focus
from .welcome_dialog import WelcomeDialog

log = create_logger("Patch Config", LOG_LEVEL)


class ConfigurePatchOptionsDialog(QDialog):
    def __init__(
        self,
        patcher: MultiGamePatcher,
        current_config: PatchConfiguration,
        font: QFont,
        window_icon: QIcon,
        parent=None,
    ):
        super().__init__(parent)

        self.patcher = patcher
        self.current_config = current_config
        self.font = font

        # --- Style and Appearance ---
        # Qt.Window treats this is a top-level window while being able to receive a parent
        # This fixes the odd behaviour where a frameless window with a parent
        # would appear off centre and clipped by the main window.
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint | Qt.Window
        )

        self.setWindowTitle("Configure Patches")
        self.setWindowIcon(window_icon)
        self.setMinimumSize(600, 400)

        # Dialog Layout that contains the frame
        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)

        # --- Frame ---
        main_frame = QFrame(self)
        main_frame.setFrameShape(QFrame.WinPanel)
        main_frame.setFrameShadow(QFrame.Plain)
        main_frame.setLineWidth(5)
        main_frame.setMidLineWidth(0)
        main_frame.setContentsMargins(10, 10, 10, 10)
        dialog_layout.addWidget(main_frame)

        # --- Content Layout ---
        content_layout = QVBoxLayout(main_frame)
        content_layout.setContentsMargins(10, 10, 10, 10)

        # --- Tab Widget ---
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(self.font)
        content_layout.addWidget(self.tab_widget)

        # --- Create Tabs ---
        self._create_patch_config_tab()
        self._create_utilities_tab()

        # --- OK/Cancel Layout ---
        ok_cancel_layout = QHBoxLayout()
        content_layout.addLayout(ok_cancel_layout)

        # --- Ok / Cancel Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        for button in button_box.buttons():
            button.setFont(self.font)
        ok_cancel_layout.addWidget(button_box)

        # --- Initial population ---
        self._populate_options()

        # --- Load settings ---
        self._load_settings()

    def _load_settings(self):
        log.info("Load Settings")
        # Reflect settings in UI
        use_local_patterns = any([USE_LOCAL_PATTERNS, PREVENT_CONN, SETTINGS.get_force_use_local_patterns()])
        print(hasattr(self, "chkbox_use_local_patterns"))
        self.chkbox_use_local_patterns.setCheckState(
            Qt.CheckState.Checked if use_local_patterns else Qt.CheckState.Unchecked
        )

    def _create_patch_config_tab(self):
        patch_tab = QWidget()
        patch_layout = QVBoxLayout(patch_tab)
        patch_layout.setContentsMargins(10, 10, 10, 10)

        # --- Game Info Section --.
        if self.current_config:
            info_label = QLabel(f"<b>Patch Configuration</b>")
            info_label.setFont(self.font)
            patch_layout.addWidget(info_label)

            desc_label = QLabel(f"Select what game to patch and with that options.")
            desc_label.setWordWrap(True)
            patch_layout.addWidget(desc_label)

        # --- Game & Version Selection ---
        selection_layout = QHBoxLayout()

        self.game_combobox = QComboBox()
        self.game_combobox.setFont(self.font)

        self.version_combobox = QComboBox()
        self.version_combobox.setFont(self.font)

        selection_layout.addWidget(QLabel("Game:"))
        selection_layout.addWidget(self.game_combobox, 1)
        selection_layout.addWidget(QLabel("Version:"))
        selection_layout.addWidget(self.version_combobox, 1)
        patch_layout.addLayout(selection_layout)

        # --- Linux Version Dropdown ---
        self.use_proton_picker = QComboBox()
        if OS.LINUX:
            self.use_proton_picker.addItems(
                [patcher_models.LINUX_VERSIONS_ENUM.NATIVE, patcher_models.LINUX_VERSIONS_ENUM.PROTON]
            )
            self.use_proton_picker.setFont(self.font)
            selection_layout.addWidget(self.use_proton_picker)
            self.use_proton_picker.currentTextChanged.connect(self._on_binary_type_changed)

        # --- Patches Area (Scrollable) ---
        self.patches_scroll_area = QScrollArea()
        self.patches_scroll_area.setWidgetResizable(True)

        self.patches_widget = QWidget()

        self.patches_layout = QVBoxLayout(self.patches_widget)
        self.patches_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.patches_scroll_area.setWidget(self.patches_widget)
        patch_layout.addWidget(self.patches_scroll_area)

        # --- Signals ---
        self.game_combobox.currentTextChanged.connect(self._on_game_changed)
        self.version_combobox.currentTextChanged.connect(self._on_version_changed)

        # --- Add Tab to Widget
        self.tab_widget.addTab(patch_tab, "Patch Configuration")

    def _create_utilities_tab(self):
        utilities_tab = QWidget()
        utilities_tab_layout = QVBoxLayout(utilities_tab)
        utilities_tab_layout.setContentsMargins(10, 10, 10, 10)
        utilities_tab_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Title ---
        title_label = QLabel("<b>General Utilities</b>")
        title_label.setFont(self.font)
        utilities_tab_layout.addWidget(title_label)

        # --- Description Label
        desc_label = QLabel("Additional tools and utilities for game management.")
        desc_label.setWordWrap(True)
        utilities_tab_layout.addWidget(desc_label)

        # --- Selected Game Label ---
        self.utilities_selected_game_label = QLabel(f"SELECTED GAME: {self.current_config.game}")
        self.utilities_selected_game_label.setObjectName("UtilitiesGameLabel")
        self.utilities_selected_game_label.setFont(self.font)
        utilities_tab_layout.addWidget(self.utilities_selected_game_label)

        # --- Scroll Area ---
        utilities_scroll_area = QScrollArea()
        utilities_scroll_area.setWidgetResizable(True)

        # --- Scrollable Content Widget
        utilities_content_widget = QWidget()
        utilities_layout = QVBoxLayout(utilities_content_widget)
        utilities_layout.setContentsMargins(5, 5, 5, 5)
        utilities_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Open Welcome Dialog Button ---
        btn_show_welcome_dialog = QPushButton("Show Welcome Dialog")
        btn_show_welcome_dialog.setFont(self.font)
        btn_show_welcome_dialog.clicked.connect(self.show_welcome_dialog)
        utilities_layout.addWidget(btn_show_welcome_dialog)

        # --- Open Config Directory Button ---
        btn_show_app_config_dir = QPushButton("Show App Config Folder")
        btn_show_app_config_dir.setFont(self.font)
        btn_show_app_config_dir.clicked.connect(self.show_app_config_folder)
        utilities_layout.addWidget(btn_show_app_config_dir)

        # --- Show Game Folder Button ---
        btn_show_game_folder = QPushButton("Show Game Folder")
        btn_show_game_folder.setFlat(False)
        btn_show_game_folder.setFont(self.font)
        btn_show_game_folder.clicked.connect(self.show_game_folder)
        utilities_layout.addWidget(btn_show_game_folder)

        # --- Steam Validate Game Files Button ---
        btn_validate_game_files = QPushButton("Validate Integrity of Game Files")
        btn_validate_game_files.setFont(self.font)
        btn_validate_game_files.setToolTip("Trigger the validation of game files through Steam.")
        btn_validate_game_files.clicked.connect(self._validate_steam_game_files)
        utilities_layout.addWidget(btn_validate_game_files)

        # --- Use Local Patterns Checkbox---
        self.chkbox_use_local_patterns = QCheckBox("Force Local Patterns")
        self.chkbox_use_local_patterns.setToolTip(
            "When toggled, application will not longer pull updated patterns from remote and will only strictly use the patterns file present on disk.\nThis is mainly useful for testing purposes, for trying out different patterns to prevent the local file from being overwritten on application startup."
        )
        self.chkbox_use_local_patterns.stateChanged.connect(self.callback_use_local_patterns)
        # Force update state when global enforcement rule is applied
        if any((USE_LOCAL_PATTERNS, PREVENT_CONN)):
            self.chkbox_use_local_patterns.setEnabled(False)
            # SETTINGS.set_force_use_local_patterns(Qt.CheckState.Unchecked.value)
        utilities_layout.addWidget(self.chkbox_use_local_patterns)

        # --- Spacer ---
        utilities_layout.addStretch()

        # --- Set scrollable widget ---
        utilities_scroll_area.setWidget(utilities_content_widget)
        utilities_tab_layout.addWidget(utilities_scroll_area)

        # --- Add Tab to Widget ---
        self.tab_widget.addTab(utilities_tab, "General Utilities")

    def _validate_steam_game_files(self):
        install_path = SETTINGS.get_install_path(self.current_config.game)
        app_id = STEAM.get_app_id_from_install_path(install_path)

        # Remove the binary file before verifying
        game_binary = Path(install_path)
        if game_binary.exists() and game_binary.is_file():
            log.info(f"Removing game binary before verifying: {game_binary}")
            try:
                game_binary.unlink()
            except Exception as e:
                log.error(f"Failed to unlink game binary: {e}")

        STEAM.validate_game_files_app_id(app_id)

        try:
            main_window = self.parent() if self.parent() else self
            restore_window_focus(main_window)
        except Exception as e:
            log.error(f"Error restoring window focus: {e}")

    def _create_default_config(self, game: str = None) -> PatchConfiguration:
        log.info(f"Creating default patch configuration.", silent=True)
        games = self.patcher.get_available_games()

        if not game and not games:
            log.error(f"No available games")
            return None

        selected_game = game or games[0]

        return PatchConfiguration(
            game=selected_game,
            version=patcher_models.CONST_VERSION_LATEST_KEY,
            is_proton=(OS.WINDOWS or self._should_use_proton()),
        )

    def _should_use_proton(self) -> bool:
        """Determine if Proton should be used for Linux"""
        if OS.LINUX and hasattr(self, "use_proton_picker"):
            return self.use_proton_picker.currentText().lower() == patcher_models.LINUX_VERSIONS_ENUM.PROTON.lower()
        return False

    def _get_current_platform(self) -> patcher_models.Platform:
        if OS.LINUX and self._should_use_proton():
            return patcher_models.Platform.WINDOWS
        return patcher_models.Platform.LINUX_NATIVE if OS.LINUX else patcher_models.Platform.WINDOWS

    def _validate_configuration(self, config: PatchConfiguration) -> bool:
        log.info(f"Validating patch configuration: {config}", silent=True)

        if not config:
            log.error("Configuration is None.")
            return False

        if not config.game:
            log.error(f"No game selected in configuration")
            return False

        if not config.version:
            log.error(f"No version selected in configuration")
            return False

        available_games = self.patcher.get_available_games()
        if config.game not in available_games:
            log.error(f"Game '{config.game}' not in available games: {available_games}")
            return False

        return True

    def _populate_options(self):
        log.info(f"Populating Options", silent=True)

        if not self.current_config or not self.current_config.game:
            self.current_config = self._create_default_config()
            if not self.current_config:
                log.error(f"Failed to create a default configuration")
                return

        # Validate
        if not self._validate_configuration(self.current_config):
            log.error(f"Invalid configuration, creating default")
            self.current_config = self._create_default_config()
            if not self.current_config or not self._validate_configuration(self.current_config):
                log.error(f"Failed to create valid configuration")
                return

        log.info(f"Retrieving available games to add to game combobox.", silent=True)
        available_games = self.patcher.get_available_games()
        self.game_combobox.blockSignals(True)
        self.game_combobox.addItems(available_games)
        self.game_combobox.setCurrentText(self.current_config.game)
        self.game_combobox.blockSignals(False)

        # Update platform UI
        if OS.LINUX:
            linux_version = (
                patcher_models.LINUX_VERSIONS_ENUM.PROTON
                if self.current_config.is_proton
                else patcher_models.LINUX_VERSIONS_ENUM.NATIVE
            )
            self.use_proton_picker.setCurrentText(linux_version)

        self._on_game_changed(self.current_config.game)

    def _on_game_changed(self, game_name: str):
        versions = self.patcher.get_available_versions(game_name)
        self.version_combobox.blockSignals(True)
        self.version_combobox.clear()
        self.version_combobox.addItems([v.capitalize() for v in versions])

        target_version = ""
        if game_name == self.current_config.game:
            target_version = self.current_config.version
        elif patcher_models.CONST_VERSION_LATEST_KEY in versions:
            target_version = patcher_models.CONST_VERSION_LATEST_KEY

        if target_version:
            self.version_combobox.setCurrentText(self.current_config.version.capitalize())

        last_platform = SETTINGS.get_last_selected_platorm(game_name)
        if last_platform:
            if OS.LINUX or OS.MACOS:
                use_proton = last_platform.lower() == patcher_models.Platform.WINDOWS.value
                log.info(f"{use_proton=}")

                if use_proton and hasattr(self, "use_proton_picker"):
                    self.use_proton_picker.setCurrentText(patcher_models.LINUX_VERSIONS_ENUM.PROTON)
                elif not use_proton and hasattr(self, "use_proton_picker"):
                    self.use_proton_picker.setCurrentText(patcher_models.LINUX_VERSIONS_ENUM.NATIVE)

        self.version_combobox.blockSignals(False)
        self._on_version_changed(self.version_combobox.currentText())

        # Update Utilities Game Title
        self.utilities_selected_game_label.setText(f"SELECTED GAME: {self.current_config.game}")

    def _on_version_changed(self, version_name: str):
        # Clear previous checkboxes
        while self.patches_layout.count():
            child = self.patches_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        game_name = self.game_combobox.currentText()
        if not game_name or not version_name:
            return

        patcher = self.patcher.get_game_patcher(game_name, version_name.lower())
        if not patcher:
            return

        # Determine platform from UI Widget
        platform = self._get_current_platform()

        # Determine if current UI selection matches intiial config
        is_initial_config = (
            game_name == self.current_config.game and version_name.lower() == self.current_config.version.lower()
        )

        # Only use saved selection if it's in the initial config and list is not empty
        use_saved_selections = is_initial_config and self.current_config.selected_patches

        # Populate scroll area with patch option checkboxes
        available_patches = patcher.get_available_patches(platform=platform)
        for patch_name, patch_info in available_patches.items():
            checkbox = QCheckBox(patch_info.display_name)
            checkbox.setToolTip(patch_info.description)
            checkbox.setFont(self.font)
            checkbox.setChecked(False)
            is_required = patch_info.required
            default_enabled = patch_info.enabled

            log.debug(f"{patch_info.display_name} {is_required=}", silent=True)
            log.debug(f"{patch_info.display_name} {default_enabled=}", silent=True)

            if is_required:
                checkbox.setChecked(True)
                checkbox.setDisabled(True)  # If required, disable to prevent edits

            if use_saved_selections:
                # Restore user's saved selections if inital config
                if patch_name in self.current_config.selected_patches:
                    checkbox.setChecked(True)
                # Otherwise remains unchecked
            else:
                # If new selection, check all by default
                checkbox.setChecked(default_enabled or is_required)

            self.patches_layout.addWidget(checkbox)

            # Store patch_name property for easy retrieval
            checkbox.setProperty("patch_name", patch_name)

        # Log current config
        log.info(
            f"Displaying current config:\nGame={self.game_combobox.currentText()}\nVersion: {self.version_combobox.currentText().lower()}\nPlatform: {platform}",
            silent=True,
        )

    def _on_binary_type_changed(self, text):
        log.info(f"Binary type changed to: {text}", silent=True)

        # Trigger re-update options
        self._on_version_changed(self.version_combobox.currentText())

    def callback_use_local_patterns(self, state):
        if state in (Qt.CheckState.Checked.value, Qt.CheckState.Unchecked.value):
            # We don't need to set for --no-conn
            if not PREVENT_CONN:
                SETTINGS.set_force_use_local_patterns(state)
        else:
            log.warning("Checkbox in Partially Checked state. We shouldn't be here.", silent=True)

    def get_configuration(self) -> PatchConfiguration:
        selected_patches = []

        for i in range(self.patches_layout.count()):
            checkbox = self.patches_layout.itemAt(i).widget()
            if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                selected_patches.append(checkbox.property("patch_name"))

        return PatchConfiguration(
            game=self.game_combobox.currentText(),
            version=self.version_combobox.currentText().lower(),
            is_proton=self._should_use_proton(),
            selected_patches=selected_patches,
        )

    def show_game_folder(self, auto_located_path: Optional[Path] = None):
        from ..main_window import StellarisChecksumPatcherGUI

        paths = [
            SETTINGS.get_install_path(self.current_config.game),
            SETTINGS.get_proton_install_path(self.current_config.game),
        ]

        # Attempt to find a valid executable from settings
        saved_path = None

        # Prioritise auto_located_path
        if auto_located_path and auto_located_path.exists():
            saved_path = auto_located_path
            log.info(f"Using auto-located path as saved path: {saved_path}", silent=True)

            # Save the paths
            if saved_path not in paths and saved_path.exists():
                if (OS.LINUX or OS.LINUX_PROTON) and self.current_config.is_proton:
                    set_path = SETTINGS.set_proton_install_path
                else:
                    set_path = SETTINGS.set_install_path
                set_path(self.current_config.game, saved_path)

        else:
            # Iterate once to test if any path exists
            for path_str in paths:
                if not path_str:
                    continue

                path = Path(path_str)

                if path.exists():
                    saved_path = path
                    break

                if path.parent.exists():
                    saved_path = path.parent
                    log.info(f"Derived Game Folder: {saved_path}", silent=True)
                    break

        if saved_path:
            log.info(f"Opening game folder: {saved_path}", silent=False)
            open_in_file_manager(saved_path)
        else:
            log.error(f"Unable to determine saved path: {saved_path}")
            log.info("Attempting to auto-locate game installation...")

            if not auto_located_path:
                # Attempt to auto locate and re-run the function
                # TODO: SUPER SCUFF EDITION: Import UI Class and canibalise the method
                # In case this proves problematic, just copy paste the method from the UI
                # to below this method and replace `self.configuration` with `self.current_config`
                path_finder_thread = Threader(target=StellarisChecksumPatcherGUI._find_game_path_worker_thread)
                path_finder_thread.signals.result.connect(self.show_game_folder)
                path_finder_thread.start()
            else:
                log.info("Auto-location already attempted and failed.", silent=True)

    def show_app_config_folder(self):
        config_dir = SETTINGS.get_config_dir()

        if config_dir.exists() and config_dir.is_dir():
            log.info(f"App Config Folder: {config_dir}", silent=True)

            open_in_file_manager(config_dir)

    def show_welcome_dialog(self):
        # --- Show welcome dialog ---
        welcome_dialog = WelcomeDialog(self.font, window_icon=self.windowIcon(), parent=self)
        welcome_dialog.show()
