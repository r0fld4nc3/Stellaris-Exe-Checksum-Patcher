# Original regex pattern patching credit: Melechtna Antelecht

import datetime
import json
import logging
import shutil

from app_services import services
from config.definitions import FILE_FORMAT
from config.path_helpers import os_darwin, system
from patchers import auto_patch, models

from .models import *

from pathlib import Path  # isort: skip
from typing import Optional, Dict, List, Union  # isort: skip

log = logging.getLogger("PDX Patchers")  # isort: skip


class GamePatcher:
    """Base class for game patchers"""

    def __init__(self, game_name: str, version_config: Dict, logger=log):
        self.game_name: str = game_name
        self.logger = logger
        self.config: dict = version_config
        self.platforms: dict = self._parse_platforms()
        self.exe_info: GameExecutable = None

    def _parse_platforms(self) -> Dict[Platform, PlatformConfig]:
        """Parse platform configurations from config"""

        platforms = {}

        for platform_key, platform_data in self.config.items():
            # Maps platform keys to enum values

            platform_enum = platform_key

            # Parse patches for this platform
            patches = {}
            for patch_name, patch_data in platform_data.get("patches", {}).items():
                if "replace_call_with" not in patch_data:
                    # Entry from the old regex-based patterns.json; "Update Patterns" fetches the new format
                    log.warning(f"Skipping '{patch_name}' ({platform_key}): outdated patterns file format.")
                    continue

                patches[patch_name] = PatchPattern(
                    display_name=patch_data.get("display_name", "N/A"),
                    description=patch_data.get("description", "N/A"),
                    required=patch_data.get("required", False),
                    enabled=patch_data.get("enabled", False),
                    checksum_string=patch_data.get("checksum_string", auto_patch.DEFAULT_CHECKSUM_STRING),
                    replace_call_with=patch_data["replace_call_with"],
                )

            platforms[platform_enum] = PlatformConfig(
                platform_name=platform_key,
                description=platform_data.get("description", "N/A"),
                exe_filename=platform_data.get("exe_filename", ""),
                path_postfix=platform_data.get("path_postfix", ""),
                patches=patches,
            )

            log.debug(f"{platforms=}")

        return platforms

    def get_platform_config(self, platform: Platform) -> Optional[PlatformConfig]:
        return self.platforms.get(platform)

    def get_available_patches(self, platform: Optional[Union[Platform, str]] = None) -> Dict[str, PatchPattern]:
        if platform is None:
            platform = models.Platform.detect_current()
        elif isinstance(platform, str):
            try:
                platform = platform.lower()
            except ValueError:
                self.logger.error(f"Invalid platform string: '{platform}'")
                return {}

        platform_config = self.get_platform_config(platform)
        if platform_config:
            return platform_config.patches
        return {}

    def get_patch(self, patch_name: str, platform: Optional[Platform] = None) -> Optional[PatchPattern]:
        if platform is None:
            platform = models.Platform.detect_current()

        patches = self.get_available_patches(platform)

        patch = patches.get(patch_name)

        log.info(f"{patch=}", silent=True)

        return patch

    def get_executable_info(self, platform: Optional[Platform] = None) -> Optional[GameExecutable]:
        if platform is None:
            platform = models.Platform.detect_current()

        platform_config = self.get_platform_config(platform)
        if platform_config:
            game_executable = GameExecutable(
                filename=platform_config.exe_filename, path_postfix=platform_config.path_postfix
            )

            self.exe_info = game_executable

            return game_executable

        self.exe_info = None
        return None

    def detect_platform(self, file_path: Path) -> Optional[Platform]:
        """Platform the executable was built for, read from its file format. None if unknown."""
        file_path = Path(file_path)

        if file_path.suffix.lower() == ".app" and file_path.is_dir():
            return Platform.DARWIN

        try:
            file_format = auto_patch.detect_format(file_path)
        except OSError as e:
            log.error(f"Unable to read executable format of '{file_path}': {e}")
            return None

        return {
            FILE_FORMAT.PE: Platform.WINDOWS,
            FILE_FORMAT.ELF: Platform.LINUX,
            FILE_FORMAT.MACHO: Platform.DARWIN,
        }.get(file_format)

    def _create_backup(self, file_path: Path) -> bool:
        """Create a backup of the file"""

        # If max is 0, don't create or delete any backups
        max_allowed_backups = services().settings.settings.max_allowed_binary_backups

        if max_allowed_backups <= 0:
            log.info(f"Backup creation disabled (max_allowed_binary_backups = {max_allowed_backups})", silent=True)
            return True

        if os_darwin():
            if file_path.is_dir() and ".app" in file_path.name.lower():
                binary_dir = file_path.parent
            else:
                binary_dir = file_path.parent
        else:
            binary_dir: Path = file_path.parent if file_path.is_file() else file_path

        self._delete_backups(binary_dir)

        # Backup with timestamp
        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        backup_path = Path(str(file_path) + f"-{timestamp_str}.orig")

        try:
            # Handle macOS .app directories
            if file_path.is_dir():
                if backup_path.exists():
                    shutil.rmtree(backup_path)
                shutil.copytree(file_path, backup_path)
            else:
                shutil.copy2(file_path, backup_path)

            self.logger.info(f"Create backup: {backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return False

    def _delete_backups(self, backup_directory: Path) -> None:
        max_allowed_backups = services().settings.settings.max_allowed_binary_backups

        log.info(f"Deleting backups if reached or over max allowance: {max_allowed_backups}", silent=True)
        log.info(f"Processing backup directory: {backup_directory}", silent=True)

        # If max is 0, don't create or delete any backups
        if max_allowed_backups <= 0:
            log.info(f"Backup deletion disabled (max_allowed_binary_backups = {max_allowed_backups})", silent=True)
            return

        # Collect backups
        backups: list[Path] = []
        for item in backup_directory.iterdir():
            if ".orig" in item.name.lower():
                backups.append(item)

        if len(backups) >= max_allowed_backups:
            backups.sort(key=lambda x: x.stat().st_mtime)

            log.info(f"Sorted backups: {backups}", silent=True)

            num_to_keep = max(0, max_allowed_backups - 1)
            num_to_delete = len(backups) - num_to_keep

            log.info(f"Keep {num_to_keep}, Delete {num_to_delete}", silent=True)

            for backup_item in backups[:num_to_delete]:
                log.info(f"Remove: '{backup_item}", silent=True)
                try:
                    if os_darwin():
                        shutil.rmtree(backup_item)
                    else:
                        backup_item.unlink()
                except Exception as e:
                    log.warning(f"Failed to delete backup: '{backup_item}': {e}")
        else:
            log.info(f"No backups to delete, found {len(backups)}/{max_allowed_backups}")

    def locate_game_install(self) -> Optional[Path]:
        """
        Returns path to game executable.
        """
        log.info("Locating game install...")

        game_install_path = services().steam_helper.get_game_install_path(self.game_name)

        log.debug(f"{game_install_path=}")

        if not game_install_path or game_install_path is None:
            return None

        if not game_install_path.exists():
            return None

        # Check the executable actually exists
        if not self.exe_info:
            log.error(f"No executable info: {self.exe_info=}")
            return None

        speculative_exe_path = game_install_path / self.exe_info.filename

        if speculative_exe_path.is_file() and speculative_exe_path.exists():
            log.info(f"Auto-located path: '{speculative_exe_path}'")
            return speculative_exe_path

        # Doesn't exist, glob for it
        for item in game_install_path.rglob("*"):
            if item.name == self.exe_info.filename:
                log.info(f"Auto-located path: '{item}'")
                return item.resolve()

        log.warning(f"Unable to auto-locate game binary. Automatic path detection failed.")

        return None

    def patch_file_multiple(
        self, file_path: Path, patch_names: List[str], platform: Optional[Platform] = None, create_backup: bool = True
    ) -> dict[str, bool]:
        """
        Apply multiple patches to a file in a single operation

        Returns:
            dict: where `key` is patch name and `value` is `bool` status whether it succeeded or failed to apply.
        """

        if platform is None:
            platform = models.Platform.detect_current()

        log.info(f"Attempting to apply {len(patch_names)} patches: {patch_names}")

        # Enforce file_path type
        if not isinstance(file_path, Path):
            file_path = Path(file_path)

        # Collect patches and validate
        patches_to_apply = []
        results = {}

        # Pre checks
        for patch_name in patch_names:
            patch = self.get_patch(patch_name, platform)
            if not patch:
                log.warning(f"Patch '{patch_name}' not found for platform {platform}")
                results[patch_name] = False
                continue

            # Check if already patched
            if self.is_patched(file_path, patch_name, platform):
                log.info(f"File already patched with '{patch_name}'; skipping.")
                results[patch_name] = True
                continue

            patches_to_apply.append((patch_name, patch))

        # If not patches to apply, return
        if not patches_to_apply:
            applied = []
            failed = []

            for patch_name, success in results.items():
                if success:
                    applied.append(patch_name)
                    log.info(f"✓ {patch_name} already applied.")
                else:
                    failed.append(patch_name)
                    log.info(f"x {patch_name} failed to apply.")

            if applied and not failed:
                log.info("No patches to apply (all already applied).")
            elif failed and not applied:
                log.error("All patches failed.")
            else:
                log.warning("General failure to apply patches.")

            log.info(f"Patch status: {json.dumps(results, indent=2)}", silent=True)
            return results

        if create_backup:
            if platform == Platform.DARWIN and not file_path.suffix.lower() == ".exe":
                # Backup the .app folder, not the binary content inside
                backup_success = self._create_backup(file_path.parent.parent.parent)
            else:
                backup_success = self._create_backup(file_path)

            if not backup_success:
                log.error("Failed to create backup, aborting all patches")
                for patch_name, _ in patches_to_apply:
                    results[patch_name] = False
                log.info(f"Patch status: {json.dumps(results, indent=2)}", silent=True)
                return results

        # Apply all patches in a single operation
        batch_results = self._apply_patches_batch(file_path, patches_to_apply, platform)

        results.update(batch_results)

        log.info(f"Patch status: {json.dumps(results, indent=2)}", silent=True)

        return results

    def _resolve_binary(self, file_path: Path, platform: Optional[Platform] = None) -> Path:
        """For macOS .app bundles, return the actual binary inside the bundle."""
        if file_path.suffix.lower() == ".app" and file_path.is_dir():
            exe_info = self.get_executable_info(platform)
            if exe_info and exe_info.path_postfix:
                return file_path / exe_info.path_postfix
        return file_path

    def _apply_patches_batch(
        self, file_path: Path, patches: List[tuple[str, PatchPattern]], platform: Platform
    ) -> Dict[str, bool]:
        """Apply each patch to the file. Returns {patch name: success}."""
        binary = self._resolve_binary(file_path, platform)
        log.info(f"{binary=}", silent=True)
        return {patch_name: self._apply_patch(binary, patch, patch_name) for patch_name, patch in patches}

    def _apply_patch(self, binary: Path, patch: PatchPattern, patch_name: str) -> bool:
        """Find every checksum comparison in `binary` and patch it. See patchers.auto_patch."""
        log.info(f"Applying patch: {patch_name}")
        try:
            result = auto_patch.patch_file(binary, patch.checksum_string, patch.replacement_bytes)
        except Exception as e:
            log.error(f"✗ Error applying patch '{patch_name}': {e}")
            return False

        if result.error:
            log.error(f"✗ Failed to apply patch '{patch_name}': {result.error}")
            return False

        log.info(
            f"✓ Applied Patch: '{patch_name}' ({len(result.sites)} checksum checks, official checksum {result.checksum})"
        )
        return True

    def patch_file(
        self, file_path: Path, patch_name: str, platform: Optional[Platform] = None, create_backup: bool = True
    ) -> bool:
        """Apply a single patch to the specified file."""
        return self.patch_file_multiple(file_path, [patch_name], platform, create_backup).get(patch_name, False)

    def is_patched(self, file_path: Path, patch_name: str, platform: Optional[Platform] = None) -> bool:
        log.info(f"Checking if patched: {patch_name}")

        if platform is None:
            platform = models.Platform.detect_current()

        patch = self.get_patch(patch_name, platform)
        if not patch:
            return False

        try:
            data = self._resolve_binary(Path(file_path), platform).read_bytes()
            return auto_patch.scan(data, patch.checksum_string, patch.replacement_bytes).fully_patched
        except Exception as e:
            self.logger.error(f"Error checking patch status: {e}")
            return False


class MultiGamePatcher:
    """Main class used for patching the binary. Used to determine and return a `GamePatcher` instance."""

    def __init__(self, patterns_file: Path, logger=log):
        self.patterns_file = patterns_file
        self.logger = logger
        self.patterns_config = self._load_patterns()
        self.games = list(self.patterns_config.keys())

    def _load_patterns(self) -> Dict:
        if not isinstance(self.patterns_file, Path):
            self.patterns_file = Path(self.patterns_file)

        if not self.patterns_file.exists():
            return {}

        self.logger.info(f"Loading patterns file: {self.patterns_file}", silent=True)

        with open(self.patterns_file, "r") as f:
            f = json.load(f)
            self.patterns_config = f
            self.games = list(self.patterns_config.keys())
            return f

    def reload_patterns(self) -> Dict:
        log.info(f"Reload Patterns...", silent=True)
        return self._load_patterns()

    def get_available_games(self) -> List[str]:
        self.logger.info(f"Available games: {self.games}", silent=True)
        return self.games

    def get_available_versions(self, game_name: str) -> List[str]:
        """Get available versions for a specific game"""
        game_config: dict = self.patterns_config.get(game_name)

        if game_config:
            versions = list(game_config.keys())
            if versions:
                self.logger.info(f"Available versions for '{game_name}': {versions}", silent=True)
                return versions
        return []

    def get_game_patcher(self, game_name: str, version: str = KEY_VERSION_LATEST) -> Optional[GamePatcher]:
        self.logger.info(f"Get game patcher for game: '{game_name}': '{version}'", silent=True)

        if game_name not in self.games:
            self.logger.error(f"Game '{game_name}' not found in patterns.")
            return None

        game_config: dict = self.patterns_config.get(game_name, {})
        version_config = game_config.get(version)

        # Let's fallback to first version we see
        if not version_config:
            self.logger.error(f"Version '{version}' not found for game '{game_name}'. Using fallback.")
            versions = self.get_available_versions(game_name)
            if versions:
                log.info(f"Got available versions for '{game_name}': {versions}")
                version = versions[0]  # Override
                version_config = game_config.get(versions[0])

        if not version_config:
            self.logger.error(f"Version '{version}' not found for game '{game_name}'.")
            return None
        else:
            self.logger.info(f"Got version '{version}' config.", silent=True)
            self.logger.debug(json.dumps(version_config, indent=2), silent=True)

        return GamePatcher(game_name=game_name, version_config=version_config)

    def get_available_patches_for_game(
        self, game_name: str, version: str = KEY_VERSION_LATEST, platform: Optional[Platform] = None
    ) -> Dict[str, PatchPattern]:

        platform_str = platform if platform else "None"

        self.logger.info(
            f"Getting available patches for '{game_name}': '{version}' {'on ' + platform_str if platform else ''}",
            silent=True,
        )
        patcher = self.get_game_patcher(game_name, version=version)
        if patcher:
            return patcher.get_available_patches(platform)
        return {}
