import logging
from typing import Iterable, Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app_services import services
from patchers import MultiGamePatcher, PatchConfiguration

from .options_tabs import GameUtilitiesTab, UtilitiesTab
from .options_tabs.base import OptionsContext, OptionsTab

log = logging.getLogger("Patch Config")

# Tabs shown in the Configure Application Options dialog, in display order.
APP_OPTIONS_TABS = [
    UtilitiesTab,
    GameUtilitiesTab,
]


class CurrentTabSizedTabWidget(QTabWidget):
    """
    QTabWidget whose height fits the current tab instead of the tallest tab.

    Width stays stable when switching.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.currentChanged.connect(self.updateGeometry)

    def sizeHint(self) -> QSize:
        return self._fit_current_height(super().sizeHint(), QWidget.sizeHint)

    def minimumSizeHint(self) -> QSize:
        return self._fit_current_height(super().minimumSizeHint(), QWidget.minimumSizeHint)

    def hasHeightForWidth(self) -> bool:
        # Word-wrapped labels make layouts ask heightForWidth().
        # QTabWidget returns the tallest tab. Opt out so the current-tab size hint above is used.
        return False

    def _fit_current_height(self, size: QSize, page_hint) -> QSize:
        """Swap the tallest tab's height in `size` for the current tab's height."""
        current = self.currentWidget()
        pages = [self.widget(i) for i in range(self.count()) if self.isTabVisible(i)]
        if current is None or not pages:
            return size

        tallest = max(page_hint(page).height() for page in pages)
        size.setHeight(size.height() - tallest + page_hint(current).height())
        return size


class TabOptionsDialog(QDialog):
    """
    Generic options dialog: a frame, a tab widget and OK/Cancel.

    Knows nothing about what the tabs contain.
    Pass tab classes in `tabs` (order is the display order) or call `add_tab()`.
    The dialog's height follows the current tab, so short tabs don't leave empty space.
    """

    # Largest share of the screen the dialog grows to when fitting a tab
    MAX_SCREEN_FRACTION = 0.9

    def __init__(
        self,
        patcher: MultiGamePatcher,
        configuration: PatchConfiguration,
        font: QFont,
        window_icon: QIcon,
        tabs: Iterable[type[OptionsTab]] = (),
        parent=None,
    ):
        super().__init__(parent)

        self.setModal(True)

        self._font = font
        self.context = OptionsContext(patcher, configuration, font, parent=self)
        self.context.reload_requested.connect(self.refresh)

        # --- Style and Appearance ---
        # Qt.Window treats this is a top-level window while being able to receive a parent
        # Fixes odd behaviour where a frameless window with a parent would appear off
        # centre and clipped by the main window.
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint | Qt.Window
        )

        self.setWindowTitle("Configure Patches")
        self.setWindowIcon(window_icon)
        self.setMinimumSize(600, 400)

        # Dialog Layout that contains the frame
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

        # --- Tab Widget ---
        self.tab_widget = CurrentTabSizedTabWidget()
        self.tab_widget.setFont(self._font)
        self.tab_widget.currentChanged.connect(self._fit_to_current_tab)
        content_layout.addWidget(self.tab_widget)

        # --- OK/Cancel Layout ---
        ok_cancel_layout = QHBoxLayout()
        content_layout.addLayout(ok_cancel_layout)

        # --- Ok / Cancel Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Write memory() changed settings when the dialog closes, regardless of how it closes (OK, Cancel or X)
        self.finished.connect(lambda _result: services().settings.save_if_dirty())

        for button in button_box.buttons():
            button.setFont(self._font)
        ok_cancel_layout.addWidget(button_box)

        # --- Tabs ---
        log.info(tabs)
        if not tabs:
            log.info(f"Passed tab list is empty: {tabs}. Using defaults {APP_OPTIONS_TABS}")
            # Can be empty, defined a default to fallback to.
            tabs = APP_OPTIONS_TABS

        for tab_cls in tabs:
            self.add_tab(tab_cls)

    # --- Tab management ---

    def add_tab(self, tab_cls: type[OptionsTab], index: Optional[int] = None) -> OptionsTab:
        """Create a tab, add it (at `index`, or at the end) and load it."""
        tab = tab_cls(self.context)
        if index is None:
            self.tab_widget.addTab(tab, tab.title)
        else:
            self.tab_widget.insertTab(index, tab, tab.title)
        tab.load()
        return tab

    def tabs(self) -> list[OptionsTab]:
        """Tabs in display order."""
        return [self.tab_widget.widget(i) for i in range(self.tab_widget.count())]

    # --- Configuration ---

    @property
    def configuration(self) -> PatchConfiguration:
        return self.context.configuration

    def set_configuration(self, configuration: PatchConfiguration):
        """Swap in a new configuration and reload every tab."""
        self.context.configuration = configuration
        self.refresh()

    def refresh(self):
        for tab in self.tabs():
            tab.load()
        self._fit_to_current_tab()

    def get_configuration(self) -> PatchConfiguration:
        """The configuration as edited in the dialog. Tabs write their changes into it as they happen."""
        config = self.context.configuration

        log.info(
            f"Returning configuration: Game={config.game}, "
            f"Version={config.version}, "
            f"Platform={config.platform} (Proton={config.is_proton}), "
            f"Patches({len(config.selected_patches)})={config.selected_patches}"
        )

        return config

    # --- Sizing ---

    def showEvent(self, event):
        super().showEvent(event)
        self._fit_to_current_tab()

    def _fit_to_current_tab(self, *_):
        """Resize the dialog's height to the current tab, between the minimum size and a share of the screen."""
        # Layouts cache size hints: refresh each one from the tab widget up to the dialog
        widget = self.tab_widget
        while widget is not None and widget is not self:
            widget.updateGeometry()
            widget = widget.parentWidget()
        self.layout().activate()

        hint = self.sizeHint()
        max_size = self.screen().availableGeometry().size() * self.MAX_SCREEN_FRACTION

        width = min(max(self.width(), hint.width(), self.minimumWidth()), max_size.width())
        height = min(max(hint.height(), self.minimumHeight()), max_size.height())
        self.resize(width, height)

    def closeEvent(self, event):
        """Let every tab release its resources when the dialog closes."""
        for tab in self.tabs():
            tab.cleanup()
        super().closeEvent(event)
