# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'StellarisChecksumPatcherUI.ui'
##
## Created by: Qt User Interface Compiler version 6.4.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QLayout, QMainWindow, QPushButton,
    QSizePolicy, QSpacerItem, QTextBrowser, QVBoxLayout,
    QWidget)

import os

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(930, 723)
        MainWindow.setStyleSheet(u"")
        self.central_widget = QWidget(MainWindow)
        self.central_widget.setObjectName(u"central_widget")
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.central_widget.sizePolicy().hasHeightForWidth())
        self.central_widget.setSizePolicy(sizePolicy)
        self.central_widget.setStyleSheet(u"background-color: rgb(35, 55, 50);\n"
"color: rgb(35, 75, 70);")
        self.gridLayout = QGridLayout(self.central_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.main_frame = QFrame(self.central_widget)
        self.main_frame.setObjectName(u"main_frame")
        self.main_frame.setMinimumSize(QSize(650, 500))
        self.main_frame.setStyleSheet(u"color: rgb(35, 75, 70);\n"
"color: rgb(67, 144, 134);")
        self.main_frame.setFrameShape(QFrame.WinPanel)
        self.main_frame.setFrameShadow(QFrame.Plain)
        self.main_frame.setLineWidth(5)
        self.main_frame.setMidLineWidth(0)
        self.verticalLayout = QVBoxLayout(self.main_frame)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.lbl_title = QLabel(self.main_frame)
        self.lbl_title.setObjectName(u"lbl_title")
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.lbl_title.sizePolicy().hasHeightForWidth())
        self.lbl_title.setSizePolicy(sizePolicy1)
        self.lbl_title.setBaseSize(QSize(0, 0))
        font = QFont()
        font.setFamilies([u"Century Gothic"])
        font.setPointSize(26)
        font.setBold(False)
        self.lbl_title.setFont(font)
        self.lbl_title.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"background-color: rgb(35, 75, 70);\n"
"border-radius: 5px;")
        self.lbl_title.setFrameShadow(QFrame.Plain)
        self.lbl_title.setTextFormat(Qt.AutoText)
        self.lbl_title.setScaledContents(False)
        self.lbl_title.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)
        self.lbl_title.setMargin(5)
        self.lbl_title.setIndent(-1)

        self.verticalLayout.addWidget(self.lbl_title)

        self.lbl_app_version = QLabel(self.main_frame)
        self.lbl_app_version.setObjectName(u"lbl_app_version")
        sizePolicy1.setHeightForWidth(self.lbl_app_version.sizePolicy().hasHeightForWidth())
        self.lbl_app_version.setSizePolicy(sizePolicy1)
        font1 = QFont()
        font1.setFamilies([u"Orbitron"])
        font1.setPointSize(10)
        self.lbl_app_version.setFont(font1)

        self.verticalLayout.addWidget(self.lbl_app_version)

        self.verticalSpacer = QSpacerItem(20, 50, QSizePolicy.Minimum, QSizePolicy.Maximum)

        self.verticalLayout.addItem(self.verticalSpacer)

        self.terminal_display = QTextBrowser(self.main_frame)
        self.terminal_display.setObjectName(u"terminal_display")
        sizePolicy2 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.terminal_display.sizePolicy().hasHeightForWidth())
        self.terminal_display.setSizePolicy(sizePolicy2)
        font2 = QFont()
        font2.setFamilies([u"Century Gothic"])
        font2.setPointSize(10)
        font2.setBold(False)
        self.terminal_display.setFont(font2)
        self.terminal_display.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"background-color: rgba(22, 59, 56, 100);\n"
"border: 4px solid rgb(35, 75, 70);")
        self.terminal_display.setFrameShape(QFrame.Box)
        self.terminal_display.setFrameShadow(QFrame.Sunken)
        self.terminal_display.setLineWidth(2)
        self.terminal_display.setOpenExternalLinks(True)

        self.verticalLayout.addWidget(self.terminal_display)

        self.verticalSpacer_2 = QSpacerItem(20, 50, QSizePolicy.Minimum, QSizePolicy.Maximum)

        self.verticalLayout.addItem(self.verticalSpacer_2)

        self.hlayout_patch_buttons = QHBoxLayout()
        self.hlayout_patch_buttons.setObjectName(u"hlayout_patch_buttons")
        self.hlayout_patch_buttons.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.hlayout_patch_buttons.setContentsMargins(0, 0, 0, 0)
        self.btn_patch_from_dir = QPushButton(self.main_frame)
        self.btn_patch_from_dir.setObjectName(u"btn_patch_from_dir")
        sizePolicy3 = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Maximum)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.btn_patch_from_dir.sizePolicy().hasHeightForWidth())
        self.btn_patch_from_dir.setSizePolicy(sizePolicy3)
        self.btn_patch_from_dir.setMinimumSize(QSize(12, 24))
        self.btn_patch_from_dir.setMaximumSize(QSize(16777215, 75))
        self.btn_patch_from_dir.setBaseSize(QSize(12, 24))
        font3 = QFont()
        font3.setFamilies([u"Century Gothic"])
        font3.setPointSize(14)
        font3.setBold(True)
        self.btn_patch_from_dir.setFont(font3)
        self.btn_patch_from_dir.setLayoutDirection(Qt.RightToLeft)
        self.btn_patch_from_dir.setAutoFillBackground(False)
        self.btn_patch_from_dir.setStyleSheet(u"QPushButton {\n"
"color: rgb(255, 255, 255);\n"
"background-color: rgba(22, 59, 56, 100);\n"
"border: 4px solid rgb(35, 75, 70);\n"
"}\n"
"QPushButton:pressed {\n"
"background-color: rgba(30, 80, 70, 100);\n"
"border-color: rgb(67, 144, 134);\n"
"}")
        icon = QIcon()
        icon.addFile(os.path.join(os.path.dirname(__file__), u"ui_icons/patch_icon.png"), QSize(), QIcon.Normal, QIcon.Off)
        self.btn_patch_from_dir.setIcon(icon)
        self.btn_patch_from_dir.setIconSize(QSize(64, 64))

        self.hlayout_patch_buttons.addWidget(self.btn_patch_from_dir)

        self.btn_patch_from_install = QPushButton(self.main_frame)
        self.btn_patch_from_install.setObjectName(u"btn_patch_from_install")
        sizePolicy3.setHeightForWidth(self.btn_patch_from_install.sizePolicy().hasHeightForWidth())
        self.btn_patch_from_install.setSizePolicy(sizePolicy3)
        self.btn_patch_from_install.setMinimumSize(QSize(12, 24))
        self.btn_patch_from_install.setMaximumSize(QSize(16777215, 75))
        self.btn_patch_from_install.setBaseSize(QSize(12, 24))
        self.btn_patch_from_install.setFont(font3)
        self.btn_patch_from_install.setLayoutDirection(Qt.RightToLeft)
        self.btn_patch_from_install.setAutoFillBackground(False)
        self.btn_patch_from_install.setStyleSheet(u"QPushButton {\n"
"color: rgb(255, 255, 255);\n"
"background-color: rgba(22, 59, 56, 100);\n"
"border: 4px solid rgb(35, 75, 70);\n"
"}\n"
"QPushButton:pressed {\n"
"background-color: rgba(30, 80, 70, 100);\n"
"border-color: rgb(67, 144, 134);\n"
"}")
        self.btn_patch_from_install.setIcon(icon)
        self.btn_patch_from_install.setIconSize(QSize(64, 64))
        self.btn_patch_from_install.setFlat(False)

        self.hlayout_patch_buttons.addWidget(self.btn_patch_from_install)


        self.verticalLayout.addLayout(self.hlayout_patch_buttons)


        self.gridLayout.addWidget(self.main_frame, 0, 1, 1, 1)

        MainWindow.setCentralWidget(self.central_widget)

        self.retranslateUi(MainWindow)

        self.btn_patch_from_install.setDefault(False)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.lbl_title.setText(QCoreApplication.translate("MainWindow", u"Stellaris Checksum Patcher", None))
        self.lbl_app_version.setText(QCoreApplication.translate("MainWindow", u"App Version", None))
        self.terminal_display.setHtml(QCoreApplication.translate("MainWindow", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:'Century Gothic'; font-size:10pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-family:'Orbitron';\">[INFO] Loading file Hex.</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-family:'Orbitron';\">[INFO] Streaming File Hex Info...</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-family:'Orbitron';\">[INFO] Read finished.</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-"
                        "right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-family:'Orbitron';\">[INFO] Acquiring Checksum Block...</span></p></body></html>", None))
        self.btn_patch_from_dir.setText(QCoreApplication.translate("MainWindow", u"Patch From Directory", None))
        self.btn_patch_from_install.setText(QCoreApplication.translate("MainWindow", u"Patch From Installation", None))
    # retranslateUi

