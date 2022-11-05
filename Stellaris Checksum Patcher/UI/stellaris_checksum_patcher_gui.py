import sys
from UI.StellarisChecksumPatcherUI import Ui_MainWindow
from PySide6.QtWidgets import QApplication, QMainWindow

class StellarisChecksumPatcherGUI(Ui_MainWindow):
    def __init__(self) -> None:
        super(StellarisChecksumPatcherGUI, self).__init__()
        
        self.app = QApplication(sys.argv)
        
        self.MainWindow = QMainWindow()
        Ui_MainWindow.setupUi(self, self.MainWindow)
        
        # self.app.aboutToQuit.connect(self.exit_application_handler)
        
    def show(self):
        self.MainWindow.show()
        sys.exit(self.app.exec_())