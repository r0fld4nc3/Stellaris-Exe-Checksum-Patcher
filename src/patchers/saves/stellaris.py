"""
Stellaris saves: the latest achievements list, reading a save into `StellarisSave`, and the fixes.

To show a new value: read it in `parse_save()` into a new `StellarisSave` field, and add a finding for it in `findings`.
To add a fix: write an `apply_*` function and a `needs_*` method, then add a `SaveFix` to `STELLARIS.fixes`.
"""

import logging
import shutil
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Optional

import certifi
import requests

from core import services
from core.definitions import REPO_BRANCH, REPO_NAME, REPO_OWNER

from .analysis import (
    FindingStatus,
    ParsedSave,
    SaveFinding,
    SaveFix,
    SaveFixError,
    SaveGame,
)
from .save_file import (
    Block,
    SaveFile,
    append_line,
    block_lines,
    find_blocks,
    find_key,
    find_root_block,
    get_value,
    insert_line_after,
    line_value,
    set_value,
)

log = logging.getLogger("Save Patcher")

GAMESTATE = "gamestate"
META = "meta"

YES = "yes"
NO = "no"


# --- Achievements list ---

ACHIEVEMENTS_FILE_NAME = "achievements.txt"
# Bundled with the app: `src/achievements/` in the source tree, `achievements/` in builds (see `builds/`).
# Copied to the config folder when there's none yet. Also read by tools that run without starting the app.
ACHIEVEMENTS_DISTRIBUTED_FILE = Path(__file__).parent.parent.parent / "achievements" / ACHIEVEMENTS_FILE_NAME
ACHIEVEMENTS_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/refs/heads/{REPO_BRANCH}/src/achievements/{ACHIEVEMENTS_FILE_NAME}"


def local_achievements_file() -> Path:
    """Achievements file in the app's config folder. Updated from remote."""
    return services().config.config_dir / ACHIEVEMENTS_FILE_NAME


def load_local_achievements() -> str:
    """Achievements file in the config folder, copied there from the bundled one first if missing. Empty on failure."""
    log.info("Loading local achievements file.")

    config = services().config

    if not local_achievements_file().exists():
        config_dir = config.config_dir
        copy_dest = config_dir / ACHIEVEMENTS_FILE_NAME

        try:
            log.info(f"Copy distributed '{ACHIEVEMENTS_FILE_NAME}' to config dir '{copy_dest}'", silent=True)
            shutil.copy2(ACHIEVEMENTS_DISTRIBUTED_FILE, copy_dest)
        except Exception as e:
            log.error(f"Failed to copy distributed '{ACHIEVEMENTS_FILE_NAME}' to config directory '{copy_dest}': {e}")
            return ""

    # Load the file
    with open(local_achievements_file(), "r", encoding="UTF-8") as f:
        contents: str = f.read()
        log.info(f"Loaded achievements file\n{contents}", silent=True)

    if not contents:
        log.error("No local achievements file found!")
        return ""

    return contents


def pull_latest_achievements() -> tuple[str, str]:
    """Achievements file contents, and where they came from: "remote" or "local"."""
    log.info("Pulling latest Achievements file from GitHub repository.")

    config = services().config

    if config.prevent_conn:
        log.info("Will not fetch achievements file from remote as prevent connections is active.")
        return load_local_achievements(), "local"

    log.info(ACHIEVEMENTS_URL, silent=True)

    try:
        response = requests.get(ACHIEVEMENTS_URL, timeout=10, verify=certifi.where())
        response.raise_for_status()
    except requests.ConnectionError as con_err:
        log.error("Unable to establish connection to update repo.")
        log.error(con_err)
        return load_local_achievements(), "local"
    except requests.RequestException as req_err:
        log.error(f"Request failed: {req_err}")
        return load_local_achievements(), "local"

    if response.status_code != 200:
        log.warning(f"{response.status_code=}")
        log.error("Not a valid repository or file not found.")
        return load_local_achievements(), "local"

    log.info(f"Achievements file: {local_achievements_file()}", silent=True)

    try:
        achievements = response.text
        log.info("Successfully pulled achievements file from repository.")
        log.debug(f"Content preview: {achievements[:200]}")

        # Update local achievements file
        log.info("Updating achievements file with repo content.")
        try:
            with local_achievements_file().open("w", encoding="utf-8") as ach_f:
                ach_f.write(achievements)
        except Exception as e:
            log.error(f"Error writing to achievements file.\nError: {e}")

        return achievements, "remote"

    except Exception as e:
        log.info(f"Error in pulling achievements from repo. Falling back to physical file.\nError: {e}")
        log.debug(response)
        # Fallback to physical file
        log.debug(f"Achievements file: {local_achievements_file()}")
        return load_local_achievements(), "local"


@cache
def latest_achievements() -> str:
    """The latest achievements list, downloaded once per app run (or the local copy). Empty if unavailable."""
    achievements, _source = pull_latest_achievements()
    return achievements


def achievement_ids(lines: list[str]) -> set[str]:
    """The achievement numbers listed in `lines` (an `achievement={ 1 2 3 }` block)."""
    ids = set()
    for line in lines:
        for word in line.replace("{", " ").replace("}", " ").split():
            if word.isdigit():
                ids.add(word)
    return ids


def main_achievement_block(blocks: list[Block], clusters: Optional[Block]) -> Optional[Block]:
    """The achievements block the game reads: the first one at root, before `clusters=`."""
    for block in blocks:
        is_before_clusters = clusters is None or block.start < clusters.start
        if block.depth == 0 and is_before_clusters:
            return block
    return None


def galaxy_ironman_index(gamestate: list[str]) -> Optional[int]:
    """Line index of `ironman=` in the `galaxy` block (the game settings), or None if missing."""
    galaxy = find_root_block(gamestate, "galaxy")
    if galaxy is None:
        return None
    return find_key(gamestate, "ironman", inside=galaxy)


# --- The save, read ---


@dataclass
class StellarisSave(ParsedSave):
    """The values read from a Stellaris save. Describes the save as it was when it was read."""

    name: str
    date: str
    version: str
    ironman_gamestate: Optional[str]  # `ironman=` in the galaxy settings. None if missing
    ironman_meta: Optional[str]  # Root `ironman=` in meta. Regular saves have none
    cheated: Optional[str]  # Root `cheated_on_save=`. None if missing
    has_achievements: bool  # The game's achievements list is where the game reads it
    achievement_ids: set[str]  # Ids in that list that are also in the latest list
    achievement_problems: list[str]  # Short sentences. Empty when the achievements are fine
    latest_achievements: str  # The latest list as text. Empty if it couldn't be loaded

    @property
    def latest_achievement_ids(self) -> set[str]:
        return achievement_ids(self.latest_achievements.split("\n"))

    # --- What it found ---

    @property
    def findings(self) -> list[SaveFinding]:
        return [
            SaveFinding(id="save_info", label="Save", value=f"{self.name}, {self.date}", status=FindingStatus.INFO),
            SaveFinding(id="game_version", label="Game version", value=self.version, status=FindingStatus.INFO),
            self.ironman_finding(),
            self.cheated_finding(),
            self.achievements_finding(),
        ]

    def ironman_finding(self) -> SaveFinding:
        detail = ""

        if self.ironman_gamestate is None:
            value = "Missing"
            status = FindingStatus.ATTENTION
            detail = "The game settings in gamestate have no Ironman line. Convert to Ironman adds it."
        elif self.ironman_gamestate == YES and self.ironman_meta == YES:
            value = "On"
            status = FindingStatus.OK
        elif self.ironman_gamestate == NO and self.ironman_meta in (None, NO):
            value = "Off"
            status = FindingStatus.OK
        else:
            value = "Mismatch"
            status = FindingStatus.ATTENTION
            meta_value = self.ironman_meta or "nothing"
            detail = f"gamestate says '{self.ironman_gamestate}', meta says '{meta_value}'. Pick a conversion to make them match."

        return SaveFinding(id="ironman", label="Ironman", value=value, status=status, detail=detail)

    def cheated_finding(self) -> SaveFinding:
        detail = ""

        if self.cheated is None:
            value = "Missing"
            status = FindingStatus.INFO
            detail = "This save has no cheated flag, so there's nothing to clear."
        elif self.cheated == YES:
            value = "Yes"
            status = FindingStatus.ATTENTION
            detail = "The save is flagged as cheated. Clear Cheated State removes the flag."
        else:
            value = self.cheated.capitalize()
            status = FindingStatus.OK

        return SaveFinding(id="cheated", label="Cheated", value=value, status=status, detail=detail)

    def achievements_finding(self) -> SaveFinding:
        latest_ids = self.latest_achievement_ids
        detail = ""

        if not self.has_achievements:
            value = "Missing"
        elif latest_ids:
            value = f"{len(self.achievement_ids)} of {len(latest_ids)}"
        else:
            value = "Present"

        if not latest_ids:
            status = FindingStatus.INFO
            detail = "The latest achievements list couldn't be loaded, so the save's list can't be checked or updated."
        elif self.achievement_problems:
            status = FindingStatus.ATTENTION
            detail = " ".join(self.achievement_problems)
        else:
            status = FindingStatus.OK

        return SaveFinding(id="achievements", label="Achievements", value=value, status=status, detail=detail)

    # --- Whether each fix would change the save ---

    def needs_achievements(self) -> bool:
        return bool(self.latest_achievement_ids) and bool(self.achievement_problems)

    def needs_ironman_on(self) -> bool:
        return self.ironman_gamestate != YES or self.ironman_meta != YES

    def needs_ironman_off(self) -> bool:
        return self.ironman_gamestate == YES or self.ironman_meta == YES

    def needs_cheated_off(self) -> bool:
        return self.cheated == YES


def parse_stellaris_save(save: SaveFile, latest: Optional[str] = None) -> StellarisSave:
    """
    Read the values of a Stellaris save.
    `latest` is the latest achievements list; by default it's downloaded once per app run.
    """
    if latest is None:
        latest = latest_achievements()

    gamestate = save.lines(GAMESTATE)
    meta = save.lines(META)

    ironman_gamestate = None
    ironman_index = galaxy_ironman_index(gamestate)
    if ironman_index is not None:
        ironman_gamestate = line_value(gamestate[ironman_index])

    # Achievements: the list the game reads, and what's wrong with all the lists found
    blocks = find_blocks(gamestate, "achievement")
    clusters = find_root_block(gamestate, "clusters")
    achievements_main_block = main_achievement_block(blocks, clusters)
    latest_ids = achievement_ids(latest.split("\n"))

    found_ids = set()
    if achievements_main_block is not None:
        found_ids = achievement_ids(block_lines(gamestate, achievements_main_block)) & latest_ids

    problems = []
    if not blocks:
        problems.append("The save has no achievements list.")
    if len(blocks) > 1:
        problems.append(f"The save has {len(blocks)} achievements lists, there should be one.")
    for block in blocks:
        if block.depth > 0:
            problems.append(f"An achievements list is inside another block (line {block.start + 1}).")
        elif clusters is not None and block.start > clusters.start:
            problems.append(f"An achievements list is in the wrong place (line {block.start + 1}).")

    missing_count = len(latest_ids) - len(found_ids)
    if achievements_main_block is not None and latest_ids and missing_count:
        problems.append(f"{missing_count} of {len(latest_ids)} achievements are missing from the list.")

    return StellarisSave(
        name=get_value(meta, "name") or "",
        date=get_value(meta, "date") or "",
        version=get_value(meta, "version") or "",
        ironman_gamestate=ironman_gamestate,
        ironman_meta=get_value(meta, "ironman"),
        cheated=get_value(gamestate, "cheated_on_save"),
        has_achievements=achievements_main_block is not None,
        achievement_ids=found_ids,
        achievement_problems=problems,
        latest_achievements=latest,
    )


# --- Fixes ---


def apply_achievements(save: SaveFile, parsed: StellarisSave) -> bool:
    """Keep one achievements list, at root before `clusters=`, holding the latest list."""
    latest_text = parsed.latest_achievements.strip()
    if not latest_text:
        raise SaveFixError("The latest achievements list couldn't be loaded.")

    new_lines = [f"{line}\n" for line in latest_text.split("\n")]
    gamestate = save.lines(GAMESTATE)
    changed = False

    # Remove every list except the one the game reads, from the bottom up so earlier line numbers stay right
    blocks = find_blocks(gamestate, "achievement")
    main_block = main_achievement_block(blocks, find_root_block(gamestate, "clusters"))
    for block in reversed(blocks):
        if block is main_block:
            continue
        del gamestate[block.start : block.end + 1]
        changed = True

    # Find it again, as removing lines above it moved it
    main_block = main_achievement_block(find_blocks(gamestate, "achievement"), find_root_block(gamestate, "clusters"))

    if main_block is not None:
        if block_lines(gamestate, main_block) != new_lines:
            gamestate[main_block.start : main_block.end + 1] = new_lines
            changed = True
        return changed

    clusters = find_root_block(gamestate, "clusters")
    if clusters is None:
        raise SaveFixError("The save has no 'clusters=' to place the achievements list before.")

    gamestate[clusters.start : clusters.start] = new_lines
    return True


def apply_ironman_on(save: SaveFile, parsed: StellarisSave) -> bool:
    """`ironman=yes` in the galaxy settings (added after `name=` if missing) and in meta (added at the end if missing)."""
    changed = False

    gamestate = save.lines(GAMESTATE)
    galaxy = find_root_block(gamestate, "galaxy")
    if galaxy is None:
        raise SaveFixError("The save has no galaxy settings to turn Ironman on in.")

    ironman_index = find_key(gamestate, "ironman", inside=galaxy)
    if ironman_index is not None:
        if set_value(gamestate, ironman_index, YES):
            changed = True
    else:
        name_index = find_key(gamestate, "name", inside=galaxy)
        if name_index is None:
            raise SaveFixError("The galaxy settings have no 'name=' line to add Ironman after.")
        insert_line_after(gamestate, name_index, f"ironman={YES}")
        changed = True

    meta = save.lines(META)
    meta_index = find_key(meta, "ironman")
    if meta_index is not None:
        if set_value(meta, meta_index, YES):
            changed = True
    else:
        append_line(meta, f"ironman={YES}")
        changed = True

    return changed


def apply_ironman_off(save: SaveFile, parsed: StellarisSave) -> bool:
    """`ironman=no` in the galaxy settings, if the line is there. Removes `ironman=yes` from meta."""
    changed = False

    gamestate = save.lines(GAMESTATE)
    ironman_index = galaxy_ironman_index(gamestate)
    if ironman_index is not None and set_value(gamestate, ironman_index, NO):
        changed = True

    meta = save.lines(META)
    meta_index = find_key(meta, "ironman")
    if meta_index is not None and line_value(meta[meta_index]) == YES:
        del meta[meta_index]
        changed = True

    return changed


def apply_cheated_off(save: SaveFile, parsed: StellarisSave) -> bool:
    """`cheated_on_save=no`, where the line is. Saves without the line are left alone."""
    gamestate = save.lines(GAMESTATE)
    cheated_index = find_key(gamestate, "cheated_on_save")
    if cheated_index is None:
        return False
    return set_value(gamestate, cheated_index, NO)


STELLARIS = SaveGame(
    name="Stellaris",
    save_extension=".sav",
    required_files=[GAMESTATE, META],
    parse=parse_stellaris_save,
    fixes=[
        SaveFix(
            id="achievements",
            label="Update Achievements",
            description="Replace the achievements list with the latest one, and remove broken or misplaced copies.",
            is_needed=StellarisSave.needs_achievements,
            apply=apply_achievements,
            pre_tick_when_needed=True,
        ),
        SaveFix(
            id="ironman_on",
            label="Convert to Ironman",
            description="Turn Ironman on in the save. Adds the Ironman setting if the save doesn't have it.",
            is_needed=StellarisSave.needs_ironman_on,
            apply=apply_ironman_on,
            conflicts_with="ironman_off",
        ),
        SaveFix(
            id="ironman_off",
            label="Convert to Regular Save",
            description="Turn Ironman off, so the save becomes a regular save.",
            is_needed=StellarisSave.needs_ironman_off,
            apply=apply_ironman_off,
            conflicts_with="ironman_on",
        ),
        SaveFix(
            id="cheated_off",
            label="Clear Cheated State",
            description="Remove the cheated flag from the save.",
            is_needed=StellarisSave.needs_cheated_off,
            apply=apply_cheated_off,
            needs_disclaimer=True,
        ),
    ],
)
