# built-ins
import logging
from pathlib import Path
from typing import Optional

from core import services
from core.paths import os_darwin, os_windows
from utils import registry_helper

from .base import StoreHelperBase
from .definitions import GameStore

log = logging.getLogger("GOG Helper")

# KEY_LOCAL_MACHINE. GOG Galaxy is 32-bit, keys are under WOW6432Node
GOG_GAMES_REGISTRY_PATH = r"SOFTWARE\WOW6432Node\GOG.com\Games"  # + "\<game id>"
GOG_GALAXY_REGISTRY_PATH = r"SOFTWARE\WOW6432Node\GOG.com\GalaxyClient\paths"
GOG_GAME_PATH_KEY = "path"
GOG_GALAXY_CLIENT_KEY = "client"

GOG_GALAXY_EXECUTABLE_WINDOWS = "GalaxyClient.exe"
# Every GOG install has this file in the folder, like Steam's steam_appid.txt
GOG_GAME_INFO_FILE_NAME = "goggame-{game_id}.info"

GOG_GALAXY_OPEN_GAME_URL = "goggalaxy://openGameView/{game_id}"

# Where GOG Galaxy installs games when the user doesn't pick a folder
GOG_DEFAULT_GAMES_FOLDERS_WINDOWS = [Path(r"C:\Program Files (x86)\GOG Galaxy\Games")]
GOG_DEFAULT_GAMES_FOLDERS_MACOS = [Path("/Applications")]
GOG_GALAXY_DEFAULT_PATH_MACOS = Path("/Applications/GOG Galaxy.app")


class GogHelper(StoreHelperBase):
    # Galaxy has no command to start Verify / Repair. Must be manually triggered.
    validate_instructions = "In GOG Galaxy, click More > Manage installation > Verify / Repair."

    # --- Game ID ---

    def get_known_game_id(self, game_name: str) -> Optional[str]:
        """GOG game ID for `game_name` from known game IDs. `None` if unknown."""
        gog_info = GameStore.GOG.game_info(game_name)
        if not gog_info:
            return None

        return str(gog_info.id)

    # --- GOG Galaxy ---

    def get_gog_galaxy_install_path(self) -> Optional[Path]:
        """GOG Galaxy's saved folder. Otherwise, found on this system. Else `None`."""
        log.info("Acquiring GOG Galaxy installation...")

        saved_path_str = services().settings.app_settings.gog_install_path
        if saved_path_str:
            saved_path = Path(saved_path_str)
            if saved_path.exists():
                log.info(f"Got GOG Galaxy install path from Settings: '{saved_path_str}'")
                return saved_path

        galaxy_path: Optional[Path] = None
        if os_windows():
            galaxy_path_str = registry_helper.read_key(GOG_GALAXY_REGISTRY_PATH, GOG_GALAXY_CLIENT_KEY)
            if galaxy_path_str:
                galaxy_path = Path(galaxy_path_str)
        elif os_darwin():
            galaxy_path = GOG_GALAXY_DEFAULT_PATH_MACOS

        if not galaxy_path or not galaxy_path.exists():
            log.error("Unable to acquire GOG Galaxy installation.")
            return None

        services().settings.app_settings.gog_install_path = galaxy_path.resolve().as_posix()
        return galaxy_path

    def get_windows_gog_galaxy_executable(self) -> Optional[Path]:
        if not os_windows():
            return None

        galaxy_path = self.get_gog_galaxy_install_path()
        if not galaxy_path:
            return None

        galaxy_exe = galaxy_path / GOG_GALAXY_EXECUTABLE_WINDOWS
        if not galaxy_exe.is_file():
            log.warning(f"GOG Galaxy executable not found: {galaxy_exe}")
            return None

        return galaxy_exe

    def open_game_view(self, game_id: str) -> None:
        galaxy_url = GOG_GALAXY_OPEN_GAME_URL.format(game_id=game_id)
        log.info(f"Opening GOG Galaxy URL: {galaxy_url}", silent=True)

        try:
            self.open_url(galaxy_url)
        except Exception as e:
            log.error(f"Error opening GOG Galaxy: {e}")

    # --- Install folder ---

    def get_game_install_path(self, game_name: str) -> Optional[Path]:
        log.info(f"Acquiring {game_name} installation...")

        game_id = self.get_known_game_id(game_name)
        if not game_id:
            log.error(f"Unable to find GOG game ID for: {game_name}")
            return None

        registry_path = self.get_registry_game_install_path(game_id)
        if registry_path:
            return registry_path

        for folder in self.get_default_game_folders(game_name):
            if self.is_game_install_folder(folder, game_id):
                log.info(f"Found game install in: {folder.as_posix()}")
                return folder

        log.error(f"Unable to determine installation folder for {game_name}")
        return None

    def get_registry_game_install_path(self, game_id: str) -> Optional[Path]:
        """Install folder GOG Galaxy saved for `game_id` in the Windows registry. None elsewhere, or if not found."""
        if not os_windows():
            return None

        game_key_path = f"{GOG_GAMES_REGISTRY_PATH}\\{game_id}"
        install_path_str = registry_helper.read_key(game_key_path, GOG_GAME_PATH_KEY)
        if not install_path_str:
            return None

        install_path = Path(install_path_str)
        if not install_path.is_dir():
            log.warning(f"Install folder from the registry does not exist: {install_path}")
            return None

        log.info(f"Found game install in the registry: {install_path.as_posix()}")
        return install_path

    def get_default_game_folders(self, game_name: str) -> list[Path]:
        """Folders GOG installs `game_name` to by default on OS."""
        if os_windows():
            return [games_folder / game_name for games_folder in GOG_DEFAULT_GAMES_FOLDERS_WINDOWS]

        # TODO: Linux support here once the devs make it available.

        if os_darwin():
            return [games_folder / f"{game_name}.app" for games_folder in GOG_DEFAULT_GAMES_FOLDERS_MACOS]

        return []

    def is_game_install_folder(self, folder: Path, game_id: str) -> bool:
        """True if `folder` has GOG info file for `game_id`."""
        if not folder.is_dir():
            return False

        info_file_name = GOG_GAME_INFO_FILE_NAME.format(game_id=game_id)
        if (folder / info_file_name).is_file():
            return True

        # macOS: file somewhere inside .app bundle
        info_files = folder.rglob(info_file_name)
        return next(info_files, None) is not None

    # --- Launch and Validate ---

    def launch_game(self, game_name: str, binary_path: Optional[Path]) -> None:
        # Known store starts its own install of the game, so binary_path isn't needed
        game_id = self.get_known_game_id(game_name)
        if not game_id:
            log.error(f"Unable to find GOG game ID for: {game_name}")
            return

        log.info(f"Launching GOG Game with id: {game_id}")

        galaxy_exe = self.get_windows_gog_galaxy_executable()
        if not galaxy_exe:
            # No GalaxyClient.exe
            self.open_game_view(game_id)
            return

        galaxy_args = [str(galaxy_exe), "/command=runGame", f"/gameId={game_id}"]
        log.info(f"GOG Galaxy Launch Command: {galaxy_args}", silent=True)

        try:
            self.run_detached(galaxy_args)
        except Exception as e:
            log.error(f"Error launching game: {e}")

    def validate_game_files(self, game_name: str, binary_path: Optional[Path]) -> bool:
        game_id = self.get_known_game_id(game_name)
        if not game_id:
            log.error(f"Unable to determine GOG game ID for '{game_name}'. Validation aborted.")
            return False

        log.info(f"Opening GOG Galaxy to verify game ID: {game_id}")
        self.open_game_view(game_id)
        return True
