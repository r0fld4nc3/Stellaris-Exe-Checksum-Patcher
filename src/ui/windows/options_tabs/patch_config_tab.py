import logging
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from config.path_helpers import os_darwin, os_linux, os_windows
from patchers import PatchConfiguration
from patchers import models as patcher_models

from .base import OptionsContext, OptionsTab
from .shared_widgets.game_combobox import GameComboBox

log = logging.getLogger("Patch Config")


class PatchConfigTab(OptionsTab):
    """Game/version/platform selection and the list of patches to apply."""

    title = "Patch Configuration"

    def __init__(self, context: OptionsContext, parent=None):
        super().__init__(context, parent)

        self._current_platform: Optional[patcher_models.Platform] = None
        self._display_key_to_pattern_key: dict[str, str] = {}

        font = self.ctx.font

        patch_layout = QVBoxLayout(self)
        patch_layout.setContentsMargins(10, 10, 10, 10)

        # --- Game Info Section ---
        if self.config:
            info_label = QLabel(f"<b>Patch Configuration</b>")
            info_label.setFont(font)
            patch_layout.addWidget(info_label)

            desc_label = QLabel(f"Select what game to patch and with that options.")
            desc_label.setWordWrap(True)
            patch_layout.addWidget(desc_label)

        # --- Game & Version Selection ---
        selection_layout = QHBoxLayout()

        self.game_combobox = GameComboBox(self.ctx)

        self.version_combobox = QComboBox()
        self.version_combobox.setFont(font)
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
            self.use_proton_picker.setFont(font)
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
        # Game can be picked here or in another tab. Rebuild versions/patches regardless
        self.ctx.game_changed.connect(self._on_game_changed)
        self.version_combobox.currentTextChanged.connect(self._on_version_changed)

    # --- OptionsTab hooks ---

    def load(self):
        log.info(f"Populating Options", silent=True)

        if not self.config or not self.config.game:
            self.config = self._create_default_config()
            if not self.config:
                log.error(f"Failed to create a default configuration")
                return

        # Validate
        if not self._validate_configuration(self.config):
            log.error(f"Invalid configuration, creating default")
            self.config = self._create_default_config()
            if not self.config or not self._validate_configuration(self.config):
                log.error(f"Failed to create valid configuration")
                return

        self.game_combobox.populate()

        # Update platform UI
        if os_linux() or os_darwin():
            translation_layer = (
                patcher_models.TRANSLATION_LAYER_ENUM.PROTON
                if self.config.is_proton
                else patcher_models.TRANSLATION_LAYER_ENUM.NATIVE
            )
            self.use_proton_picker.setCurrentText(translation_layer)

        self._on_game_changed(self.config.game)

    def apply(self, configuration: PatchConfiguration):
        selected_patches = []

        for i in range(self.patches_layout.count()):
            checkbox = self.patches_layout.itemAt(i).widget()
            if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                selected_patches.append(checkbox.property("patch_name"))

        configuration.game = self.game_combobox.currentText()
        configuration.platform = self.get_selected_platform()

        # Get the key name from the display name
        display_version: str = self.version_combobox.currentText()
        configuration.version = self._display_key_to_pattern_key.get(display_version, display_version)

        configuration.is_proton = self._should_use_proton()
        configuration.selected_patches = selected_patches

    def _create_default_config(self, game: str = None) -> PatchConfiguration:
        log.info(f"Creating default patch configuration.", silent=True)
        games = self.ctx.patcher.get_available_games()

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
        if os_linux() or os_darwin():
            return self.use_proton_picker.currentText().lower() == patcher_models.TRANSLATION_LAYER_ENUM.PROTON.lower()
        return False

    def _get_current_platform(self) -> patcher_models.Platform:
        return (
            patcher_models.Platform.detect_current()
            if not self._should_use_proton()
            else patcher_models.Platform.WINDOWS
        )

    def get_selected_platform(self) -> patcher_models.Platform:
        use_proton = self._should_use_proton()

        if os_linux():
            if not use_proton:
                return patcher_models.Platform.LINUX
        elif os_darwin():
            if not use_proton:
                return patcher_models.Platform.DARWIN

        return patcher_models.Platform.WINDOWS

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

        available_games = self.ctx.patcher.get_available_games()
        if config.game not in available_games:
            log.error(f"Game '{config.game}' not in available games: {available_games}")
            return False

        return True

    # --- Slots ---
    def _on_game_changed(self, game_name: str):
        """Per-tab decision on what to do when the selected game changes."""

        versions = self.ctx.patcher.get_available_versions(game_name)
        self.version_combobox.blockSignals(True)
        self.version_combobox.clear()

        # Clear key cache for new game
        self._display_key_to_pattern_key.clear()

        last_platform_str = self.svc.settings.game(game_name).patched_platform

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

            if use_proton:
                self.use_proton_picker.setCurrentText(patcher_models.TRANSLATION_LAYER_ENUM.PROTON)
            else:
                self.use_proton_picker.setCurrentText(patcher_models.TRANSLATION_LAYER_ENUM.NATIVE)

        for version_key in versions:
            # Build a cache of display versions and the real key they represent
            # Visual nicety and cached retrieval is fast and won't break with formatting
            display_version: str = version_key.capitalize() if not " " in version_key else version_key.title()
            self._display_key_to_pattern_key[display_version] = version_key
            self.version_combobox.addItem(display_version)

        # Keep the configured version if it still applies, otherwise let the patcher choose.
        # (Changing game resets the configured version, see OptionsContext.select_game.)
        target_version_key = self.ctx.patcher.pick_version(
            game_name, platform=self._current_platform, preferred=self.config.version
        )

        if target_version_key:
            display_name = next(
                (display for display, key in self._display_key_to_pattern_key.items() if key == target_version_key),
                target_version_key.capitalize(),
            )
            self.version_combobox.setCurrentText(display_name)
            # Update current config version
            self.config.version = target_version_key
            log.info(f"Set config version: {target_version_key} (display: {display_name})")
        else:
            log.warning(f"No version with patches available for {game_name} on {self._current_platform}")

        self.version_combobox.blockSignals(False)

        log.info(f"Current text before _on_version_changed: '{self.version_combobox.currentText()}'")
        self._on_version_changed(self.version_combobox.currentText())

        # Let other tabs know the selection changed
        self.ctx.configuration_changed.emit()

    def _on_version_changed(self, version_display_name: str):
        # Clear previous checkboxes
        while self.patches_layout.count():
            child = self.patches_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        game_name = self.game_combobox.currentText()
        if not game_name or not version_display_name:
            return

        version_key: str = self._display_key_to_pattern_key.get(version_display_name, version_display_name)
        log.debug(f"Display: '{version_display_name}' -> '{version_key}'")

        # Update current config to match UI
        self.config.game = game_name
        self.config.version = version_key

        patcher = self.ctx.patcher.get_game_patcher(game_name, version_key)
        if not patcher:
            return

        # Determine platform from UI Widget
        self._current_platform = self._get_current_platform()
        log.warning(f"Platform was not set, auto-detected from system: {self._current_platform}")

        # Determine if current UI selection matches initial config
        is_initial_config = game_name == self.config.game and version_key == self.config.version

        # Only use saved selection if it's in the initial config and list is not empty
        use_saved_selections: bool = is_initial_config and len(self.config.selected_patches) > 0

        log.info(f"{use_saved_selections=}", silent=True)

        # Populate scroll area with patch option checkboxes
        available_patches = patcher.get_available_patches(platform=self._current_platform)

        log.debug(
            f"ON VERSION CHANGED: Patches for version {version_key} on platform {self._current_platform}: {available_patches=}"
        )

        for patch_name, patch_info in available_patches.items():
            checkbox = QCheckBox(patch_info.display_name)
            checkbox.setToolTip(patch_info.description)
            checkbox.setFont(self.ctx.font)
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
                if patch_name in self.config.selected_patches:
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
        # Assign a new list rather than appending, so repeated calls don't pile up duplicates.
        if not use_saved_selections:
            self.config.selected_patches = [
                patch_name
                for patch_name, patch_info in available_patches.items()
                if patch_info.enabled or patch_info.required
            ]

        # Log current config
        log.info(
            f"Displaying current config:\nGame={self.game_combobox.currentText()}\nVersion: {self.version_combobox.currentText()}\nPlatform: {self._current_platform}",
            silent=True,
        )

    def _on_binary_type_changed(self, text):
        log.info(f"Binary type changed to: {text}", silent=True)

        # Update AppConfig
        self.svc.config.use_proton = self._should_use_proton()

        # Trigger re-update options
        self._on_version_changed(self.version_combobox.currentText())
