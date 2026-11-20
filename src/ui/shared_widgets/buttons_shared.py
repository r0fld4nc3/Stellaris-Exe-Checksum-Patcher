import logging

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QPushButton, QSizePolicy, QWidget

log = logging.getLogger("Buttons Shared")


class QSquarePushButton(QPushButton):
    """QPushButton as wide as it is tall. Height from the font and style."""

    def __init__(self, text: str = "", parent: QWidget = None):
        super().__init__(text, parent)
        # The layout uses sizeHint() as is, never stretches it
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def sizeHint(self) -> QSize:
        side = super().sizeHint().height()
        return QSize(side, side)

    def minimumSizeHint(self) -> QSize:
        # A  layout never shrinks a button below this, so it stays square in a narrow window too
        return self.sizeHint()
