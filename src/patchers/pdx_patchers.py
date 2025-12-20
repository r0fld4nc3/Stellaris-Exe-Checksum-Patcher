# Regex Pattern Patching Credit: Melechtna Antelecht

import binascii
import datetime
import json
import mmap
import platform
import re
import shutil

from .models import *

from pathlib import Path  # isort: skip
from typing import Optional, Dict, List  # isort: skip

from conf_globals import LOG_LEVEL, OS, STEAM  # isort: skip
from logger import create_logger  # isort: skip

log = create_logger("PDX Patchers", LOG_LEVEL)  # isort: skip


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
            if platform_key == Platform.WINDOWS.value:
                platform_enum = Platform.WINDOWS
            elif platform_key == Platform.LINUX_NATIVE.value:
                platform_enum = Platform.LINUX_NATIVE
            elif platform_key == Platform.MACOS.value:
                platform_enum = Platform.MACOS
            else:
                # Skip unknown platforms
                continue

            # Parse patches for this platform
            patches = {}
            for patch_name, patch_data in platform_data.get("patches", {}).items():
                patches[patch_name] = PatchPattern(
                    display_name=patch_data.get("display_name", "N/A"),
                    description=patch_data.get("description", "N/A"),
                    required=patch_data.get("required", False),
                    enabled=patch_data.get("enabled", False),
                    hex_find=patch_data.get("hex_find", ""),
                    hex_replace=patch_data.get("hex_replace", ""),
                    patch_pattern=patch_data.get("patch_pattern", ""),
                )

            platforms[platform_enum] = PlatformConfig(
                platform_name=platform_key,
                description=platform_data.get("description", "N/A"),
                exe_filename=platform_data.get("exe_filename", ""),
                path_postfix=platform_data.get("path_postfix", ""),
                patches=patches,
            )

        # Linux Proton uses Windows configuration
        if Platform.WINDOWS in platforms:
            platforms[Platform.LINUX_PROTON] = platforms[Platform.WINDOWS]

        return platforms

    def get_platform_config(self, platform: Platform) -> Optional[PlatformConfig]:
        return self.platforms.get(platform)

    def get_available_patches(self, platform: Optional[Platform] = None) -> Dict[str, PatchPattern]:
        if platform is None:
            platform = self.detect_platform()

        platform_config = self.get_platform_config(platform)
        if platform_config:
            return platform_config.patches
        return {}

    def get_patch(self, patch_name: str, platform: Optional[Platform] = None) -> Optional[PatchPattern]:
        if platform is None:
            platform = self.detect_platform()

        patches = self.get_available_patches(platform)

        patch = patches.get(patch_name)

        log.info(f"{patch=}", silent=True)

        return patch

    def get_executable_info(self, platform: Optional[Platform] = None) -> Optional[GameExecutable]:
        if platform is None:
            platform = self.detect_platform()

        platform_config = self.get_platform_config(platform)
        if platform_config:
            game_executable = GameExecutable(
                filename=platform_config.exe_filename, path_postfix=platform_config.path_postfix
            )

            self.exe_info = game_executable

            return game_executable

        self.exe_info = None
        return None

    def detect_platform(self) -> Platform:
        system = platform.system().lower()

        if system == Platform.WINDOWS.value:
            return Platform.WINDOWS
        elif system == Platform.LINUX_NATIVE.value:
            return Platform.LINUX_NATIVE
        elif system == "darwin":
            return Platform.MACOS
        else:
            raise ValueError(f"Unsupported platform: {system}")

    def _create_backup(self, file_path: Path) -> bool:
        """Create a backup of the file"""

        # Backup with timestamp
        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        backup_path = Path(str(file_path) + f"_{timestamp_str}.orig")

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

    def locate_game_install(self) -> Optional[Path]:
        """
        Returns path to game executable.
        """
        log.info("Locating game install...")

        game_install_path = STEAM.get_game_install_path(self.game_name)

        log.debug(f"{game_install_path=}")

        if not game_install_path.exists():
            return None

        # Check the executable actually exists
        if not self.exe_info:
            log.error(f"No executable info: {self.exe_info=}")
            return None

        speculative_exe_path = game_install_path / self.exe_info.filename

        if speculative_exe_path.is_file() and speculative_exe_path.exists():
            log.info(f"Auto-located path: {speculative_exe_path}")
            return speculative_exe_path

        # Doesn't exist, glob for it
        for item in game_install_path.rglob("*"):
            if item.name == self.exe_info.filename:
                log.info(f"Auto-located path: {item}")
                return item.resolve()

        log.warning(f"Unable to auto-locate game binary. Automatic path detection failed.")

        return None

    def patch_file_multiple(
        self, file_path: Path, patch_names: List[str], platform: Optional[Platform] = None, create_backup: bool = True
    ):
        """
        Apply multiple patches to a file in a single operation
        """

        if platform is None:
            platform = self.detect_platform()

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
                log.warning(f"Patch '{patch_name}' not found for platform {platform.value}")
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
            if not self._create_backup(file_path):
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

    def _apply_patches_batch(
        self, file_path: Path, patches: List[tuple[str, PatchPattern]], platform: Platform
    ) -> Dict[str, bool]:
        """
        Dispatcher to apply multiple patches to a file in a single memory mapped session.
        """

        try:
            # Handle macOS .app bundles
            actual_file = file_path
            if file_path.suffix.lower() == ".app" and file_path.is_dir():
                exe_info = self.get_executable_info(platform)
                if exe_info and exe_info.path_postfix:
                    actual_file = file_path / exe_info.path_postfix

            log.info(f"{actual_file=}", silent=True)

            with open(actual_file, "r+b") as f:
                with mmap.mmap(f.fileno(), 0) as mm:
                    original_hex = binascii.hexlify(mm).decode()
                    patched_hex = original_hex  # Original working copy and comparison

                    results = {}
                    all_patches_applied = []

                    # Apply each patch
                    for patch_name, pattern in patches:
                        log.info(f"Applying patch: {patch_name}")

                        # Apply patch to current hex string
                        temp_hex, applied = self._apply_patch_to_hex(patched_hex, pattern, patch_name)
                        results[patch_name] = applied

                        if applied:
                            log.info(f"✓ Applied Patch: '{patch_name}'")
                            patched_hex = temp_hex
                            all_patches_applied.append((patch_name, pattern))
                        else:
                            log.error(f"✗ Failed to apply patch: {patch_name}")
                            # Optionally, continue with other patches or rollback all changes

                    # Commit the changes
                    # If we made it here, all patches were successful
                    if patched_hex != original_hex:
                        log.info(f"Writing all {len(all_patches_applied)} patches to file")

                        # Convert back to binary and write once
                        binary_data_patched = binascii.unhexlify(patched_hex)
                        mm[:] = binary_data_patched
                        mm.flush()

                        log.info("Finished applying patches.")

                        # Save info about patches (optional)
                        for patch_name, pattern in all_patches_applied:
                            log.info(f"✓ {patch_name} applied", silent=True)
                    else:
                        log.warning("No changes made to file")

                    return results

        except Exception as e:
            log.error(f"Critical error occurred while applying patches: {e}")
            return {patch_name: False for patch_name, _ in patches}

    def _apply_patch_to_hex(self, binary_hex: str, pattern: PatchPattern, patch_name: str) -> tuple[str, bool]:
        try:
            regex = pattern.compile_regex()
            match = regex.search(binary_hex)

            if not match:
                log.info(f"Pattern not found for patch: {patch_name}")
                return binary_hex, False

            matched_line = binary_hex[match.start() : match.end()]
            log.info(f"MATCHED BYTES: {matched_line.upper()}", silent=True)
            log.info(f"MATCH POSITION: {match.start()}", silent=True)
            hex_index = matched_line.upper().rfind(pattern.hex_find.upper())

            if hex_index == -1:
                log.error(f"Cannot find '{pattern.hex_find}' in matched pattern for patch: {patch_name}")
                return binary_hex, False

            patched_line = (
                matched_line[:hex_index]
                + pattern.hex_replace.lower()
                + matched_line[hex_index + len(pattern.hex_find) :]
            )

            log.info(f"Patch '{patch_name}' - Original: {matched_line.upper()}", silent=True)
            log.info(f"Patch '{patch_name}' - Patched:  {patched_line.upper()}", silent=True)

            # Apply to the full hex string
            binary_hex_patched = binary_hex[: match.start()] + patched_line + binary_hex[match.end() :]

            return binary_hex_patched, True
        except Exception as e:
            log.error(f"Error applying patch '{patch_name}': {e}")
            return binary_hex, False

    def patch_file(
        self, file_path: Path, patch_name: str, platform: Optional[Platform] = None, create_backup: bool = True
    ) -> bool:
        """
        Apply patch to the specified file
        """

        if platform is None:
            platform = self.detect_platform()

        log.info(f"Attempting to patch: {patch_name}")

        patch = self.get_patch(patch_name, platform)
        log.info(f"{patch=}", silent=True)
        if not patch:
            self.logger.error(f"Patch '{patch_name}' not found for platform {platform.value}")
            return False

        # Enforce file_path type
        if not isinstance(file_path, Path):
            file_path = Path(file_path)

        # Check if file is patched
        if self.is_patched(file_path, patch_name, platform=platform):
            log.info(f"File {file_path.name} has already been patched with {patch_name}")
            return True

        # Create backup if requested
        if create_backup:
            if not self._create_backup(file_path):
                return False

        # Apply the patch
        return self._apply_patch(file_path, patch)

    def _apply_patch(self, file_path: Path, pattern: PatchPattern) -> bool:
        """Apply a patch pattern to a file"""
        try:
            # For macOS, handle the actual binary inside the .app
            actual_file = file_path
            if file_path.suffix.lower() == ".app" and file_path.is_dir():
                exe_info = self.get_executable_info()
                if exe_info and exe_info.path_postfix:
                    actual_file = file_path / exe_info.path_postfix

            regex = pattern.compile_regex()

            with open(actual_file, "r+b") as f:
                with mmap.mmap(f.fileno(), 0) as mm:
                    binary_hex = binascii.hexlify(mm).decode()

                    match = regex.search(binary_hex)
                    if not match:
                        self.logger.info(f"Pattern found in file")
                        return False

                    matched_line = binary_hex[match.start() : match.end()]
                    hex_index = matched_line.upper().rfind(pattern.hex_find.upper())

                    if hex_index == -1:
                        self.logger.error(f"Cannot find '{pattern.hex_find}' in matched pattern")
                        return False

                    # Replace 'hex_find' with 'hex_replace' before 'hex_find'
                    patched_line = (
                        matched_line[:hex_index]
                        + pattern.hex_replace.lower()
                        + matched_line[hex_index + len(pattern.hex_find) :]
                    )

                    log.info(f"Patched hex: {str(patched_line).upper()}")

                    # Apply the patch
                    binary_hex_patched = binary_hex[: match.start()] + patched_line + binary_hex[match.end() :]

                    # Convert the patched binary hex back to binary
                    binary_data_patched = binascii.unhexlify(binary_hex_patched)

                    # Write the patched binary data back to the file
                    log.info(f"Writing changes to file {file_path}")
                    mm[:] = binary_data_patched
                    mm.flush()

                    log.info("Patch applied successfully.")
                    return True
        except Exception as e:
            self.logger.error(f"Error applying patch: {e}")
            return False

    def is_patched(self, file_path: Path, patch_name: str, platform: Optional[Platform] = None) -> bool:
        log.info(f"Checking if patched: {patch_name}")

        if platform is None:
            platform = self.detect_platform()

        patch = self.get_patch(patch_name, platform)
        if not patch:
            return False

        try:
            # Handle macOS .app
            actual_file = file_path
            if file_path.suffix.lower() == ".app" and file_path.is_dir():
                exe_info = self.get_executable_info(platform)
                if exe_info and exe_info.path_postfix:
                    actual_file = file_path / exe_info.path_postfix

            with open(actual_file, "rb") as f:
                binary_hex = binascii.hexlify(f.read()).decode()

            # Create pattern with replaced value
            check_pattern = patch.patch_pattern.replace("%s", patch.hex_replace)
            regex = re.compile(check_pattern, re.IGNORECASE)

            return regex.search(binary_hex) is not None
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
        return self._load_patterns()

    def get_available_games(self) -> List[str]:
        self.logger.info(f"Available games: {self.games}", silent=True)
        return self.games

    def get_available_versions(self, game_name: str, version: str = CONST_VERSION_LATEST_KEY) -> List[str]:
        """Get available versions for a specific game"""
        game_config: dict = self.patterns_config.get(game_name)

        if game_config:
            versions = list(game_config.keys())
            if versions:
                self.logger.info(f"Available versions for '{game_name}': {versions}", silent=True)
                return versions
        return []

    def get_game_patcher(self, game_name: str, version: str = CONST_VERSION_LATEST_KEY) -> Optional[GamePatcher]:
        self.logger.info(f"Get game patcher for game: '{game_name}': '{version}'", silent=True)

        if game_name not in self.games:
            self.logger.error(f"Game '{game_name}' not found in patterns.")
            return None

        game_config: dict = self.patterns_config.get(game_name, {})
        version_config = game_config.get(version)

        # Let's fallback to first version we see
        if not version_config:
            self.logger.error(f"Version '{version}' not found for game '{game_name}'. Using fallback.")
            versions = self.get_available_versions(game_name, version)
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
        self, game_name: str, version: str = CONST_VERSION_LATEST_KEY, platform: Optional[Platform] = None
    ) -> Dict[str, PatchPattern]:
        self.logger.info(
            f"Getting available patches for '{game_name}': '{version}' {platform if platform is not None else ''}",
            silent=True,
        )
        patcher = self.get_game_patcher(game_name, version=version)
        if patcher:
            return patcher.get_available_patches(platform)
        return {}
