import logging

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFrame, QVBoxLayout

from remote_messages import Message, save_message_as_seen
from ui.shared_widgets import MarkdownTextBrowser
from ui.utils import EventFilterMoveResize, adapt_to_parent_size

log = logging.getLogger("Message Dialog")


class MessageDialog(QDialog):
    SIZE_PCT = (90, 95)
    MIN_SIZE_PCT = (40, 40)

    def __init__(self, message: Message, font: QFont, window_icon: QIcon, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.font = font
        self.message = message

        self.setWindowTitle("Message Dialog")
        self.setWindowIcon(window_icon)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)

        # Frameless. Handle moving and resizing with same filter as main window.
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

        # --- Message text. Colours are in the QSS (`QTextBrowser#MarkdownText`) ---
        message_text = MarkdownTextBrowser()
        message_text.setObjectName("MarkdownText")
        message_text.setOpenExternalLinks(True)
        message_text.setFrameShape(QFrame.NoFrame)
        message_text.set_markdown(message.text)
        content_layout.addWidget(message_text)

        # --- Buttons ---
        button_box = QDialogButtonBox(QDialogButtonBox.Close)

        button_box.rejected.connect(self.reject)
        font_updated = QFont(self.font)
        font_updated.setPointSize(12)
        _min_size_w: int = 64

        for button in button_box.buttons():
            button.setFont(self.font)
            button.setMinimumSize(QSize(_min_size_w, int(_min_size_w * 0.3)))
        content_layout.addWidget(button_box)

    def done(self, result: int):
        # Every way of closing ends up here. Message always marked as seen.
        save_message_as_seen(self.message)
        super().done(result)

    def showEvent(self, event):
        super().showEvent(event)
        adapt_to_parent_size(self, self.parent, self.SIZE_PCT, self.MIN_SIZE_PCT)
