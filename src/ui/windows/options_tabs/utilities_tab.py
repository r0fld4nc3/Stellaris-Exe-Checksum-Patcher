import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from patch_patterns.patterns import get_patterns_config_remote
from utils.platform import open_in_file_manager

from ..welcome_dialog import WelcomeDialog
from .base import OptionsContext, OptionsTab

log = logging.getLogger("Utilities")


class UtilitiesTab(OptionsTab):
    """General app settings and helper tools."""

    title = "General Utilities"

    def __init__(self, context: OptionsContext, parent=None):
        super().__init__(context, parent)

        font = self.ctx.font

        utilities_tab_layout = QVBoxLayout(self)
        utilities_tab_layout.setContentsMargins(10, 10, 10, 10)
        utilities_tab_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Title ---
        title_label = QLabel("<b>General Utilities</b>")
        title_label.setFont(font)
        utilities_tab_layout.addWidget(title_label)

        # --- Description Label
        desc_label = QLabel("Additional tools and utilities for game management.")
        desc_label.setWordWrap(True)
        utilities_tab_layout.addWidget(desc_label)

        # --- Scroll Area ---
        utilities_scroll_area = QScrollArea()
        utilities_scroll_area.setWidgetResizable(True)

        # --- Scrollable Content Widget
        utilities_content_widget = QWidget()
        utilities_layout = QVBoxLayout(utilities_content_widget)
        utilities_layout.setContentsMargins(5, 5, 5, 5)
        utilities_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Fetch/Update Patterns File Button ---
        btn_update_patch_patterns = QPushButton("Update Patterns")
        btn_update_patch_patterns.setFont(font)
        btn_update_patch_patterns.clicked.connect(self.fetch_patch_patterns)
        utilities_layout.addWidget(btn_update_patch_patterns)

        # --- Open Config Directory Button ---
        btn_show_app_config_dir = QPushButton("Show App Config Folder")
        btn_show_app_config_dir.setFont(font)
        btn_show_app_config_dir.clicked.connect(self.show_app_config_folder)
        utilities_layout.addWidget(btn_show_app_config_dir)

        # --- Open Welcome Dialog Button ---
        btn_show_welcome_dialog = QPushButton("Show Welcome Dialog")
        btn_show_welcome_dialog.setFont(font)
        btn_show_welcome_dialog.clicked.connect(self.show_welcome_dialog)
        utilities_layout.addWidget(btn_show_welcome_dialog)

        # --- Maximum Allowed Backups ---
        max_backups_control_layout = QHBoxLayout()

        # Maximum Backups Label
        max_backups_label = QLabel("Maximum Backups:")
        max_backups_label.setFont(font)
        max_backups_label.setToolTip(
            "Define the maximum number of backup files to keep for the game binary. Set to 0 to disable backups."
        )

        # Maximum Backups Slider
        self.max_backups_slider = QSlider(Qt.Horizontal)
        self.max_backups_slider.setMinimum(0)
        self.max_backups_slider.setMaximum(10)  # Reasonable max allowed backups
        self.max_backups_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.max_backups_slider.setTickInterval(1)
        self.max_backups_slider.setToolTip("Drag to adjust maximum number of backups.")
        self.max_backups_slider.valueChanged.connect(self._on_max_backups_slider_changed)

        # Value Display Label
        self.max_backup_value_label = QLabel()
        self.max_backup_value_label.setFont(font)
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
        self.chkbox_use_local_patterns.stateChanged.connect(self._on_use_local_patterns_changed)
        # Force update state when global enforcement rule is applied
        if any((self.svc.config.use_local_patterns, self.svc.config.prevent_conn)):
            self.chkbox_use_local_patterns.setEnabled(False)
        utilities_layout.addWidget(self.chkbox_use_local_patterns)

        # --- Include Pre-releases in Update Check Checkbox ---
        self.chkbox_include_prerelease_updates = QCheckBox("Include Pre-releases in Update Check")
        self.chkbox_include_prerelease_updates.setToolTip(
            "When toggled, newer pre-releases also count as an available update, not only stable releases.\nPre-releases are early versions for testing and may be less stable."
        )
        self.chkbox_include_prerelease_updates.toggled.connect(self._on_include_prerelease_updates_toggled)

        # Update checks don't run with --no-conn
        if self.svc.config.prevent_conn:
            self.chkbox_include_prerelease_updates.setEnabled(False)
        utilities_layout.addWidget(self.chkbox_include_prerelease_updates)

        # --- Spacer ---
        utilities_layout.addStretch()

        # --- Set scrollable widget ---
        utilities_scroll_area.setWidget(utilities_content_widget)
        utilities_tab_layout.addWidget(utilities_scroll_area)

    # --- OptionsTab hooks ---

    def load(self):
        log.info("Load Settings")

        # Backups slider (no signal: value comes from settings, nothing to save)
        max_backups = self.svc.settings.settings.max_allowed_binary_backups
        self.max_backups_slider.blockSignals(True)
        self.max_backups_slider.setValue(max_backups)
        self.max_backups_slider.blockSignals(False)
        self._update_max_backups_label(max_backups)

        # Reflect settings in UI
        use_local_patterns = any(
            [
                self.svc.config.use_local_patterns,
                self.svc.config.prevent_conn,
                self.svc.settings.settings.force_local_patterns,
            ]
        )
        self.chkbox_use_local_patterns.setCheckState(
            Qt.CheckState.Checked if use_local_patterns else Qt.CheckState.Unchecked
        )

        # TODO: Helper pattern for this blockSignals.
        self.chkbox_include_prerelease_updates.blockSignals(True)
        self.chkbox_include_prerelease_updates.setChecked(self.svc.settings.settings.include_prerelease_updates)
        self.chkbox_include_prerelease_updates.blockSignals(False)

    # --- Slots ---

    def _on_max_backups_slider_changed(self, value: int):
        self._update_max_backups_label(value)

        # Save to settings
        self.svc.settings.settings.max_allowed_binary_backups = value

        log.info(f"Maximum allowed backups set to: {value}")

    def _on_use_local_patterns_changed(self, state):
        if state in (Qt.CheckState.Checked.value, Qt.CheckState.Unchecked.value):
            # We don't need to set for --no-conn
            if not self.svc.config.prevent_conn:
                self.svc.settings.settings.force_local_patterns = bool(state)
        else:
            log.warning("Checkbox in Partially Checked state. We shouldn't be here.", silent=True)

    def _on_include_prerelease_updates_toggled(self, checked: bool):
        self.svc.settings.settings.include_prerelease_updates = checked

        log.info(f"Include pre-releases in update check: {checked}")

    def show_app_config_folder(self):
        config_dir = self.svc.config.config_dir

        if config_dir.exists() and config_dir.is_dir():
            log.info(f"App Config Folder: {config_dir}", silent=True)

            open_in_file_manager(config_dir)

    def fetch_patch_patterns(self):
        log.info("Fetch Patch Patterns...", silent=True)

        get_patterns_config_remote()

        self.ctx.patcher.reload_patterns()

        # New patterns may change games/versions/patches: reload every tab
        self.ctx.reload_requested.emit()

    def show_welcome_dialog(self):
        dialog = self.window()
        welcome_dialog = WelcomeDialog(self.ctx.font, window_icon=dialog.windowIcon(), parent=dialog)
        welcome_dialog.show()

    # --- Helpers ---

    def _update_max_backups_label(self, value: int):
        self.max_backup_value_label.setText("Off" if value <= 0 else str(value))
