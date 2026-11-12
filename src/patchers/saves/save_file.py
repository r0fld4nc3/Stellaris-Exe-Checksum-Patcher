"""
A save file opened into memory, and finding and changing values in its text.

Paradox saves (Stellaris `.sav`) are zip archives of plain text files, like `gamestate` and `meta`.
`open_save()` reads every file inside as a list of lines. Fixes edit those lines, then `write_save()` writes the archive back.

The text (the "Clausewitz" format) is made of `key=value` lines and blocks:

    galaxy=
    {
        name="..."
        ironman=no
    }

A key at "root" is not inside any block. Blocks are found by counting `{` and `}` on each line.
Braces inside quoted text (like a name with a `{` in it) are counted too.

The text functions work on a list of lines that each keep their line ending, as `SaveFile.lines()` returns them.
Functions that change lines edit the list in place.

Also finds the game's save games folders, and backs saves up before they're fixed.
"""

import datetime
import logging
import os
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import chardet

from core import services
from core.paths import os_darwin, os_linux, os_windows
from utils.helpers import get_fpath_size

# Same logger as the old save patcher, which the main window shows on the information screen
log = logging.getLogger("Save Patcher")


class SaveFileError(Exception):
    """The save can't be opened or written."""


@dataclass
class SaveEntry:
    """One text file inside the save archive."""

    info: zipfile.ZipInfo  # Name, date and compression, reused when writing back
    encoding: str
    lines: list[str]  # Each line keeps its line ending, so writing back changes nothing else

    @property
    def name(self) -> str:
        return self.info.filename

    def text(self) -> str:
        return "".join(self.lines)


@dataclass
class SaveFile:
    path: Path
    entries: list[SaveEntry]  # In archive order

    # Set when opened. Used to detect the save changed on disk, and to restore timestamps after writing.
    size: int
    accessed_ns: int
    modified_ns: int

    def entry(self, name: str) -> Optional[SaveEntry]:
        for entry in self.entries:
            if entry.name == name:
                return entry
        return None

    def lines(self, name: str) -> list[str]:
        """Lines of the file `name` inside the save. Edited in place."""
        entry = self.entry(name)
        if entry is None:
            raise SaveFileError(f"'{name}' is not in the save '{self.path.name}'")
        return entry.lines

    def changed_on_disk(self) -> bool:
        """True if the save file was changed or removed since it was opened."""
        try:
            stat = self.path.stat()
        except OSError:
            return True

        return stat.st_size != self.size or stat.st_mtime_ns != self.modified_ns


def open_save(path: Path | str) -> SaveFile:
    """Read every file inside the save archive into memory. Raises SaveFileError if it can't."""
    path = Path(path)
    log.info(f"Opening save: {path}")

    try:
        stat = path.stat()
        with zipfile.ZipFile(path, "r") as archive:
            entries = []
            for info in archive.infolist():
                data = archive.read(info)
                encoding, text = _decode(info.filename, data)
                entries.append(SaveEntry(info=info, encoding=encoding, lines=_split_lines(text)))
    except (OSError, zipfile.BadZipFile) as e:
        err_msg: str = f"Unable to open save '{path.name}': {e}"
        log.error(err_msg)
        raise SaveFileError(err_msg) from e

    names = [entry.name for entry in entries]
    log.info(f"Save files: {names}", silent=True)

    return SaveFile(
        path=path,
        entries=entries,
        size=stat.st_size,
        accessed_ns=stat.st_atime_ns,
        modified_ns=stat.st_mtime_ns,
    )


def write_save(save: SaveFile) -> None:
    """
    Write the save back to its file, with the same file order, dates and compression inside the archive.

    Writes to a temporary file first and then replaces the save, so a failure never leaves a half-written save.
    The save file keeps the timestamps it had when it was opened.
    """
    temp_path = save.path.with_name(save.path.name + ".tmp")
    log.info(f"Writing save: {save.path}")

    try:
        with zipfile.ZipFile(temp_path, "w") as archive:
            for entry in save.entries:
                archive.writestr(entry.info, entry.text().encode(entry.encoding))

        os.replace(temp_path, save.path)
        os.utime(save.path, ns=(save.accessed_ns, save.modified_ns))
    except OSError as e:
        temp_path.unlink(missing_ok=True)
        raise SaveFileError(f"Unable to write save '{save.path.name}': {e}") from e

    # The file on disk is now this save, so it doesn't count as changed
    save.size = save.path.stat().st_size


# --- Save games folders and backups ---

# TODO: More paths options (such as cloud saves and different distribution platforms support)
# Check the wiki for details
WINDOWS_PARADOX_INTERACTIVE_PATHS = [Path.home() / "Documents" / "Paradox Interactive"]
LINUX_PARADOX_INTERACTIVE_PATHS = [Path.home() / ".local" / "share" / "Paradox Interactive"]
MACOS_PARADOX_INTERACTIVE_PATHS = [Path.home() / "Documents" / "Paradox Interactive"]

SAVE_BACKUPS_FOLDER_NAME = "saves_backup"

# Name of each save backup folder: saves_backup/<playthrough>/<timestamp>/<save file>
SAVE_BACKUP_TIMESTAMP_FORMAT = "%Y-%m-%d %H-%M-%S"


def get_save_games_folders(game_name: str) -> list[Path]:
    """
    The save games folder of `game_name`, remembered in its settings.

    1. The folder saved in settings, if it still exists.
    2. Otherwise, one found on disk or all choices if multiple exist. Must be checked afterwards.

    Empty list when no folder was found.
    """
    game_settings = services().settings.game(game_name)

    saved = game_settings.save_games_folder
    if saved and Path(saved).is_dir():
        log.info(f"Got save games folder from settings: {saved}", silent=True)
        return [Path(saved)]

    found = _search_save_games_folders(game_name)

    if not found:
        log.warning(f"No save games folder found for {game_name}.")

    return found


def _search_save_games_folders(game_name: str) -> list[Path]:
    """Every "save games" folder of `game_name` in the known Paradox Interactive folders of this system."""
    if not game_name:
        return []

    if os_windows():
        potential_paths = WINDOWS_PARADOX_INTERACTIVE_PATHS
    elif os_linux():
        potential_paths = LINUX_PARADOX_INTERACTIVE_PATHS
    elif os_darwin():
        potential_paths = MACOS_PARADOX_INTERACTIVE_PATHS
    else:
        potential_paths = []

    # Folders named after the game
    game_folders: list[Path] = []
    for path in potential_paths:
        game_folder = path / game_name
        if game_folder.is_dir() and game_folder not in game_folders:
            game_folders.append(game_folder)

    log.info(f"Look into folder(s): {game_folders}")

    save_games_folders: list[Path] = []
    for game_folder in game_folders:
        for folder in game_folder.rglob("**/save games/"):
            if folder not in save_games_folders:
                save_games_folders.append(folder)

    log.info(f"Found the following save games folder(s): {save_games_folders}")
    return save_games_folders


def save_backups_folder() -> Path:
    """Where saves are backed up before they're fixed, in the app's config folder."""
    return services().config.config_dir / SAVE_BACKUPS_FOLDER_NAME


@dataclass
class SaveBackup:
    """One save backup: a timestamped folder holding the save file(s) as they were before a fix."""

    playthrough: str
    folder: Path
    created: datetime.datetime
    files: list[Path] = field(default_factory=list)
    size: int = 0


def backup_save(save_file: Path | str, backup_base_dir: Path | str | None = None) -> Path:
    """
    Copy `save_file` to `<backups folder>/<playthrough>/<timestamp>/<save file>`. Returns the copy's path.
    Raises SaveFileError if it can't.
    """
    save_file = Path(save_file)

    if backup_base_dir is None:
        backup_base_dir = save_backups_folder()

    timestamp_str = datetime.datetime.now().strftime(SAVE_BACKUP_TIMESTAMP_FORMAT)
    backup_dir = Path(backup_base_dir) / save_file.parent.name / timestamp_str
    backup_file = backup_dir / save_file.name

    try:
        log.info(f"Creating backup: {backup_file}")
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(save_file, backup_file)
    except OSError as e:
        raise SaveFileError(f"Unable to back up '{save_file.name}': {e}") from e

    log.info(f"Successfully backed up {save_file.name}")
    return backup_file


def find_save_backups(backup_base_dir: Path | str | None = None) -> dict[str, list[SaveBackup]]:
    """
    Save backups made when fixing saves, by playthrough folder name.

    Playthroughs with the newest backup come first, and each playthrough's backups are newest first.
    """
    base_dir = Path(backup_base_dir) if backup_base_dir else save_backups_folder()

    if not base_dir.is_dir():
        log.debug(f"No save backups folder: '{base_dir}'")
        return {}

    by_playthrough: dict[str, list[SaveBackup]] = {}

    try:
        playthrough_dirs = [d for d in base_dir.iterdir() if d.is_dir()]
    except OSError as e:
        log.warning(f"Unable to list save backups in '{base_dir}': {e}")
        return {}

    for playthrough_dir in playthrough_dirs:
        backups: list[SaveBackup] = []

        try:
            backup_dirs = [d for d in playthrough_dir.iterdir() if d.is_dir()]
        except OSError as e:
            log.warning(f"Unable to list save backups in '{playthrough_dir}': {e}")
            continue

        for backup_dir in backup_dirs:
            # Folder name is the backup time, fall back to when the folder was last changed
            try:
                created = datetime.datetime.strptime(backup_dir.name, SAVE_BACKUP_TIMESTAMP_FORMAT)
            except ValueError:
                created = datetime.datetime.fromtimestamp(backup_dir.stat().st_mtime)

            files = sorted(f for f in backup_dir.iterdir() if f.is_file())
            backups.append(
                SaveBackup(
                    playthrough=playthrough_dir.name,
                    folder=backup_dir,
                    created=created,
                    files=files,
                    size=get_fpath_size(backup_dir),
                )
            )

        if backups:
            backups.sort(key=lambda b: b.created, reverse=True)
            by_playthrough[playthrough_dir.name] = backups

    log.debug(f"Found save backups for {len(by_playthrough)} playthrough(s) in '{base_dir}'")

    return dict(sorted(by_playthrough.items(), key=lambda item: item[1][0].created, reverse=True))


def _split_lines(text: str) -> list[str]:
    """
    Lines of `text`, each keeping its "\\n" (and "\\r" on Windows line endings).
    Unlike `str.splitlines()`, only splits on "\\n", so unusual characters in names never split a line.
    """
    parts = text.split("\n")
    lines = [part + "\n" for part in parts[:-1]]

    # Text that doesn't end with a line break has one last line without it
    if parts[-1]:
        lines.append(parts[-1])

    return lines


def _decode(name: str, data: bytes) -> tuple[str, str]:
    """Encoding and text of one file inside the save. Raises SaveFileError for binary files."""
    if b"\x00" in data[:4096]:
        raise SaveFileError(f"'{name}' is a binary file, only text saves are supported")

    try:
        return "utf-8", data.decode("utf-8")
    except UnicodeDecodeError:
        pass

    # Not UTF-8: guess from the start of the file, like `detect_file_encoding` does for files on disk
    detected = chardet.detect(data[:4096]).get("encoding")
    if detected is None:
        raise SaveFileError(f"Unable to tell the text encoding of '{name}'")

    try:
        return detected, data.decode(detected)
    except (UnicodeDecodeError, LookupError) as e:
        raise SaveFileError(f"Unable to read '{name}' as {detected}: {e}") from e


# --- Finding and changing values in the text ---


@dataclass
class Block:
    """Where a key and its value are: from the `key=` line to the line closing its block (the same line for `key=value`)."""

    key: str
    start: int  # Line index of `key=`
    end: int  # Line index of the closing `}`, or `start` for `key=value`
    depth: int = 0  # How many blocks it's inside. 0 is root


def line_key(line: str) -> str:
    """Key of a `key=value` line, or "" if the line has no `=`."""
    stripped = line.strip()
    if "=" not in stripped:
        return ""
    return stripped.split("=", 1)[0]


def line_value(line: str) -> str:
    """Value of a `key=value` line, without quotes. "" for a block (`key=` with `{` on the next line)."""
    stripped = line.strip()
    if "=" not in stripped:
        return ""
    value = stripped.split("=", 1)[1].strip()
    return value.strip('"')


def find_blocks(lines: list[str], key: str, root_only: bool = False) -> list[Block]:
    """Every place `key` appears, in file order. With `root_only`, only those not inside any block."""
    key_eq = f"{key}="
    blocks: list[Block] = []
    # Blocks of `key` whose closing `}` hasn't been reached yet, each with whether its `{` was seen
    open_blocks: list[tuple[Block, bool]] = []
    depth = 0

    for index, line in enumerate(lines):
        stripped = line.strip()
        opens = stripped.count("{")
        closes = stripped.count("}")

        # Quick text check first before running on every line of a big save
        is_key_line = key_eq in stripped and line_key(line) == key
        if is_key_line and (depth == 0 or not root_only):
            block = Block(key=key, start=index, end=index, depth=depth)
            value = line_value(line)

            if value and "{" not in value:
                # `key=value`, ends on this line
                blocks.append(block)
            else:
                open_blocks.append((block, False))

        depth += opens - closes

        still_open = []
        for block, opened in open_blocks:
            if opens > 0 or depth > block.depth:
                opened = True

            # A block ends once its `{` was seen and the depth is back to where its `key=` line was
            if opened and depth <= block.depth:
                block.end = index
                blocks.append(block)
            else:
                still_open.append((block, opened))
        open_blocks = still_open

    # Order by where they start because blocks close before the blocks around them
    blocks.sort(key=lambda b: b.start)
    return blocks


def find_root_block(lines: list[str], key: str) -> Optional[Block]:
    """First `key` at root, or None."""
    blocks = find_blocks(lines, key, root_only=True)
    if not blocks:
        return None
    return blocks[0]


def find_key_in_block(lines: list[str], block: Block, key: str) -> Optional[int]:
    """Line index of the first `key=` directly inside `block` (not inside a block within it), or None."""
    depth = 0

    for index in range(block.start, block.end + 1):
        line = lines[index]

        # Directly inside the block means one level deeper than its `key=` line
        if depth == 1 and line_key(line) == key:
            return index

        stripped = line.strip()
        depth += stripped.count("{") - stripped.count("}")

    return None


def find_key(lines: list[str], key: str, inside: Optional[Block] = None) -> Optional[int]:
    """Line index of the first `key=` at root, or directly inside the block `inside`. None if missing."""
    if inside is not None:
        return find_key_in_block(lines, inside, key)

    block = find_root_block(lines, key)
    if block is None:
        return None
    return block.start


def get_value(lines: list[str], key: str, inside: Optional[Block] = None) -> Optional[str]:
    """Value of the first `key=` at root, or directly inside the block `inside`. None if missing."""
    index = find_key(lines, key, inside)
    if index is None:
        return None
    return line_value(lines[index])


def block_lines(lines: list[str], block: Block) -> list[str]:
    """The lines of `block`, from its `key=` line to its closing `}`."""
    return lines[block.start : block.end + 1]


def _indent(line: str) -> str:
    """The spaces and tabs at the start of `line`."""
    return line[: len(line) - len(line.lstrip())]


def set_value(lines: list[str], index: int, value: str) -> bool:
    """Change the value of the `key=value` line at `index`, keeping its indentation and line ending. True if it changed."""
    line = lines[index]
    ending = line[len(line.rstrip("\r\n")) :]
    new_line = f"{_indent(line)}{line_key(line)}={value}{ending}"

    if new_line == line:
        return False

    lines[index] = new_line
    return True


def insert_line_after(lines: list[str], index: int, text: str) -> None:
    """Insert `text` as a new line after the line at `index`, with the same indentation."""
    lines.insert(index + 1, f"{_indent(lines[index])}{text}\n")


def append_line(lines: list[str], text: str) -> None:
    """Add `text` as the last line."""
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    lines.append(f"{text}\n")
