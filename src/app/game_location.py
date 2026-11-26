"""
Where the game is, its executable, the folder to show and its save games folders.

Combines packages that don't know about each other - the saved paths in settings, the install folder from the game's store, and the executable's name and .app bundle from the patcher.

Every function works on the configuration's game and binary type (native, or the Windows one through Proton).
"""

import logging
from pathlib import Path
from typing import Optional

from core.services import services
from patchers import PatchConfiguration, Patcher
from patchers.saves import get_save_games_folders
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


def find_game_executables(patcher: Patcher, configuration: PatchConfiguration) -> list[Path]:
    """
    The game executables to patch.
    The saved one if it still exists, otherwise every one found through the game's store.
    Several when the game is installed more than once (two Steam libraries), so the caller lets the user pick.
    Empty if none.
    """
    saved_path = saved_game_executable(configuration)
    if saved_path:
        if saved_path.is_file():
            log.info(f"Retrieved game executable from settings: '{saved_path}'", silent=True)
            return [saved_path]
        log.warning("Saved game path found, but executable is invalid.")

    store_helper = get_store_helper(configuration.game)
    if not store_helper:
        log.error(f"Failed to locate {configuration.game} installation.")
        return []

    log.info("Attempting to auto-locate game installation.")
    executables: list[Path] = []
    for install_folder in store_helper.get_game_install_paths(configuration.game):
        executable = patcher.find_executable(configuration, install_folder)
        if executable and executable not in executables:
            executables.append(executable)

    if not executables:
        log.error(f"Failed to locate {configuration.game} installation.")
        return []

    log.info(f"Auto-located path(s): {executables}")
    return executables


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


def find_save_games_folders(game_name: str) -> list[Path]:
    """
    Save games folders for `game_name` also looking inside the game store's Proton prefixes.
    """
    documents_folders: list[Path] = []

    store_helper = get_store_helper(game_name)
    if store_helper:
        documents_folders = store_helper.get_proton_documents_folders(game_name)

    return get_save_games_folders(game_name, documents_folders)
