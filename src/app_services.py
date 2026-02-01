# App Services serves as a global gather-all class to bootstrap and initialise all
# wanted app related services like configs, settings, etc.
# Typically holds global variables to services that need initialisation due to
# dynamic dependencies.
# This serves as a centralised location to hold and retrieve all these required
# services post initialisation.

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

# TYPE_CHECKING used to restore IntelliSense auto-completion
if TYPE_CHECKING:
    from config.definitions import AppConfig
    from settings.settings import SettingsManager
    from updater.updater import Updater
    from utils.steam_helper import SteamHelper


@dataclass(slots=True)
class AppServices:
    config: "AppConfig"
    settings: "SettingsManager"
    updater: "Updater"
    steam_helper: Optional["SteamHelper"] = None


_current: Optional[AppServices] = None


def init_services(services: AppServices) -> None:
    global _current
    if _current is not None:
        raise RuntimeError("Services already initialised")
    _current = services


def services() -> AppServices:
    if _current is None:
        raise RuntimeError("Services not initialised")
    return _current
