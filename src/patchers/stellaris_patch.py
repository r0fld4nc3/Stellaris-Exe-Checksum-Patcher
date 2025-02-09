# Regex Pattern Patching Credit: Melechtna Antelecht

import re
from pathlib import Path
import binascii
import shutil
from typing import Union

from conf_globals import OS, steam, settings, LOG_LEVEL
from logger import create_logger

log = create_logger("Patcher", LOG_LEVEL)

EXE_DEFAULT_FILENAME = ""
HEX_FIND = ""
HEX_REPLACE = ""
PATCH_PATTERN = None
BIN_PATH_POSTPEND = ""


def update_patcher_globals():
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

        _fwd_slashed_exec = str(game_executable).replace('\\', '/').replace('\\\\', '/')
        log.info(f"Located game executable: {str(_fwd_slashed_exec)}")

        return game_executable

    return None


def is_patched(file_path: Path) -> bool:
    _fwd_slashed_path = str(file_path).replace('\\', '/').replace('\\\\', '/')
    log.info(f"Checking if patched: {_fwd_slashed_path}")
    patched_pattern = settings.get_patched_block()
    log.info(f"Patched pattern (settings): {patched_pattern}")

    if not patched_pattern:
        return False

    with open(file_path, 'rb') as file:
        binary_data = file.read()

    binary_hex = binascii.hexlify(binary_data).decode()

    # Define regex pattern to find 31DB (ignoring casing) at the end of the line
    regex_pattern = re.compile(patched_pattern, re.IGNORECASE)

    match = regex_pattern.search(binary_hex)
    if match:
        matched_line = binary_hex[match.start():match.end()].upper()
        log.info(f"Matched hex: {matched_line}")
        return True

    return False


def create_backup(file_path: Path, overwrite=False) -> Path | None:
    backup_file = Path(str(file_path) + ".orig")

    _fwd_slashed_path = str(file_path).replace('\\', '/').replace('\\\\', '/')
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

    with open(file_path, 'rb') as file:
        binary_data = file.read() # This stores all in memory. Careful with large files

    binary_hex = binascii.hexlify(binary_data).decode()

    # Define regex pattern to find 85DB (ignoring casing) at the end of the line
    log.debug(f"{PATCH_PATTERN=}")
    regex_pattern = PATCH_PATTERN

    patch_success = False
    match = regex_pattern.search(binary_hex)
    if match:
        matched_line = binary_hex[match.start():match.end()]
        log.info(f"Matched hex: {str(matched_line).upper()}")

        # Locate the index of the last occurrence of 'HEX_FIND' in the matched line
        hex_index = matched_line.upper().rfind(HEX_FIND)

        if hex_index != -1:
            # Replace 'HEX_FIND' with 'HEX_REPLACE' before 'HEX_FIND'
            patched_line = matched_line[:hex_index] + HEX_REPLACE

            log.info(f"Patched hex: {str(patched_line).upper()}")

            # Replace the matched line in the binary hex with the patched line
            binary_hex_patched = binary_hex[:match.start()] + patched_line + binary_hex[match.end():]

            # Convert the patched binary hex back to binary
            binary_data_patched = binascii.unhexlify(binary_hex_patched)

            # Write the patched binary data back to the file
            log.info(f"Writing file {file_path}")
            with open(file_path, 'wb') as file:
                file.write(binary_data_patched)

            # Save patched block for comparison
            settings.set_patched_block(str(patched_line).upper())
            log.info("Patch applied successfully.")
            patch_success = True
        else:
            log.error(f"Pattern found but unable to locate '{HEX_FIND}' in the matched line.")
    else:
        log.info("Failed to match to pattern.")

    return patch_success
