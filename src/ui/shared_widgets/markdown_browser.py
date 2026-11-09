from PySide6.QtCore import Property
from PySide6.QtGui import (
    QColor,
    QTextBlock,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
)
from PySide6.QtWidgets import QTextBrowser


class MarkdownTextBrowser(QTextBrowser):
    """
    Shows Markdown. Heading and link colours come from the stylesheet.
    `qproperty-headerColor`, `qproperty-subheaderColor` and `qproperty-linkColor`, next to `color` for the text.
    `# Headers` use the header colour, `## Subheaders` and smaller use the subheader colour (or the header colour if unset).

    QSS can't reach parts of the text, so Qt calls the setters when it applies the stylesheet and again whenever the stylesheet changes.
    """

    # Markdown import leaves no space between paragraphs, so it's added after each block
    PARAGRAPH_SPACING = 4
    HEADING_SPACING = 12

    def __init__(self, parent=None):
        super().__init__(parent)
        self._markdown = ""
        self._header_colour = QColor()
        self._subheader_colour = QColor()
        self._link_colour = QColor()

    def set_markdown(self, text: str):
        self._markdown = text
        self._render()

    def _render(self):
        """Load the Markdown again, then space blocks and colour headings and links."""
        markdown = QTextDocument.MarkdownFeature
        self.document().setMarkdown(self._markdown, markdown.MarkdownDialectGitHub | markdown.MarkdownNoHTML)

        block = self.document().begin()
        while block.isValid():
            self._space_block(block)
            if block.blockFormat().headingLevel() > 0:
                self._colour_heading(block)
            self._colour_links(block)
            block = block.next()

    def _space_block(self, block: QTextBlock):
        """Space after paragraphs, headings and whole lists. List items stay together."""
        block_format = block.blockFormat()

        is_first_block = block == self.document().begin()
        if block_format.headingLevel() > 0 and not is_first_block:
            block_format.setTopMargin(self.HEADING_SPACING)

        text_list = block.textList()
        if text_list is not None:
            is_last_item = block.next().textList() != text_list
            if not is_last_item:
                return

        block_format.setBottomMargin(self.PARAGRAPH_SPACING)
        QTextCursor(block).setBlockFormat(block_format)

    def _colour_heading(self, block: QTextBlock):
        heading_colour = self._header_colour
        if block.blockFormat().headingLevel() > 1 and self._subheader_colour.isValid():
            heading_colour = self._subheader_colour

        if not heading_colour.isValid():
            return

        header_format = QTextCharFormat()
        header_format.setForeground(heading_colour)

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

    def get_subheader_colour(self) -> QColor:
        return self._subheader_colour

    def set_subheader_colour(self, colour: QColor):
        self._subheader_colour = QColor(colour)
        self._render()

    subheaderColor = Property(QColor, get_subheader_colour, set_subheader_colour)

    def get_link_colour(self) -> QColor:
        return self._link_colour

    def set_link_colour(self, colour: QColor):
        self._link_colour = QColor(colour)
        self._render()

    linkColor = Property(QColor, get_link_colour, set_link_colour)
