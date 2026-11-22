# Original regex pattern patching credit: Melechtna Antelecht
"""
`Patcher`: reads the patterns file and patches game executables with it.

    patcher = Patcher(patterns_file)
    patcher.get_available_games()
    patcher.get_available_patches(configuration)
    patcher.patch_game(configuration, binary_path)

Methods about one game take the `PatchConfiguration` (game, version, platform).

Methods that are given the executable use the platform that file was built for, see `platform_of()`.
"""

import json
import logging
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

from core.paths import FILE_EXTENSION
from patchers import auto_patch, backups
from patchers.models import (
    KEY_VERSION_LATEST,
    GameExecutable,
    PatchConfiguration,
    PatchOutcome,
    PatchPattern,
    Platform,
    PlatformConfig,
)
from patchers.patterns_parser import ParsedPatterns, parse_patterns
from utils.characters import CHAR_CHECKMARK, CHAR_CROSS
from utils.helpers import spread_over_percent

log = logging.getLogger("PDX Patchers")

RESTORE_ORIGINAL_ADVICE = "restore the original executable (a backup or verifying the game files in Steam)"

# {patch name: patch} and {patch name: the scan its checks were found in}
Patches = Dict[str, PatchPattern]
Scans = Dict[str, auto_patch.ScanResult]


class Patcher:
    """Patches game executables, using the games, versions and patches listed in the patterns file."""

    def __init__(self, patterns_file: Path):
        self._patterns_file = Path(patterns_file)
        self.patterns: ParsedPatterns = {}
        self.reload_patterns()

    @property
    def patterns_file(self) -> Path:
        return self._patterns_file

    @patterns_file.setter
    def patterns_file(self, value: Path) -> None:
        old = self._patterns_file
        self._patterns_file = Path(value)
        try:
            self._load_patterns()
        except Exception:
            self._patterns_file = old
            raise

    # ------------------------------------------------------------------------
    # Patterns file: games, versions and patches
    # ------------------------------------------------------------------------

    def _load_patterns(self) -> None:
        """Load the patterns file. If it's missing, the patterns already loaded are kept."""
        if not self.patterns_file.exists():
            log.warning(f"Patterns file not found: {self.patterns_file}", silent=True)
            return

        log.info(f"Loading patterns file: {self.patterns_file}", silent=True)

        patterns_data = json.loads(self.patterns_file.read_bytes())
        self.patterns = parse_patterns(patterns_data)

        log.info(f"Loaded patterns: {json.dumps(patterns_data, indent=2)}", silent=True)

    def reload_patterns(self) -> None:
        """Load the patterns file. If it can't be read, the patterns already loaded are kept."""
        log.info("Reload Patterns...", silent=True)

        try:
            self._load_patterns()
        except (OSError, ValueError, AttributeError, TypeError) as load_err:
            log.error(f"Unable to read patterns file '{self.patterns_file}': {load_err}")

    def get_available_games(self) -> List[str]:
        games = list(self.patterns)
        log.debug(f"Available games: {games}", silent=True)
        return games

    def get_available_versions(self, game: str) -> List[str]:
        """Versions of `game` in the patterns file, in file order."""
        versions = list(self.patterns.get(game, {}))
        log.debug(f"Available versions for '{game}': {versions}", silent=True)
        return versions

    def get_versions_with_patches(self, game: str, platform: Optional[Platform] = None) -> List[str]:
        """Versions of `game` that have at least one patch for `platform`, in patterns-file order."""
        versions = []
        for version in self.get_available_versions(game):
            if self._patches_of(game, version, platform):
                versions.append(version)
        return versions

    def pick_version(
        self, game: str, platform: Optional[Platform] = None, preferred: Optional[str] = None
    ) -> Optional[str]:
        """
        Choose which version of `game` to select.

        Order: `preferred` (saved version), then 'latest', then the first version with patches.
        Only versions with patches for `platform` are considered. Returns None if there are none.
        """
        candidates = self.get_versions_with_patches(game, platform)

        for version in (preferred, KEY_VERSION_LATEST):
            if version and version in candidates:
                return version

        if candidates:
            return candidates[0]
        return None

    def get_available_patches(self, configuration: PatchConfiguration, platform: Optional[Platform] = None) -> Patches:
        """
        {patch name: patch} for the configuration's game and version.
        For the configuration's platform, unless another `platform` is given (ex.: from `platform_of()`).
        """
        if platform is None:
            platform = configuration.platform
        return self._patches_of(configuration.game, configuration.version, platform)

    def get_executable_info(
        self, configuration: PatchConfiguration, platform: Optional[Platform] = None
    ) -> Optional[GameExecutable]:
        """
        File name of the game's executable, and where it is inside a macOS bundle.
        """
        if platform is None:
            platform = configuration.platform

        platform_config = self._platform_config(configuration.game, configuration.version, platform)
        if not platform_config:
            return None

        return GameExecutable(filename=platform_config.exe_filename, path_postfix=platform_config.path_postfix)

    def _platform_configs(self, game: str, version: str) -> Dict[str, PlatformConfig]:
        """
        {platform: config} of `game` at `version`.
        A version that isn't in the patterns file falls back to the game's first version. Empty if there is none.
        """
        if game not in self.patterns:
            log.error(f"Game '{game}' not found in patterns.")
            return {}

        versions = self.patterns[game]
        platform_configs = versions.get(version)

        # Fall back to the first version in the patterns file
        if not platform_configs:
            log.error(f"Version '{version}' not found for game '{game}'. Using fallback.")
            available_versions = list(versions)
            if available_versions:
                log.info(f"Got available versions for '{game}': {available_versions}")
                version = available_versions[0]
                platform_configs = versions[version]

        if not platform_configs:
            log.error(f"Version '{version}' not found for game '{game}'.")
            return {}

        return platform_configs

    def _platform_config(self, game: str, version: str, platform: Optional[Platform]) -> Optional[PlatformConfig]:
        """Config of one platform. None if the platform is unknown or the patterns have nothing for it."""
        # Unknown platforms give None, so no patches, rather than another platform's patches
        platform = Platform.parse(platform)
        return self._platform_configs(game, version).get(platform)

    def _patches_of(self, game: str, version: str, platform: Optional[Platform]) -> Patches:
        """{patch name: patch} of `game` at `version` for `platform` (this computer's platform if None)."""
        if platform is None:
            platform = Platform.detect_current()

        platform_config = self._platform_config(game, version, platform)
        if platform_config:
            return platform_config.patches
        return {}

    # ------------------------------------------------------------------------
    # The executable: the platform and where it is
    # ------------------------------------------------------------------------

    @staticmethod
    def detect_platform(file_path: Path) -> Optional[Platform]:
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

    def platform_of(self, configuration: PatchConfiguration, file_path: Path) -> Platform:
        """
        Platform to patch `file_path` for.
        The one the file was built for (ex.: a Linux binary patched from macOS).
        The configuration's platform (the Native/Proton choice) if the file doesn't tell.
        """
        detected_platform = self.detect_platform(file_path)
        if detected_platform:
            return detected_platform
        return configuration.platform

    def find_executable(self, configuration: PatchConfiguration, install_folder: Optional[Path]) -> Optional[Path]:
        """
        The game executable inside `install_folder`, the game's install folder. None otherwise.
        On macOS, the binary inside the .app bundle.
        """

        exe_info = self.get_executable_info(configuration)
        if not exe_info:
            log.error(f"No executable info for {configuration.game} version {configuration.version}")
            return None

        executable = self._search_for_executable(install_folder, exe_info.filename)
        if executable and exe_info.path_postfix:
            # macOS: inside .app bundle
            executable = executable / exe_info.path_postfix

        return executable

    def find_bundle_root(self, configuration: PatchConfiguration, binary_path: Path) -> Optional[Path]:
        """
        The bundle holding `binary_path` if macOS, using each platform's `path_postfix`.
        None if not in one.
        """
        for platform_config in self._platform_configs(configuration.game, configuration.version).values():
            bundle_root = platform_config.bundle_root(binary_path)
            if bundle_root:
                return bundle_root
        return None

    def find_binary_backups(self, configuration: PatchConfiguration, binary_path: Union[Path, str]) -> List[Path]:
        """Backups the Patcher made of the game binary at `binary_path`, oldest first."""
        binary_path = Path(binary_path)
        return backups.find_backups(binary_path, self.find_bundle_root(configuration, binary_path))

    @staticmethod
    def _search_for_executable(game_install_path: Optional[Path], filename: str) -> Optional[Path]:
        """
        Returns path to the game executable named `filename` (from `get_executable_info()`) inside
        `game_install_path`, the game's install folder. None if it isn't there.
        """
        log.info("Locating game install...")
        log.debug(f"{game_install_path=}")

        if not game_install_path or not game_install_path.exists():
            return None

        # The install folder is the executable itself (ex.: a macOS .app bundle from GOG)
        if game_install_path.name.lower() == filename.lower():
            log.info(f"Auto-located path: '{game_install_path}'")
            return game_install_path

        expected_exe_path = game_install_path / filename
        if expected_exe_path.is_file():
            log.info(f"Auto-located path: '{expected_exe_path}'")
            return expected_exe_path

        # Not where we expected it, search the whole install folder
        for item in game_install_path.rglob("*"):
            if item.name == filename:
                log.info(f"Auto-located path: '{item}'")
                return item.resolve()

        log.warning("Unable to auto-locate game binary. Automatic path detection failed.")
        return None

    def _resolve_binary(self, configuration: PatchConfiguration, file_path: Path, platform: Platform) -> Path:
        """For macOS .app bundles, return the actual binary inside the bundle."""
        if file_path.suffix.lower() == FILE_EXTENSION.APP and file_path.is_dir():
            platform_config = self._platform_config(configuration.game, configuration.version, platform)
            if platform_config and platform_config.path_postfix:
                return file_path / platform_config.path_postfix
        return file_path

    # ------------------------------------------------------------------------
    # Patching
    # ------------------------------------------------------------------------

    def patch_game(
        self,
        configuration: PatchConfiguration,
        file_path: Path,
        use_default_patches: bool = False,
        max_backups: int = backups.DEFAULT_MAX_BACKUPS,
        progress: Optional[Callable[[int, str], None]] = None,
    ) -> PatchOutcome:
        """
        Patch the game executable at `file_path` with the configuration's selected patches.
        Picks the platform and the patches, backs up and patches.
        """
        file_path = Path(file_path)
        log.info(f"Proceeding to patch executable: {file_path}")
        log.info(f"Using configuration: {configuration}", silent=True)

        if not configuration.game:
            log.error("Configuration game is empty")
            return PatchOutcome(platform=configuration.platform)

        # Patch for whatever the selected binary actually is (ex.: Linux binary patched from macOS)
        platform = self.platform_of(configuration, file_path)
        if platform != configuration.platform:
            log.info(f"Selected binary is a {platform.value} executable. Using {platform.value} patches.")

        outcome = PatchOutcome(platform=platform)
        outcome.patches_to_apply = self.pick_patches(configuration, platform, use_default_patches)

        if not outcome.patches_to_apply:
            log.error(f"No patches available for {configuration.game} '{configuration.version}' on {platform}.")
            return outcome

        log.info(f"Patches to apply: {outcome.patches_to_apply}", silent=True)

        if progress:
            progress(10, "Preparing patches")

        outcome.results = self.apply_patches_to_file(
            configuration, file_path, outcome.patches_to_apply, max_backups=max_backups, progress=progress
        )

        for patch_name, success in outcome.results.items():
            if not success:
                log.warning(f"Failed patch: {patch_name}")

        return outcome

    def pick_patches(
        self, configuration: PatchConfiguration, platform: Platform, use_default_patches: bool = False
    ) -> List[str]:
        """
        Pick names of the patches to apply for `platform`. Prioritises `configuration`'s selected patches that
        still exist plus every required patch.

        The Patches on a non-first run and applied to `configuration` on startup or load, so even if the user
        doesn't open the patch configuration window, the selected patches they had applied previously
        will still apply on subsequent runs.

        `use_default_patches`: when none of the selected patches exist (nothing was picked yet or an empty
        `configuration` of patches is present), start from the patches that are enabled by default.
        """
        available_patches = self.get_available_patches(configuration, platform)

        # Ignore saved patch names that no longer exist
        patch_names = [name for name in configuration.selected_patches if name in available_patches]
        outdated_patches = [name for name in configuration.selected_patches if name not in available_patches]
        if outdated_patches:
            log.info(f"Ignoring saved patches that no longer exist: {outdated_patches}", silent=True)

        if not patch_names and use_default_patches:
            patch_names = [name for name, patch in available_patches.items() if patch.enabled]
            log.info(f"No saved patch selection. Using default patches for '{configuration.version}'.")

        # Required patches are always applied, even if not in the selection
        for name, patch in available_patches.items():
            if patch.required and name not in patch_names:
                patch_names.append(name)

        return patch_names

    def apply_patches_to_file(
        self,
        configuration: PatchConfiguration,
        file_path: Path,
        patch_names: List[str],
        max_backups: int = backups.DEFAULT_MAX_BACKUPS,
        progress: Optional[Callable[[int, str], None]] = None,
    ) -> Dict[str, bool]:
        """
        Apply the patches named `patch_names` to the game executable at `file_path`.

        Returns {patch name: success}.
        """
        file_path = Path(file_path)
        platform = self.platform_of(configuration, file_path)
        patches = self.get_available_patches(configuration, platform)

        log.info(f"Attempting to apply {len(patch_names)} patches: {patch_names}")

        if progress:
            progress(20, "Checking existing patches")

        binary = self._resolve_binary(configuration, file_path, platform)
        scans = self._scan_file(binary, patches)
        for error in self._scan_errors(scans):
            log.error(f"✗ Unable to patch '{binary}': {error}")

        status = self._status_from(scans)
        self._log_unselected_patched(status, patch_names, patches)
        patches_to_apply, results = self._check_patches(scans, status, patch_names, patches, platform)

        if not patches_to_apply:
            self._log_nothing_to_apply(results)
            self._log_patch_status(results)
            return results

        if progress:
            progress(40, "Creating backup")

        # Back up the whole bundle (ex.: macOS .app) when the executable is inside one, like `find_binary_backups()` expects
        backup_target = self.find_bundle_root(configuration, file_path)
        if not backup_target:
            backup_target = file_path

        if not backups.create_backup(backup_target, max_backups):
            log.error("Failed to create backup, aborting all patches")
            for patch_name, _ in patches_to_apply:
                results[patch_name] = False
            self._log_patch_status(results)
            return results

        results.update(self._apply_patches_batch(binary, scans, patches_to_apply, progress))

        if progress:
            progress(95, "Checking the result")
        self._confirm_patches(binary, results, patches)

        self._log_patch_status(results)
        return results

    @staticmethod
    def _check_patches(
        scans: Scans, status: Dict[str, bool], patch_names: List[str], patches: Patches, platform: Platform
    ) -> Tuple[List[Tuple[str, PatchPattern]], Dict[str, bool]]:
        """
        Sort `patch_names` into patches still to apply and patches already decided, using `scans` from
        `_scan_file()` and `status` from `_status_from()`.

        Returns (patches to apply, {patch name: success}). Unknown patches and patches whose scan failed have failed,
        already applied ones succeeded.
        """
        patches_to_apply = []
        results = {}

        for patch_name in patch_names:
            patch = patches.get(patch_name)
            log.info(f"{patch=}", silent=True)

            if not patch:
                log.warning(f"Patch '{patch_name}' not found for platform {platform}")
                results[patch_name] = False
                continue

            # The reason was logged in `apply_patches_to_file()`
            if scans[patch_name].error:
                results[patch_name] = False
                continue

            if status.get(patch_name):
                log.info(f"File already patched with '{patch_name}'. Skipping.")
                results[patch_name] = True
                continue

            patches_to_apply.append((patch_name, patch))

        return patches_to_apply, results

    @staticmethod
    def _log_unselected_patched(status: Dict[str, bool], patch_names: List[str], patches: Patches) -> None:
        """
        Patches already in the file but not selected stay applied.
        Patching never restores original code.
        """
        for patch_name, patched in status.items():
            if not patched or patch_name in patch_names:
                continue

            log.warning(
                f"'{patches[patch_name].display_name}' is already patched and stays patched. To undo this, "
                f"{RESTORE_ORIGINAL_ADVICE}, then patch again."
            )

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
                log.info(f"{CHAR_CHECKMARK} {patch_name} already applied.")
            else:
                failed.append(patch_name)
                log.info(f"{CHAR_CROSS} {patch_name} failed to apply.")

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
        binary: Path,
        scans: Scans,
        patches_to_apply: List[Tuple[str, PatchPattern]],
        progress: Optional[Callable[[int, str], None]] = None,
    ) -> Dict[str, bool]:
        """
        Write each patch's unpatched checksum checks.

        Returns {patch name: success}.
        """
        log.info(f"{binary=}", silent=True)
        results = {}
        patches_length = len(patches_to_apply)

        for index, (patch_name, patch) in enumerate(patches_to_apply):

            if progress:
                # Spread patches over 50-95%
                percent = spread_over_percent(patches_length, index, 50, 95)
                progress(percent, f"Applying {patch.display_name}")

            result = scans[patch_name]
            if not self._log_patch_sites(result, patch_name, patch):
                results[patch_name] = False
                continue

            unpatched = [site for site in result.sites_of(patch_name) if not site.patched]
            try:
                auto_patch.patch_sites(binary, unpatched, patch.replacement_bytes)
            except Exception as e:
                log.error(f"✗ Error applying patch '{patch.display_name}': {e}")
                results[patch_name] = False
                continue

            log.info(
                f"{CHAR_CHECKMARK} Applied Patch: '{patch.display_name}' ({len(result.sites_of(patch_name))} checksum checks)"
            )
            results[patch_name] = True

        return results

    def _confirm_patches(self, binary: Path, results: Dict[str, bool], patches: Patches) -> None:
        """Scan `binary` again and set to failed, in `results`, the patches that didn't end up in the file."""
        status = self._patch_status(binary, patches)

        for patch_name, success in results.items():
            if success and not status.get(patch_name):
                log.error(f"✗ '{patch_name}' was written, but the executable doesn't show it as patched.")
                results[patch_name] = False

    @staticmethod
    def _log_patch_sites(result: auto_patch.ScanResult, patch_name: str, patch: PatchPattern) -> bool:
        """Log the checksum checks found for `patch_name` in `result`. Returns False, saying why, if there are none."""
        sites = result.sites_of(patch_name)

        if not sites and result.unconfirmed_of(patch_name):
            # The scan couldn't confirm its calls go to the compare function. See auto_patch._pick_compare_function()
            log.warning(
                f"✗ The checksum checks of '{patch.display_name}' couldn't be confirmed, so they were left alone. "
                f"If the executable is already patched, {RESTORE_ORIGINAL_ADVICE}, then patch with all desired patches."
            )
            return False

        if not sites:
            log.warning(
                f"✗ No checksum checks found for '{patch.display_name}'. If its strings changed in a game update, "
                f"its checks were patched along with the required patch."
            )
            return False

        for site in sites:
            log.info(f"  {site.call_offset:#x}: {site.matched_by}", silent=True)
        return True

    # ------------------------------------------------------------------------
    # Scanning: which checks an executable has, and which are patched
    # ------------------------------------------------------------------------

    def get_patch_status(self, configuration: PatchConfiguration, file_path: Path) -> Dict[str, bool]:
        """
        {patch name: applied} for every patch the game executable at `file_path` can get, from scanning the file.
        A patch is applied when it has checksum checks and all of them are patched.
        """
        file_path = Path(file_path)
        platform = self.platform_of(configuration, file_path)
        patches = self.get_available_patches(configuration, platform)

        binary = self._resolve_binary(configuration, file_path, platform)
        return self._patch_status(binary, patches)

    def scan_data(self, configuration: PatchConfiguration, data: bytes, platform: Optional[Platform] = None) -> Scans:
        """
        Find the checksum checks of each patch in executable `data`. Used by and in report tool.

        Returns {patch name: scan result}, empty if the platform has no patches. Check each result's `error`.
        """
        return self._scan(data, self.get_available_patches(configuration, platform))

    def _patch_status(self, binary: Path, patches: Patches) -> Dict[str, bool]:
        """{patch name: applied} for each of `patches`, from scanning `binary`."""
        scans = self._scan_file(binary, patches)
        for error in self._scan_errors(scans):
            log.error(f"Error checking patch status: {error}")

        status = self._status_from(scans)
        log.debug(f"Patch status of '{binary}': {status}")
        return status

    def _scan_file(self, binary: Path, patches: Patches) -> Scans:
        """`_scan()` for the executable at `binary`. Check each result's `error`."""
        try:
            data = Path(binary).read_bytes()
        except OSError as e:
            unreadable = auto_patch.ScanResult(error=f"Unable to read '{binary}': {e}")
            return dict.fromkeys(patches, unreadable)
        return self._scan(data, patches)

    def _scan(self, data: bytes, patches: Patches) -> Scans:
        """
        Find the checksum checks of each of `patches` in executable `data`.

        Returns {patch name: scan result}. Check each result's `error`.
        Every patch uses its own `target_string` and `replace_call_with`.
        Patches with the same `target_string` share one scan result, in which each
        check is labelled with the patch it belongs to.
        """
        scans = {}

        for target_string, patches_of_string in self._patches_by_target_string(patches).items():
            replacements = [patch.replacement_bytes for patch in patches_of_string.values()]
            rules = {}
            for patch_name, patch in patches_of_string.items():
                rules[patch_name] = patch.site_rule

            result = auto_patch.scan(data, target_string, replacements)
            auto_patch.label_sites(data, result, rules)
            self._mark_patched(data, result, patches_of_string)

            for patch_name in patches_of_string:
                scans[patch_name] = result

        return scans

    @staticmethod
    def _patches_by_target_string(patches: Patches) -> Dict[str, Patches]:
        """
        {
            target_string: {
                patch name: patch
            }
        }

        Patches looking for the same string are found in one scan, and its checks are shared out between them.
        """
        groups = {}
        for patch_name, patch in patches.items():
            groups.setdefault(patch.target_string, {})[patch_name] = patch
        return groups

    @staticmethod
    def _mark_patched(data: bytes, result: auto_patch.ScanResult, patches: Patches) -> None:
        """
        A check is patched when it holds the replacement bytes of the patch it belongs to.
        The scan only knows it holds one of the replacements, which can be another patch's.
        """
        for site in result.sites:
            patch = patches.get(site.patch_name)
            if patch:
                site_bytes = data[site.call_offset : site.call_offset + auto_patch.CALL_LENGTH]
                site.patched = site_bytes == patch.replacement_bytes

    @staticmethod
    def _scan_errors(scans: Scans) -> List[str]:
        """Each different error in `scans`, once. Error is shared for patches that share a scan."""
        errors = []
        for result in scans.values():
            if result.error and result.error not in errors:
                errors.append(result.error)
        return errors

    @staticmethod
    def _status_from(scans: Scans) -> Dict[str, bool]:
        """{patch name: applied} for each patch in `scans`. False if its scan failed."""
        status = {}
        for patch_name, result in scans.items():
            sites = result.sites_of(patch_name)
            status[patch_name] = bool(sites) and all(site.patched for site in sites)
        return status
