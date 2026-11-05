"""
Defintions for `GameStore`. The stores, the default store, and every supported game's name and ID in each store.

Edit this file to:
- Add a game store. One entry in `GAME_STORE_INFOS`.

- Add a game store. A `GameStore` member, its `STORE_DISPLAY_NAMES` entry and a line in `GAME_STORE_INFOS` for each game it sells. Then its helper in `game_stores.py`.

- Change the default store.
"""

import logging
from enum import Enum
from typing import Optional

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

# Every supported game (lowercased), and its name and ID in each store it is available in
GAME_STORE_INFOS: dict[str, dict[GameStore, StoreGameInfo]] = {
    "stellaris": {
        GameStore.STEAM: StoreGameInfo(name="stellaris", id=281990),
        GameStore.GOG: StoreGameInfo(name="stellaris", id=1508702879),
    },
}
