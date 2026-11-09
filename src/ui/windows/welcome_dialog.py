import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core import services
from ui.utils import EventFilterMoveResize, adapt_to_parent_size

log = logging.getLogger("Welcome Dialog")


class WelcomeDialog(QDialog):
    SIZE_PCT = (80, 90)
    MIN_SIZE_PCT = (50, 50)

    COLOUR_HEADER_1 = "#179361"
    COLOUR_SUBHEADER_1 = "#EBBC3D"
    COLOUR_TEXT = "#FFFFFF"
    COLOUR_TEXT_MUTED = "#E0E0E0"

    FONT_SIZE_HEADER_1 = "28px"
    FONT_SIZE_SUBHEADER_1 = "24px"
    FONT_SIZE_TEXT = "18px"

    def __init__(self, font: QFont, window_icon: QIcon, parent=None):
        super().__init__(parent)

        self.settings = services().settings

        self.font = font

        # --- Style & Appearance
        self.setWindowFlags(
            Qt.Dialog | Qt.WindowStaysOnTopHint | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint
        )

        self.setWindowTitle("Welcome and Overview")
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
        title_label = QLabel("<h1>Welcome to Checksum Patcher!</h1>")
        title_label.setObjectName("WelcomeDialogTitleLabel")
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

        # --- Welcome Statement ---
        welcome_text = QLabel(
            self._style_html("""
            <p class="header">Introduction</p>
            <p>This quick guide aims to help you get started with the basic main features and functionalities.</p>
            """),
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        welcome_text.setWordWrap(True)

        foreword_text = QLabel(self._style_html("""
                <p>Before that, I would like to thank you for choosing to use this project. It is something I invest quite a bit of time in and I consider it one of my <i>babies</i>. Thank you for supporting and contributing with issues and suggestions, I am always eager to hear what can be improved and to fix what may be broken so that we all share in this <i>bounty</i>.</p>
            """))
        foreword_text.setWordWrap(True)

        content_widget_layout.addWidget(welcome_text)
        content_widget_layout.addWidget(QLabel())  # Spacer
        content_widget_layout.addWidget(foreword_text)

        # --- How to Use Section ---
        how_to_use_header = QLabel(
            self._style_html("<p class='header'>Basic Overview</p>"), alignment=Qt.AlignmentFlag.AlignCenter
        )
        how_to_use_header.setWordWrap(True)

        how_to_use_desc = QLabel(self._style_html("""
                <p>For basic usage, the Patcher provides a quick one-click solution to patch your game and start playing immediately.</p>

                <p>Let's get started.</p>

                <p class="subheader">The Information Screen</p>
                <p>An information panel displays textual feedback as the Patcher operates. While primarily visual, it provides valuable information about progress, errors and warnings. Pay attention to these messages, especially when reporting issues.</p>

                <p>While patching, a progress bar below it shows which step the Patcher is on, and whether it finished successfully.</p>

                <p class="subheader">Main Action Buttons</p>
                <p>Below the information screen are two main buttons:</p>
                <ul>
                    <li><b>Fix Save</b> opens the save configurator and picker, allowing you to modify specific save properties such as restoring achievement eligibility and enabling or converting saves to and from Ironman mode.</li>

                    <li><b>The Patch button</b>, with the achievement icon. Once the application has initialised successfully, just click this button to patch your game so achievements are earnable with mods.</li>
                </ul>

                <p>At the top right, the <b>cogwheel</b> opens the options window and the <b>?</b> button opens quick tips and answers to common problems.</p>

                <p class="subheader">Patching</p>
                <p>Patching requires the application to know where the game's executable is, and it attempts to determine this automatically once the patching process starts.</p>

                <p>This, however, <i>can</i> fail, and in such cases it should prompt you to point to the file path manually.</p>

                <p>To start the patch process, click the patch button indicated by the greyed-out image of an achievement.</p>

                <p>Patching requires some base information to identify the correct sites to patch. The patcher should now be much more robust as it automatically tries to find the sites to patch based off of checksum information and some byte regex rules.</p>

                <p>These rules are found in a patterns file that comes bundled with the application, whoever, the default behaviour is to always check online and update this local file with one from the remote repository. In case something needs to change, the patterns and regex rules can be updated without requiring an update to the Patcher application itself.</p>

                <p>Once patching is complete, the button turns into a <b>Launch</b> button, so <b>you can launch the game directly from the Patcher.</b> If every patch applied, its achievement icon also becomes coloured.</p>

                <p>Patching an already patched executable should be safe, as the Patcher should recognise it is already patched and leave it alone.</p>

                <p><b>NOTE:</b> If patching ever fails after a game update, please check GitHub for any existing discussions about the current status before opening a new issue. A fix may already be on its way, and it can take some time depending on (my) availability.</p>

                <p class="subheader">The Options Window</p>
                <p>The <b>cogwheel</b> at the top right of the main application screen opens the options window. It has two tabs: <b>General Utilities</b> and <b>Game Utilities</b>.</p>

                <p>Changes are applied as you make them. Press <b>OK</b> to keep them, or <b>Cancel</b> to undo them.</p>

                <p class="subheader">General Utilities</p>
                <p>This tab gathers tools for the Patcher itself, so you don't need to dig through folders by hand: update the patch configuration, open the Patcher's own folder, <b>Manage Save Backups</b>, and show this welcome guide again.</p>

                <p>It also has a few settings, such as including pre-releases when checking for updates.</p>
                
                <p class="subheader">Game Utilities</p>
                <p>Everything that applies to a specific game lives here, and acts on the game selected at the top of the tab.</p>

                <p>Under <b>Patch Configuration</b> you can choose which game to patch, which version of the patch configuration to use and, on Linux and macOS, whether you're patching the native game or the Windows version running through <b>Proton</b>.</p>

                <p>Below that, you can see the patches that will be applied. The defaults are all you need, so you technically don't <i>need</i> to change anything here, but I would rather give you options than restrict them.</p>

                <p>This tab also has buttons to <b>Show Game Folder</b> and <b>Show Save Games Folder</b>, to <b>Validate Integrity of Game Files</b> through your game's store, and to <b>Delete Backups</b> of the game executable made when patching.</p>

                <p>You can also choose where your game comes from: <b>Steam</b>, <b>GOG</b> or <b>Generic</b> (anywhere else, or started with another app). This doesn't change how the game is patched, only where the Patcher looks for it and how it launches and validates it.</p>

                <p class="header" align="center">General Tips</p>

                <p class="subheader">Handling Game Updates</p>
                <p>A game update replaces the game executable, so you will need to patch again afterwards. Usually that's just one click on the Patch button.</p>
                <p>If you believe you should be receiving achievements or notice that patching did not work correctly, go to the <b>Game Utilities</b> tab and click <b>Validate Integrity of Game Files</b>.</p>
                <p>On <b>Steam</b>, this starts Steam's verification, which replaces the executable with a fresh copy. On <b>GOG</b>, it opens the game in GOG Galaxy, where you click <b>Verify / Repair</b>. For <b>Generic</b> games, use your launcher's own verify or repair option. Once finished, apply the patches again, and you should be good to go.</p>

                <p class="subheader">Restoring Achievements</p>
                <p>Patching the executable does <b>not</b> necessarily make an existing save eligible to receive achievements. These are two separate systems.</p>
                <p>To restore the ability to gain achievements on an existing save game, use the <b>Fix Save</b> button next to the Patch button.</p>
                <p>This prompts you to select a save game and, similarly to patching, asks which modifications to perform on the save.</p>
                <p>If all goes well, the save will have achievements enabled again, and loading it in-game should restore the ability to receive them.</p>

                <p class="subheader">Save Backups</p>
                <p>When fixing a save, a backup is created in the application's configuration directory.</p>
                <p>It would be good practice to delete old and unused save backups from time to time. To do so, click <b>Manage Save Backups</b> in the <b>General Utilities</b> tab. It lists every backup by playthrough and lets you choose which ones to keep and which to delete.</p>

                <p class="header" align="center">Closing Remarks</p>
                <p>Well, that should cover most of it for now. I hope this was informative without being too technical or tiring to read.</p>
                <p>Once again, thank you for choosing this project and I hope it works well for you and makes you happier to play a wonderful game!</p>
                <p>For quick answers to common problems, press the <b>?</b> button at the top right of the main window.</p>
                <p>In case you are faced with any issues, don't hesitate to open an Issue on GitHub, but before you press "Create", please search for existing issues or fixes that may have already been addressed in the past!</p>
                <p></p>
                <p>Happy Achievement Hunting!</p>
                <p>- r0fld4nc3</p>
            """))
        how_to_use_desc.setWordWrap(True)
        content_widget_layout.addWidget(how_to_use_header)
        content_widget_layout.addWidget(how_to_use_desc)

        # --- Spacer ---
        content_widget_layout.addStretch()

        # Set scrollable widget
        scroll_area.setWidget(content_widget)
        content_layout.addWidget(scroll_area)

        # --- Buttons ---
        button_layout = QVBoxLayout()

        # Confirm and Don't Show Again
        # Make it dynamic! Appear only if never accepted!
        has_accepted = self.settings.app_settings.accepted_welcome_dialog
        if not has_accepted:
            btn_confirm = QPushButton("Understood! - Don't Show Again")
            # Override button font
            button_font = QFont(self.font)
            button_font.setPointSize(self.font.pointSize() + 6)
            # Set button font override
            btn_confirm.setFont(button_font)

            btn_confirm.clicked.connect(self._on_confirm)
            button_layout.addWidget(btn_confirm)

        # Close Button (without saving preference)
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        for button in button_box.buttons():
            button.setFont(self.font)
        button_layout.addWidget(button_box)

        content_layout.addLayout(button_layout)

    def _on_confirm(self):
        self.settings.app_settings.accepted_welcome_dialog = True
        self.accept()

    @staticmethod
    def _style_html(content: str) -> str:
        """Apply a consistent styling to  HTML content"""
        style = f"""
        <style>
            p {{
                color: {WelcomeDialog.COLOUR_TEXT};
                font-size: {WelcomeDialog.FONT_SIZE_TEXT};
            }}
            /* Qt ignores font-size on h2/h3, so sized headers are paragraphs with the header or subheader class */
            p.header {{
                color: {WelcomeDialog.COLOUR_HEADER_1};
                font-size: {WelcomeDialog.FONT_SIZE_HEADER_1};
                font-weight: bold;
                margin-top: 10px;
            }}
            p.subheader {{
                color: {WelcomeDialog.COLOUR_SUBHEADER_1};
                font-size: {WelcomeDialog.FONT_SIZE_SUBHEADER_1};
                font-weight: bold;
                margin-top: 8px;
            }}
            li {{
                color: {WelcomeDialog.COLOUR_TEXT_MUTED};
                font-size: {WelcomeDialog.FONT_SIZE_TEXT};
                margin: 5px 0;
            }}
            ul {{
                color: {WelcomeDialog.COLOUR_TEXT_MUTED};
                margin-left: 20px;
                margin-top: 5px;
                margin-bottom: 10px;
            }}
        </style>
        """

        return style + content

    def showEvent(self, event):
        super().showEvent(event)
        # --- Set welcome dialog responsive to screen size ---
        adapt_to_parent_size(self, self.parentWidget().parentWidget(), self.SIZE_PCT, self.MIN_SIZE_PCT)
