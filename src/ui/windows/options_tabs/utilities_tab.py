import logging
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from patch_patterns.patterns import get_patterns_config_remote
from remote_messages import read_cached_message
from ui.shared_widgets import QSquarePushButton
from ui.utils import prompt_path
from utils.helpers import block_signals
from utils.platform import open_in_file_manager

from ..message_dialog import MessageDialog
from ..welcome_dialog import WelcomeDialog
from .base import OptionsContext, OptionsTab

log = logging.getLogger("Utilities")

RUNNER_EXAMPLES_HTML = """
<p><b>How it works:</b> the Generic Runner is started with these arguments. <b>{binary}</b> becomes the game executable and <b>{folder}</b> the folder it's in. Leave the field empty to pass only the game executable.</p>
<p>Some runners, like Heroic and Lutris, start their own install of the game rather than the patched file. Make sure they point to the same install you patched.</p>
<p><b>Wine</b><br>Runner: /usr/bin/wine<br>Arguments: {binary}</p>
<p><b>Proton outside Steam (umu-run)</b><br>Runner: /usr/bin/umu-run<br>Arguments: {binary}</p>
<p><b>Heroic (Stellaris GOG)</b><br>Runner: heroic<br>Arguments: --no-gui heroic://launch/gog/1508702879</p>
<p><b>Heroic (sideloaded game)</b><br>Runner: heroic<br>Arguments: --no-gui heroic://launch/sideload/&lt;game ID in Heroic&gt;</p>
<p><b>Heroic (Flatpak)</b><br>Runner: /usr/bin/flatpak<br>Arguments: run com.heroicgameslauncher.hgl --no-gui heroic://launch/gog/1508702879</p>
<p><b>Lutris</b><br>Runner: lutris<br>Arguments: lutris:rungame/&lt;game slug in Lutris&gt;</p>
<p><b>CrossOver (macOS)</b><br>Runner: /Applications/CrossOver.app/Contents/SharedSupport/CrossOver/bin/wine<br>Arguments: --bottle &lt;your bottle&gt; {binary}</p>
"""


class UtilitiesTab(OptionsTab):
    """General app settings and helper tools."""

    title = "General Utilities"

    def __init__(self, context: OptionsContext, parent=None):
        super().__init__(context, parent)

        font = self.ctx.font

        font_section = QFont(font)
        font_section.setPointSize(18)

        font_header = QFont(font)
        font_header.setPointSize(16)

        utilities_tab_layout = QVBoxLayout(self)
        utilities_tab_layout.setContentsMargins(10, 10, 10, 10)
        utilities_tab_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Title ---
        title_label = QLabel("<b>General Utilities</b>")
        title_label.setObjectName("SectionTitle")
        title_label.setFont(font_section)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        utilities_tab_layout.addWidget(title_label)

        # --- Description Label
        desc_label = QLabel("Additional tools and utilities")
        desc_label.setFont(font_header)
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

        # --- Manage Save Backups Button ---
        btn_manage_save_backups = QPushButton("Manage Save Backups")
        btn_manage_save_backups.setFont(font)
        btn_manage_save_backups.setToolTip("Choose which of the generated save backups to keep or delete.")
        btn_manage_save_backups.clicked.connect(self.show_save_backups_dialog)
        utilities_layout.addWidget(btn_manage_save_backups)

        # --- Open Welcome Dialog Button ---
        btn_show_welcome_dialog = QPushButton("Show Welcome Dialog")
        btn_show_welcome_dialog.setFont(font)
        btn_show_welcome_dialog.clicked.connect(self.show_welcome_dialog)
        utilities_layout.addWidget(btn_show_welcome_dialog)

        # --- Show Information Message Button ---
        btn_show_info_message = QPushButton("Show Information Message")
        btn_show_info_message.setFont(font)
        btn_show_info_message.clicked.connect(self.show_information_message)
        utilities_layout.addWidget(btn_show_info_message)

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
        self.chkbox_use_local_patterns.setObjectName("StyledCheckbox1")
        # self.chkbox_use_local_patterns.setFont(self.ctx.font)
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
        self.chkbox_include_prerelease_updates.setObjectName("StyledCheckbox1")
        # self.chkbox_include_prerelease_updates.setFont(self.ctx.font)
        self.chkbox_include_prerelease_updates.setToolTip(
            "When toggled, newer pre-releases also count as an available update, not only stable releases.\nPre-releases are early versions for testing and may be less stable."
        )
        self.chkbox_include_prerelease_updates.toggled.connect(self._on_include_prerelease_updates_toggled)

        # Update checks don't run with --no-conn
        if self.svc.config.prevent_conn:
            self.chkbox_include_prerelease_updates.setEnabled(False)
        utilities_layout.addWidget(self.chkbox_include_prerelease_updates)

        # --- Spacer ---
        utilities_layout.addWidget(QLabel())

        # --- Launchers ---
        # What starts the game after patching.
        launchers_label = QLabel("<b>Launchers</b>")
        launchers_label.setObjectName("SectionTitle")
        launchers_label.setFont(font_section)
        launchers_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        utilities_layout.addWidget(launchers_label)

        self.system_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)

        launchers_layout = QGridLayout()
        launchers_layout.setColumnStretch(1, 1)

        self.steam_launcher_path_field = self._add_launcher_row(
            launchers_layout,
            0,
            "Steam:",
            "Steam folder, used to find, launch and validate Steam games.\n" "Found automatically when empty.",
            on_browse=self._browse_steam_folder,
            on_clear=self._clear_steam_path,
        )

        self.gog_launcher_path_field = self._add_launcher_row(
            launchers_layout,
            1,
            "GOG Galaxy:",
            "GOG Galaxy folder, used to find and launch GOG games.\n" "Found automatically when empty.",
            on_browse=self._browse_gog_folder,
            on_clear=self._clear_gog_path,
        )

        self.generic_runner_path_field = self._add_launcher_row(
            launchers_layout,
            2,
            "Generic Runner:",
            "Anything that can run the game executable (Wine, Bottles, Lutris, Heroic...).\n"
            "Used to launch games set to Generic.",
            on_browse=self._browse_generic_runner,
            on_clear=self._clear_generic_runner_path,
        )

        generic_runner_args_label = QLabel("Runner Arguments:")
        generic_runner_args_label.setFont(font)
        generic_runner_args_label.setObjectName("FieldNameLabel")

        self.generic_runner_args_field = QLineEdit()
        self.generic_runner_args_field.setFont(self.system_font)
        self.generic_runner_args_field.setPlaceholderText("--no-gui heroic://launch/gog/1508702879")
        self.generic_runner_args_field.editingFinished.connect(self._on_generic_runner_args_edited)

        # --- Runner examples (scrolls on its own, so the tab stays short) ---
        runner_examples_label = QLabel(RUNNER_EXAMPLES_HTML)
        runner_examples_label.setObjectName("HintLabel")
        runner_examples_label.setFont(self.system_font)
        runner_examples_label.setWordWrap(True)
        runner_examples_label.setTextFormat(Qt.TextFormat.RichText)
        runner_examples_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        runner_examples_label.setAlignment(Qt.AlignmentFlag.AlignTop)

        runner_examples_scroll_area = QScrollArea()
        runner_examples_scroll_area.setWidgetResizable(True)
        runner_examples_scroll_area.setMinimumHeight(160)
        runner_examples_scroll_area.setWidget(runner_examples_label)

        launchers_layout.addWidget(generic_runner_args_label, 3, 0)
        launchers_layout.addWidget(self.generic_runner_args_field, 3, 1, 1, 3)
        launchers_layout.addWidget(runner_examples_scroll_area, 4, 1, 1, 3)
        # launchers_layout.addWidget(generic_runner_note_label, 4, 1, 1, 3)
        utilities_layout.addLayout(launchers_layout)

        # --- Spacer ---
        # utilities_layout.addWidget(QLabel())

        # --- Set scrollable widget ---
        utilities_scroll_area.setWidget(utilities_content_widget)
        utilities_tab_layout.addWidget(utilities_scroll_area)

    # --- OptionsTab hooks ---

    def load(self):
        log.info("Load Settings")

        # Backups slider (no signal: value comes from settings, nothing to save)
        max_backups = self.svc.settings.settings.max_allowed_binary_backups
        with block_signals(self.max_backups_slider):
            self.max_backups_slider.setValue(max_backups)
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

        with block_signals(self.chkbox_include_prerelease_updates):
            self.chkbox_include_prerelease_updates.setChecked(self.svc.settings.settings.include_prerelease_updates)

        self._update_launchers_paths()

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

    def _on_generic_runner_args_edited(self):
        self.svc.settings.settings.generic_runner_args = self.generic_runner_args_field.text().strip()

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

    def show_save_backups_dialog(self):
        from ui.windows import SaveBackupsDialog

        dialog = SaveBackupsDialog(self.ctx.font, parent=self.window())
        dialog.exec()

    def show_welcome_dialog(self):
        window = self.window()
        dialog = WelcomeDialog(self.ctx.font, window_icon=window.windowIcon(), parent=window)
        dialog.show()

    def show_information_message(self):
        """Show the last downloaded message again."""
        message = read_cached_message()
        window = self.window()

        if not message.text:
            log.info("No information message to show.")
            QMessageBox.information(window, "Information Message", "There's no information message right now.")
            return

        dialog = MessageDialog(message, self.ctx.font, window_icon=window.windowIcon(), parent=window)
        dialog.SIZE_PCT = (90, 100)
        dialog.show()

    # --- Helpers ---

    def _add_launcher_row(
        self,
        layout: QGridLayout,
        row: int,
        label_text: str,
        tooltip: str,
        on_browse: Callable[[], None],
        on_clear: Callable[[], None],
    ) -> QLineEdit:
        """Label, read-only path field and Browse button on `row` of `layout`. Returns the path field."""
        font = self.ctx.font

        label = QLabel(label_text)
        label.setFont(font)
        label.setToolTip(tooltip)
        label.setObjectName("FieldNameLabel")

        path_field = QLineEdit()
        path_field.setFont(self.system_font)
        path_field.setReadOnly(True)
        path_field.setPlaceholderText("Not set")
        path_field.setToolTip(tooltip)

        btn_browse = QPushButton("Browse...")
        btn_browse.setFont(font)
        btn_browse.clicked.connect(on_browse)

        btn_clear = QSquarePushButton("X")
        btn_clear.setFont(font)
        btn_clear.setToolTip("Forget this path")
        btn_clear.clicked.connect(on_clear)

        layout.addWidget(label, row, 0)
        layout.addWidget(path_field, row, 1)
        layout.addWidget(btn_browse, row, 2)
        layout.addWidget(btn_clear, row, 3)
        return path_field

    def _update_max_backups_label(self, value: int):
        self.max_backup_value_label.setText("Off" if value <= 0 else str(value))

    def _browse_steam_folder(self):
        saved_path = self.svc.settings.settings.steam_install_path

        picked = prompt_path(
            self,
            "Choose the Steam folder",
            pick_folder=True,
            start_path=Path(saved_path) if saved_path else None,
        )
        if not picked:
            return

        self.svc.settings.settings.steam_install_path = picked.as_posix()

        self._update_launchers_paths()

    def _browse_gog_folder(self):
        saved_path = self.svc.settings.settings.gog_install_path

        picked = prompt_path(
            self,
            "Choose the GOG Galaxy folder",
            pick_folder=True,
            start_path=Path(saved_path) if saved_path else None,
        )
        if not picked:
            return

        self.svc.settings.settings.gog_install_path = picked.as_posix()

        self._update_launchers_paths()

    def _browse_generic_runner(self):
        saved_path = self.svc.settings.settings.generic_runner_path

        picked = prompt_path(
            self,
            "Choose preferred generic runner binary",
            start_path=Path(saved_path) if saved_path else None,
        )
        if not picked:
            return

        self.svc.settings.settings.generic_runner_path = picked.as_posix()

        self._update_launchers_paths()

    def _clear_steam_path(self):
        self.svc.settings.settings.steam_install_path = ""
        self._update_launchers_paths()

    def _clear_gog_path(self):
        self.svc.settings.settings.gog_install_path = ""
        self._update_launchers_paths()

    def _clear_generic_runner_path(self):
        self.svc.settings.settings.generic_runner_path = ""
        self._update_launchers_paths()

    def _update_launchers_paths(self):
        """
        Fill the launcher fields from settings.
        Empty fields show the placeholder.
        """

        app_settings = self.svc.settings.settings
        self.steam_launcher_path_field.setText(app_settings.steam_install_path)
        self.gog_launcher_path_field.setText(app_settings.gog_install_path)
        self.generic_runner_path_field.setText(app_settings.generic_runner_path)
        self.generic_runner_args_field.setText(app_settings.generic_runner_args)
