"""
Analysing a save and fixing it, for any game.

A game is described by `SaveGame`:
- `parse` reads a save into the game's own dataclass (a `ParsedSave`), which lists what it found as `SaveFinding`s.
- `fixes` are the `SaveFix`es the user can pick. A ticked fix always writes its value, even if the save already has it.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from .save_file import SaveFile, SaveFileError, backup_save, open_save, write_save

log = logging.getLogger("Save Patcher")


class FindingStatus(str, Enum):
    OK = "ok"  # As it should be
    ATTENTION = "attention"  # A fix can change this
    INFO = "info"  # For context only


@dataclass
class SaveFinding:
    id: str  # "ironman", "cheated", "achievements"
    label: str  # "Ironman"
    value: str  # "On", "Off", "Missing", "211 of 211"
    status: FindingStatus
    detail: str = ""  # Longer explanation, shown as a tooltip


class ParsedSave:
    """
    A game's save, read into a dataclass: the values the findings and fixes need.
    Each game subclasses it (Stellaris: `StellarisSave`) and lists what it found in `findings`.
    """

    @property
    def findings(self) -> list[SaveFinding]:
        """What was found, one row each, built from the values read."""
        raise NotImplementedError


class SaveFixError(Exception):
    """A fix can't be applied to this save. The message says why, for the user."""


@dataclass
class SaveFix:
    id: str
    label: str
    description: str

    # Whether the parsed save would change. Pre-ticks the fix when `pre_tick_when_needed`, otherwise only shown.
    is_needed: Callable[[ParsedSave], bool]

    # Edit the save's lines in place. Returns True if anything changed.
    # Fixes search the current lines, because an earlier fix may have added or removed some.
    apply: Callable[[SaveFile, ParsedSave], bool]

    conflicts_with: str = ""  # Id of a fix that can't be picked together with this one
    pre_tick_when_needed: bool = False
    needs_disclaimer: bool = False  # Ask the user to accept the cheated save disclaimer first


@dataclass
class SaveGame:
    """What the save tools need to know about one game. Listed in `SAVE_GAMES` (`__init__.py`)."""

    name: str  # As in the game settings. Ex.: "Stellaris"
    save_extension: str  # Ex.: ".sav"
    required_files: list[str]  # Text files that must be inside the save archive
    parse: Callable[[SaveFile], ParsedSave]
    fixes: list[SaveFix]  # Shown and applied in this order

    def fix(self, fix_id: str) -> Optional[SaveFix]:
        for fix in self.fixes:
            if fix.id == fix_id:
                return fix
        return None


@dataclass
class SaveAnalysis:
    game: SaveGame
    save: SaveFile  # The save in memory. Fixes change it, `write_save()` writes it
    parsed: ParsedSave  # The values read when it was analysed. What it found: `parsed.findings`


def analyse_save(path: Path | str, game: SaveGame) -> SaveAnalysis:
    """Open the save at `path` and read it. Raises SaveFileError if it can't be read."""
    save = open_save(path)

    for file_name in game.required_files:
        if save.entry(file_name) is None:
            raise SaveFileError(f"'{save.path.name}' has no '{file_name}', it doesn't look like a {game.name} save")

    parsed = game.parse(save)

    for finding in parsed.findings:
        log.info(f"{finding.label}: {finding.value} ({finding.status.value})", silent=True)

    return SaveAnalysis(game=game, save=save, parsed=parsed)


@dataclass
class SaveFixReport:
    """What fixing a save did."""

    changed_fixes: list[SaveFix] = field(default_factory=list)  # Fixes that changed the save
    unchanged_fixes: list[SaveFix] = field(default_factory=list)  # Fixes the save already had
    backup_file: Optional[Path] = None  # None when nothing changed


def apply_fixes(analysis: SaveAnalysis, fixes: list[SaveFix]) -> SaveFixReport:
    """
    Apply `fixes` to the save in memory, in the order given. Nothing is written to disk.
    To actually apply the changes, call `write_save()` afterwards.
    Raises ValueError if two of `fixes` conflict.
    """
    picked_ids = {fix.id for fix in fixes}
    for fix in fixes:
        if fix.conflicts_with in picked_ids:
            raise ValueError(f"Fixes '{fix.id}' and '{fix.conflicts_with}' can't be picked together")

    report = SaveFixReport()
    for fix in fixes:
        if fix.apply(analysis.save, analysis.parsed):
            log.info(f"{fix.label}: changed", silent=True)
            report.changed_fixes.append(fix)
        else:
            log.info(f"{fix.label}: already as wanted", silent=True)
            report.unchanged_fixes.append(fix)

    return report


def fix_save(analysis: SaveAnalysis, fixes: list[SaveFix]) -> SaveFixReport:
    """
    Apply `fixes`, then back up the save file and write the fixed save over it.
    When no fix changes anything, the file is left alone.

    Raises SaveFileError if the save changed on disk since it was read or can't be backed up or written,
    SaveFixError if a fix can't be applied, and ValueError if two fixes conflict.
    """
    if analysis.save.changed_on_disk():
        raise SaveFileError(f"'{analysis.save.path.name}' changed since it was read. Pick it again to fix it.")

    report = apply_fixes(analysis, fixes)

    if not report.changed_fixes:
        log.info("The save already had everything the picked fixes write. Nothing to save.")
        return report

    report.backup_file = backup_save(analysis.save.path)
    write_save(analysis.save)
    log.info("Finished fixing save.")

    return report
