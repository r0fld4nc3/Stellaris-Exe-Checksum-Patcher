# Original regex pattern patching credit: Melechtna Antelecht

import datetime
import json
import logging
import re
import shutil
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

from core import services
from core.paths import FILE_EXTENSION
from patchers import auto_patch
from patchers.models import (
    KEY_VERSION_LATEST,
    GameExecutable,
    PatchPattern,
    PatchPatternProperties,
    Platform,
    PlatformConfig,
    PlatformConfigProperties,
)

log = logging.getLogger("PDX Patchers")


class GamePatcher:
    """Patches the executable of a game version, using that version's config from the patterns file."""

    def __init__(self, game_name: str, version_config: Dict):
        self.game_name: str = game_name
        self.config: dict = version_config
        self.platforms: Dict[Platform, PlatformConfig] = self._parse_platforms()
        self.exe_info: Optional[GameExecutable] = None

    # ------------------------------------------------------------------------
    # Patterns config
    # ------------------------------------------------------------------------

    def _parse_platforms(self) -> Dict[Platform, PlatformConfig]:
        """Parse platform configurations from config"""
        platforms = {}

        for platform_key, platform_data in self.config.items():
            platforms[platform_key] = PlatformConfig(
                platform_name=platform_key,
                description=platform_data.get(PlatformConfigProperties.description, "N/A"),
                exe_filename=platform_data.get(PlatformConfigProperties.exe_filename, ""),
                path_postfix=platform_data.get(PlatformConfigProperties.path_postfix, ""),
                patches=self._parse_patches(platform_key, platform_data.get(PlatformConfigProperties.patches, {})),
            )

        log.debug(f"{platforms=}")
        return platforms

    @staticmethod
    def _parse_patches(platform_key: str, patches_data: Dict) -> Dict[str, PatchPattern]:
        patches = {}

        for patch_name, patch_data in patches_data.items():
            if "replace_call_with" not in patch_data:
                # Entry from the old regex-based patterns.json. "Update Patterns" fetches the new format
                log.warning(f"Skipping '{patch_name}' ({platform_key}): outdated patterns file format.")
                continue

            patches[patch_name] = PatchPattern(
                display_name=patch_data.get(PatchPatternProperties.display_name, "N/A"),
                description=patch_data.get(PatchPatternProperties.description, "N/A"),
                required=patch_data.get(PatchPatternProperties.required, False),
                enabled=patch_data.get(PatchPatternProperties.enabled, False),
                checksum_string=patch_data.get(
                    PatchPatternProperties.checksum_string, auto_patch.DEFAULT_CHECKSUM_STRING
                ),
                replace_call_with=patch_data[PatchPatternProperties.replace_call_with],
            )

        return patches

    @staticmethod
    def _platform_or_current(platform: Optional[Platform]) -> Platform:
        if platform is None:
            return Platform.detect_current()
        return platform

    def get_platform_config(self, platform: Platform) -> Optional[PlatformConfig]:
        return self.platforms.get(platform)

    def get_available_patches(self, platform: Optional[Union[Platform, str]] = None) -> Dict[str, PatchPattern]:
        # Unknown platforms give None, so no patches, rather than another platform's patches
        platform = Platform.parse(self._platform_or_current(platform))

        platform_config = self.get_platform_config(platform)
        if platform_config:
            return platform_config.patches
        return {}

    def get_patch(self, patch_name: str, platform: Optional[Platform] = None) -> Optional[PatchPattern]:
        patch = self.get_available_patches(platform).get(patch_name)
        log.info(f"{patch=}", silent=True)
        return patch

    def get_executable_info(self, platform: Optional[Platform] = None) -> Optional[GameExecutable]:
        """Executable info for `platform`. Also remembered in `exe_info` for `locate_game_install()`."""
        platform_config = self.get_platform_config(self._platform_or_current(platform))

        if not platform_config:
            self.exe_info = None
            return None

        self.exe_info = GameExecutable(filename=platform_config.exe_filename, path_postfix=platform_config.path_postfix)
        return self.exe_info

    # ------------------------------------------------------------------------
    # Locating the executable
    # ------------------------------------------------------------------------

    def detect_platform(self, file_path: Path) -> Optional[Platform]:
        """Platform the executable was built for, read from its file format. None if unknown."""
        file_path = Path(file_path)

        if file_path.suffix.lower() == FILE_EXTENSION.APP and file_path.is_dir():
            return Platform.DARWIN

        try:
            file_format = auto_patch.detect_format(file_path)
        except OSError as e:
            log.error(f"Unable to read executable format of '{file_path}': {e}")
            return None

        return Platform.from_file_format(file_format)

    def locate_game_install(self, game_install_path: Optional[Path]) -> Optional[Path]:
        """
        Returns path to game executable inside `game_install_path`, the game's install folder.

        Call `get_executable_info()` first, as it sets which executable to look for.
        """
        log.info("Locating game install...")
        log.debug(f"{game_install_path=}")

        if not game_install_path or not game_install_path.exists():
            return None

        if not self.exe_info:
            log.error(f"No executable info: {self.exe_info=}")
            return None

        # The install folder is the executable itself (ex.: a macOS .app bundle from GOG)
        if game_install_path.name.lower() == self.exe_info.filename.lower():
            log.info(f"Auto-located path: '{game_install_path}'")
            return game_install_path

        expected_exe_path = game_install_path / self.exe_info.filename
        if expected_exe_path.is_file():
            log.info(f"Auto-located path: '{expected_exe_path}'")
            return expected_exe_path

        # Not where we expected it, search the whole install folder
        for item in game_install_path.rglob("*"):
            if item.name == self.exe_info.filename:
                log.info(f"Auto-located path: '{item}'")
                return item.resolve()

        log.warning("Unable to auto-locate game binary. Automatic path detection failed.")
        return None

    def _resolve_binary(self, file_path: Path, platform: Optional[Platform] = None) -> Path:
        """For macOS .app bundles, return the actual binary inside the bundle."""
        if file_path.suffix.lower() == FILE_EXTENSION.APP and file_path.is_dir():
            platform_config = self.get_platform_config(self._platform_or_current(platform))
            if platform_config and platform_config.path_postfix:
                return file_path / platform_config.path_postfix
        return file_path

    # ------------------------------------------------------------------------
    # Backups
    # ------------------------------------------------------------------------

    def _backup_target(self, file_path: Path, platform: Platform) -> Path:
        """
        What to back up before patching `file_path`.
        The whole bundle (ex.: macOS .app) if it's inside one.
        """

        platform_config = self.get_platform_config(platform)
        if not platform_config:
            # Unknown platform
            return file_path

        bundle_root = platform_config.bundle_root(file_path)
        if bundle_root:
            # macOS bundle root path
            return bundle_root

        return file_path

    def _create_backup(self, file_path: Path) -> bool:
        """Create a timestamped backup next to `file_path`, removing the oldest backups over the limit."""
        max_allowed_backups = services().settings.app_settings.max_allowed_binary_backups

        # If max is 0, don't create or delete any backups
        if max_allowed_backups <= 0:
            log.info(f"Backup creation disabled (max_allowed_binary_backups = {max_allowed_backups})", silent=True)
            return True

        self._delete_old_backups(file_path, max_allowed_backups)

        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        backup_path = Path(f"{file_path}-{timestamp_str}.orig")

        try:
            # macOS .app bundles are folders
            if file_path.is_dir():
                if backup_path.exists():
                    shutil.rmtree(backup_path)
                shutil.copytree(file_path, backup_path)
            else:
                shutil.copy2(file_path, backup_path)

            log.info(f"Create backup: {backup_path}")
            return True
        except Exception as e:
            log.error(f"Failed to create backup: {e}")
            return False

    def find_bundle_root(self, binary_path: Path) -> Optional[Path]:
        """The bundle (ex.: macOS .app) holding `binary_path`, using each platform's `path_postfix`. None if not in one."""
        for platform_config in self.platforms.values():
            bundle_root = platform_config.bundle_root(binary_path)
            if bundle_root:
                return bundle_root
        return None

    def find_binary_backups(self, binary_path: Union[Path, str]) -> List[Path]:
        """
        Backups the Patcher made of the game binary at `binary_path`, oldest first.

        Backups sit next to what was backed up and are named after it:
        `<name>-<timestamp>.orig` now, `<name>_<timestamp>.orig` or `<name>.orig` in older versions.
        If the binary is inside a bundle (ex.: macOS .app), the whole bundle is backed up, so its backups are included too.
        """
        binary_path = Path(binary_path)

        targets = [binary_path]
        bundle_root = self.find_bundle_root(binary_path)
        if bundle_root:
            targets.append(bundle_root)

        backups: List[Path] = []
        for target in targets:
            folder = target.parent
            if not folder.is_dir():
                continue

            pattern = re.compile(rf"^{re.escape(target.name)}([-_].+)?\.orig$", re.IGNORECASE)
            try:
                for item in folder.iterdir():
                    if pattern.match(item.name):
                        backups.append(item)
            except OSError as e:
                log.warning(f"Unable to list backups in '{folder}': {e}")

        backups = sorted(set(backups), key=lambda item: item.stat().st_mtime)
        log.debug(f"Binary backups of '{binary_path}': {backups}")
        return backups

    def _delete_old_backups(self, backup_target: Path, max_allowed_backups: int) -> None:
        """Delete the oldest backups of `backup_target` so there is room for one more within `max_allowed_backups`."""
        log.info(f"Deleting backups if reached or over max allowance: {max_allowed_backups}", silent=True)
        log.info(f"Processing backups of: {backup_target}", silent=True)

        # Only backups of this target, so backups of other files in the folder keep their own limit
        backups = self.find_binary_backups(backup_target)

        if len(backups) < max_allowed_backups:
            log.info(f"No backups to delete, found {len(backups)}/{max_allowed_backups}")
            return

        log.info(f"Sorted backups: {backups}", silent=True)

        num_to_keep = max_allowed_backups - 1
        num_to_delete = len(backups) - num_to_keep
        log.info(f"Keep {num_to_keep}, Delete {num_to_delete}", silent=True)

        for backup_item in backups[:num_to_delete]:
            log.info(f"Remove: '{backup_item}", silent=True)
            try:
                # macOS .app backups are folders
                if backup_item.is_dir():
                    shutil.rmtree(backup_item)
                else:
                    backup_item.unlink()
            except Exception as e:
                log.warning(f"Failed to delete backup: '{backup_item}': {e}")

    # ------------------------------------------------------------------------
    # Patching
    # ------------------------------------------------------------------------

    def patch_file_multiple(
        self,
        file_path: Path,
        patch_names: List[str],
        platform: Optional[Platform] = None,
        create_backup: bool = True,
        progress: Optional[Callable[[int, str], None]] = None,
    ) -> Dict[str, bool]:
        """
        Apply multiple patches to a file in a single operation.

        `progress` is called with (percent, text) before each step, if provided.

        Returns:
            dict: where `key` is patch name and `value` is `bool` status whether it succeeded or failed to apply.
        """
        platform = self._platform_or_current(platform)
        file_path = Path(file_path)

        log.info(f"Attempting to apply {len(patch_names)} patches: {patch_names}")

        if progress:
            progress(20, "Checking existing patches")

        patches_to_apply, results = self._check_patches(file_path, patch_names, platform)

        if not patches_to_apply:
            self._log_nothing_to_apply(results)
            self._log_patch_status(results)
            return results

        if create_backup:
            if progress:
                progress(40, "Creating backup")

            if not self._create_backup(self._backup_target(file_path, platform)):
                log.error("Failed to create backup, aborting all patches")
                for patch_name, _ in patches_to_apply:
                    results[patch_name] = False
                self._log_patch_status(results)
                return results

        results.update(self._apply_patches_batch(file_path, patches_to_apply, platform, progress))

        self._log_patch_status(results)
        return results

    def _check_patches(
        self,
        file_path: Path,
        patch_names: List[str],
        platform: Platform,
        progress: Optional[Callable[[int, str], None]] = None,
    ) -> Tuple[List[Tuple[str, PatchPattern]], Dict[str, bool]]:
        """
        Sort `patch_names` into patches still to apply and patches already decided.

        Returns (patches to apply, {patch name: success}). Unknown patches have failed, already applied ones succeeded.
        """
        patches_to_apply = []
        results = {}

        for index, patch_name in enumerate(patch_names):
            patch = self.get_patch(patch_name, platform)

            # Spread patches over 40-50%
            percent = 40 + 10 * index // len(patch_names)
            if progress:
                progress(percent, patch_name)

            if not patch:
                log.warning(f"Patch '{patch_name}' not found for platform {platform}")
                results[patch_name] = False
                continue

            if self.is_patched(file_path, patch_name, platform):
                log.info(f"File already patched with '{patch_name}'; skipping.")
                results[patch_name] = True
                continue

            patches_to_apply.append((patch_name, patch))

        return patches_to_apply, results

    @staticmethod
    def _log_nothing_to_apply(results: Dict[str, bool]) -> None:
        """
        Summarise why nothing was patched.
        Everything was already applied, or patches were not found.
        """
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

    @staticmethod
    def _log_patch_status(results: Dict[str, bool]) -> None:
        log.info(f"Patch status: {json.dumps(results, indent=2)}", silent=True)

    def _apply_patches_batch(
        self,
        file_path: Path,
        patches: List[Tuple[str, PatchPattern]],
        platform: Platform,
        progress: Optional[Callable[[int, str], None]] = None,
    ) -> Dict[str, bool]:
        """Apply each patch to the file. Returns {patch name: success}."""
        binary = self._resolve_binary(file_path, platform)
        log.info(f"{binary=}", silent=True)

        results = {}

        for index, (patch_name, patch) in enumerate(patches):
            if progress:
                # Spread patches over 50-95%
                percent = 50 + 45 * index // len(patches)
                progress(percent, f"Applying {patch_name}")

            results[patch_name] = self._apply_patch(binary, patch, patch_name)

        return results

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

        platform = self._platform_or_current(platform)
        patch = self.get_patch(patch_name, platform)
        if not patch:
            return False

        try:
            data = self._resolve_binary(Path(file_path), platform).read_bytes()
            return auto_patch.scan(data, patch.checksum_string, patch.replacement_bytes).fully_patched
        except Exception as e:
            log.error(f"Error checking patch status: {e}")
            return False


class MultiGamePatcher:
    """Main class used for patching the binary. Used to determine and return a `GamePatcher` instance."""

    def __init__(self, patterns_file: Path):
        self.patterns_file = Path(patterns_file)
        self.patterns_config: Dict = {}
        self.games: List[str] = []
        self._load_patterns()

    def _load_patterns(self) -> Dict:
        """Load the patterns file. If it's missing, the patterns already loaded are kept."""
        if not self.patterns_file.exists():
            log.warning(f"Patterns file not found: {self.patterns_file}", silent=True)
            return {}

        log.info(f"Loading patterns file: {self.patterns_file}", silent=True)

        self.patterns_config = json.loads(self.patterns_file.read_bytes())
        self.games = list(self.patterns_config.keys())

        log.info(f"Loaded patterns: {json.dumps(self.patterns_config, indent=2)}", silent=True)
        return self.patterns_config

    def reload_patterns(self) -> Dict:
        log.info("Reload Patterns...", silent=True)
        return self._load_patterns()

    def get_available_games(self) -> List[str]:
        log.debug(f"Available games: {self.games}", silent=True)
        return self.games

    def get_available_versions(self, game_name: str) -> List[str]:
        """Get available versions for a specific game"""
        game_config = self.patterns_config.get(game_name) or {}
        versions = list(game_config.keys())
        log.debug(f"Available versions for '{game_name}': {versions}", silent=True)
        return versions

    def get_game_patcher(self, game_name: str, version: str = KEY_VERSION_LATEST) -> Optional[GamePatcher]:
        log.debug(f"Get game patcher for game: '{game_name}': '{version}'", silent=True)

        if game_name not in self.games:
            log.error(f"Game '{game_name}' not found in patterns.")
            return None

        game_config: dict = self.patterns_config.get(game_name, {})
        version_config = game_config.get(version)

        # Fall back to the first version in the patterns file
        if not version_config:
            log.error(f"Version '{version}' not found for game '{game_name}'. Using fallback.")
            versions = self.get_available_versions(game_name)
            if versions:
                log.info(f"Got available versions for '{game_name}': {versions}")
                version = versions[0]
                version_config = game_config.get(version)

        if not version_config:
            log.error(f"Version '{version}' not found for game '{game_name}'.")
            return None

        log.debug(f"Got version '{version}' config.", silent=True)
        log.debug(json.dumps(version_config, indent=2), silent=True)
        return GamePatcher(game_name=game_name, version_config=version_config)

    def get_available_patches_for_game(
        self, game_name: str, version: str = KEY_VERSION_LATEST, platform: Optional[Platform] = None
    ) -> Dict[str, PatchPattern]:
        log.debug(f"Getting available patches for '{game_name}': '{version}' on platform: {platform}", silent=True)

        patcher = self.get_game_patcher(game_name, version=version)
        if patcher:
            return patcher.get_available_patches(platform)
        return {}

    def get_versions_with_patches(self, game_name: str, platform: Optional[Platform] = None) -> List[str]:
        """Versions of `game_name` that have at least one patch for `platform`, in patterns-file order."""
        return [
            version
            for version in self.get_available_versions(game_name)
            if self.get_available_patches_for_game(game_name, version, platform)
        ]

    def pick_version(
        self, game_name: str, platform: Optional[Platform] = None, preferred: Optional[str] = None
    ) -> Optional[str]:
        """
        Choose which version of `game_name` to select.

        Order: `preferred` (ex.: the saved version), then 'latest', then the first version with patches.
        Only versions with patches for `platform` are considered. Returns None if there are none.
        """
        candidates = self.get_versions_with_patches(game_name, platform)

        for version in (preferred, KEY_VERSION_LATEST):
            if version and version in candidates:
                return version

        return candidates[0] if candidates else None
