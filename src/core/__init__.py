"""
    definitions.py  What never changes: app name, version, repository.
    paths.py        OS detection and OS folders.
    runtime.py      AppConfig: this run. How it was started (CLI flags, folders). Lost on quit.
    settings/       User settings and choices. Saved to disk.
    services.py     How to reach all of it: `services()`.
    bootstrap.py    How it's put together at startup: `start()`.

Everywhere else, reach the running services through `services()`:

    from core import services

    services().settings.game("Stellaris").install_path
"""

from .services import AppServices, services

__all__ = ["AppServices", "services"]
