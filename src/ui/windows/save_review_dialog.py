import logging
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from patchers.saves import SaveAnalysis, SaveFinding, SaveFix
from ui.utils import EventFilterMoveResize, adapt_to_parent_size, centre_on_parent

log = logging.getLogger("Save Review Dialog")


class FixSaveReviewDialog(QDialog):
    """
    Shows what was found in a save and lets the user pick the fixes to apply.

    `ask()` returns the picked fixes, or None on Cancel. A ticked fix always writes its value.
    """

    # (width, height) as percentages of the parent window
    SIZE_PCT = (60, 70)
    MIN_SIZE_PCT = (50, 50)

    def __init__(self, analysis: SaveAnalysis, font: QFont, window_icon: QIcon, parent=None):
        super().__init__(parent)

        self.analysis = analysis
        self.game = analysis.game
        self.section_header_font_size: int = 18
        self.fix_checkboxes: dict[str, QCheckBox] = {}

        self.setObjectName("SaveReviewDialog")
        self.setWindowTitle("Fix Save")
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

        title_label = QLabel(f"Fix {self.game.name} Save")
        title_label.setObjectName("SectionTitle")
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(title_label)

        file_label = QLabel(analysis.save.path.name)
        file_label.setObjectName("HintLabel")
        file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(file_label)

        # --- Scrollable findings and fixes ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_area.setWidget(scroll_widget)
        content_layout.addWidget(scroll_area, 1)

        # --- Save contents ---
        scroll_layout.addWidget(self._section_label("Save contents", font))

        findings_layout = QGridLayout()
        findings_layout.setColumnStretch(1, 1)
        for row, finding in enumerate(analysis.parsed.findings):
            self._add_finding_row(findings_layout, row, finding)
        scroll_layout.addLayout(findings_layout)

        # --- Fixes ---
        scroll_layout.addWidget(self._section_label("Fixes", font))

        fixes_layout = QGridLayout()
        fixes_layout.setColumnStretch(1, 1)
        for row, fix in enumerate(self.game.fixes):
            self._add_fix_row(fixes_layout, row, fix)
        scroll_layout.addLayout(fixes_layout)

        # --- Buttons ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText("Apply Fixes")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        for button in self.button_box.buttons():
            button.setFont(font)
        content_layout.addWidget(self.button_box)

        self._update_apply_button()

    @classmethod
    def ask(cls, analysis: SaveAnalysis, font: QFont, window_icon: QIcon, parent=None) -> Optional[list[SaveFix]]:
        """Show the dialog. The ticked fixes, in the game's order, or None if the user cancels."""
        dialog = cls(analysis, font, window_icon, parent=parent)
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        picked_fixes = dialog.selected_fixes()

        # Parented to the main window, so it would otherwise stay alive until the app closes, holding the whole save
        # (tens of MB). Every Fix Save run would add another one.
        dialog.deleteLater()

        if not accepted:
            log.info("Fix Save cancelled.", silent=True)
            return None

        return picked_fixes

    def selected_fixes(self) -> list[SaveFix]:
        picked = []
        for fix in self.game.fixes:
            if self.fix_checkboxes[fix.id].isChecked():
                picked.append(fix)
        return picked

    def _section_label(self, text: str, font: QFont) -> QLabel:
        section_font = QFont(font)
        section_font.setPointSize(self.section_header_font_size)

        label = QLabel(text)
        label.setObjectName("FieldNameLabel")
        label.setFont(section_font)
        return label

    def _add_finding_row(self, layout: QGridLayout, row: int, finding: SaveFinding):
        """Label and value, with the explanation under the value when there is one."""
        name_label = QLabel(finding.label)
        name_label.setObjectName("FieldNameLabel")
        layout.addWidget(name_label, row * 2, 0, Qt.AlignmentFlag.AlignTop)

        # Coloured by status in the stylesheet: QLabel#FindingValue[status="..."]
        value_label = QLabel(finding.value)
        value_label.setObjectName("FindingValue")
        value_label.setProperty("status", finding.status.value)
        value_label.setToolTip(finding.detail)
        layout.addWidget(value_label, row * 2, 1)

        if finding.detail:
            detail_label = QLabel(finding.detail)
            detail_label.setObjectName("HintLabel")
            detail_label.setWordWrap(True)
            layout.addWidget(detail_label, row * 2 + 1, 1)

    def _add_fix_row(self, layout: QGridLayout, row: int, fix: SaveFix):
        """Checkbox, and whether the fix would change the save."""
        is_needed = fix.is_needed(self.analysis.parsed)

        checkbox = QCheckBox(fix.label)
        checkbox.setObjectName("StyledCheckbox1")
        checkbox.setToolTip(fix.description)
        checkbox.setChecked(is_needed and fix.pre_tick_when_needed)
        checkbox.toggled.connect(lambda checked, fix_id=fix.id: self._on_fix_toggled(fix_id, checked))
        layout.addWidget(checkbox, row, 0)
        self.fix_checkboxes[fix.id] = checkbox

        if is_needed:
            hint_text = "Would change the save"
        else:
            hint_text = "Done"

        hint_label = QLabel(hint_text)
        hint_label.setObjectName("HintLabel")
        layout.addWidget(hint_label, row, 1)

    def _on_fix_toggled(self, fix_id: str, checked: bool):
        # Ticking a fix unticks the others in its group (Convert to Ironman / Convert to Regular Save)
        if checked:
            fix = self.game.fix(fix_id)
            if fix.exlcusive_group:
                for other_fix in self.game.fixes:
                    if other_fix.id == fix.id:
                        continue
                    if other_fix.exlcusive_group == fix.exlcusive_group:
                        self.fix_checkboxes[other_fix.id].setChecked(False)

        self._update_apply_button()

    def _update_apply_button(self):
        """Apply Fixes only works with at least one fix ticked."""
        apply_button = self.button_box.button(QDialogButtonBox.Ok)
        apply_button.setEnabled(bool(self.selected_fixes()))

    def showEvent(self, event):
        super().showEvent(event)
        adapt_to_parent_size(self, self.parentWidget(), self.SIZE_PCT, self.MIN_SIZE_PCT)

        self.setMinimumSize(self.minimumSize().expandedTo(self.minimumSizeHint()))
        centre_on_parent(self, self.parentWidget())
