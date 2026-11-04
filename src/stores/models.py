"""
Store data with no store logic: the stores themselves and the IDs each game has in them.

Kept apart from the store helpers so any of them can import it without a circular import.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

log = logging.getLogger("Game Stores")


class GameStore(str, Enum):
    """
    Where a game was installed from. Decides how it's located, launched and validated.

    Values are the settings keys, written as literals.
    Not to be confused with `patchers.models.Platform`, which is the OS a binary is built for.
    """

    STEAM = "steam"
    GOG = "gog"
    # No store: the user picks the executable themselves
    GENERIC = "generic"

    @property
    def display_name(self) -> str:
        display_names = {GameStore.STEAM: "Steam", GameStore.GOG: "GOG", GameStore.GENERIC: "Generic"}
        return display_names[self]

    @classmethod
    def parse(cls, value: Optional[str]) -> Optional["GameStore"]:
        """Store for a saved settings value. None if empty or unknown."""
        try:
            return cls(value)
        except ValueError:
            return None

    def game_info(self, game_name: str) -> Optional["StoreGameInfo"]:
        """`game_name`'s name and ID in this store (any case). None if this store doesn't have it."""
        store_infos = GAME_STORE_INFOS.get(game_name.lower())
        if not store_infos:
            log.warning(f"No store IDs for game: {game_name}")
            return None

        return store_infos.get(self)


@dataclass(frozen=True)
class StoreGameInfo:
    """A game's name and ID in one store."""

    name: str
    id: int


# Every supported game (lowercased name), and its name and ID in each store that sells it.
# Add a game: one entry here. Add a store: a GameStore member, then a line in each game it sells.
GAME_STORE_INFOS: dict[str, dict[GameStore, StoreGameInfo]] = {
    "stellaris": {
        GameStore.STEAM: StoreGameInfo(name="stellaris", id=281990),
        GameStore.GOG: StoreGameInfo(name="stellaris", id=1508702879),
    },
}
