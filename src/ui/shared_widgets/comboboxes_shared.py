import logging
from typing import Optional

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QComboBox

from utils.helpers import block_signals

from ..windows.options_tabs.base import OptionsContext

log = logging.getLogger("GameComboBox")


class AutoWidthComboBox(QComboBox):
    """
    ComboBox whose dropdown items should never get cut off.

    The closed box is at least as wide as its longest item up to a maximum, and the popup list is always wide enough for every item.

    Subclasses can fix the closed box's width (see GameComboBox) and still get a full-width popup.
    """

    # Width of the closed box, in characters.
    # Fixed, so long game names never widen the dialog or push neighbouring widgets out of view.
    # Popup list still shows full names.
    # MIN_CONTENTS_LENGTH: int = 8
    POPUP_WIDTH_PADDING: int = 16

    def __init__(self, font: Optional[QFont] = None, parent=None):
        super().__init__(parent)

        if font:
            self.setFont(font)

        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        # self.setMinimumContentsLength(self.MIN_CONTENTS_LENGTH)

    def showPopup(self):
        # Items can change at any time. Measure before showing.
        view = self.view()
        widest_item = view.sizeHintForColumn(0)
        scrollbar_width = view.verticalScrollBar().sizeHint().width()

        # Fix for OS's that measure items in system font rather than passed font
        popup_width = (
            max(widest_item + scrollbar_width, self.width(), self.sizeHint().width()) + self.POPUP_WIDTH_PADDING
        )

        view.setMinimumWidth(popup_width)
        super().showPopup()


class GameComboBox(AutoWidthComboBox):
    """
    Dropdown of supported games, linked to the shared options configuration.

    Every instance stays in sync. Picking a game in one updates the configuration
    through the context, and all other instances.
    """

    MIN_CONTENTS_LENGTH = 16

    def __init__(self, context: OptionsContext, parent=None):
        super().__init__(font=context.font, parent=parent)
        self.ctx = context
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(self.MIN_CONTENTS_LENGTH)

        self.currentTextChanged.connect(self.ctx.select_game)
        self.ctx.game_changed.connect(self.sync)

    def populate(self):
        """Refill games list, then select the configured game."""
        log.info("Retrieving available games to add.", silent=True)

        with block_signals(self):
            self.clear()
            self.addItems(self.ctx.patcher.get_available_games())
        self.sync()

    def sync(self, *_):
        """Show the configured game. Avoud re-triggering a selection change."""
        game = self.ctx.configuration.game if self.ctx.configuration else None
        if game and game != self.currentText():
            with block_signals(self):
                self.setCurrentText(game)
