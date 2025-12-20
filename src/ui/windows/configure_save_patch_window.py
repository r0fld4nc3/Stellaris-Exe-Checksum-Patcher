from typing import Dict, List

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from conf_globals import LOG_LEVEL
from logger import create_logger
from patchers import models as patcher_models

log = create_logger("Save Patch Config", LOG_LEVEL)


class ConfigureSavePatchDialog(QDialog):
    def __init__(
        self,
        game_name: str,
        font: QFont,
        window_icon: QIcon,
        parent=None,
    ):
        super().__init__(parent)

        self.font = font
        self.game_name = game_name
        self.current_config = patcher_models.SavePatchConfigRegistry.get_config(game_name)

        self.option_checkboxes: Dict[str, QCheckBox] = {}

        # --- Style and Appearance ---
        # Qt.Window treats this is a top-level window while being able to receive a parent
        # This fixes the odd behaviour where a frameless window with a parent
        # would appear off centre and clipped by the main window.
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint | Qt.Window
        )

        self.setWindowTitle("Configure Save Patch")
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

        # --- Game Info Section --.
        if self.current_config:
            info_label = QLabel(f"<b>{self.current_config.display_name}</b>")
            info_label.setFont(self.font)
            content_layout.addWidget(info_label)

            desc_label = QLabel(self.current_config.description)
            desc_label.setWordWrap(True)
            content_layout.addWidget(desc_label)

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

        # --- Ok / Cancel Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        for button in button_box.buttons():
            button.setFont(self.font)
        ok_cancel_layout.addWidget(button_box)

        # --- Initial population ---
        self._populate_options()

    def _populate_options(self):
        log.info(f"Populating Options", silent=True)

        while self.patches_layout.count():
            child = self.patches_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not self.current_config or not self.game_name:
            log.error(f"No configuration for game: {self.game_name}")
            error_label = QLabel(f"No patch options available for: {self.game_name}")
            self.patches_layout.addWidget(error_label)
            return

        # Get available options
        available_options = self.current_config.get_available_options()

        if not available_options:
            log.warning(f"No available options for: {self.game_name}")
            no_options_label = QLabel("No patch options currently available")
            self.patches_layout.addWidget(no_options_label)
            return

        # Create checkboxes
        for option in available_options:
            checkbox = QCheckBox(option.display_name)
            checkbox.setToolTip(option.description)
            checkbox.setChecked(option.default_value)
            checkbox.setEnabled(option.enabled)

            # Store ID as property for later easy retrieval
            checkbox.setProperty("option_id", option.id)

            self.patches_layout.addWidget(checkbox)

            # Store reference for later retrieval
            self.option_checkboxes[option.id] = checkbox

        log.info(
            f"Displaying patch options for {self.game_name}: {len(available_options)} option(s) avaialble.", silent=True
        )

    def get_configuration(self) -> patcher_models.GameSavePatchConfig:
        for patch_id, checkbox_widget_ref in self.option_checkboxes.items():
            self.current_config.set_enabled(patch_id, checkbox_widget_ref.isChecked())
            log.info(f"{patch_id}: {self.current_config.get_option(patch_id).enabled}", silent=True)

        return self.current_config

    def get_enabled_patches(self) -> List[patcher_models.SavePatchOption]:
        return self.get_configuration().get_enabled_options()
