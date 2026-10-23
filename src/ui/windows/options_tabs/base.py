from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget

from app_services import services
from patchers import MultiGamePatcher, PatchConfiguration


class OptionsContext(QObject):
    """
    State shared by every tab in the options dialog.

    Tabs never talk to each other directly.
    They read/write the shared configuration here and use signals to react to each other.
    """

    # The selected game/version/platform changed
    configuration_changed = Signal()
    # Ask dialog to reload every tab
    reload_requested = Signal()

    def __init__(self, patcher: MultiGamePatcher, configuration: PatchConfiguration, font: QFont, parent=None):
        super().__init__(parent)
        self.patcher = patcher
        self.configuration = configuration
        self.font = font


class OptionsTab(QWidget):
    """
    Base class for a tab in OptionsTab.

    Subclasses set `title`, build their widgets in __init__ and override hooks they need.
    Dialog calls the hooks.
    Tabs don't need to know about the dialog or about other tabs.
    """

    title: str = "Untitled Tab"
    svc = services()

    def __init__(self, context: OptionsContext, parent=None):
        super().__init__(parent)
        self.ctx = context

    @property
    def config(self) -> PatchConfiguration:
        return self.ctx.configuration

    @config.setter
    def config(self, value: PatchConfiguration):
        self.ctx.configuration = value

    def load(self):
        """Fill the UI from the configuration/settings. Called when added and every time the dialog is refreshed."""

    def apply(self, configuration: PatchConfiguration):
        """Write UI selections into the configuration. Called when the dialog result is collected."""

    def cleanup(self):
        """Release resources (threads, etc.) when the dialog closes."""
