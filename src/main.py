from ui import StellarisChecksumPatcherGUI  # isort: skip

log = None


def show_message_box(title: str, msg: str):
    import sys

    from PySide6.QtWidgets import QApplication, QMessageBox

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setWindowTitle(title)
    msg_box.setText(msg)

    msg_box.exec_()


if __name__ == "__main__":
    from logger import create_logger  # isort: skip
    from logger.logs import LOG_FILE  # isort: skip

    log = create_logger("Entry_Point", 0)
    log.info("Application Entry Point")

    try:
        app = StellarisChecksumPatcherGUI()
        app.show()
    except Exception as e:
        import traceback

        error_msg = f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}"
        error_msg += f"\nPlease look for or write an Issue on GitHub addressing this. You can find more information in the log file at:\n{LOG_FILE}"

        log.critical(e)
        log.error(error_msg)

        show_message_box("Initialisation Error", error_msg)

        raise
