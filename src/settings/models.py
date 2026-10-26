from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AutoSaveHookedSettingsClass:
    """Base class that saves the settings whenever a public field is assigned."""

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
            manager._mark_dirty()


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

    app_version: str = ""
    accepted_welcome_dialog: bool = False
    update_last_checked: int = 0
    max_allowed_binary_backups: int = 1
    patch_patterns_update_last_checked: int = 0
    force_local_patterns: bool = False
    update_available: bool = False
    window_width: int = 800
    window_height: int = 600
    last_selected_game: str = ""
    steam_install_path: str = ""
    games: dict[str, GameSettings] = field(default_factory=dict)
