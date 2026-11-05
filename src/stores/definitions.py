"""
Defintions for `GameStore`. The stores, the default store, and every supported game's name and ID in each store.

Edit this file to:
- Add a game. Its entry in `GAME_STORE_INFOS`.

- Add a game store. A `GameStore` member, its `STORE_DISPLAY_NAMES` entry and a line in `GAME_STORE_INFOS` for each game it sells. Then its helper in `game_stores.py`.

- Limit a store to some systems. Its entry in `STORE_SUPPORTED_SYSTEMS`.
- Change the default store.
"""

import logging
from enum import Enum
from typing import Optional

from config.path_helpers import OS_TYPE, system

from .base import StoreGameInfo

log = logging.getLogger("Game Stores")


class GameStore(str, Enum):
    """
    Values are the settings keys, written as literals.
    Not to be confused with `patchers.models.Platform`, which is the OS a binary is built for.
    """

    STEAM = "steam"
    GOG = "gog"
    # No store: the user picks the executable themselves
    GENERIC = "generic"

    @property
    def display_name(self) -> str:
        return STORE_DISPLAY_NAMES[self]

    @property
    def is_supported(self) -> bool:
        """
        True if store works on OS.
        Stores without `STORE_SUPPORTED_SYSTEMS` work everywhere.
        """
        supported_systems = STORE_SUPPORTED_SYSTEMS.get(self)
        if supported_systems is None:
            return True

        return system() in supported_systems

    @classmethod
    def parse(cls, value: Optional[str]) -> Optional["GameStore"]:
        """Store for a saved settings value. None if empty or unknown."""
        try:
            return cls(value)
        except ValueError:
            return None

    def game_info(self, game_name: str) -> Optional[StoreGameInfo]:
        """`game_name`'s name and ID in this store (any case). None if this store doesn't have it."""
        store_infos = GAME_STORE_INFOS.get(game_name.lower())
        if not store_infos:
            log.warning(f"No store IDs for game: {game_name}")
            return None

        return store_infos.get(self)


# Store for games without one picked yet.
DEFAULT_GAME_STORE = GameStore.STEAM

# Store names shown in the app
STORE_DISPLAY_NAMES: dict[GameStore, str] = {
    GameStore.STEAM: "Steam",
    GameStore.GOG: "GOG",
    GameStore.GENERIC: "Generic",
}

STORE_SUPPORTED_SYSTEMS: dict[GameStore, list[str]] = {
    GameStore.GOG: [OS_TYPE.WINDOWS, OS_TYPE.DARWIN],  # No GoG on Linux
    # GameStore.STEAM and GameStore.GENERIC are supported everywhere, so no need to filter.
}

# Every supported game (lowercased), and its name and ID in each store it is available in
GAME_STORE_INFOS: dict[str, dict[GameStore, StoreGameInfo]] = {
    "stellaris": {
        GameStore.STEAM: StoreGameInfo(name="stellaris", id=281990),
        GameStore.GOG: StoreGameInfo(name="stellaris", id=1508702879),
    },
}
