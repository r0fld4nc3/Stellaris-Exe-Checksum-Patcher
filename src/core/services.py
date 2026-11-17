"""
The one way to reach the app's services once they are started.

`app.bootstrap.start()` creates them and calls `init_services()` once. Everything else calls `services()`.

Call `services()` when the value is needed (inside functions and `__init__`), not at import time or
in class bodies, so importing a module never depends on the app having started.

Only holds what lives in `core`, so every layer of the app may call `services()`.
Objects from higher layers (ex.: the `Updater`) are owned by the code that uses them.
"""

from dataclasses import dataclass
from typing import Optional

from .runtime import AppConfig
from .settings import SettingsManager


@dataclass(slots=True)
class AppServices:
    config: AppConfig  # This run: how it was started and what it learned, lost on quit
    settings: SettingsManager  # What the user chose, saved to disk


_current: Optional[AppServices] = None


def init_services(app_services: AppServices) -> None:
    global _current
    if _current is not None:
        raise RuntimeError("Services already initialised")
    _current = app_services


def services() -> AppServices:
    if _current is None:
        raise RuntimeError("Services not initialised")
    return _current
