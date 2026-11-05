import logging
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QLabel,
    QRadioButton,
    QVBoxLayout,
)

from stores import DEFAULT_GAME_STORE, GameStore
from ui.utils import EventFilterMoveResize, adapt_to_parent_size, centre_on_parent

log = logging.getLogger("Store Picker Dialog")


class StorePickerDialog(QDialog):
    """
    Asks where a game was installed from (Steam, GOG, Generic) the first time it's patched.

    Only stores supported on this system are offered. Use `ask()`, which returns the pick or None on Cancel.
    """

    # (width, height) as percentages of the parent window
    SIZE_PCT = (60, 60)
    MIN_SIZE_PCT = (40, 40)

    def __init__(self, game: str, preselected_store: GameStore, font: QFont, window_icon: QIcon, parent=None):
        super().__init__(parent)

        self.store_buttons: dict[GameStore, QRadioButton] = {}

        self.setObjectName("StorePickerDialog")
        self.setWindowTitle(f"Where is {game} from?")
        self.setWindowIcon(window_icon)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setFont(font)

        # Frameless. Handle moving and resizing with same filter
        self.resize_move_filter = EventFilterMoveResize(self)
        self.installEventFilter(self.resize_move_filter)

        # --- Dialog layout with frame ---
        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)

        # --- Frame ---
        main_frame = QFrame(self)
        main_frame.setProperty("windowDragHandle", True)  # Drag handle on QWidgets
        main_frame.setFrameShape(QFrame.WinPanel)
        main_frame.setFrameShadow(QFrame.Plain)
        main_frame.setLineWidth(5)
        main_frame.setMidLineWidth(0)
        main_frame.setContentsMargins(10, 10, 10, 10)
        dialog_layout.addWidget(main_frame)

        # --- Content Layout ---
        content_layout = QVBoxLayout(main_frame)
        content_layout.setContentsMargins(10, 10, 10, 10)

        # --- Title ---
        title_font = QFont(font)
        title_font.setPointSize(16)

        title_label = QLabel(f"Where is {game} from?")
        title_label.setObjectName("SectionTitle")
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(title_label)

        # --- Intro Label (explanation for both new and existing users) ---
        intro_label = QLabel(
            f"The Patcher now supports GOG as well as Steam. Pick where your copy of {game} comes from, so the Patcher knows how to find, launch and validate it.\n\n"
            "You only need to do this once. You can change it later in the options, under Game Utilities."
        )
        intro_label.setObjectName("StorePickerText")
        intro_label.setWordWrap(True)
        content_layout.addWidget(intro_label)

        # --- Stores ---
        for store in GameStore:
            if not store.is_supported:
                continue
            self._add_store_option(content_layout, store)

        self._check_store(preselected_store)

        content_layout.addStretch(1)

        # --- Buttons ---
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("Continue")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        for button in button_box.buttons():
            button.setFont(font)
        content_layout.addWidget(button_box)

    @classmethod
    def ask(
        cls, game: str, preselected_store: GameStore, font: QFont, window_icon: QIcon, parent=None
    ) -> Optional[GameStore]:
        """Show the picker and wait. The picked store, or None if the user cancels."""
        store_picker = cls(game, preselected_store, font, window_icon, parent=parent)
        if store_picker.exec() != QDialog.DialogCode.Accepted:
            return None

        return store_picker.selected_store()

    def selected_store(self) -> GameStore:
        """The store the user picked."""
        for store, button in self.store_buttons.items():
            if button.isChecked():
                return store

        # Not reached: one button is always selected
        return DEFAULT_GAME_STORE

    def _add_store_option(self, layout: QVBoxLayout, store: GameStore):
        radio_button = QRadioButton(store.display_name)
        layout.addWidget(radio_button)

        description_label = QLabel(store.description)
        description_label.setObjectName("StoreDescription")
        description_label.setWordWrap(True)
        # Line the text up with the button's label not the radio circle
        description_label.setContentsMargins(30, 0, 0, 10)
        layout.addWidget(description_label)

        self.store_buttons[store] = radio_button

    def _check_store(self, store: GameStore):
        """Check `store`'s button. The first store's when `store` isn't supported on this system."""
        button = self.store_buttons.get(store)
        if not button:
            log.debug(f"{store.display_name} isn't supported here. Pre-selecting the first store.")
            button = next(iter(self.store_buttons.values()))

        button.setChecked(True)

    def showEvent(self, event):
        super().showEvent(event)
        adapt_to_parent_size(self, self.parentWidget(), self.SIZE_PCT, self.MIN_SIZE_PCT)
        self.setMinimumSize(self.minimumSize().expandedTo(self.minimumSizeHint()))
        centre_on_parent(self, self.parentWidget())
