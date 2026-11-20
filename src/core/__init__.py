"""
    definitions.py  What never changes: app name, version, repository.
    paths.py        OS detection and OS folders.
    runtime.py      AppConfig: this run. How it was started (CLI flags, folders). Lost on quit.
    settings/       User settings and choices. Saved to disk.
    services.py     How to reach all of it: `services()`.

The bottom layer: imports nothing else from the app. Startup lives in `app.bootstrap`.

Everywhere else, reach the running services through `services()`:

    from core.services import services

    services().settings.game("Stellaris").install_path

Kept empty on purpose: `logger` imports `core.definitions` and `core.paths` before it swaps in its Logger class,
so importing them must not load `core.settings` (which creates a logger).
"""
