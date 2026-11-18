import logging

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QPushButton,
    QVBoxLayout,
)

from core.services import services
from ui.resources import AppGuide, load_guide
from ui.shared_widgets import MarkdownTextBrowser
from ui.utils import EventFilterMoveResize, adapt_to_parent_size, restore_window_focus

log = logging.getLogger("Welcome Dialog")


class WelcomeDialog(QDialog):
    SIZE_PCT = (100, 100)
    MIN_SIZE_PCT = (90, 90)

    def __init__(self, font: QFont, window_icon: QIcon, parent=None):
        super().__init__(parent)

        self.settings = services().settings

        self.font = font

        # --- Style & Appearance
        self.setWindowFlags(
            Qt.Dialog | Qt.WindowStaysOnTopHint | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint
        )

        self.setWindowTitle("Welcome and Overview")
        self.setWindowIcon(window_icon)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)

        # Hand activation back to the window underneath on every way out (Understood, Close, Escape)
        self.finished.connect(self._on_finished)

        # Frameless. Handle moving and resizing with same filter as main window.
        self.resize_move_filter = EventFilterMoveResize(self)
        self.installEventFilter(self.resize_move_filter)

        # --- Dialog layout with frame ---
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

        # --- Welcome text. Colours are in the QSS (`QTextBrowser#MarkdownText`) ---
        welcome_text = MarkdownTextBrowser()
        welcome_text.setObjectName("MarkdownText")
        welcome_text.setOpenExternalLinks(True)
        welcome_text.setFrameShape(QFrame.NoFrame)
        welcome_text.set_markdown(load_guide(AppGuide.WELCOME))
        content_layout.addWidget(welcome_text)

        # --- Buttons ---
        button_layout = QVBoxLayout()

        # Confirm and Don't Show Again
        # Make it dynamic! Appear only if never accepted!
        has_accepted = self.settings.app_settings.accepted_welcome_dialog
        if not has_accepted:
            btn_confirm = QPushButton("Understood! - Don't Show Again")
            # Override button font
            button_font = QFont(self.font)
            button_font.setPointSize(self.font.pointSize() + 6)
            # Set button font override
            btn_confirm.setFont(button_font)

            btn_confirm.clicked.connect(self._on_confirm)
            button_layout.addWidget(btn_confirm)

        # Close Button (without saving preference)
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        for button in button_box.buttons():
            button.setFont(self.font)
        button_layout.addWidget(button_box)

        content_layout.addLayout(button_layout)

    def _on_confirm(self):
        self.settings.app_settings.accepted_welcome_dialog = True
        self.accept()

    @Slot(int)
    def _on_finished(self, _result: int):
        # The window underneath doesn't always become active again by itself
        restore_window_focus(self.parentWidget().window())

    def showEvent(self, event):
        super().showEvent(event)
        # --- Set welcome dialog responsive to screen size ---
        adapt_to_parent_size(self, self.parentWidget().parentWidget(), self.SIZE_PCT, self.MIN_SIZE_PCT)

        # Frameless windows don't always become active when shown, and inactive windows get no hover
        restore_window_focus(self)
