import logging

from PySide6.QtCore import Property, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QTextBlock,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
)
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QTextBrowser,
    QVBoxLayout,
)

from remote_messages import Message, save_message_as_seen
from ui.utils import EventFilterMoveResize, adapt_to_parent_size

log = logging.getLogger("Message Dialog")


class MarkdownTextBrowser(QTextBrowser):
    """
    Shows Markdown. Heading and link colours come from the stylesheet.
    `qproperty-headerColor` and `qproperty-linkColor`, next to `color` for the text.

    QSS can't reach parts of the text, so Qt calls the setters when it applies the stylesheet and again whenever the stylesheet changes.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._markdown = ""
        self._header_colour = QColor()  # Invalid until the stylesheet sets it
        self._link_colour = QColor()

    def set_markdown(self, text: str):
        self._markdown = text
        self._render()

    def _render(self):
        """Load the Markdown again, then colour headings and links."""
        markdown = QTextDocument.MarkdownFeature
        self.document().setMarkdown(self._markdown, markdown.MarkdownDialectGitHub | markdown.MarkdownNoHTML)

        block = self.document().begin()
        while block.isValid():
            if block.blockFormat().headingLevel() > 0:
                self._colour_heading(block)
            self._colour_links(block)
            block = block.next()

    def _colour_heading(self, block: QTextBlock):
        if not self._header_colour.isValid():
            return

        header_format = QTextCharFormat()
        header_format.setForeground(self._header_colour)

        cursor = QTextCursor(block)
        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        cursor.mergeCharFormat(header_format)

    def _colour_links(self, block: QTextBlock):
        """
        Markdown import makes links pure blue, which can be hard to read on certain backgrounds.
        Using stylesheet's link colour, or the text colour underlined if it has none.
        """
        # A block is split into fragments of text with the same format, so a link is one fragment
        fragments = block.begin()
        while not fragments.atEnd():
            fragment = fragments.fragment()
            link_format = fragment.charFormat()

            if link_format.isAnchor():
                if self._link_colour.isValid():
                    link_format.setForeground(self._link_colour)
                else:
                    # Same colour as the text, so underline it to still look like a link
                    link_format.clearForeground()
                    link_format.setFontUnderline(True)

                cursor = QTextCursor(self.document())
                cursor.setPosition(fragment.position())
                cursor.setPosition(fragment.position() + fragment.length(), QTextCursor.MoveMode.KeepAnchor)
                cursor.setCharFormat(link_format)

            fragments += 1

    def get_header_colour(self) -> QColor:
        return self._header_colour

    def set_header_colour(self, colour: QColor):
        self._header_colour = QColor(colour)
        self._render()

    headerColor = Property(QColor, get_header_colour, set_header_colour)

    def get_link_colour(self) -> QColor:
        return self._link_colour

    def set_link_colour(self, colour: QColor):
        self._link_colour = QColor(colour)
        self._render()

    linkColor = Property(QColor, get_link_colour, set_link_colour)


class MessageDialog(QDialog):
    SIZE_PCT = (70, 80)
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

        # --- Message text. Colours are in the QSS (`QTextBrowser#MessageText`) ---
        message_text = MarkdownTextBrowser()
        message_text.setObjectName("MessageText")
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
