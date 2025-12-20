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

MACOS_PARADOX_INTERACTIVE_PATHS = []

ACHIEVEMENTS_FILE_NAME = "achievements.txt"
ACHIEVEMENTS_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/refs/heads/{REPO_BRANCH}/src/achievements/{ACHIEVEMENTS_FILE_NAME}"
ACHIEVEMENTS_FILE_LOCAL = SETTINGS.get_config_dir() / ACHIEVEMENTS_FILE_NAME
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


class StellarisSavePatcher(SavePatcher):
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

        log.info(f"Save Directory: {save_dir}")
        log.info(f"Save Name: {save_file_name}")

        # --- Setup directories ---
        repair_dir = save_dir / "save_repair"
        Path(repair_dir).mkdir(parents=True, exist_ok=True)
        log.debug(f"Repair Directory: {repair_dir}")

        # --- Backup with timestamp ---
        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        backup_dir = SETTINGS.get_config_dir() / "saves backup" / save_dir.name / timestamp_str
        backup_save_file = Path(backup_dir) / save_file_name
        Path(backup_dir).mkdir(parents=True, exist_ok=True)

        # --- Create the backup ---
        try:
            log.info(f"Backup Directory: {backup_dir}")
            shutil.copy2(save_file, backup_save_file)
            log.info(f"Backed up {save_file_name} to {backup_save_file}")
        except Exception as e:
            log.error(f"Backup failed: {e}")
            return False

        # --- Unzip save file ---
        try:
            log.info(f"Unzip file: {save_file}")
            with zipfile.ZipFile(save_file, "r") as zip_file:
                zip_file.extractall(repair_dir)
        except Exception as e:
            log.error(f"Failed to extract save file: {e}")
            return False

        files_access_times = {}
        for file in Path(repair_dir).iterdir():
            files_access_times[file.name] = (os.stat(file).st_atime, os.stat(file).st_mtime)

        log.info(f"{files_access_times=}", silent=True)

        gamestate_file = Path(repair_dir) / "gamestate"
        meta_file = Path(repair_dir) / "meta"

        # --- Pull latest achievements ---
        self.achievements = self.pull_latest_achievements_file()
        if not self.achievements or self.achievements == "":
            log.error("Unable to fix save: achievements could not be retrieved")
            return False

        # --- Process gamestate ---
        if not self._process_gamestate(gamestate_file):
            log.error(f"Failed to process gamestate for {save_file_name}")
            return False

        # --- Process meta ---
        if not self._process_meta(meta_file):
            log.error(f"Failed to process meta for {save_file_name}")
            return False

        # --- Rebuild the .sav ---
        try:
            with zipfile.ZipFile(save_file, "w", zipfile.ZIP_DEFLATED) as zf:
                for file in Path(repair_dir).iterdir():
                    # Restore original access times
                    fname = file.name
                    if fname in files_access_times:
                        os.utime(file, files_access_times[fname])

                    _encoding = detect_file_encoding(file)
                    with open(file, "r", encoding=_encoding) as fread:
                        zf.writestr(Path(file).name, fread.read())
        except Exception as e:
            log.error(f"Failed to rebuild save file: {e}")
            return False

        # --- Restore original save file times ---
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

        log.info(f"Iroman fix: {ironman_mode}", silent=True)
        log.info(f"Achievement fix: {update_achievements}", silent=True)

        try:
            with gamestate_file.open("r", encoding=_encoding) as f:
                lines = f.readlines()
        except Exception as e:
            log.error(f"Failed to read gamestate: {e}")
            return False

        achievement_lines = self.achievements.strip().split("\n")
        log.debug(f"{achievement_lines=}", silent=True)

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
                # Track achievements block
                if not in_achievements_block and ACHIEVEMENT_EQ_LINE in stripped:
                    achievements_found = True
                    in_achievements_block = True
                    achievement_depth = 0
                    # Insert new achievement block
                    for achievement_line in achievement_lines:
                        new_lines.append(achievement_line + "\n")
                    achievements_inserted = True
                    i += 1
                    continue

                if in_achievements_block:
                    if "{" in stripped:
                        achievement_depth += stripped.count("{")
                    if "}" in stripped:
                        achievement_depth -= stripped.count("}")
                        if achievement_depth <= 0:
                            in_achievements_block = False
                    i += 1
                    continue  # Skip original achievement lines

                # Insert achievements before clusters if not found
                if not achievements_found and not achievements_inserted and CLUSTERS_EQ_LINE in stripped:
                    clusters_found = True
                    log.info(f"Clusters found!", silent=True)
                    for achievement_line in achievement_lines:
                        new_lines.append(achievement_line + "\n")
                    achievements_inserted = True
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
                    lines[ironman_line_index] = "\n"

                    modified = True
            elif has_ironman_no:
                # Replace ironman=no with ironman=yes
                if ironman_mode in (IronmanMode.SET_ENABLE, IronmanMode.FORCE_ADD):
                    log.info(f"Replacing {IRONMAN_NO} with {IRONMAN_YES} in meta file")
                    lines.remove(f"{IRONMAN_YES}\n")
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

    def load_local_achievements_file(self) -> str:
        log.info("Loading local achievements file.")

        if not ACHIEVEMENTS_FILE_LOCAL.exists():
            config_dir = SETTINGS.get_config_dir()
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
            log.info(f"Successfully pulled achievements file from repository")
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
