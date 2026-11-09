"""
The one way to reach the app's services once they are started.

`bootstrap.start()` creates them and calls `init_services()` once. Everything else calls `services()`.

Call `services()` when the value is needed (inside functions and `__init__`), not at import time or
in class bodies, so importing a module never depends on the app having started.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

# TYPE_CHECKING used to restore IntelliSense auto-completion
if TYPE_CHECKING:
    from updater.updater import Updater

    from .runtime import AppConfig
    from .settings import SettingsManager


@dataclass(slots=True)
class AppServices:
    config: "AppConfig"  # This run: how it was started and what it learned, lost on quit
    settings: "SettingsManager"  # What the user chose, saved to disk
    updater: "Updater"


_current: Optional[AppServices] = None


def init_services(app_services: AppServices) -> None:
    global _current
    if _current is not None:
        raise RuntimeError("Services already initialised")
    _current = app_services


def services_initialised() -> bool:
    """True once `bootstrap.start()` has run. For code that can also run before, like logging."""
    return _current is not None


def services() -> AppServices:
    if _current is None:
        raise RuntimeError("Services not initialised")
    return _current
