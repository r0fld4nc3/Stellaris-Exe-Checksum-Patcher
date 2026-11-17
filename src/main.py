import logging
from pathlib import Path

from app import bootstrap
from cli import parse_args

log = logging.getLogger("Entry Point")


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

    msg_box.exec()


def main():
    args = parse_args()
    app_services = bootstrap.start(args, working_dir=Path(__file__).parent)
    config = app_services.config
    log_file = config.log_file
    print(log_file)

    log.info("Application Entry Point")

    log.info("[INIT] Running Application.")

    bootstrap.dump_app_info()

    try:
        from ui import StellarisChecksumPatcherGUI

        app = StellarisChecksumPatcherGUI()
        app.show()
    except Exception as e:
        import traceback

        error_msg = f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}"
        error_msg += f"\nPlease look for or write an Issue on GitHub addressing this. You can find more information in the log file at:\n{log_file}"

        log.critical(e)
        log.error(error_msg)

        show_message_box("Initialisation Error", error_msg)

        raise


if __name__ == "__main__":
    main()
