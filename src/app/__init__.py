"""
App layer: starts the app and holds code that combines the domain packages.

    bootstrap.py      How it all is put together at startup: `start()`.
    game_location.py  Where the game is: the saved executable, finding it through the store, the folder to show.
    report.py         Command line report of where each patch would go and signatures, without patching.

Empty on purpose. Importing `app.bootstrap` must not load the domain packages (and `requests`) before `start()` has turned on the --no-conn network block, therefore, import from the modules themselves.
"""
