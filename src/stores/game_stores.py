"""
Which store a game uses, and that store's helper.

`definitions.py` holds the stores, the default store and each game's store ID.
"""

import logging
from typing import Optional

from core import services

from .base import StoreHelperBase
from .definitions import DEFAULT_GAME_STORE, GameStore
from .generic import GenericHelper
from .gog import GogHelper
from .steam import SteamHelper

log = logging.getLogger("Game Stores")

# One helper per store.
# Generic finds nothing itself (the user picks the executable) and launches with the Generic runner.
_STORE_HELPERS: dict[GameStore, StoreHelperBase] = {
    GameStore.STEAM: SteamHelper(),
    GameStore.GOG: GogHelper(),
    GameStore.GENERIC: GenericHelper(),
}


def game_store(game_name: str) -> GameStore:
    """
    Store to locate, launch and validate `game_name` with: the one picked for it in Game Utilities.

    `DEFAULT_GAME_STORE` when none was picked yet, or the saved value is unknown.
    Only reads settings: never creates an entry for `game_name`.
    """
    settings = services().settings
    if not settings.has_game(game_name):
        return DEFAULT_GAME_STORE

    saved_store = settings.game(game_name).store
    if not saved_store:
        return DEFAULT_GAME_STORE

    store = GameStore.parse(saved_store)
    if not store:
        log.warning(f"Invalid saved store '{saved_store}' for {game_name}. Using {DEFAULT_GAME_STORE.display_name}.")
        return DEFAULT_GAME_STORE

    if not store.is_supported:
        log.warning(
            f"{store.display_name} is not supported on this system. Using {GameStore.GENERIC.display_name} for {game_name}."
        )
        return GameStore.GENERIC

    return store


def has_picked_store(game_name: str) -> bool:
    """True if a store was picked for `game_name` (first-time store picker or Game Utilities). Only reads settings."""
    settings = services().settings
    if not settings.has_game(game_name):
        return False

    return bool(settings.game(game_name).store)


def set_game_store(game_name: str, store: GameStore) -> None:
    """Save `store` as the store `game_name` is from."""
    log.info(f"{game_name} store set to: {store.display_name}")
    services().settings.game(game_name).store = store


def get_store_helper(game_name: str) -> Optional[StoreHelperBase]:
    """Helper for the store `game_name` is installed from. None if that store has no helper."""
    store = game_store(game_name)
    helper = _STORE_HELPERS.get(store)
    if not helper:
        log.warning(f"No store helper for {store.display_name}.")
    return helper
