from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget

from core import services
from patchers import MultiGamePatcher, PatchConfiguration
from patchers.models import KEY_VERSION_LATEST
from utils.threads import Threader


class OptionsContext(QObject):
    """
    State shared by every tab in the options dialog.

    Tabs never talk to each other directly.
    They read/write the shared configuration here and use signals to react to each other.
    """

    # User picked a different game (from any tab). Carries the game name object.
    game_changed = Signal(str)
    # Ask dialog to reload every tab
    reload_requested = Signal()

    def __init__(self, patcher: MultiGamePatcher, configuration: PatchConfiguration, font: QFont, parent=None):
        super().__init__(parent)
        self.patcher = patcher
        self.configuration = configuration
        self.font = font

    def select_game(self, game: str):
        """
        Propagate `game` as the selected game for every tab.

        Version and patch selections belong to the previous game, so they are reset.
        Tabs that depend on them (Patch Configuration, etc.) rebuild them on `game_changed`.
        """
        if not game or not self.configuration or game == self.configuration.game:
            return

        self.configuration.game = game
        self.configuration.version = KEY_VERSION_LATEST
        self.configuration.selected_patches = []
        self.game_changed.emit(game)


class OptionsTab(QWidget):
    """
    Base class for a tab in OptionsTab.

    Subclasses set `title`, build their widgets in __init__ and override hooks they need.
    Dialog calls the hooks.
    Tabs don't need to know about the dialog or about other tabs.
    """

    title: str = "Untitled Tab"

    def __init__(self, context: OptionsContext, parent=None):
        super().__init__(parent)
        self.ctx = context
        self.svc = services()
        self.active_threads: list[Threader] = []

    @property
    def config(self) -> PatchConfiguration:
        return self.ctx.configuration

    @config.setter
    def config(self, value: PatchConfiguration):
        self.ctx.configuration = value

    @property
    def selected_game(self) -> Optional[str]:
        """Game picked in any GameComboBox. Game-specific actions act on this."""
        return self.config.game if self.config else None

    def load(self):
        """Fill the UI from the configuration/settings. Called when added and every time the dialog is refreshed."""

    def cleanup(self):
        """Release resources (threads, etc.) when the dialog closes."""
        for thread in self.active_threads:
            if thread.isRunning():
                thread.quit()
                thread.wait()
            thread.deleteLater()
        self.active_threads.clear()

    def start_thread(self, thread: Threader):
        """
        Start `thread` and keep a reference to it until it has ended.
        Qt aborts if a running thread is garbage collected, so tabs start threads through here.
        """
        # QThread's own `finished` fires once run() has returned, unlike `thread.signals.finished`
        thread.finished.connect(self.prune_finished)
        self.active_threads.append(thread)
        thread.start()

    @Slot()
    def prune_finished(self):
        """Drop and delete threads that have ended. Running threads stay referenced."""
        for thread in reversed(self.active_threads):
            if thread.isFinished():
                thread.deleteLater()
                self.active_threads.remove(thread)
