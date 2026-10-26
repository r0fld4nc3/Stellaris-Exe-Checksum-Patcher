import logging

from PySide6.QtWidgets import QComboBox

from ..base import OptionsContext

log = logging.getLogger("GameComboBox")


class GameComboBox(QComboBox):
    """
    Dropdown of supported games, linked to the shared options configuration.

    Every instance stays in sync. Picking a game in one updates the configuration
    through the context, and all other instances.
    """

    # Width of the closed box, in characters.
    # Fixed, so long game names never widen the dialog or push neighbouring widgets out of view.
    # Popup list still shows full names.
    MIN_CONTENTS_LENGTH = 16

    def __init__(self, context: OptionsContext, parent=None):
        super().__init__(parent)
        self.ctx = context
        self.setFont(context.font)
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(self.MIN_CONTENTS_LENGTH)

        self.currentTextChanged.connect(self.ctx.select_game)
        self.ctx.game_changed.connect(self.sync)

    def populate(self):
        """Refill games list, then select the configured game."""
        log.info(f"Retrieving available games to add.", silent=True)

        self.blockSignals(True)
        self.clear()
        self.addItems(self.ctx.patcher.get_available_games())
        self.blockSignals(False)
        self.sync()

    def sync(self, *_):
        """Show the configured game. Avoud re-triggering a selection change."""
        game = self.ctx.configuration.game if self.ctx.configuration else None
        if game and game != self.currentText():
            self.blockSignals(True)
            self.setCurrentText(game)
            self.blockSignals(False)
