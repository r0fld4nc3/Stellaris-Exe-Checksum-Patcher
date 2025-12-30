import base64
import datetime
import os
import shutil
import ssl
import zipfile
from enum import Enum
from pathlib import Path

import certifi
import requests

from conf_globals import (
    LOG_LEVEL,
    OS,
    PREVENT_CONN,
    REPO_BRANCH,
    REPO_NAME,
    REPO_OWNER,
    SETTINGS,
)
from logger import create_logger

# 3rd Party
from utils.encodings import detect_file_encoding

from .models import GameSavePatchConfig

log = create_logger("Save Patcher", LOG_LEVEL)

WINDOWS_PARADOX_INTERACTIVE_PATHS = [Path.home() / "Documents" / "Paradox Interactive"]

LINUX_PARADOX_INTERACTIVE_PATHS = [Path.home() / ".local" / "share" / "Paradox Interactive"]

MACOS_PARADOX_INTERACTIVE_PATHS = [Path.home() / "Documents" / "Paradox Interactive"]

ACHIEVEMENTS_FILE_NAME = "achievements.txt"
ACHIEVEMENTS_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/refs/heads/{REPO_BRANCH}/src/achievements/{ACHIEVEMENTS_FILE_NAME}"
ACHIEVEMENTS_FILE_LOCAL = SETTINGS.config_dir / ACHIEVEMENTS_FILE_NAME
ACHIEVEMENTS_DISTRIBUTED_FILE = Path(__file__).parent / ACHIEVEMENTS_FILE_NAME
if not ACHIEVEMENTS_DISTRIBUTED_FILE.exists():
    # We're not running a compiled build
    ACHIEVEMENTS_DISTRIBUTED_FILE = Path(__file__).parent.parent / "achievements" / ACHIEVEMENTS_FILE_NAME

NAME_EQ_LINE = "name="
GALAXY_EQ_LINE = "galaxy="
ACHIEVEMENT_EQ_LINE = "achievement="
CLUSTERS_EQ_LINE = "clusters="

IRONMAN_EQ_LINE = "ironman="
IRONMAN_YES = f"{IRONMAN_EQ_LINE}yes"
IRONMAN_NO = f"{IRONMAN_EQ_LINE}no"


class IronmanMode(Enum):
    NONE = 0  # Don't address ironman flag
    SET_ENABLE = 1  # Convert existing ironman=no to ironman=yes
    SET_DISABLE = 2  # Convert existing ironman=yes to ironman=no
    FORCE_ADD = 3  # Always add, even if not present


class SavePatcher:
    """
    Base class for game save file patching operations.

    This abstract patcher provides core functionality for locating and managing
    game save files across different operating systems. It serves as a foundation
    for game-specific save patchers that implement actual patching logic.

    The class automatically attempts to locate save game folders upon initialization
    by searching standard Paradox Interactive directory locations based on the
    current operating system.

    Attributes:
        game_name (str): Name of the game (e.g., "Stellaris") used to locate save folders.
        config (GameSavePatchConfig): Configuration object defining patch operations.
        save_extension (str | None): File extension for save files (e.g., ".sav").
            Must be set by subclasses.
        save_games_folders (list[Path]): List of discovered "save games" directories.
        saves (dict[str, list[Path]]): Dictionary mapping playthrough names to their
            save file paths.

    Platform Support:
        - Windows: Searches in Documents/Paradox Interactive/
        - Linux: Searches in ~/.local/share/Paradox Interactive/
        - macOS: Currently not implemented

    Usage:
        This class should be subclassed for specific games. Subclasses must:
        1. Set the `save_extension` attribute
        2. Implement game-specific patching logic
    """

    def __init__(self, game_name: str, config: GameSavePatchConfig = None):
        self.game_name = game_name
        self.config: GameSavePatchConfig = config
        self.save_extension = None
        self.save_games_folders: list[Path] = []
        self.saves: dict[str, list[Path]] = {}

        # Immediately kick-off a location task if possible
        self._locate_savegames_folder()

    def _locate_savegames_folder(self):
        if not self.game_name:
            return False

        if OS.WINDOWS:
            potential_paths = WINDOWS_PARADOX_INTERACTIVE_PATHS
        elif OS.LINUX:
            potential_paths = LINUX_PARADOX_INTERACTIVE_PATHS
        elif OS.MACOS:
            potential_paths = MACOS_PARADOX_INTERACTIVE_PATHS
        else:
            potential_paths = []

        look_into: list[Path] = []

        # First Pass: Collect root folders matching with game name
        for path in potential_paths:
            path_with_game_name = path / self.game_name
            cond_path_valid = all([path_with_game_name.name == self.game_name, path_with_game_name.is_dir()])

            log.info(f"{cond_path_valid=}", silent=True)

            if cond_path_valid:
                if path_with_game_name not in look_into:
                    look_into.append(path_with_game_name)

        log.info(f"Look into folder(s): {look_into}")

        # Second Pass: Recurse and look for "save games" folder
        self.save_games_folders.clear()
        for root_path in look_into:
            # Recurse each
            for item in root_path.rglob("**/save games/"):
                if item not in self.save_games_folders:
                    self.save_games_folders.append(item)

        log.info(f"Found the following save games folder(s): {self.save_games_folders}")

    def collect_saves(self) -> dict[str, list[Path]]:
        if self.save_extension is None:
            log.error(f"Unable to collect saves: No save extension defined: {self.save_extension}")

        if not self.save_games_folders:
            log.error(f"Unable to collect saves: No save games folder(s) collected: {self.save_games_folders}")

        self.saves = {}
        for save_game_folder in self.save_games_folders:
            for playthrough_folder in save_game_folder.iterdir():
                for item in playthrough_folder.iterdir():
                    log.info(f"{item=}")
                    self.saves.setdefault(playthrough_folder.name, item)

        log.info(f"{self.saves}")
        return self.saves

    def extract_save_archive(self, save_file: str | Path, extract_dir: str | Path) -> bool:
        """
        Extract a save file archive to the specified directoty.

        Args:
            save_file: Path to the save file (.sav or other) to extract.
            extract_dir: Directory where the contents will be extracted to.

        Returns:
            bool: True for succesfull extraction, False otherwise.

        Note:
            Creates the necessary paths for extract_dir if they don't exist.
        """

        save_file = Path(save_file)
        extract_dir = Path(extract_dir)

        # Ensure extraction directory exists
        extract_dir.mkdir(parents=True, exist_ok=True)

        try:
            log.info(f"Extracting archive: {save_file} to {extract_dir}")
            with zipfile.ZipFile(save_file, "r") as zip_file:
                zip_file.extractall(extract_dir)
            log.info(f"Successfully extracted {save_file.name}")
            return True
        except Exception as e:
            log.error(f"Failed to extract save file '{save_file}': {e}")
            return False

    def repackage_save_archive(self, source_dir: str | Path, output_file: str | Path, preserve_timestamps: bool = True):
        """
        Repackage files from a directory into a save file archive.

        Args:
            source_dir: Directory containing files to be archived.
            output_file: Path where the new archive will be created.
            preserve_timestamps: If True, preserves original file access/modification times.

        Returns:
            bool: True if repackaging was successful, False otherwise.

        Note:
            - Uses ZIP_DEFLATED compression
            - Reads files with detected encoding to prevent corruption
            - Optionally preserves file timestamps before archiving
        """

        source_dir = Path(source_dir)
        output_file = Path(output_file)

        if not source_dir.exists() or not source_dir.is_dir():
            log.error(f"Source directory does not exist: {source_dir}")
            return False

        # Store original timestamps
        files_access_times = {}
        if preserve_timestamps:
            for file in source_dir.iterdir():
                if file.is_file():
                    files_access_times[file.name] = (os.stat(file).st_atime, os.stat(file).st_mtime)
            log.debug(f"Stored timestamps for {len(files_access_times)} files.", silent=True)

        try:
            log.info(f"Repackaging files from {source_dir} to {output_file}")
            with zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as zf:
                for file in source_dir.iterdir():
                    if not file.is_file():
                        log.warning(f"Not a file: {file.name}")
                        continue

                    # Restore original access times before archiving
                    fname = file.name
                    if preserve_timestamps and fname in files_access_times:
                        os.utime(file, files_access_times[fname])

                    # Detect encoding and write to archive
                    _encoding = detect_file_encoding(file)
                    with open(file, "r", encoding=_encoding) as fread:
                        zf.writestr(file.name, fread.read())
                        log.info(f"Added: {file.name}")

            log.info(f"Successfully repackaged archive: {output_file.name}")
            return True
        except Exception as e:
            log.error(f"Failed to repackage save file '{output_file}': {e}")
            return False

    def create_timestamped_backup(self, save_file: str | Path, backup_base_dir: str | Path = None) -> Path | None:
        """
        Create a timestamped backup of a save file.

        Args:
            save_file: Path to the save file to backup.
            backup_base_dir: Base directory for backups. If None, uses config directory.

        Returns:
            Path: Path to the created backup file, or None if backup failed.

        Note:
            Backup structure: backup_base_dir/playthrough_name/YYYY-MM-DD HH-MM-SS/filename
        """

        save_file = Path(save_file)

        if not save_file.exists():
            log.error(f"Cannot backup non-existent file: {save_file}")
            return None

        # Determine backup directory
        if backup_base_dir is None:
            backup_base_dir = SETTINGS.config_dir / "saves_backup"

        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        backup_dir = backup_base_dir / save_file.parent.name / timestamp_str
        backup_file = backup_dir / save_file.name

        # Create backup directory
        backup_dir.mkdir(parents=True, exist_ok=True)

        try:
            log.info(f"Creating backup: {backup_file}")
            shutil.copy2(save_file, backup_file)
            log.info(f"Successfully backed up {save_file.name}")
            return backup_file
        except Exception as e:
            log.error(f"Backup failed for '{save_file}': {e}")
            return None


class StellarisSavePatcher(SavePatcher):
    """
    Specialized save file patcher class for Stellaris game saves.

    This patcher handles the repair and modification of Stellaris .sav files, which
    are ZIP archives containing game state data. It can apply various fixes including
    achievement restoration and Ironman mode modifications.

    The patcher works by:
    1. Extracting the .sav file (ZIP archive)
    2. Modifying internal files (gamestate, meta)
    3. Repackaging the modified files back into a .sav file
    4. Attempting to preserve original file timestamps and creating backups

    Attributes:
        game_name (str): Always "Stellaris" for this patcher.
        config (GameSavePatchConfig): Configuration defining which patches to apply.
        achievements (str): Content of the achievements definition file.
        save_extension (str): Format of the targetted save file extension. .sav for Stellaris.
        save_games_folders (list[Path]): Discovered Stellaris save game directories.
        saves (dict[str, list[Path]]): Collected save files organized by playthrough.
    """

    def __init__(self, game_name: str, config: GameSavePatchConfig = None):
        super().__init__(game_name)

        self.config = config

        self.achievements = ""
        self.save_extension = ".sav"

        log.info(f"Game Name: {self.game_name}")
        log.info(f"Save Games Folder: {self.save_games_folders}")

    def set_config(self, config: GameSavePatchConfig) -> bool:
        if not isinstance(config, GameSavePatchConfig):
            return False

        self.config = config

        log.info(f"Set Stellaris Save Patcher GameSavePatchConfig: {config}", silent=True)

        return True

    def get_update_achievements(self) -> bool:
        update_achievements = self.config.is_enabled("update_achievements") if self.config else False

        return update_achievements

    def get_ironman_fix(self) -> IronmanMode:
        # Determine ironman behavior based on enabled patches
        set_ironman_enabled = self.config.is_enabled("set_ironman_yes") if self.config else False
        set_ironman_disabled = self.config.is_enabled("set_ironman_no") if self.config else False
        convert_ironman_enabled = self.config.is_enabled("convert_ironman") if self.config else False

        ironman_mode = IronmanMode.NONE
        if convert_ironman_enabled:
            ironman_mode = IronmanMode.FORCE_ADD
        elif set_ironman_enabled:
            # Only allow if we're not already setting it to disabled
            if not set_ironman_disabled:
                ironman_mode = IronmanMode.SET_ENABLE
        elif set_ironman_disabled:
            # Only allow if we're not already setting it to enabled
            if not set_ironman_enabled:
                ironman_mode = IronmanMode.SET_DISABLE

        if set_ironman_enabled and set_ironman_disabled:
            log.warning(
                f"Conflicting Ironman detected! Both options to enable and disable are checked, and this causes a conflict. None will be applied."
            )

        return ironman_mode

    def repair_save(self, save_file):
        save_dir = Path(save_file).parent
        save_file_name = Path(save_file).name
        save_file_times = (os.stat(save_file).st_atime, os.stat(save_file).st_mtime)

        # Store original timestamps
        save_file_times = (os.stat(save_file).st_atime, os.stat(save_file).st_mtime)

        log.info(f"Save Directory: {save_dir}")
        log.info(f"Save Name: {save_file_name}")

        # --- Setup directory ---
        repair_dir = save_dir / "save_repair"
        Path(repair_dir).mkdir(parents=True, exist_ok=True)
        log.debug(f"Repair Directory: {repair_dir}")

        # --- Backup with timestamp ---
        backup_file = self.create_timestamped_backup(save_file)
        if backup_file is None:
            log.error(f"Backup creation failed, aborting repair.")
            return False
        log.info(f"Backup created at: {backup_file}")

        # --- Extract save archive ---
        if not self.extract_save_archive(save_file, repair_dir):
            log.error(f"Failed to extract the save file, aborting repair!")
            return False

        # --- Define file paths ---
        gamestate_file = Path(repair_dir) / "gamestate"
        meta_file = Path(repair_dir) / "meta"

        # --- Pull latest achievements file ---
        self.achievements = self.pull_latest_achievements_file()
        if not self.achievements or self.achievements == "":
            log.error(f"Unable to fix save: Could not retrieve achievements.")
            shutil.rmtree(repair_dir)
            return False

        # --- Process gamestate ---
        if not self._process_gamestate(gamestate_file):
            log.error(f"Failed to process gamestate for {save_file_name}")
            shutil.rmtree(repair_dir)
            return False

        # --- Process meta ---
        if not self._process_meta(meta_file):
            log.error(f"Failed to process meta for {save_file_name}")
            shutil.rmtree(repair_dir)
            return False

        # --- Repackage save archive ---
        if not self.repackage_save_archive(repair_dir, save_file, preserve_timestamps=True):
            log.error(f"Failed to rebuild save file!")
            shutil.rmtree(repair_dir)
            return False

        # --- Restore original timestamps ---
        os.utime(save_file, save_file_times)

        # --- Cleanup ---
        shutil.rmtree(repair_dir)

        log.info(f"Finished repairing save.")
        return True

    def _process_gamestate(self, gamestate_file: str | Path):
        log.info(f"Process gamestate: '{gamestate_file}'")
        _encoding = detect_file_encoding(gamestate_file)

        ironman_mode = self.get_ironman_fix()
        update_achievements = self.get_update_achievements()

        log.info(f"Achievement fix: {update_achievements}", silent=True)
        log.info(f"Ironman fix: {ironman_mode}", silent=True)

        try:
            with gamestate_file.open("r", encoding=_encoding) as f:
                lines = f.readlines()
        except Exception as e:
            log.error(f"Failed to read gamestate: {e}")
            return False

        achievement_lines = self.achievements.strip().split("\n")
        log.debug(f"{achievement_lines=}", silent=True)

        # --- Cleanup malformed achievement blocks ---
        if update_achievements:
            lines = self._cleanup_malformed_achievements(lines)

        # --- State tracking ---
        new_lines = []
        in_achievements_block = False
        in_galaxy_block = False
        achievement_depth = 0
        galaxy_depth = 0
        achievements_found = False
        clusters_found = False
        achievements_inserted = False
        ironman_handled = False

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if update_achievements:
                # Only match achievement= at the START if a line after whitespace
                # Prevents matching achievement= in middle of other content
                if not in_achievements_block and stripped.startswith(ACHIEVEMENT_EQ_LINE):
                    achievements_found = True
                    in_achievements_block = True
                    achievement_depth = 0

                    # Get indentation for current line
                    indent_level = len(line) - len(line.lstrip())
                    indent = "\t" * (indent_level // 4) if indent_level > 0 else ""

                    # Insert new achievement block with proper indentation
                    for achievement_line in achievement_lines:
                        new_lines.append(f"{indent}{achievement_line}\n")
                    achievements_inserted = True

                    # Start tracking depth from this line
                    if "{" in stripped:
                        achievement_depth += stripped.count("{")

                    i += 1
                    continue

                if in_achievements_block:
                    # Track bracket depth to know when block ends
                    if "{" in stripped:
                        achievement_depth += stripped.count("{")
                    if "}" in stripped:
                        achievement_depth -= stripped.count("}")
                        if achievement_depth <= 0:
                            in_achievements_block = False

                    # Skip all lines in the original achievements block
                    i += 1
                    continue

                # Insert achievements before clusters if not found
                if not achievements_found and not achievements_inserted and stripped.startswith(CLUSTERS_EQ_LINE):
                    clusters_found = True
                    log.info(f"Clusters found! Inserting achievements before it.", silent=True)

                    # Get indentation from clusters line
                    indent_level = len(line) - len(line.lstrip())
                    indent = "\t" * (indent_level // 4) if indent_level > 0 else ""

                    # Insert new achievement block BEFORE clusters=
                    for achievement_line in achievement_lines:
                        new_lines.append(f"{indent}{achievement_line}\n")
                    achievements_inserted = True

                    # Then add clusters= line
                    new_lines.append(line)
                    i += 1
                    continue

            if ironman_mode != IronmanMode.NONE and not ironman_handled:
                # Galaxy block
                if GALAXY_EQ_LINE in stripped:
                    log.info(f"In galaxy block", silent=True)
                    in_galaxy_block = True
                    galaxy_depth = 0

                if in_galaxy_block:
                    if "{" in stripped:
                        galaxy_depth += stripped.count("{")
                    if "}" in stripped:
                        galaxy_depth -= stripped.count("}")
                        if galaxy_depth <= 0:
                            in_galaxy_block = False

                    # Found name=, check next line for ironman
                    if NAME_EQ_LINE in stripped:
                        log.info(f"Found {NAME_EQ_LINE}", silent=True)
                        new_lines.append(line)
                        i += 1

                        # Check if next is ironman
                        if i < len(lines):
                            next_line = lines[i].strip()
                            log.info(f"Next line: {next_line}", silent=True)
                            log.info(f"{IRONMAN_EQ_LINE} in {next_line}: {IRONMAN_EQ_LINE in next_line}")

                            if IRONMAN_EQ_LINE in next_line:
                                # Ironman flag exists - handle it depending on option
                                if ironman_mode == IronmanMode.SET_ENABLE:
                                    indent = len(lines[i]) - len(lines[i].lstrip())
                                    new_lines.append("\t" * indent + f"{IRONMAN_YES}\n")
                                elif ironman_mode == IronmanMode.SET_DISABLE:
                                    indent = len(lines[i]) - len(lines[i].lstrip())
                                    new_lines.append("\t" * indent + f"{IRONMAN_NO}\n")
                                else:
                                    # For other modes, keep the original line
                                    new_lines.append(lines[i])
                                i += 1
                                ironman_handled = True
                                continue
                            elif ironman_mode == IronmanMode.FORCE_ADD:
                                # Insert ironman=yes
                                indent = len(line) - len(line.lstrip())
                                new_lines.append("\t" * indent + f"{IRONMAN_YES}\n")
                                ironman_handled = True
                                continue

            new_lines.append(line)
            i += 1

        if update_achievements and achievements_inserted:
            log.info(f"Repaired achievements line.")
        else:
            log.warning(f"Did not fix achievements line. Already present or not configured.")

        # Validate only if we're updating achievements
        if update_achievements and not achievements_found and not clusters_found:
            log.error(f"Neither '{ACHIEVEMENT_EQ_LINE}' nor '{CLUSTERS_EQ_LINE}' found in gamestate.")
            return False

        # Write modified gamestate
        try:
            with gamestate_file.open("w", encoding=_encoding) as f:
                f.writelines(new_lines)
        except Exception as e:
            log.error(f"Failed to write gamestate: {e}")
            return False

        return True

    def _process_meta(self, meta_file: str | Path):
        _encoding = detect_file_encoding(meta_file)

        try:
            with meta_file.open("r", encoding=_encoding) as f:
                lines = f.readlines()
        except Exception as e:
            log.error(f"Failed to read meta: {e}")
            return False

        modified = False  # Track if changes where made to the file

        # --- IRONMAN PROCESSING ---
        ironman_mode = self.get_ironman_fix()

        if ironman_mode != IronmanMode.NONE:
            # Check if ironman flag exists and its value
            has_ironman_yes = False
            has_ironman_no = False
            ironman_line_index = -1

            for i, line in enumerate(lines):
                if IRONMAN_YES in line:
                    has_ironman_yes = True
                    ironman_line_index = i
                    break
                elif IRONMAN_NO in line:
                    has_ironman_no = True
                    ironman_line_index = i
                    break

            if has_ironman_yes:
                log.info(f"Meta file has {IRONMAN_YES}")
                if ironman_mode == IronmanMode.SET_DISABLE:
                    log.info(f"Removing {IRONMAN_YES} in meta file")
                    lines[ironman_line_index] = ""

                    modified = True
            elif has_ironman_no:
                # Replace ironman=no with ironman=yes
                if ironman_mode in (IronmanMode.SET_ENABLE, IronmanMode.FORCE_ADD):
                    log.info(f"Replacing {IRONMAN_NO} with {IRONMAN_YES} in meta file")
                    lines[ironman_line_index] = f"{IRONMAN_YES}\n"
                    modified = True
            else:
                if ironman_mode in (IronmanMode.SET_ENABLE, IronmanMode.FORCE_ADD):
                    # No ironman flag found, append it
                    log.info(f"Adding {IRONMAN_YES} to meta file")

                    # Ensure last line has newline before appending
                    if lines and not lines[-1].endswith("\n"):
                        lines[-1] += "\n"

                    lines.append(f"{IRONMAN_YES}\n")
                    modified = True

        if modified:
            # Write modified data
            try:
                with meta_file.open("w", encoding=_encoding) as f:
                    f.writelines(lines)
                log.info(f"Meta file updated.")
            except Exception as e:
                log.error(f"Failed to write meta: {e}")
                return False
        else:
            log.info(f"No changes needed for meta file.")

        return True

    def _cleanup_malformed_achievements(self, lines: list[str]) -> list[str]:
        """
        Remove any malformed or incorrectly placed achievement blocks from gamestate.

        This method scans through the file and removes `achievement=` blocks that are :
        - Not at root level (incorrectly nested)
        - Appear multiple times
        - Located after `clusters=` line

        Args:
            lines: List of lines from file

        Returns:
        list[str]: Cleaned lines with malformed blocks removed.
        """
        log.info("Cleaning malformed achievement blocks...")

        cleaned_lines = []
        removed_lines = []  # Track removed lines with their line number for debugging
        in_malformed_achievement = False
        achievement_depth = 0
        root_level = True
        bracket_depth = 0
        clusters_seen = False
        achievement_count = 0

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Track overall bracked depth to determine root level
            if "{" in stripped:
                bracket_depth += stripped.count("{")
            if "}" in stripped:
                bracket_depth -= stripped.count("}")

            # Root level when bracket_depth is at 0 or 1
            root_level = bracket_depth <= 1

            # Have we seen clusters= (achievement= should come before this)
            if stripped.startswith(CLUSTERS_EQ_LINE):
                clusters_seen = True

            # Detect achievement blocks
            if stripped.startswith(ACHIEVEMENT_EQ_LINE):
                achievement_count += 1

                # Malformed if:
                # - Not at root level, OR
                # - Appears after clusters=, OR
                # - Is a duplicate (count > 1)
                if not root_level or clusters_seen or achievement_count > 1:
                    log.warning(
                        f"Found malformed achievement block at line {i+1} (root_level={root_level}, after_clusters={clusters_seen}, count={achievement_count})"
                    )
                    in_malformed_achievement = True
                    achievement_depth = 0

                    if "{" in stripped:
                        achievement_depth += stripped.count("{")

                    # Log removed line:
                    removed_lines.append((i + 1, line.rstrip("\n")))

                    continue  # Skip this line

            # If inside malformed achievement block, track depth and skip
            if in_malformed_achievement:
                if "{" in stripped:
                    achievement_depth += stripped.count("{")
                if "}" in stripped:
                    achievement_depth -= stripped.count("}")
                    if achievement_depth <= 0:
                        in_malformed_achievement = False

                # Log the removed line
                removed_lines.append((i + 1, line.rstrip("\n")))
                continue

            # Keep this line
            cleaned_lines.append(line)

        removed_count = len(lines) - len(cleaned_lines)
        if removed_count > 0:
            log.info(f"Removed {removed_count} lines from malformed achievement blocks.")

            # Log detailed information about removed lines
            log.info("=== Removed Lines Details ===", silent=True)
            log.info(f"Total removed: {len(removed_lines)} lines", silent=True)

            # Group consecutive removed lines for better readability
            if removed_lines:
                current_block_start = removed_lines[0][0]
                current_block_lines = [removed_lines[0]]

                for j in range(1, len(removed_lines)):
                    line_num, content = removed_lines[j]
                    prev_line_num = removed_lines[j - 1][0]

                    # If consecutive, add to current block
                    if line_num == prev_line_num + 1:
                        current_block_lines.append((line_num, content))
                    else:
                        # Log the completed block
                        self._log_removed_block(current_block_start, current_block_lines)

                        # Start new block
                        current_block_start = line_num
                        current_block_lines = [(line_num, content)]

                # Log the last block
                self._log_removed_block(current_block_start, current_block_lines)

            log.info("=== End of Removed Lines ===", silent=True)
        else:
            log.info(f"No malformed achievement blocks found.")

        return cleaned_lines

    def _log_removed_block(self, block_start: int, block_lines: list[tuple[int, str]]):
        """
        Args:
            block_start: Starting line number of the block
            block_lines: List of tuples (line_number, line_content)
        """
        block_end = block_lines[-1][0]

        if len(block_lines) == 1:
            log.debug(f"Line {block_start}:", silent=True)
        else:
            log.debug(f"Lines {block_start}-{block_end} ({len(block_lines)} lines):", silent=True)

        preview_limit = -1  # -1 to show without limit, otherwise limti with positive number.

        # Determine how many lines to show
        if preview_limit == -1:
            # Show all lines without cutoff
            lines_to_show = block_lines
            show_truncation_notice = False
        else:
            # Show only up to preview_limit lines
            lines_to_show = block_lines[:preview_limit]
            show_truncation_notice = len(block_lines) > preview_limit

        for line_num, content in lines_to_show:
            if preview_limit <= -1:
                log.debug(f"  [{line_num}] {content}", silent=True)
            else:
                # Truncate very long lines
                display_content = content[:100] + "..." if len(content) > 100 else content
                log.debug(f"  [{line_num}] {display_content}", silent=True)

        # If block is longer than preview limit
        if show_truncation_notice:
            log.debug(f"  ... ({len(block_lines) - preview_limit} more lines)", silent=True)

            # Show last line of block
            last_line_num, last_content = block_lines[-1]
            display_content = last_content[:100] + "..." if len(last_content) > 100 else last_content
            log.debug(f"  [{last_line_num}] {display_content}", silent=True)

    def load_local_achievements_file(self) -> str:
        log.info("Loading local achievements file.")

        if not ACHIEVEMENTS_FILE_LOCAL.exists():
            config_dir = SETTINGS.config_dir
            copy_dest = config_dir / ACHIEVEMENTS_FILE_NAME

            try:
                log.info(f"Copy distributed '{ACHIEVEMENTS_FILE_NAME}' to config dir '{copy_dest}'", silent=True)
                shutil.copy2(ACHIEVEMENTS_DISTRIBUTED_FILE, copy_dest)
            except Exception as e:
                log.error(
                    f"Failed to copy distributed '{ACHIEVEMENTS_FILE_NAME}' to config directory '{copy_dest}': {e}"
                )
                return []

        # Load the file
        with open(ACHIEVEMENTS_FILE_LOCAL, "r", encoding="UTF-8") as f:
            contents: list = f.read()
            log.info(f"Loaded achievements file\n{contents}", silent=True)

        if not contents:
            log.error(f"No local achievements file found!")
            return ""

        return contents

    def pull_latest_achievements_file(self) -> str:
        log.info("Pulling latest Achievements file from GitHub repository.")

        if PREVENT_CONN:
            log.info(f"Will not fetch achievements file from remote as prevent connections is active.")
            return self.load_local_achievements_file()

        # Force SSL context to fix Thread issues
        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
        except Exception as e:
            log.error(f"Failed to create SSL context: {e}", silent=True)

        log.info(ACHIEVEMENTS_URL, silent=True)

        try:
            response = requests.get(ACHIEVEMENTS_URL, timeout=10, verify=certifi.where())
            response.raise_for_status()
        except requests.ConnectionError as con_err:
            log.error(f"Unable to establish connection to update repo.")
            log.error(con_err)
            return self.load_local_achievements_file()
        except requests.RequestException as req_err:
            log.error(f"Request failed: {req_err}")
            return self.load_local_achievements_file()

        if response.status_code != 200:
            log.warning(f"{response.status_code=}")
            log.error("Not a valid repository or file not found.")
            return self.load_local_achievements_file()

        log.info(f"Achievements file: {ACHIEVEMENTS_FILE_LOCAL}", silent=True)

        try:
            achievements = response.text
            log.info(f"Successfully pulled achievements file from repository.")
            log.debug(f"Content preview: {achievements[:200]}")

            # Update local achievements file
            log.info("Updating achievements file with repo content.")
            try:
                with ACHIEVEMENTS_FILE_LOCAL.open("w", encoding="utf-8") as ach_f:
                    ach_f.write(achievements)
            except Exception as e:
                log.error(f"Error writing to achievements file.\nError: {e}")

            return achievements

        except Exception as e:
            log.info(f"Error in pulling achievements from repo. Falling back to physical file.\nError: {e}")
            log.debug(response)
            # Fallback to physical file
            log.debug(f"Achievements file: {ACHIEVEMENTS_FILE_LOCAL}")
            return self.load_local_achievements_file()
