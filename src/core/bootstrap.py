"""
Starts the app's core services, in order, and makes them reachable through `services()`.

Order matters:
1. Config: folders and command line flags. Everything else reads it.
2. Network blocking (--no-conn): before anything imports `requests`.
3. Logging: as early as possible, once the log file location is known.
4. Settings and updater, then `init_services()`.
5. Load the settings file: it reads its folder from `services().config`.
"""

import argparse
import logging
from pathlib import Path

# Imported first: swaps in the app's Logger class before any module creates its logger
from logger import configure_logging, reset_log_file

from . import runtime
from .definitions import APP_NAME, HOST, REPO_NAME, REPO_OWNER
from .runtime import AppConfig
from .services import AppServices, init_services
from .settings import SettingsManager

log = logging.getLogger("Bootstrap")


def start(args: argparse.Namespace, working_dir: Path) -> AppServices:
    """Build every service from the command line `args` and register them. Call once, at startup."""
    config = runtime.build(APP_NAME, HOST, working_dir=working_dir)
    _apply_args(config, args)

    if config.prevent_conn:
        from utils import network_blocker

        network_blocker.enable_network_blocking()

    configure_logging(config.log_file, level=config.log_level)
    reset_log_file(config.log_file)

    # Logged after logging is configured, so they reach the log file
    if config.prevent_conn:
        log.info("Network blocking is ENABLED (--no-conn flag)")
    if config.prevent_settings_save:
        log.info("Prevent settings write is ENABLED (--prevent-settings-write)")

    # Imported here so the --no-conn network block is in place before `requests` loads
    from updater.updater import Updater

    app_services = AppServices(
        config=config,
        settings=SettingsManager(),
        updater=Updater(REPO_OWNER, REPO_NAME),
    )
    init_services(app_services)

    # After init_services(), have settings load() its required parameters.
    app_services.settings.load()

    return app_services


def _apply_args(config: AppConfig, args: argparse.Namespace):
    """Command line flags that change the config."""
    if args.debug:
        config.debug = True
        config.log_level = logging.DEBUG

    if args.no_conn:
        config.prevent_conn = True

    if args.prevent_save_write:
        config.prevent_settings_save = True
