"""
Starts the app's core services, in order, and makes them reachable through `services()`.

Important ordering:
1. Config: folders and command line flags. Everything else reads it.
2. Network blocking (--no-conn): before anything imports `requests`.
3. Logging: as early as possible, once the log file location is known.
4. Settings, then `init_services()`.
5. Load the settings file.

The updater isn't and doesn't need to be a service. Modules create and own it.
"""

# Swap the app's Logger class asap before everything else imports their loggers.
from logger import configure_logging, reset_log_file  # isort: skip

import argparse
import logging
from pathlib import Path

from core import runtime
from core.definitions import (
    APP_NAME,
    APP_REVISION,
    APP_VERSION,
    HOST,
    REPO_BRANCH,
    VISUAL_BRANCH,
)
from core.paths import system
from core.runtime import AppConfig
from core.services import AppServices, init_services, services
from core.settings import SettingsManager
from utils import network_blocker

log = logging.getLogger("Bootstrap")


def start(args: argparse.Namespace, working_dir: Path) -> AppServices:
    """Build every service from the command line `args` and register them. Call once, at startup."""
    config = runtime.build(APP_NAME, HOST, working_dir=working_dir)
    _apply_args(config, args)

    if config.prevent_conn:
        network_blocker.enable_network_blocking()

    configure_logging(config)
    reset_log_file(config.log_file)

    # Logged after logging is configured
    if config.prevent_conn:
        log.info("Network blocking is ENABLED (--no-conn flag)")
    if config.prevent_settings_save:
        log.info("Prevent settings write is ENABLED (--prevent-settings-write)")

    app_services = AppServices(
        config=config,
        settings=SettingsManager(config),
    )
    init_services(app_services)

    app_services.settings.load()

    return app_services


def dump_app_info():
    """Log what the app started with: version, system, config and settings. Call after `start()`."""
    log.info(f"Debug:                  {services().config.debug}")
    log.info(f"App Version:            {APP_VERSION}")
    log.info(f"App Revision:           {APP_REVISION}")
    log.info(f"Repo Branch:            {REPO_BRANCH}")
    log.info(f"Tracking Branch:        {VISUAL_BRANCH}")
    log.info(f"Target System:          {system()}")
    log.info(f"AppConfig:              {services().config.dump_json()}")
    log.info(f"AppSettings:            {services().settings.app_settings.dump_json()}")


def _apply_args(config: AppConfig, args: argparse.Namespace):
    """Command line flags that change the config."""
    if args.debug:
        config.debug = True
        config.log_level = logging.DEBUG

    if args.no_conn:
        config.prevent_conn = True

    if args.prevent_save_write:
        config.prevent_settings_save = True
