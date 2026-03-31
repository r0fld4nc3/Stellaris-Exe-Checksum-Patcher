import logging

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

log = logging.getLogger("Welcome Dialog")


class DisclaimerFixCheatedSave(QDialog):
    COLOUR_HEADER_H2 = "#179361"
    COLOUR_HEADER_H3 = "#EBBC3D"
    COLOUR_TEXT = "#FFFFFF"
    COLOUR_TEXT_MUTED = "#E0E0E0"

    FONT_SIZE_H2 = "28px"
    FONT_SIZE_H3 = "24px"
    FONT_SIZE_H4 = "22px"
    FONT_SIZE_TEXT = "18px"

    def __init__(self, font: QFont, window_icon: QIcon, parent=None):
        super().__init__(parent)

        self.font = font

        # --- Style & Appearance
        self.setWindowFlags(
            Qt.Dialog | Qt.WindowStaysOnTopHint | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint
        )

        self.setWindowTitle("Cheated Save Disclaimer")
        self.setWindowIcon(window_icon)

        # --- Set welcome dialog responsive to screen size
        self.adapt_to_screen_size(parent, 30, 50)

        # --- Dialog layout with frame ---
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

        # --- Title ---
        title_label = QLabel("<h1>You Must Agree To These Conditions</h1>")
        title_label.setFont(self.font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(title_label)

        # --- Scroll Area for Content ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        # --- Scrollable Content Widget ---
        content_widget = QWidget()
        content_widget_layout = QVBoxLayout(content_widget)
        content_widget_layout.setContentsMargins(10, 10, 10, 10)
        content_widget_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- How to Use Section ---
        liability_disclaimer_header = QLabel(
            self._style_html("<h2>Personal Liability Disclaimer</h2>"), alignment=Qt.AlignmentFlag.AlignCenter
        )
        liability_disclaimer_header.setWordWrap(True)

        disclaimer_text_desc = QLabel(
            self._style_html(
                """
                <h2>This action will remove the cheated flag from your save file, re-enabling achievement eligibility.</h2>

                <h3>Important Considerations</h3>

                <p>You are taking responsibility for clearing this flag yourself. By proceeding, you acknowledge that:</p>

                <ul>
                    <li><b>Legitimate use</b>: This feature is provided to recover save files from broken game states, stuck events, or unintended consequences — not to obscure intentional use of console commands for illegitimate advantages.</li>

                    <li><b>Your choice, your consequence</b>: Paradox Interactive and this tool's author cannot verify how you used console commands or mods. Clearing this flag is entirely your decision and responsibility.</li>
                </ul>

                <p>By declining this agreement, the the save repair process will continue without this option enabled.</p>
            """
            )
        )
        disclaimer_text_desc.setWordWrap(True)
        content_widget_layout.addWidget(liability_disclaimer_header)
        content_widget_layout.addWidget(disclaimer_text_desc)

        # --- Spacer ---
        content_widget_layout.addStretch()

        # Set scrollable widget
        scroll_area.setWidget(content_widget)
        content_layout.addWidget(scroll_area)

        # --- Buttons ---
        button_layout = QVBoxLayout()

        btn_confirm = QPushButton("I Agree")
        # Override button font
        button_font = QFont(self.font)
        button_font.setPointSize(self.font.pointSize() + 6)
        # Set button font override
        btn_confirm.setFont(button_font)

        btn_confirm.clicked.connect(self._on_confirm)
        button_layout.addWidget(btn_confirm)

        # Close Button
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        for button in button_box.buttons():
            button.setFont(self.font)
        button_layout.addWidget(button_box)

        content_layout.addLayout(button_layout)

    def _on_confirm(self):
        self.accept()

    def adapt_to_screen_size(self, parent=None, width_pct: int = 50, height_pct: int = 80):
        if parent:
            screen = parent.screen()
        else:
            screen = QApplication.primaryScreen()

        screen_geometry = screen.availableGeometry()

        width = int(screen_geometry.width() * (width_pct * 0.01))
        height = int(screen_geometry.height() * (height_pct * 0.01))

        # Set minimum size
        self.setMinimumSize(700, 500)

        # Set initial size
        self.resize(width, height)

        # Center the window on the screen
        self.move(screen_geometry.center().x() - self.width() // 2, screen_geometry.center().y() - self.height() // 2)

    @staticmethod
    def _style_html(content: str) -> str:
        """Apply a consistent styling to  HTML content"""
        style = f"""
        <style>
            h2 {{
                color: {DisclaimerFixCheatedSave.COLOUR_HEADER_H2};
                font-size: {DisclaimerFixCheatedSave.FONT_SIZE_H2};
                font-weight: bold;
                margin-top: 10px;
            }}
            h3 {{
                color: {DisclaimerFixCheatedSave.COLOUR_HEADER_H3};
                font-size: {DisclaimerFixCheatedSave.FONT_SIZE_H3};
                font-weight: bold;
                margin-top: 8px;
            }}
            h4 {{
                font-size: {DisclaimerFixCheatedSave.FONT_SIZE_H4};
                font-weight: bold;
                margin-top: 20px;
            }}
            p {{ 
                color: {DisclaimerFixCheatedSave.COLOUR_TEXT};
                font-size: {DisclaimerFixCheatedSave.FONT_SIZE_TEXT};
            }}
            li {{
                color: {DisclaimerFixCheatedSave.COLOUR_TEXT_MUTED};
                font-size: {DisclaimerFixCheatedSave.FONT_SIZE_TEXT};
                margin: 5px 0;
            }}
            ul {{
                color: {DisclaimerFixCheatedSave.COLOUR_TEXT_MUTED};
                margin-left: 20px;
                margin-top: 5px;
                margin-bottom: 10px;
            }}
        </style>
        """

        return style + content
