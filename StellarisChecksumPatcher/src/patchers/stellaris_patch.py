# Regex Pattern Patching Credit: Melechtna Antelecht

import re
import pathlib
import binascii
import shutil
from typing import Union

from src.utils.global_defines import OS, logger, steam, settings

Path = pathlib.Path

if OS.WINDOWS:
    # Windows and Proton Linux
    EXE_DEFAULT_FILENAME = "stellaris.exe"  # Game executable name plus extension
    hex_find = "85C0"
    hex_replace = "33C0"
    patch_pattern = re.compile(r"488B1248.{20,26}%s" % hex_find, re.IGNORECASE)
elif OS.LINUX:
    # Native Linux
    EXE_DEFAULT_FILENAME = "stellaris"
    hex_find = "85DB"
    hex_replace = "31DB"
    # TODO: Check if it actually patches the right place
    patch_pattern = re.compile(r"488B3.{20,50}%s" % hex_find, re.IGNORECASE)
elif OS.MACOS:
    # .app IS NOT A FILE, IT'S A DIRECTORY
    # The actual executable is inside the .app -> /.../stellaris.app/Contents/MacOS/stellaris
    EXE_DEFAULT_FILENAME = "stellaris.app"
    EXE_PATH_POSTPEND = "Contents/MacOS/stellaris"
    hex_find = "85DB"
    hex_replace = "31DB"
    # TODO: Check if it actually patches the right place
    patch_pattern = re.compile(r"488B3.{20,38}%s" % hex_find, re.IGNORECASE)
else:
    EXE_DEFAULT_FILENAME = "stellaris.wtf"
    hex_find = "85C0"
    hex_replace = "33C0"
    patch_pattern = re.compile(r"488B1248.{20,26}%s" % hex_find, re.IGNORECASE)

TITLE_NAME = "Stellaris"  # Steam title name


def locate_game_executable() -> Union[Path, None]:
    """
    Returns path to game executable.
    """
    logger.info("Locating game install...")

    stellaris_install_path = steam.get_game_install_path(TITLE_NAME)

    # Add additional check, because it might be Proton Linux and therefore have a .exe
    if OS.LINUX and not stellaris_install_path:
        logger.info("System is Linux but unable to locate native game install. Trying as Proton Linux")
        stellaris_install_path = steam.get_game_install_path(TITLE_NAME + ".exe")

    if stellaris_install_path:
        game_executable = Path(stellaris_install_path) / EXE_DEFAULT_FILENAME

        if not Path(game_executable).exists():
            return None

        logger.info(f"Located game executable: {game_executable}")
        return game_executable

    return None

def is_patched(file_path: Path) -> bool:
    logger.info(f"Checking if patched: {file_path}")
    patched_pattern = settings.get_patched_block()
    logger.info(f"Patched pattern (settings): {patched_pattern}")

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
        logger.info(f"Matched line (hex): {matched_line}")
        return True

    return False

def create_backup(file_path: Path, overwrite=False) -> bool:
    backup_file = Path(str(file_path) + ".orig")

    logger.info(f"Creating backup of {file_path}")

    # Create or replace file
    if backup_file.exists():
        if not overwrite:
            logger.info(f"Aborting backup as overwrite backup is {overwrite}")
            return True

        logger.info(f"Unlinking/Removing {backup_file}")

        # Remove the file
        if OS.MACOS:
            # For MacOS the .app is a directory
            try:
                shutil.rmtree(backup_file)
                logger.info(f"Removed directory {backup_file}")
            except Exception as e:
                logger.error(e)
                return False
        else:
            try:
                backup_file.unlink()
                logger.info(f"Unlinked {backup_file}")
            except Exception as e:
                logger.error(e)
                return False

        # Now copy the file and set the name
        if OS.MACOS:
            # For MacOS, .app is a directory
            try:
                logger.info(f"Copying {file_path} to {backup_file}")
                shutil.copytree(file_path, backup_file)
            except Exception as e:
                logger.error(e)
        else:
            try:
                logger.info(f"Copying {file_path} -> {backup_file}")
                shutil.copy2(file_path, backup_file)
            except Exception as e:
                logger.error(e)
    else:
        # Now copy the file and set the name
        if OS.MACOS:
            # For MacOS, .app is a directory
            try:
                logger.info(f"Copying {file_path} to {backup_file}")
                shutil.copytree(file_path, backup_file)
            except Exception as e:
                logger.error(e)
        else:
            try:
                logger.info(f"Copying {file_path} -> {backup_file}")
                shutil.copy2(file_path, backup_file)
            except Exception as e:
                logger.error(e)

    return True

def patch(file_path: Path, duplicate_to: Path = None, both=False):
    if not file_path.exists():
        logger.warning(f"{file_path} does not exist")
        return False

    if not file_path.is_file():
        logger.warning(f"{file_path} is not a file")
        return False

    logger.info(f"Processing file: {file_path}")

    with open(file_path, 'rb') as file:
        binary_data = file.read()

    binary_hex = binascii.hexlify(binary_data).decode()

    # Define regex pattern to find 85DB (ignoring casing) at the end of the line
    regex_pattern = patch_pattern

    patch_success = False
    match = regex_pattern.search(binary_hex)
    if match:
        matched_line = binary_hex[match.start():match.end()]
        logger.info(f"Matched line (hex): {matched_line}")

        # Locate the index of the last occurrence of '85DB' in the matched line
        hex_index = matched_line.upper().rfind(hex_find)

        if hex_index != -1:
            # Replace 'hex_find' with 'hex_replace' before 'hex_find'
            patched_line = matched_line[:hex_index] + hex_replace

            logger.info(f"Patched line (hex): {patched_line}")

            # Replace the matched line in the binary hex with the patched line
            binary_hex_patched = binary_hex[:match.start()] + patched_line + binary_hex[match.end():]

            # Convert the patched binary hex back to binary
            binary_data_patched = binascii.unhexlify(binary_hex_patched)

            # Write the patched binary data back to the file
            if not duplicate_to or (duplicate_to and both):
                logger.info(f"Writing file {file_path}")
                with open(file_path, 'wb') as file:
                    file.write(binary_data_patched)

            if duplicate_to:
                duplicate_to_fp = duplicate_to / file_path.name
                logger.info(f"Writing duplicate to {duplicate_to_fp}")
                with open(duplicate_to_fp, 'wb') as duplicate_file:
                    duplicate_file.write(binary_data_patched)

            # Save patched block for comparison
            settings.set_patched_block(str(patched_line).upper())
            logger.info("Patch applied successfully")
            patch_success = True
        else:
            logger.error(f"Pattern found but unable to locate '{hex_find}' in the matched line")
    else:
        logger.info("Pattern not found")

    return patch_success