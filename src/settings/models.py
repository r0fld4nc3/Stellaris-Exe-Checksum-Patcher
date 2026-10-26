"""
Settings data, as plain dataclasses.

Every public field is one setting. How it is stored depends on how it is declared:

    accepted_welcome_dialog: bool = False      # plain field -> written to disk immediately
    window_width: int = memory(800)            # memory()    -> kept in memory, written on close
    app_version: str = memory("v3", locked=True)  # locked   -> always the default, write-only

Memory settings are also written whenever an immediate setting is saved, and when the options dialog closes.

Locked settings always hold their default value(s). The value in the file is ignored when loading,
and assigning one raises an error. They are still written on every save (ex.: which app version wrote the file).

Good rule of thumb: change a list by assigning a new one:
    `game.patches = applied`

Not in place:
    `game.patches.append(x)`

Only assignments are noticed and saved.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from config.definitions import APP_VERSION_STR

if TYPE_CHECKING:
    from .settings import SettingsManager

_MEMORY = "MEMORY"
_LOCKED = "LOCKED"


def memory(default, locked: bool = False):
    """
    Setting that is kept in memory and only written to disk later.

    locked=True: the value can never change. It is always `default`, never loaded from the file.
    """
    return field(default=default, metadata={_MEMORY: True, _LOCKED: locked})


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

        if self._is_locked_field(name):
            raise AttributeError(f"Setting '{name}' is locked and can't be changed.")

        with manager.lock:
            object.__setattr__(self, name, value)
            manager._on_change(save_now=not self._is_memory_field(name))

    @classmethod
    def _is_memory_field(cls, name: str) -> bool:
        return cls._field_flag(name, _MEMORY)

    @classmethod
    def _is_locked_field(cls, name: str) -> bool:
        return cls._field_flag(name, _LOCKED)

    @classmethod
    def _field_flag(cls, name: str, flag: str) -> bool:
        """True if field `name` was declared with `flag` set in its metadata (see memory())."""
        f = cls.__dataclass_fields__.get(name)
        return f is not None and f.metadata.get(flag, False)


@dataclass
class GameSettings(AutoSaveHookedSettingsClass):
    """Representation of settings for a game."""

    install_path: str = ""
    proton_install_path: str = ""
    save_games_folder: str = ""
    patches: list[str] = field(default_factory=list)
    patched_version: str = ""
    patched_platform: str = ""


@dataclass
class AppSettings(AutoSaveHookedSettingsClass):
    """Main application settings."""

    # --- Locked ---
    # Want it to show first on the list of settings.
    # Records which app version last wrote the file. Never read back.
    app_version: str = memory(APP_VERSION_STR, locked=True)

    # --- Saved immediately ---
    accepted_welcome_dialog: bool = False
    force_local_patterns: bool = False
    selected_game: str = ""
    steam_install_path: str = ""
    games: dict[str, GameSettings] = field(default_factory=dict)

    # --- Kept in memory ---
    window_width: int = memory(800)
    window_height: int = memory(600)
    update_last_checked: int = memory(0)
    update_available: bool = memory(False)
    patch_patterns_update_last_checked: int = memory(0)
    max_allowed_binary_backups: int = memory(1)
