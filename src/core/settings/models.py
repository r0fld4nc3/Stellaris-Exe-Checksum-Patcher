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

import json
from contextlib import AbstractContextManager
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Optional, Protocol

from ..definitions import APP_IS_PRERELEASE, APP_REVISION, APP_VERSION_STR

_MEMORY = "MEMORY"
_LOCKED = "LOCKED"
GAMES_KEY = "games"  # Name of the `AppSettings.games` field and its key in the settings file


def memory(default, locked: bool = False):
    """
    Setting that is kept in memory and only written to disk later.

    locked=True: the value can never change. It is always `default`, never loaded from the file.
    """
    return field(default=default, metadata={_MEMORY: True, _LOCKED: locked})


class SettingsOwner(Protocol):
    """
    What a settings object needs from whoever owns it. `SettingsManager` in manager.py.

    Defined here so the models don't import the manager (which imports the models).
    """

    lock: AbstractContextManager  # Held while a field changes and while saving

    def _on_change(self, save_now: bool) -> None:
        """
        A field changed.

        `save_now`: save right away. Otherwise a memory() field.
        """
        ...


@dataclass
class AutoSaveHookedSettingsClass:
    """Base class with manager."""

    _manager: Optional[SettingsOwner] = field(default=None, init=False, repr=False, compare=False)
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

    def dump(self) -> dict:
        values = {}
        for settings_field in fields(self):
            if settings_field.name.startswith("_"):
                continue

            values[settings_field.name] = getattr(self, settings_field.name)
        return values

    def dump_json(self) -> str:
        """`dump()` as indented JSON text."""
        return json.dumps(self.dump(), indent=2, default=str)


@dataclass
class GameSettings(AutoSaveHookedSettingsClass):
    """Representation of settings for a game."""

    install_path: str = ""
    proton_install_path: str = ""
    save_games_folder: str = ""
    patches: list[str] = field(default_factory=list)
    patched_version: str = ""
    patched_platform: str = ""
    store: str = ""  # GameStore value. Empty = not picked yet

    def saved_binary_paths(self) -> list[Path]:
        """The saved game executables that are set.
        Native first, then Proton. They may no longer exist."""
        binary_paths = []
        for path_str in (self.install_path, self.proton_install_path):
            if path_str:
                binary_paths.append(Path(path_str))

        return binary_paths

    def binary_path(self, is_proton: bool) -> str:
        """Saved executable for the native game, or the Windows one run through Proton. Empty if not set."""
        if is_proton:
            return self.proton_install_path
        return self.install_path

    def set_binary_path(self, is_proton: bool, path: str) -> None:
        """Save the executable for the native game, or the Windows one run through Proton."""
        if is_proton:
            self.proton_install_path = path
        else:
            self.install_path = path


@dataclass
class AppSettings(AutoSaveHookedSettingsClass):
    """Main application settings."""

    # --- Locked ---
    # Want it to show first on the list of settings.
    # Records which app version last wrote the file. Never read back.
    app_version: str = memory(APP_VERSION_STR, locked=True)
    app_revision: int = memory(APP_REVISION, locked=True)
    app_is_prerelease: bool = memory(APP_IS_PRERELEASE, locked=True)

    # --- Saved immediately ---
    accepted_welcome_dialog: bool = False
    force_local_patterns: bool = False
    include_prerelease_updates: bool = False
    selected_game: str = ""
    steam_install_path: str = ""  # Steam folder
    gog_install_path: str = ""  # GOG Folder
    generic_runner_path: str = ""  # Executable that runs when no game store set
    generic_runner_args: str = ""  # Arguments for generic runner.
    games: dict[str, GameSettings] = field(default_factory=dict)
    last_seen_message_hash: str = ""  # Fingerprint of the last remote message the user closed

    # --- Kept in memory ---
    window_width: int = memory(800)
    window_height: int = memory(600)
    update_last_checked: int = memory(0)
    update_available: bool = memory(False)
    patch_patterns_update_last_checked: int = memory(0)
    message_last_checked: int = memory(0)
    max_allowed_binary_backups: int = memory(1)

    def dump(self) -> dict:
        values = super().dump()

        games = {}
        for game, game_settings in self.games.items():
            games[game] = game_settings.dump()
        values[GAMES_KEY] = games

        return values
