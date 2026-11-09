import logging
from pathlib import Path

from cli import parse_args
from core import bootstrap
from core.definitions import (
    APP_REVISION,
    APP_VERSION,
    REPO_BRANCH,
    VISUAL_BRANCH,
)
from core.paths import system

log = logging.getLogger("Entry_Point")


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

    log.info(f"Debug:                  {config.debug}")
    log.info(f"App Version:            {APP_VERSION}")
    log.info(f"App Revision:           {APP_REVISION}")
    log.info(f"Repo Branch:            {REPO_BRANCH}")
    log.info(f"Tracking Branch:        {VISUAL_BRANCH}")
    log.info(f"Target System:          {system()}")
    log.info(f"AppConfig:              {config}")
    log.info(f"AppSettings:            {app_services.settings.app_settings}")

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
