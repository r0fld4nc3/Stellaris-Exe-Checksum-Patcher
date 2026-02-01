import logging
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
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app_services import services
from config.path_helpers import os_darwin, os_linux, os_windows
from patch_patterns.patterns import get_patterns_config_remote
from patchers import MultiGamePatcher, PatchConfiguration
from patchers import models as patcher_models
from thread_utils import Threader
from utils.platform import open_in_file_manager

from ..utils import find_game_path, prompt_install_dir, restore_window_focus
from .welcome_dialog import WelcomeDialog

log = logging.getLogger("Patch Config")


class ConfigurePatchOptionsDialog(QDialog):
    svc = services()

    def __init__(
        self,
        patcher: MultiGamePatcher,
        configuration: PatchConfiguration,
        font: QFont,
        window_icon: QIcon,
        parent=None,
    ):
        super().__init__(parent)

        self.setModal(True)  # Always a modal dialog

        self.active_threads = []

        self.patcher = patcher
        self.patch_options_configuration = configuration
        self._current_platform: Optional[patcher_models.Platform] = None
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
        use_local_patterns = any(
            [
                self.svc.config.use_local_patterns,
                self.svc.config.prevent_conn,
                self.svc.settings.settings.force_local_patterns,
            ]
        )
        log.debug(f"Has Attribute 'chkbox_use_local_patterns': {hasattr(self, 'chkbox_use_local_patterns')}")
        self.chkbox_use_local_patterns.setCheckState(
            Qt.CheckState.Checked if use_local_patterns else Qt.CheckState.Unchecked
        )

    def _create_patch_config_tab(self):
        patch_tab = QWidget()
        patch_layout = QVBoxLayout(patch_tab)
        patch_layout.setContentsMargins(10, 10, 10, 10)

        # --- Game Info Section --.
        if self.patch_options_configuration:
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
        self.version_combobox.setMaximumWidth(140)

        selection_layout.addWidget(QLabel("Game:"))
        selection_layout.addWidget(self.game_combobox, 1)
        selection_layout.addWidget(QLabel("Version:"))
        selection_layout.addWidget(self.version_combobox, 1)
        patch_layout.addLayout(selection_layout)

        # --- Linux Version Dropdown ---
        self.use_proton_picker = QComboBox()
        if os_linux() or os_darwin():
            self.use_proton_picker.addItems(
                [patcher_models.TRANSLATION_LAYER_ENUM.NATIVE, patcher_models.TRANSLATION_LAYER_ENUM.PROTON]
            )
            self.use_proton_picker.setFont(self.font)
            selection_layout.addWidget(self.use_proton_picker)
            self.use_proton_picker.currentTextChanged.connect(self._on_binary_type_changed)
            self.use_proton_picker.setMinimumWidth(100)

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
        self.utilities_selected_game_label = QLabel(f"SELECTED GAME: {self.patch_options_configuration.game}")
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

        # --- Fetch/Update Patterns File Button ---
        btn_update_patch_patterns = QPushButton("Update Patterns")
        btn_update_patch_patterns.setFont(self.font)
        btn_update_patch_patterns.clicked.connect(self.fetch_patch_patterns)
        utilities_layout.addWidget(btn_update_patch_patterns)

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
        btn_validate_game_files = QPushButton("Validate Integrity of Game Files (Steam)")
        btn_validate_game_files.setFont(self.font)
        btn_validate_game_files.setToolTip("Trigger the validation of game files through Steam.")
        btn_validate_game_files.clicked.connect(self._validate_steam_game_files)
        utilities_layout.addWidget(btn_validate_game_files)

        # --- Maximum Allowed Backups ---
        max_backups_control_layout = QHBoxLayout()

        # Maximum Backups Laber
        max_backups_label = QLabel("Maximum Backups:")
        max_backups_label.setFont(self.font)
        max_backups_label.setToolTip(
            "Define the maximum number of backup files to keep for the game binary. Set to 0 to disable backups."
        )

        # Maximum Backups Slider
        self.max_backups_slider = QSlider(Qt.Horizontal)
        self.max_backups_slider.setMinimum(0)
        self.max_backups_slider.setMaximum(10)  # Reasonable max allowed backups
        self.max_backups_slider.setValue(self.svc.settings.settings.max_allowed_binary_backups)
        self.max_backups_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.max_backups_slider.setTickInterval(1)
        self.max_backups_slider.setToolTip("Drag to adjust maximum number of backups.")
        self.max_backups_slider.valueChanged.connect(self._on_max_backups_slider_changed)

        # Value Display Label
        current_value = self.max_backups_slider.value()
        display_text = "Off" if current_value <= 0 else str(current_value)
        self.max_backup_value_label = QLabel(display_text)
        self.max_backup_value_label.setFont(self.font)
        self.max_backup_value_label.setMaximumWidth(70)
        self.max_backup_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Add widgets
        max_backups_control_layout.addWidget(max_backups_label)
        max_backups_control_layout.addWidget(self.max_backup_value_label)
        max_backups_control_layout.addWidget(self.max_backups_slider, 1)
        utilities_layout.addLayout(max_backups_control_layout)

        # --- Use Local Patterns Checkbox---
        self.chkbox_use_local_patterns = QCheckBox("Force Local Patterns")
        self.chkbox_use_local_patterns.setToolTip(
            "When toggled, application will not longer pull updated patterns from remote and will only strictly use the patterns file present on disk.\nThis is mainly useful for testing purposes, for trying out different patterns to prevent the local file from being overwritten on application startup."
        )
        self.chkbox_use_local_patterns.stateChanged.connect(self.callback_use_local_patterns)
        # Force update state when global enforcement rule is applied
        if any((self.svc.config.use_local_patterns, self.svc.config.prevent_conn)):
            self.chkbox_use_local_patterns.setEnabled(False)
            # SETTINGS.settings.force_local_patterns = Qt.CheckState.Unchecked.value
        utilities_layout.addWidget(self.chkbox_use_local_patterns)

        # --- Spacer ---
        utilities_layout.addStretch()

        # --- Set scrollable widget ---
        utilities_scroll_area.setWidget(utilities_content_widget)
        utilities_tab_layout.addWidget(utilities_scroll_area)

        # --- Add Tab to Widget ---
        self.tab_widget.addTab(utilities_tab, "General Utilities")

    def _validate_steam_game_files(self):
        install_path = self.svc.settings.game(self.patch_options_configuration.game).install_path
        app_id = self.svc.steam_helper.get_app_id_from_install_path(install_path)

        # Remove the binary file before verifying
        game_binary = Path(install_path)
        if game_binary.exists() and game_binary.is_file():
            log.info(f"Removing game binary before verifying: {game_binary}")
            try:
                game_binary.unlink()
            except Exception as e:
                log.error(f"Failed to unlink game binary: {e}")

        self.svc.steam_helper.validate_game_files_app_id(app_id)

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
            version=patcher_models.KEY_VERSION_LATEST,
            is_proton=(os_windows() or self._should_use_proton()),
        )

    def _should_use_proton(self) -> bool:
        """Determine if Proton should be used and is picked bu User."""
        if os_linux() or os_darwin() and hasattr(self, "use_proton_picker"):
            return self.use_proton_picker.currentText().lower() == patcher_models.TRANSLATION_LAYER_ENUM.PROTON.lower()
        return False

    def _get_current_platform(self) -> patcher_models.Platform:
        return (
            patcher_models.Platform.detect_current()
            if not self._should_use_proton()
            else patcher_models.Platform.WINDOWS
        )

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

        if not self.patch_options_configuration or not self.patch_options_configuration.game:
            self.patch_options_configuration = self._create_default_config()
            if not self.patch_options_configuration:
                log.error(f"Failed to create a default configuration")
                return

        # Validate
        if not self._validate_configuration(self.patch_options_configuration):
            log.error(f"Invalid configuration, creating default")
            self.patch_options_configuration = self._create_default_config()
            if not self.patch_options_configuration or not self._validate_configuration(
                self.patch_options_configuration
            ):
                log.error(f"Failed to create valid configuration")
                return

        log.info(f"Retrieving available games to add to game combobox.", silent=True)
        available_games = self.patcher.get_available_games()
        self.game_combobox.blockSignals(True)
        self.game_combobox.clear()
        self.game_combobox.addItems(available_games)
        self.game_combobox.setCurrentText(self.patch_options_configuration.game)
        self.game_combobox.blockSignals(False)

        # Update platform UI
        if os_linux():
            linux_version = (
                patcher_models.TRANSLATION_LAYER_ENUM.PROTON
                if self.patch_options_configuration.is_proton
                else patcher_models.TRANSLATION_LAYER_ENUM.NATIVE
            )
            self.use_proton_picker.setCurrentText(linux_version)
        elif os_darwin():
            macos_version = (
                patcher_models.TRANSLATION_LAYER_ENUM.PROTON
                if self.patch_options_configuration.is_proton
                else patcher_models.TRANSLATION_LAYER_ENUM.NATIVE
            )
            self.use_proton_picker.setCurrentText(macos_version)

        self._on_game_changed(self.patch_options_configuration.game)

    def _on_game_changed(self, game_name: str):
        versions = self.patcher.get_available_versions(game_name)
        self.version_combobox.blockSignals(True)
        self.version_combobox.clear()

        last_platform_str = self.svc.settings.game(game_name).last_patched_platform

        # Convert to Enum
        if last_platform_str:
            try:
                self._current_platform = patcher_models.Platform(last_platform_str.lower())
                log.info(f"Using saved platform: {self._current_platform}")
            except ValueError:
                log.warning(f"Invalid saved platform '{last_platform_str}', auto-detecting current.")
                self._current_platform = self._get_current_platform()
        else:
            # No saved platform, auto-detect
            self._current_platform = self._get_current_platform()
            log.info(f"No saved platform, auto-detected: {self._current_platform}")

        if os_linux() or os_darwin():
            use_proton = self._current_platform == patcher_models.Platform.WINDOWS
            log.info(f"{use_proton=}")

            if use_proton and hasattr(self, "use_proton_picker"):
                self.use_proton_picker.setCurrentText(patcher_models.TRANSLATION_LAYER_ENUM.PROTON)
            elif not use_proton and hasattr(self, "use_proton_picker"):
                self.use_proton_picker.setCurrentText(patcher_models.TRANSLATION_LAYER_ENUM.NATIVE)

        # Add available versions provided they have patches
        available_versions_with_patches = []
        for version in versions:
            patches = self.patcher.get_available_patches_for_game(game_name, version, self._current_platform)
            if patches:
                self.version_combobox.addItem(version.capitalize())
                available_versions_with_patches.append(version)

        # Determine version to select
        target_version = None

        # If it's the same as current config, try to use that version
        if (
            game_name == self.patch_options_configuration.game
            and self.patch_options_configuration.version in available_versions_with_patches
        ):
            target_version = self.patch_options_configuration.version
        # Otherwise, prefer 'latest' if available
        elif patcher_models.KEY_VERSION_LATEST in available_versions_with_patches:
            target_version = patcher_models.KEY_VERSION_LATEST
        # Fall back to first available version
        elif available_versions_with_patches:
            target_version = available_versions_with_patches[0]

        if target_version:
            self.version_combobox.setCurrentText(target_version.capitalize())
            # Update current config version
            self.patch_options_configuration.version = target_version
            log.info(f"Set config version: {target_version}")
        else:
            log.warning(f"No version with patches available for {game_name} on {self._current_platform}")

        self.version_combobox.blockSignals(False)

        log.info(f"Current text before _on_version_changed: '{self.version_combobox.currentText()}'")
        self._on_version_changed(self.version_combobox.currentText())

        # Update Utilities Game Title
        self.utilities_selected_game_label.setText(f"SELECTED GAME: {self.patch_options_configuration.game}")

    def _on_version_changed(self, version_name: str):
        # Clear previous checkboxes
        while self.patches_layout.count():
            child = self.patches_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        game_name = self.game_combobox.currentText()
        if not game_name or not version_name:
            return

        # Update current config to match UI
        self.patch_options_configuration.game = game_name
        self.patch_options_configuration.version = version_name.lower()

        patcher = self.patcher.get_game_patcher(game_name, version_name.lower())
        if not patcher:
            return

        # Determine platform from UI Widget
        # Use stored platform if available, otherwise detect it
        if not self._current_platform:
            self._current_platform = self._get_current_platform()
            log.warning(f"Platform was not set, auto-detected from system: {self._current_platform}")

        # Determine if current UI selection matches initial config
        is_initial_config = (
            game_name == self.patch_options_configuration.game
            and version_name.lower() == self.patch_options_configuration.version.lower()
        )

        # Only use saved selection if it's in the initial config and list is not empty
        use_saved_selections: bool = is_initial_config and len(self.patch_options_configuration.selected_patches) > 0

        log.info(f"{use_saved_selections=}", silent=True)

        # Populate scroll area with patch option checkboxes
        available_patches = patcher.get_available_patches(platform=self._current_platform)

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
                if patch_name in self.patch_options_configuration.selected_patches:
                    checkbox.setChecked(True)
                # Otherwise remains unchecked
            else:
                # If new selection, check all by default
                checkbox.setChecked(default_enabled or is_required)

            self.patches_layout.addWidget(checkbox)

            # Store patch_name property for easy retrieval
            checkbox.setProperty("patch_name", patch_name)

        # Update config with selection if not using a saved selection.
        # This is so that if the dialog was never spawned, there is a default config to retrieve.
        if not use_saved_selections:
            for patch_name, patch_info in available_patches.items():
                if patch_info.enabled or patch_info.required:
                    self.patch_options_configuration.selected_patches.append(patch_name)

        # Log current config
        log.info(
            f"Displaying current config:\nGame={self.game_combobox.currentText()}\nVersion: {self.version_combobox.currentText().lower()}\nPlatform: {self._current_platform}",
            silent=True,
        )

    def _on_binary_type_changed(self, text):
        log.info(f"Binary type changed to: {text}", silent=True)

        # Update AppConfig
        self.svc.config.use_proton = self._should_use_proton()

        # Trigger re-update options
        self._on_version_changed(self.version_combobox.currentText())

    def callback_use_local_patterns(self, state):
        if state in (Qt.CheckState.Checked.value, Qt.CheckState.Unchecked.value):
            # We don't need to set for --no-conn
            if not self.svc.config.prevent_conn:
                self.svc.settings.settings.force_local_patterns = bool(state)
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

    def show_game_folder(self, auto_located_path: Optional[Path] = None, _retry_attempted: bool = False):
        paths = [
            self.svc.settings.game(self.patch_options_configuration.game).install_path,
            self.svc.settings.game(self.patch_options_configuration.game).proton_install_path,
        ]

        # Attempt to find a valid executable from settings
        saved_path = None

        # Prioritise auto_located_path
        if auto_located_path and auto_located_path.exists():
            saved_path = auto_located_path
            log.info(f"Using auto-located: {saved_path}", silent=True)

            # Save the paths
            if saved_path and saved_path.exists():
                saved_path_posix = saved_path.resolve().as_posix()
                log.info(f"Save: '{saved_path_posix}'")

                if os_windows():
                    self.svc.settings.game(self.patch_options_configuration.game).install_path = saved_path_posix
                elif (os_linux() and self.svc.config.use_proton) or (
                    os_linux() and self.patch_options_configuration.is_proton
                ):
                    self.svc.settings.game(self.patch_options_configuration.game).proton_install_path = saved_path_posix
                else:
                    # Also account for proton cases
                    if self.patch_options_configuration.is_proton:
                        self.svc.settings.game(self.patch_options_configuration.game).proton_install_path = (
                            saved_path_posix
                        )
                    else:
                        self.svc.settings.game(self.patch_options_configuration.game).install_path = saved_path_posix

        else:
            # Iterate once to test if any path exists
            for path_str in paths:
                if not path_str:
                    continue

                path = Path(path_str)

                if path.exists():
                    saved_path = path
                    log.info(f"Saved path: '{saved_path}'", silent=True)
                    break

                if path.parent.exists():
                    saved_path = path.parent
                    log.info(f"Derived Game Folder: {saved_path}", silent=True)
                    break

        if saved_path:
            # MacOS specific case
            if os_darwin():
                if saved_path.is_file():
                    saved_path = saved_path.parent.parent.parent

            log.info(f"Opening game folder: '{saved_path}'", silent=False)
            open_in_file_manager(saved_path)
            return saved_path
        else:
            log.warning(f"Unable to determine saved path: '{saved_path}'")
            log.info("Attempting to auto-locate game installation...")

            if not auto_located_path and not _retry_attempted:
                # Attempt to auto locate and re-run the function
                path_finder_thread = Threader(target=self._find_game_path_worker_thread)
                path_finder_thread.signals.result.connect(
                    lambda result: self.show_game_folder(result, _retry_attempted=True)
                )
                path_finder_thread.signals.finished.connect(lambda: self._cleanup_thread(path_finder_thread))
                self.active_threads.append(path_finder_thread)
                path_finder_thread.start()
                return None
            else:
                log.info("Auto-location already attempted and failed.", silent=True)
                picked_path = prompt_install_dir(self.patch_options_configuration.game)

                if picked_path:
                    self.show_game_folder(auto_located_path=picked_path, _retry_attempted=_retry_attempted)
                if not picked_path:
                    # User cancelled
                    log.warning(f"User cancelled location. Aborting patch")
                    return None

    def _find_game_path_worker_thread(self) -> Optional[Path]:
        """
        WORKER FUNCTION: Tries to find the game path automatically.
        Returns the path if found, otherwise None.
        """

        return find_game_path(self.patcher, self.patch_options_configuration)

    def _cleanup_thread(self, thread: Threader):
        """Remove finished thread from active list."""

        if thread in self.active_threads:
            self.active_threads.remove(thread)
            thread.deleteLater()
            log.info(f"Cleaned up worker thread. Active threads: {len(self.active_threads)}", silent=True)

    def _on_max_backups_slider_changed(self, value: int):
        # Update display label
        if value <= 0:
            self.max_backup_value_label.setText("Off")
        else:
            self.max_backup_value_label.setText(str(value))

        # Save to settings
        self.svc.settings.settings.max_allowed_binary_backups = value

        log.info(f"Maximum allowed backups set to: {value}")

    def show_app_config_folder(self):
        config_dir = self.svc.config.config_dir

        if config_dir.exists() and config_dir.is_dir():
            log.info(f"App Config Folder: {config_dir}", silent=True)

            open_in_file_manager(config_dir)

    def fetch_patch_patterns(self) -> bool:
        log.info(f"Fetch Patch Patterns...", silent=True)

        get_patterns_config_remote()

        self.patcher.reload_patterns()

        self._populate_options()

    def show_welcome_dialog(self):
        # --- Show welcome dialog ---
        welcome_dialog = WelcomeDialog(self.font, window_icon=self.windowIcon(), parent=self)
        welcome_dialog.show()

    def closeEvent(self, event):
        """Cleanup all active threads when dialog closes."""

        for thread in self.active_threads:
            if thread.isRunning():
                thread.quit()
                thread.wait()
            thread.deleteLater()
            self.active_threads.clear()
            super().closeEvent(event)
