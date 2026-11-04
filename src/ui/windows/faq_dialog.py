import logging

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ui.utils import EventFilterMoveResize, adapt_to_parent_size

from .welcome_dialog import WelcomeDialog

log = logging.getLogger("FAQ Dialog")


class FAQDialog(QDialog):
    SIZE_PCT = (80, 90)
    MIN_SIZE_PCT = (50, 50)

    FAQ_HTML = """
        <p class="header">Patching</p>

        <p class="subheader">Patching failed after a game update</p>
        <p>The Patcher finds the game's checksum checks by itself, so after most updates you only need to press <b>Patch</b> again.</p>
        <p>If it still fails, get a clean copy of the game: open the options with the <b>cogwheel</b>, go to <b>Game Utilities</b> and click <b>Validate Integrity of Game Files (Steam)</b>. Once Steam has finished, patch again.</p>
        <p>If that doesn't help, the update may have changed something the Patcher doesn't recognise yet. Check GitHub for an existing Issue, or open a new one and include the text from the information screen.</p>

        <p class="subheader">Is my game already patched?</p>
        <p>Just press <b>Patch</b>. If the game is already patched, the Patcher says so and leaves the file alone, so patching twice is safe.</p>
        <p>The patch stays in place until Steam updates or validates the game. After that, patch again.</p>

        <p class="subheader">The Patcher can't find my game</p>
        <p>If the game isn't found automatically, you'll be asked to select its executable (for example <b>stellaris.exe</b> on Windows or <b>stellaris</b> on Linux). The Patcher remembers it for next time.</p>

        <p class="subheader">"Unsupported executable format" or "No patches available"</p>
        <p>The Patcher can patch the Windows and Linux versions of the game. Make sure you selected the game's executable, not a shortcut or launcher.</p>
        <p>Patching the macOS version of the game isn't supported yet. The macOS app can still patch the Windows or Linux version.</p>

        <p class="subheader">Playing through Proton</p>
        <p>If you run the Windows version of the game on Linux or macOS, select <b>Proton</b> next to the game in <b>Game Utilities</b> before patching. Otherwise keep <b>Native</b>.</p>

        <p class="header">Achievements</p>

        <p class="subheader">Still no achievements after patching</p>
        <p>Patching the game and fixing a save are two separate steps. An existing save also has to allow achievements: use <b>Fix Save</b> next to the <b>Patch</b> button and pick your save.</p>
        <p>Remember that the game only awards achievements in Ironman games.</p>

        <p class="header">Backups</p>

        <p class="subheader">Where do backups go?</p>
        <p>Before patching, the Patcher keeps a copy of the game executable next to it, ending in <b>.orig</b>. <b>Delete Backups</b> in <b>Game Utilities</b> removes them.</p>
        <p>Saves fixed with <b>Fix Save</b> are backed up too. Clean those up with <b>Manage Save Backups</b> in <b>General Utilities</b>.</p>

        <p class="header">Still stuck?</p>
        <p>Search the Issues on GitHub first, as your problem may already be solved. If not, open a new Issue and include the text from the information screen.</p>
    """

    def __init__(self, font: QFont, window_icon: QIcon, parent=None):
        super().__init__(parent)

        self.parent = parent
        self.font = font

        self.setWindowTitle("Quick Tips & FAQs")
        self.setWindowIcon(window_icon)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)

        # Frameless. Handle moving and resizing with same filter as main window.
        self.resize_move_filter = EventFilterMoveResize(self)
        self.installEventFilter(self.resize_move_filter)

        # --- Dialog layout with frame ---
        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)

        # --- Frame ---
        main_frame = QFrame(self)
        main_frame.setProperty("windowDragHandle", True)  # Drag handle on QWidgets
        main_frame.setFrameShape(QFrame.WinPanel)
        main_frame.setFrameShadow(QFrame.Plain)
        main_frame.setLineWidth(5)
        main_frame.setMidLineWidth(0)
        main_frame.setContentsMargins(10, 10, 10, 10)
        dialog_layout.addWidget(main_frame)

        # --- Content Layout ---
        content_layout = QVBoxLayout(main_frame)
        content_layout.setContentsMargins(10, 10, 10, 10)

        # --- Scroll Area for Content ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        # --- Scrollable Content Widget ---
        content_widget = QWidget()
        content_widget_layout = QVBoxLayout(content_widget)
        content_widget_layout.setContentsMargins(10, 10, 10, 10)
        content_widget_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        faq_text = QLabel(WelcomeDialog._style_html(self.FAQ_HTML))
        faq_text.setWordWrap(True)
        # Handle rich text link clicks. No link passes through and allows the window to be dragged.
        faq_text.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        content_widget_layout.addWidget(faq_text)

        scroll_area.setWidget(content_widget)
        content_layout.addWidget(scroll_area)

        # --- Buttons ---
        button_box = QDialogButtonBox(QDialogButtonBox.Close)

        button_box.rejected.connect(self.reject)
        font_updated = QFont(self.font)
        font_updated.setPointSize(12)
        _min_size_w: int = 64

        for button in button_box.buttons():
            button.setFont(self.font)
            button.setMinimumSize(QSize(_min_size_w, int(_min_size_w * 0.3)))
        content_layout.addWidget(button_box)

    def showEvent(self, event):
        super().showEvent(event)
        # --- Set welcome dialog responsive to screen size ---
        adapt_to_parent_size(self, self.parent, self.SIZE_PCT, self.MIN_SIZE_PCT)
