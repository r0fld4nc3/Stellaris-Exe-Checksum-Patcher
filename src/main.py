import logging
from pathlib import Path

from app_services import AppServices, init_services
from cli import parse_args
from config import runtime
from config.definitions import (
    APP_NAME,
    APP_REVISION,
    APP_VERSION,
    HOST,
    REPO_BRANCH,
    REPO_NAME,
    REPO_OWNER,
    TRACKING_BRANCH,
)
from config.path_helpers import get_os_env_config_folder, system
from config.runtime import AppConfig
from logger import configure_logging, reset_log_file
from settings import settings

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
    log_file = get_os_env_config_folder() / HOST / APP_NAME / f"{APP_NAME}.log"
    print(log_file)

    args = parse_args()
    working_dir: Path = Path(__file__).parent
    config: AppConfig = runtime.init(runtime.build(APP_NAME, HOST, working_dir=working_dir))

    if args.debug:
        config.debug = True
        config.log_level = logging.DEBUG

    if args.no_conn:
        from utils import network_blocker

        network_blocker.enable_network_blocking()

        config.prevent_conn = True
        log.info("Network blocking is ENABLED (--no-conn flag)")

    if args.prevent_save_write:
        config.prevent_settings_save = True
        log.info("Prevent settings write is ENABLED (--prevent-settings-write)")

    # Importing here so the no-conn monkey patch works
    from updater import updater

    configure_logging(log_file, level=config.log_level)
    reset_log_file(log_file)

    log.info("Application Entry Point")

    stgs = settings.init()
    upd = updater.init(REPO_OWNER, REPO_NAME)

    # Bootstrap services
    init_services(AppServices(config=config, settings=stgs, updater=upd))

    log.info(f"[INIT] Running Application.")

    log.info(f"Debug:                  {config.debug}")
    log.info(f"App Version:            {APP_VERSION}")
    log.info(f"App Revision:           {APP_REVISION}")
    log.info(f"Repo Branch:            {REPO_BRANCH}")
    log.info(f"Tracking Branch:        {TRACKING_BRANCH}")
    log.info(f"Target System:          {system()}")
    log.info(f"AppConfig:              {config}")
    log.info(f"AppSettings:            {stgs.settings}")

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
