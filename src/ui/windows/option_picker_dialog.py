import logging
from dataclasses import dataclass
from typing import Any, Generic, Optional, TypeVar

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.utils import EventFilterMoveResize, adapt_to_parent_size, centre_on_parent

log = logging.getLogger("Option Picker Dialog")

# Type of the value each option stands for (a Path, a store, a library...)
# Tells the editor what option_dialog_pick_from_options() returns: give (label, Path, description), get a Path back.
OptionValue = TypeVar("OptionValue")


@dataclass(frozen=True)
class PickerOption(Generic[OptionValue]):
    """One choice in the `OptionPickerDialog`: what the user sees, and what picking it returns."""

    label: str
    value: OptionValue
    # Shown on a second line under the label. Empty: label only.
    description: str = ""


class OptionPickerDialog(QDialog):
    """
    Asks the user to pick one of several found options, ex.: when more than one save games folder exists.

    Generic: give any list of `PickerOption`s and `ask()` returns the picked option's `value`, or None on Cancel.
    """

    # (width, height) as percentages of the parent window
    SIZE_PCT = (100, 100)
    MIN_SIZE_PCT = (35, 30)

    def __init__(
        self,
        title: str,
        text: str,
        options: list[PickerOption],
        font: QFont,
        window_icon: QIcon,
        preselected_index: int = 0,
        parent=None,
    ):
        super().__init__(parent)

        self.options = options

        self.setObjectName("OptionPickerDialog")
        self.setWindowTitle(title)
        self.setWindowIcon(window_icon)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setFont(font)

        # Frameless. Handle moving and resizing with same filter as main window.
        self.resize_move_filter = EventFilterMoveResize(self)
        self.installEventFilter(self.resize_move_filter)

        # --- Dialog layout with frame ---
        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)

        # --- Frame ---
        main_frame = QFrame(self)
        main_frame.setProperty("windowDragHandle", True)
        main_frame.setFrameShape(QFrame.WinPanel)
        main_frame.setFrameShadow(QFrame.Plain)
        main_frame.setLineWidth(5)
        main_frame.setMidLineWidth(0)
        main_frame.setContentsMargins(10, 10, 10, 10)
        dialog_layout.addWidget(main_frame)

        # --- Content Layout ---
        content_layout = QVBoxLayout(main_frame)
        content_layout.setContentsMargins(10, 10, 10, 10)

        # --- Title ---
        title_font = QFont(font)
        title_font.setPointSize(16)

        title_label = QLabel(title)
        title_label.setObjectName("SectionTitle")
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(title_label)

        # --- What to pick ---
        text_label = QLabel(text)
        text_label.setObjectName("OptionPickerText")
        text_label.setWordWrap(True)
        content_layout.addWidget(text_label)

        # --- Options ---
        self.options_list = QListWidget()
        self.options_list.setObjectName("OptionPickerList")
        for option in options:
            self._add_option(option)

        self.options_list.setCurrentRow(self._valid_index(preselected_index))
        # Double-clicking an option picks it immediately
        self.options_list.itemDoubleClicked.connect(self.accept)
        content_layout.addWidget(self.options_list, 1)

        # --- Buttons ---
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("Select")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        for button in button_box.buttons():
            button.setFont(font)
        content_layout.addWidget(button_box)

    @classmethod
    def ask(
        cls,
        title: str,
        text: str,
        options: list[PickerOption[OptionValue]],
        font: QFont,
        window_icon: QIcon,
        preselected_index: int = 0,
        parent=None,
    ) -> Optional[OptionValue]:
        """
        Show the picker. The picked option's `value`, or None if the user cancels.
        With no options, nothing is shown and None is returned.
        """
        if not options:
            log.warning(f"No options to pick from for: {title}")
            return None

        picker = cls(title, text, options, font, window_icon, preselected_index=preselected_index, parent=parent)
        accepted = picker.exec() == QDialog.DialogCode.Accepted
        picked_option = picker.selected_value()

        # Parented to a window, so it would otherwise stay alive until the app closes. Every ask would add another one.
        picker.deleteLater()

        if not accepted:
            log.info(f"Option picker cancelled: {title}", silent=True)
            return None

        return picked_option

    def selected_value(self) -> Optional[OptionValue]:
        """Value of the selected option. None when nothing is selected."""
        row = self.options_list.currentRow()
        if row < 0:
            return None

        return self.options[row].value

    def _add_option(self, option: PickerOption):
        """One row in the list. Label, with the description under it when there is one."""
        if option.description:
            item_text = f"{option.label}\n{option.description}"
        else:
            item_text = option.label

        item = QListWidgetItem(item_text)
        item.setToolTip(item_text)
        self.options_list.addItem(item)

    def _valid_index(self, index: int) -> int:
        """`index` when it's one of the options, otherwise the first option."""
        if 0 <= index < len(self.options):
            return index

        return 0

    def showEvent(self, event):
        super().showEvent(event)
        adapt_to_parent_size(self, self.parentWidget(), self.SIZE_PCT, self.MIN_SIZE_PCT)

        self.setMinimumSize(self.minimumSize().expandedTo(self.minimumSizeHint()))
        centre_on_parent(self, self.parentWidget())


def option_dialog_pick_from_options(
    title: str,
    text: str,
    options: list[tuple[str, OptionValue, str]],
    font: Optional[QFont] = None,
    parent: Optional[QWidget] = None,
) -> Optional[OptionValue]:
    """
    Ask the user to pick one of `options`, each a (label, value, description) tuple. Returns the picked value.

    No options: None. One option: its value, without asking.
    Several: shown in the `OptionPickerDialog`, None if cancelled. Without a running Qt application
    (command line) there's no way to ask yet, so nothing is picked.
    """

    if not options:
        return None

    if len(options) == 1:
        _label, value, _description = options[0]
        return value

    if QApplication.instance() is None:
        # TODO: Ask in the terminal once the Patcher can run from the command line
        log.warning(f"{title}: picking from the command line isn't supported yet.")
        return None

    window_icon = QIcon()
    if parent:
        window_icon = parent.windowIcon()

    if font is None:
        font = QFont()

    picker_options: list[PickerOption] = _build_picker_options(options)
    return OptionPickerDialog.ask(title, text, picker_options, font=font, window_icon=window_icon, parent=parent)


def _build_picker_options(options: list[tuple[str, Any, str]]) -> list[PickerOption]:
    picker_options: list[PickerOption] = []

    for label, value, description in options:
        picker_options.append(PickerOption(label=label, value=value, description=description))

    return picker_options
