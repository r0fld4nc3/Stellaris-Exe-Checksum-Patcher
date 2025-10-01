# Regex Pattern Patching Credit: Melechtna Antelecht

import re  # isort: skip
import json  # isort: skip
import mmap  # isort: skip
import shutil  # isort: skip
import binascii  # isort: skip
from pathlib import Path  # isort: skip
from typing import Union  # isort: skip

from conf_globals import LOG_LEVEL, USE_LOCAL_PATTERNS, OS, settings, steam  # isort: skip
from logger import create_logger  # isort: skip
from utils.hashing import calc_file_hash  # isort: skip
from patch_patterns import patterns  # isort: skip

log = create_logger("Patcher", LOG_LEVEL)  # isort: skip

EXE_DEFAULT_FILENAME = ""  # isort: skip
HEX_FIND = ""  # isort: skip
HEX_REPLACE = ""  # isort: skip
PATCH_PATTERN = re.compile(r"", re.IGNORECASE)  # isort: skip
BIN_PATH_POSTPEND = ""  # isort: skip


def update_patcher_globals(patch_warning=False):
    """
    Update Patcher Global Variables according to OS
    """

    # Get the remote config
    if not USE_LOCAL_PATTERNS:
        config = patterns.get_patterns_config_remote()
    else:
        config = None

    # Fallback to local config
    if not config:
        config: dict = patterns.get_patterns_config_local()

    if not config:
        return False

    if not patch_warning:
        # Checksum specific values
        patch_config_key = "checksum_patch"
    else:
        # Checksum Warning specific values
        patch_config_key = "checksum_warning"

    log.info(f"Using patch configuration key: '{patch_config_key}'.", silent=True)

    patch_config = config.get(patch_config_key)

    if not patch_config:
        log.error(f"Patch config patterns not found in config for key '{patch_config_key}'.")
        return False

    global EXE_DEFAULT_FILENAME, HEX_FIND, HEX_REPLACE, PATCH_PATTERN, BIN_PATH_POSTPEND

    EXE_DEFAULT_FILENAME = config.get("exe_filename")
    HEX_FIND = patch_config.get("hex_find")
    HEX_REPLACE = patch_config.get("hex_replace")
    BIN_PATH_POSTPEND = config.get("bin_path_postpend", "")

    # Build regex pattern
    pattern_string = patch_config.get("patch_pattern")
    if pattern_string and HEX_FIND:
        PATCH_PATTERN = re.compile(rf"{pattern_string.replace('%s', HEX_FIND)}", re.IGNORECASE)
    else:
        log.error(f"'patch_pattern' or 'hex_find' missing in config!")
        log.error(f"{json.dumps(config, indent=2)}", silent=True)
        return False

    log.info(f"Successfully updated Patcher globals for key '{patch_config_key}'.")
    log.info(f"{EXE_DEFAULT_FILENAME=}", silent=True)
    log.info(f"{BIN_PATH_POSTPEND=}", silent=True)
    log.info(f"{HEX_FIND=}", silent=True)
    log.info(f"{HEX_REPLACE=}", silent=True)
    log.info(f"{PATCH_PATTERN=}", silent=True)

    return True


def update_patcher_globals_depr():
    """
    Update Patcher Globals to patch mods acceptance with Achievements/Ironman
    """
    global EXE_DEFAULT_FILENAME, HEX_FIND, HEX_REPLACE, PATCH_PATTERN, BIN_PATH_POSTPEND

    log.info("Updating Patcher Globals for 1st patch...", silent=True)

    if OS.WINDOWS or (OS.LINUX and OS.LINUX_PROTON):
        if OS.LINUX_PROTON:
            log.info("Setting globals to Linux Proton", silent=True)
        else:
            log.info("Setting globals to Windows", silent=True)

        # Windows and Proton Linux
        EXE_DEFAULT_FILENAME = "stellaris.exe"  # Game executable name plus extension
        HEX_FIND = "85C0"
        HEX_REPLACE = "31C0"
        PATCH_PATTERN = re.compile(r"C8CA018BF8%s" % HEX_FIND, re.IGNORECASE)

    elif OS.LINUX:
        log.info("Setting globals to Linux Native", silent=True)

        # Native Linux
        # Working as of 27 September 2025
        EXE_DEFAULT_FILENAME = "stellaris"
        HEX_FIND = "85DB"
        HEX_REPLACE = "31DB"
        PATCH_PATTERN = re.compile(r"E8BC55.{8,16}%s" % HEX_FIND, re.IGNORECASE)

    elif OS.MACOS:
        log.info("Setting globals to Linux macOS", silent=True)

        # The actual executable is inside the .app -> /.../stellaris.app/Contents/MacOS/stellaris
        # TODO: update Mac Patch1
        EXE_DEFAULT_FILENAME = "stellaris.app"
        BIN_PATH_POSTPEND = "Contents/MacOS/stellaris"
        HEX_FIND = "85DB"
        HEX_REPLACE = "31DB"
        PATCH_PATTERN = re.compile(r"89C3E851.{8,10}%s" % HEX_FIND, re.IGNORECASE)

    else:
        log.warning("Setting globals to we shouldn't be here, but here we are...", silent=True)

        EXE_DEFAULT_FILENAME = "stellaris.wtf"
        HEX_FIND = "85C0"
        HEX_REPLACE = "31C0"
        PATCH_PATTERN = re.compile(r"C8CA018BF8%s" % HEX_FIND, re.IGNORECASE)

    log.info(f"{EXE_DEFAULT_FILENAME=}", silent=True)
    log.info(f"{BIN_PATH_POSTPEND=}", silent=True)
    log.info(f"{HEX_FIND=}", silent=True)
    log.info(f"{HEX_REPLACE=}", silent=True)
    log.info(f"{PATCH_PATTERN=}", silent=True)


def update_patcher_globals2():
    """
    Update Patcher Globals to patch modifier checksum warning
    """
    log.info("Updating Patcher Globals for 2nd patch...", silent=True)
    global EXE_DEFAULT_FILENAME, HEX_FIND, HEX_REPLACE, PATCH_PATTERN, BIN_PATH_POSTPEND

    if OS.WINDOWS:
        log.info("Setting globals to Windows", silent=True)
        # Windows and Proton Linux
        EXE_DEFAULT_FILENAME = "stellaris.exe"  # Game executable name plus extension
        HEX_FIND = "85C0"
        HEX_REPLACE = "31C0"
        PATCH_PATTERN = re.compile(r"3401E8C9971501%s" % HEX_FIND, re.IGNORECASE)
    elif OS.LINUX:
        if not OS.LINUX_PROTON:
            log.info("Setting globals to Linux Native", silent=True)
            # Native Linux
            EXE_DEFAULT_FILENAME = "stellaris"
            HEX_FIND = "85C0"
            HEX_REPLACE = "31C0"
            PATCH_PATTERN = re.compile(r"8B30BF13219D03E86400DAFE%s" % HEX_FIND, re.IGNORECASE)
        else:
            log.info("Setting globals to Linux Proton", silent=True)
            # Linux Proton (Windows equivalent?)
            EXE_DEFAULT_FILENAME = "stellaris.exe"
            HEX_FIND = "85C0"
            HEX_REPLACE = "31C0"
            PATCH_PATTERN = re.compile(r"3401E8C9971501%s" % HEX_FIND, re.IGNORECASE)
    elif OS.MACOS:
        log.info("Setting globals to Linux macOS", silent=True)
        # The actual executable is inside the .app -> /.../stellaris.app/Contents/MacOS/stellaris
        # TODO: Add Mac Patch2
        EXE_DEFAULT_FILENAME = "stellaris.app"
        BIN_PATH_POSTPEND = "Contents/MacOS/stellaris"
        HEX_FIND = "85DB"
        HEX_REPLACE = "31DB"
        PATCH_PATTERN = re.compile(r"89C3E851.{8,10}%s" % HEX_FIND, re.IGNORECASE)
    else:
        log.warning("Setting globals to we shouldn't be here, but here we are...", silent=True)
        EXE_DEFAULT_FILENAME = "stellaris.wtf"
        HEX_FIND = "85C0"
        HEX_REPLACE = "31C0"
        PATCH_PATTERN = re.compile(r"3401E8C9971501%s" % HEX_FIND, re.IGNORECASE)

    log.info(f"{EXE_DEFAULT_FILENAME=}", silent=True)
    log.info(f"{BIN_PATH_POSTPEND=}", silent=True)
    log.info(f"{HEX_FIND=}", silent=True)
    log.info(f"{HEX_REPLACE=}", silent=True)
    log.info(f"{PATCH_PATTERN=}", silent=True)


def update_patcher_globals_old():
    log.info("Updating Patcher Globals", silent=True)
    global EXE_DEFAULT_FILENAME, HEX_FIND, HEX_REPLACE, PATCH_PATTERN, BIN_PATH_POSTPEND

    if OS.WINDOWS:
        log.info("Setting globals to Windows", silent=True)

        # Windows and Proton Linux
        EXE_DEFAULT_FILENAME = "stellaris.exe"  # Game executable name plus extension
        HEX_FIND = "85C0"
        HEX_REPLACE = "33C0"
        PATCH_PATTERN = re.compile(r"488B1248.{20,26}%s" % HEX_FIND, re.IGNORECASE)

    elif OS.LINUX:
        if not OS.LINUX_PROTON:
            log.info("Setting globals to Linux Native", silent=True)

            # Native Linux
            EXE_DEFAULT_FILENAME = "stellaris"
            HEX_FIND = "85DB"
            HEX_REPLACE = "33DB"
            PATCH_PATTERN = re.compile(r"488B30.{20,50}%s" % HEX_FIND, re.IGNORECASE)
        else:
            log.info("Setting globals to Linux Proton", silent=True)

            # Linux Proton (Windows equivalent?)
            EXE_DEFAULT_FILENAME = "stellaris.exe"
            HEX_FIND = "85C0"
            HEX_REPLACE = "33C0"
            PATCH_PATTERN = re.compile(r"488B1248.{20,26}%s" % HEX_FIND, re.IGNORECASE)

    elif OS.MACOS:
        log.info("Setting globals to Linux macOS", silent=True)

        # .app IS NOT A FILE, IT'S A DIRECTORY
        # The actual executable is inside the .app -> /.../stellaris.app/Contents/MacOS/stellaris
        EXE_DEFAULT_FILENAME = "stellaris.app"
        BIN_PATH_POSTPEND = "Contents/MacOS/stellaris"
        HEX_FIND = "85DB"
        HEX_REPLACE = "31DB"
        PATCH_PATTERN = re.compile(r"89C3E851.{8,10}%s" % HEX_FIND, re.IGNORECASE)

    else:
        log.warning("Setting globals to we shouldn't be here, but here we are...", silent=True)

        EXE_DEFAULT_FILENAME = "stellaris.wtf"
        HEX_FIND = "85C0"
        HEX_REPLACE = "33C0"
        PATCH_PATTERN = re.compile(r"488B1248.{20,26}%s" % HEX_FIND, re.IGNORECASE)

    log.info(f"{EXE_DEFAULT_FILENAME=}", silent=True)
    log.info(f"{BIN_PATH_POSTPEND=}", silent=True)
    log.info(f"{HEX_FIND=}", silent=True)
    log.info(f"{HEX_REPLACE=}", silent=True)
    log.info(f"{PATCH_PATTERN=}", silent=True)


TITLE_NAME = "Stellaris"  # Steam title name


def locate_game_executable() -> Union[Path, None]:
    """
    Returns path to game executable.
    """
    log.info("Locating game install...")

    if not OS.LINUX_PROTON:
        stellaris_install_path = steam.get_game_install_path(TITLE_NAME)
    else:
        stellaris_install_path = steam.get_game_install_path(TITLE_NAME)

    log.debug(f"{stellaris_install_path=}")

    if stellaris_install_path:
        game_executable = Path(stellaris_install_path) / EXE_DEFAULT_FILENAME

        log.debug(f"{game_executable=} ({game_executable.exists()})")

        if not Path(game_executable).exists():
            log.info(f"Invalid game executable: {str(game_executable)}")
            return None

        _fwd_slashed_exec = str(game_executable).replace("\\", "/").replace("\\\\", "/")
        log.info(f"Located game executable: {str(_fwd_slashed_exec)}")

        return game_executable

    return None


def is_patched(file_path: Path) -> bool:
    _fwd_slashed_path = str(file_path).replace("\\", "/").replace("\\\\", "/")
    log.info(f"Checking if patched: {_fwd_slashed_path}")

    patched_hash = settings.get_patched_hash()
    file_hash = calc_file_hash(file_path)
    log.info(f"Patched hash (settings): {patched_hash}", silent=True)
    log.info(f"File hash:{' '*14} {file_hash}", silent=True)

    patched_pattern = settings.get_patched_block()
    log.info(f"Patched pattern (settings): {patched_pattern}", silent=True)

    # Is the file the same hash?
    if file_hash == patched_hash:
        return True

    log.info("File hashing test failed. Comparing patch patterns...")

    if not patched_pattern:
        return False

    with open(file_path, "rb") as file:
        binary_data = file.read()

    binary_hex = binascii.hexlify(binary_data).decode()

    # Define regex pattern to find PATCH_PATTERN (ignoring casing) at the end of the line
    regex_pattern = re.compile(patched_pattern, re.IGNORECASE)

    match = regex_pattern.search(binary_hex)
    if match:
        matched_line = binary_hex[match.start() : match.end()].upper()
        log.info(f"Matched hex: {matched_line}")
        return True

    return False


def create_backup(file_path: Path, overwrite=False) -> Path | None:
    backup_file = Path(str(file_path) + ".orig")

    _fwd_slashed_path = str(file_path).replace("\\", "/").replace("\\\\", "/")
    log.info(f"Creating backup of {file_path}")

    # Create or replace file
    if backup_file.exists():
        if not overwrite:
            log.info(f"Aborting backup as a backup already exists and overwriting is set to {overwrite}.")
            return backup_file

        log.info(f"Unlinking/Removing {backup_file}")

        # Remove the file
        if OS.MACOS:
            # For macOS the .app is a directory
            try:
                shutil.rmtree(backup_file)
                log.info(f"Removed directory {backup_file}")
            except Exception as e:
                log.error(e)
                return None
        else:
            try:
                backup_file.unlink()
                log.info(f"Unlinked {backup_file}")
            except Exception as e:
                log.error(e)
                return None

        # Now copy the file and set the name
        if OS.MACOS:
            # For macOS, .app is a directory
            try:
                log.info(f"Copying {file_path} to {backup_file}")
                shutil.copytree(file_path, backup_file)
            except Exception as e:
                log.error(e)
        else:
            try:
                log.info(f"Copying {file_path} -> {backup_file}")
                shutil.copy2(file_path, backup_file)
            except Exception as e:
                log.error(e)
    else:
        # Now copy the file and set the name
        if OS.MACOS:
            # For macOS, .app is a directory
            try:
                log.info(f"Copying {file_path} to {backup_file}")
                shutil.copytree(file_path, backup_file)
            except Exception as e:
                log.error(e)
        else:
            try:
                log.info(f"Copying {file_path} -> {backup_file}")
                shutil.copy2(file_path, backup_file)
            except Exception as e:
                log.error(e)

    return backup_file


def patch(file_path: Path) -> bool:
    if not file_path.exists():
        log.warning(f"{file_path} does not exist.")
        return False

    if not file_path.is_file():
        log.warning(f"{file_path} is not a file.")
        return False

    log.info(f"Patching file: {file_path}")

    # Define regex pattern to find PATCH_PATTERN (ignoring casing) at the end of the line
    log.debug(f"{PATCH_PATTERN=}")
    regex_pattern = PATCH_PATTERN

    patch_success = False

    try:
        # Create memory map of file with "r+b" for memory efficient loading and file handling
        with open(file_path, "r+b") as file:
            with mmap.mmap(file.fileno(), 0) as mm:
                binary_hex = binascii.hexlify(mm).decode()

                match = regex_pattern.search(binary_hex)
                if match:
                    matched_line = binary_hex[match.start() : match.end()]
                    log.info(f"Matched hex: {str(matched_line).upper()}")

                    # Locate the index of the last occurrence of 'HEX_FIND' in the matched line
                    hex_index = matched_line.upper().rfind(HEX_FIND)

                    if hex_index != -1:
                        # Replace 'HEX_FIND' with 'HEX_REPLACE' before 'HEX_FIND'
                        patched_line = matched_line[:hex_index] + HEX_REPLACE

                        log.info(f"Patched hex: {str(patched_line).upper()}")

                        # Replace the matched line in the binary hex with the patched line
                        binary_hex_patched = binary_hex[: match.start()] + patched_line + binary_hex[match.end() :]

                        # Convert the patched binary hex back to binary
                        binary_data_patched = binascii.unhexlify(binary_hex_patched)

                        # Write the patched binary data back to the file
                        log.info(f"Writing changes to file {file_path}")
                        mm[:] = binary_data_patched
                        mm.flush()

                        # Save patched block for comparison
                        settings.set_patched_block(str(patched_line).upper())
                        log.info("Patch applied successfully.")
                        patch_success = True
                    else:
                        log.error(f"Pattern found but unable to locate '{HEX_FIND}' in the matched line.")
                else:
                    log.info("Failed to match to pattern.")
    except Exception as e:
        log.error(f"An error occurred during patching: {e}")
        return False

    # Save patched file hash
    if patch_success:
        settings.set_patched_hash(calc_file_hash(file_path))

    return patch_success
