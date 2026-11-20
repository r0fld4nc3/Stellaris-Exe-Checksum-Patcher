"""
Where the game is, its executable and the folder to show.

Combines packages that don't know about each other - the saved paths in settings, the install folder from the game's store, and the executable's name and .app bundle from the patcher.

Every function works on the configuration's game and binary type (native, or the Windows one through Proton).
"""

import logging
from pathlib import Path
from typing import Optional

from core.services import services
from patchers import PatchConfiguration, Patcher
from stores import get_store_helper

log = logging.getLogger("Game Location")


def saved_game_executable(configuration: PatchConfiguration) -> Optional[Path]:
    """The saved executable. None if none is saved yet. It may no longer exist."""
    saved_path_str = services().settings.game(configuration.game).binary_path(configuration.is_proton)
    if not saved_path_str:
        return None
    return Path(saved_path_str)


def save_game_executable(configuration: PatchConfiguration, executable: Path) -> None:
    """Remember `executable` for next time."""
    executable_posix = executable.resolve().as_posix()
    services().settings.game(configuration.game).set_binary_path(configuration.is_proton, executable_posix)
    log.info(f"Saved {configuration.game} executable: '{executable_posix}'", silent=True)


def find_game_executable(patcher: Patcher, configuration: PatchConfiguration) -> Optional[Path]:
    """
    The game executable to patch if a saved one still exists, otherwise found through the game's store.
    None if neither works.
    """
    saved_path = saved_game_executable(configuration)
    if saved_path:
        if saved_path.is_file():
            log.info(f"Retrieved game executable from settings: '{saved_path}'", silent=True)
            return saved_path
        log.warning("Saved game path found, but executable is invalid.")

    store_helper = get_store_helper(configuration.game)
    if not store_helper:
        log.error(f"Failed to locate {configuration.game} installation.")
        return None

    log.info("Attempting to auto-locate game installation.")
    install_folder = store_helper.get_game_install_path(configuration.game)
    executable = patcher.find_executable(configuration, install_folder)
    if not executable:
        log.error(f"Failed to locate {configuration.game} installation.")
        return None

    log.info(f"Auto-located path: {executable}")
    return executable


def find_game_folder(patcher: Patcher, configuration: PatchConfiguration) -> Optional[Path]:
    """
    The first saved executable that still exists (native first, then Proton), or its folder if only that is left.
    None if neither exists.
    """
    for path in services().settings.game(configuration.game).saved_binary_paths():
        if path.exists():
            log.info(f"Saved path: '{path}'", silent=True)
            return game_folder_for(patcher, configuration, path)

        if path.parent.exists():
            log.info(f"Derived Game Folder: {path.parent}", silent=True)
            return game_folder_for(patcher, configuration, path.parent)

    return None


def game_folder_for(patcher: Patcher, configuration: PatchConfiguration, path: Path) -> Path:
    """
    What to show for `path`.
    The bundle holding it (ex.: macOS .app), or `path` itself when it's in none.
    """
    bundle_root = patcher.find_bundle_root(configuration, path)
    if bundle_root:
        return bundle_root
    return path
