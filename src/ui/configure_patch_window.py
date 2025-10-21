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
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from conf_globals import IS_DEBUG, LOG_LEVEL, OS, SETTINGS, USE_LOCAL_PATTERNS
from logger import create_logger
from patchers import MultiGamePatcher, PatchConfiguration
from patchers import models as patcher_models

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

        # --- Game & Version Selection --.
        selection_layout = QHBoxLayout()

        self.game_combobox = QComboBox()
        self.game_combobox.setFont(self.font)

        self.version_combobox = QComboBox()
        self.version_combobox.setFont(self.font)

        selection_layout.addWidget(QLabel("Game:"))
        selection_layout.addWidget(self.game_combobox, 1)
        selection_layout.addWidget(QLabel("Version:"))
        selection_layout.addWidget(self.version_combobox, 1)
        content_layout.addLayout(selection_layout)

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
        content_layout.addWidget(self.patches_scroll_area)

        # --- OK/Cancel Layout ---
        ok_cancel_layout = QHBoxLayout()
        content_layout.addLayout(ok_cancel_layout)

        # --- Use Local Patterns CheckBox---
        self.chkbox_use_local_patterns = QCheckBox("Force Local Patterns")
        self.chkbox_use_local_patterns.setToolTip(
            "When toggled, application will not longer pull updated patterns from remote and will only strictly use the patterns file present on disk.\nThis is mainly useful for testing purposes, for trying out different patterns to prevent the local file from being overwritten on application startup."
        )
        self.chkbox_use_local_patterns.stateChanged.connect(self.callback_use_local_patterns)
        # Force update state when global enforcement rule is applied
        if USE_LOCAL_PATTERNS:
            self.chkbox_use_local_patterns.setEnabled(False)
            SETTINGS.set_force_use_local_patterns(Qt.CheckState.Unchecked.value)
        ok_cancel_layout.addWidget(self.chkbox_use_local_patterns)

        # --- Ok / Cancel Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        for button in button_box.buttons():
            button.setFont(self.font)
        ok_cancel_layout.addWidget(button_box)

        # --- Signals ---
        self.game_combobox.currentTextChanged.connect(self._on_game_changed)
        self.version_combobox.currentTextChanged.connect(self._on_version_changed)

        # --- Initial population ---
        self._populate_options()

        # --- Load settings ---
        self._load_settings()

    def _load_settings(self):
        # Reflect settings in UI
        use_local_patterns = any([USE_LOCAL_PATTERNS, SETTINGS.get_force_use_local_patterns()])
        self.chkbox_use_local_patterns.setCheckState(
            Qt.CheckState.Checked if use_local_patterns else Qt.CheckState.Unchecked
        )

    def _create_default_config(self, game: str = None) -> PatchConfiguration:
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

        available_patches = patcher.get_available_patches(platform=platform)
        for patch_name, patch_info in available_patches.items():
            checkbox = QCheckBox(patch_info.display_name)
            checkbox.setToolTip(patch_info.description)
            checkbox.setFont(self.font)

            if use_saved_selections:
                # Restore user's saved selections if inital config
                if patch_name in self.current_config.selected_patches:
                    checkbox.setChecked(True)
                # Otherwise remains unchecked
            else:
                # If new selection, check all by default
                checkbox.setChecked(True)

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
