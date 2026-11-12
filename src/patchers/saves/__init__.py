"""
Save analysis and fixes: open a save, show what it contains, and change what the user picks.

    save_file.py   The save in memory (open_save(), write_save()), finding and changing values in its text,
                   save games folders and backups.
    analysis.py    Findings, fixes and games: analyse_save(), apply_fixes() and fix_save().
    stellaris.py   Stellaris: the achievements list, StellarisSave (the values read from a save) and its fixes.
    __main__.py    Dev tool: `python -m patchers.saves <save file>` prints what a save contains.

Usage:

    game = get_save_game("Stellaris")
    analysis = analyse_save(path, game)                       # Opens and reads the save
    report = fix_save(analysis, [game.fix("achievements")])   # Backs up, applies the fixes and writes the save

To support another game, describe it with a `SaveGame` in its own module (like `stellaris.py`) and add it to `SAVE_GAMES`.
"""

from typing import Optional

from .analysis import (
    FindingStatus,
    ParsedSave,
    SaveAnalysis,
    SaveFinding,
    SaveFix,
    SaveFixError,
    SaveFixReport,
    SaveGame,
    analyse_save,
    apply_fixes,
    fix_save,
)
from .save_file import (
    SaveBackup,
    SaveFile,
    SaveFileError,
    backup_save,
    find_save_backups,
    get_save_games_folders,
    open_save,
    save_backups_folder,
    write_save,
)
from .stellaris import STELLARIS

# Games whose saves can be analysed and fixed, by game name
SUPPORTED_SAVE_GAMES: dict[str, SaveGame] = {
    STELLARIS.name: STELLARIS,
}


def get_supported_save_game(game_name: str) -> Optional[SaveGame]:
    """The supported save definition for `game_name`, or None if its saves aren't supported."""
    return SUPPORTED_SAVE_GAMES.get(game_name)


__all__ = [
    "FindingStatus",
    "ParsedSave",
    "SUPPORTED_SAVE_GAMES",
    "SaveAnalysis",
    "SaveFile",
    "SaveFileError",
    "SaveFinding",
    "SaveFix",
    "SaveFixError",
    "SaveFixReport",
    "SaveBackup",
    "backup_save",
    "find_save_backups",
    "get_save_games_folders",
    "fix_save",
    "save_backups_folder",
    "SaveGame",
    "analyse_save",
    "apply_fixes",
    "get_supported_save_game",
    "open_save",
    "write_save",
]
