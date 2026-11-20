import os
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from core.paths import os_darwin, os_linux, os_windows

# Windows process creation flags: the started process keeps running after the app closes
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200


@dataclass(frozen=True)
class StoreGameInfo:
    """A game's name and ID in one store."""

    name: str
    id: int


class StoreHelperBase(ABC):
    """
    Base for a game store helper (Steam, GOG, ..., Generic). Find, launch and validate a game.

    Each store implements the abstract methods. Code any store can use lives here.
    """

    # Shown after validate_game_files() when the store can't validate on its own. None: nothing to show.
    validate_instructions: Optional[str] = None

    @abstractmethod
    def get_game_install_path(self, game_name: str) -> Optional[Path]:
        """Folder `game_name` is installed in. None if not found."""

    @abstractmethod
    def launch_game(self, game_name: str, binary_path: Optional[Path]) -> None:
        """
        Start `game_name` through the appropriate store.
        `binary_path` is the saved game executable, if any. Stores that start their own install can ignore it (Steam, GOG, ...).
        """

    @abstractmethod
    def validate_game_files(self, game_name: str, binary_path: Optional[Path]) -> bool:
        """
        Ask the store to restore unmodified game files.
        `binary_path` is the saved game executable, if any. False if validation couldn't start.
        """

    def run_detached(self, args: list[str], cwd: Optional[Path] = None) -> None:
        """
        Start `args` as its own process, so it keeps running after the app closes.
        `cwd` is the folder it starts in or the app's own folder when `None`.
        """
        if os_windows():
            subprocess.Popen(args, cwd=cwd, creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP, close_fds=True)
            return

        subprocess.Popen(
            args,
            cwd=cwd,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )

    def open_url(self, url: str) -> None:
        """Open a store URL (ex.: steam://...) with the app the OS has registered for it."""
        if os_windows():
            os.startfile(url)
        elif os_linux():
            self.run_detached(["xdg-open", url])
        elif os_darwin():
            self.run_detached(["open", url])
