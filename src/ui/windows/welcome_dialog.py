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

from conf_globals import LOG_LEVEL, SETTINGS
from logger import create_logger

log = create_logger("Welcome Dialog", LOG_LEVEL)


class WelcomeDialog(QDialog):
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

        self.setWindowTitle("Welcome and Overview")
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
        title_label = QLabel("<h1>Welcome to Checksum Patcher 2.0!</h1>")
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
            self._style_html(
                """
            <h2>Introduction</h2>
            <p>This quick guide aims to help you get started with the basic main features and functionalities.</p>
            """
            ),
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        welcome_text.setWordWrap(True)

        foreword_text = QLabel(
            self._style_html(
                """
                <p>Before that, I would like to thank you for choosing to use this project. It is something I invest quite a bit of time in and I consider it one of my <i>babies</i>. Thank you for supporting and contributing with issues and suggestions, I am always eager to hear what can be improved and to fix what may be broken so that we all share in this <i>bounty</i>.</p>
                <p>Happy Achievement Hunting!</p>
            """
            )
        )
        foreword_text.setWordWrap(True)

        content_widget_layout.addWidget(welcome_text)
        content_widget_layout.addWidget(foreword_text)

        # --- How to Use Section ---
        how_to_use_header = QLabel(self._style_html("<h2>Basic Overview</h2>"), alignment=Qt.AlignmentFlag.AlignCenter)
        how_to_use_header.setWordWrap(True)

        how_to_use_desc = QLabel(
            self._style_html(
                """
                <p>For basic usage, the Patcher provides a quick one-click solution to patch your game and start playing immediately.</p>

                <p>Let's get started.</p>

                <h3>The Information Screen</h3>
                <p>A large information panel displays textual feedback as the Patcher operates. While primarily visual, it provides valuable information about progress, errors and warnings. Pay attention to these messages, especially when reporting issues.</p>

                <h3>Main Action Buttons</h3>
                <p>Below the information screen are two main buttons:</p>
                <ul>
                    <li><b>The Left button</b> opens the save editor, allowing you to modify specific save properties such as restoring achievement eligibility and enabling or converting saves to Ironman mode.</li>

                    <li><b>The Right button</b> is the star of the show. Once the application has initialised successfully, simply click this button to patch your game and prepare it for play.</li>
                </ul>

                <h3>Patching</h3>
                <p>Patching requires the application to know where the game's executable is, and it attempts to determine this automatically once the patching process begins.</p>

                <p>This, however, <i>can</i> fail, and in such cases it should prompt you to point to the file path manually.</p>

                <p>To start the patch process, simply click the patch button indicated by the singular greyed-out image of an achievement.</p>

                <p>If you pay attention to the information screen, you'll notice that it seems to load and apply a <b>patch configuration</b>. To maximise uptime and minimise the times the application itself needs to be updated, it downloads a remote patterns file that describes exactly which patterns to patch. This allows me incredible flexibility to update the patterns quickly if they no longer work and doesn't require a new compiled binary of the application whenever this happens.</p>

                <p>A patch configuration is simply a set of different patterns that should be applied during the patching process. These can include required patterns, such as the one to remove the altered checksum test, or optional ones that remove the yellow text and warning labels in the menus.</p>

                <p>You can customise your pattern package via the <b>cogwheel</b> button located at the top right of the main application screen.</p>

                <p>Once patching is complete, the icon of the button should become coloured and <b>you can launch the game directly from the Patcher!</b></p>

                <h3>Configuring The Patch Pattern(s)</h3>
                <p>The patch configuration screen can be accessed via the aforementioned <b>cogwheel</b> at the top right of the main application screen. This will open a new window where you may access the Patch Configuration tab.</p>

                <p>Here you can choose which game to patch, what version the patterns should target and whether you're patching for a native system or "Proton", which is used to differentiate and adjust paths when a Linux environment runs a Windows game.</p>

                <p>Below is the area where individual patterns can be toggled on or off. There is a default configuration that is loaded if you've never altered the configuration. You technically don't <i>need</i> to change it, but I would rather give you options than restrict them.</p>

                <p>If you have made changes to the configuration, do not forget to press <b>OK</b> to save the changes.</p>

                <h3>General Utilities</h3>
                <p>The General Utilities tab is a place to congregate useful tools to make it easier to perform certain actions without needing to, for example, manually go to a folder and delete a file, or manually go to Steam and navigate to the game options to launch a verification of file integrity.</p>

                <p>As it stands, this section offers only a limited range of utilities, and it may be expanded in the future as we identify key functions that can be classified and added as utilities.</p>

                <h2 style="text-align: center";>General Tips</h2>

                <h3>Handling Game Updates</h3>
                <p>A game update is usually followed by a requirement to reapply the patches.</p>
                <p>If you believe you should be receiving achievements or notice that certain patches did not apply correctly, go to the <b>General Utilities Tab</b> and click the button to <b>Validate Integrity of Game Files</b>.</p>
                <p>This will start Steam's verification process. It should remove your executable file, which will be reacquired during verification. Once finished, apply the patches again, and you should be good to go.</p>

                <h3>Restoring Achievements</h3>
                <p>Patching the executable does <b>not</b> necessarily make an existing save eligible to receive achievements. These are two separate systems.</p>
                <p>To restore the ability to gain achievements on an existing save game, use the <b>Fix Save</b> button next to the Patch button.</p>
                <p>This prompts you to select a save game and, similarly to patching, asks which modifications to perform on the save.</p>
                <p>If all goes well, the save will have achievements enabled again, and loading it in-game should restore the ability to receive them.</p>

                <h3>Save Backups</h3>
                <p>When fixing a save, a backup is created in the application's configuration directory.</p>
                <p>It would be good practice to delete old and unused save backups from time to time. To do so, you can directly open the configuration folder from the <b>General Utilities Tab</b>, giving you direct access to the <b>save games</b> folder where all backups are stored.</p>

                <h2 style="text-align: center";>Closing Remarks</h2>
                <p>Well, that should cover most of it for now. I hope this was informative without being too technical or tiring to read.</p>
                <p>Once again, thank you for choosing this project and I hope it works well for you and makes you happier to play a wonderful game!</p>
                <p>In case you are faced with any issues, don't hesitate to open an Issue on GitHub, but before you press "Create", please search for existing issues or fixes that may have already been addressed in the past!</p>
                <p></p>
                <p>Happy Hunting!</p>
                <p>- r0fld4nc3</p>
            """
            )
        )
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
        has_accepted = SETTINGS.settings.accepted_welcome_dialog
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
        with SETTINGS.batch_update():
            SETTINGS.settings.accepted_welcome_dialog = True
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
                color: {WelcomeDialog.COLOUR_HEADER_H2};
                font-size: {WelcomeDialog.FONT_SIZE_H2};
                font-weight: bold;
                margin-top: 10px;
            }}
            h3 {{
                color: {WelcomeDialog.COLOUR_HEADER_H3};
                font-size: {WelcomeDialog.FONT_SIZE_H3};
                font-weight: bold;
                margin-top: 8px;
            }}
            h4 {{
                font-size: {WelcomeDialog.FONT_SIZE_H4};
                font-weight: bold;
                margin-top: 20px;
            }}
            p {{ 
                color: {WelcomeDialog.COLOUR_TEXT};
                font-size: {WelcomeDialog.FONT_SIZE_TEXT};
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
