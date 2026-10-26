"""
Settings data, as plain dataclasses.

Every public field is one setting. How it is stored depends on how it is declared:

    accepted_welcome_dialog: bool = False      # plain field -> written to disk immediately
    window_width: int = memory(800)            # memory()    -> kept in memory, written on close

Memory settings are also written whenever an immediate setting is saved, and when the options dialog closes.

Good rule of thumb: change a list by assigning a new one:
    `game.patches = applied`

Not in place:
    `game.patches.append(x)`

Only assignments are noticed and saved.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .settings import SettingsManager

_MEMORY = "MEMORY"


def memory(default):
    """Setting that is kept in memory and only written to disk later."""
    return field(default=default, metadata={_MEMORY: True})


@dataclass
class AutoSaveHookedSettingsClass:
    """Base class with manager."""

    _manager: Optional["SettingsManager"] = field(default=None, init=False, repr=False, compare=False)
    # Keys found in the file that this version doesn't know about. Written back unchanged
    # Running an older/newer version of the app doesn't throw them away.
    _unknown: dict = field(default_factory=dict, init=False, repr=False, compare=False)

    def __setattr__(self, name: str, value):
        manager = getattr(self, "_manager", None)

        # Internal fields, or not attached to a manager yet (ex.: during __init__): just set it.
        if name.startswith("_") or manager is None:
            object.__setattr__(self, name, value)
            return

        with manager.lock:
            object.__setattr__(self, name, value)
            manager._on_change(save_now=not self._is_memory_field(name))

    @classmethod
    def _is_memory_field(cls, name: str) -> bool:
        f = cls.__dataclass_fields__.get(name)
        return f is not None and f.metadata.get(_MEMORY, False)


@dataclass
class GameSettings(AutoSaveHookedSettingsClass):
    """Representation of settings for a game."""

    install_path: str = ""
    proton_install_path: str = ""
    save_games_folder: str = ""
    patches: list[str] = field(default_factory=list)
    last_patched_version: str = ""
    last_patched_platform: str = ""


@dataclass
class AppSettings(AutoSaveHookedSettingsClass):
    """Main application settings."""

    # --- Saved immediately ---
    accepted_welcome_dialog: bool = False
    force_local_patterns: bool = False
    last_selected_game: str = ""
    steam_install_path: str = ""
    games: dict[str, GameSettings] = field(default_factory=dict)

    # --- Kept in memory ---
    app_version: str = memory("")
    window_width: int = memory(800)
    window_height: int = memory(600)
    update_last_checked: int = memory(0)
    update_available: bool = memory(False)
    patch_patterns_update_last_checked: int = memory(0)
    max_allowed_binary_backups: int = memory(1)
