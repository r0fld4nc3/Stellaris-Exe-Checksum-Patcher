import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from core.paths import OS_TYPE, os_windows, system
from patchers.auto_patch import FILE_FORMAT

log = logging.getLogger("Patcher Models")

KEY_VERSION_LATEST = "latest"


class TRANSLATION_LAYER_ENUM(str, Enum):
    NATIVE = "Native"
    PROTON = "Proton"


class Platform(str, Enum):
    """
    Platform values for the application's own data. These values can be
    similar to `OS_TYPE` but their similarity is coincidental.

    These values are mapped against `OS_TYPE` returns to correctly
    pull required data from the patters file.
    """

    WINDOWS = "windows"
    LINUX = "linux"
    DARWIN = "darwin"

    @classmethod
    def detect_current(cls) -> "Platform":
        platfrom_by_os = {OS_TYPE.WINDOWS: cls.WINDOWS, OS_TYPE.LINUX: cls.LINUX, OS_TYPE.DARWIN: cls.DARWIN}
        return platfrom_by_os.get(system(), cls.WINDOWS)

    @classmethod
    def from_file_format(cls, file_format: Optional[str]) -> Optional["Platform"]:
        """Platform an executable of `file_format` (from `auto_patch.detect_format()`) is built for. None if unknown."""
        platforms_by_file_format = {
            FILE_FORMAT.PE: cls.WINDOWS,
            FILE_FORMAT.ELF: cls.LINUX,
            FILE_FORMAT.MACHO: cls.DARWIN,
        }
        return platforms_by_file_format.get(file_format)

    @classmethod
    def parse(cls, value) -> Optional["Platform"]:
        """Platform from an enum or a string such as "windows" or "linux". None if empty or unknown."""
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value)) if value else None
        except ValueError as e:
            log.error("Error parsing Platform from Enum.")
            log.error(f"{e}", silent=True)
            return None


@dataclass
class PatchPatternProperties:
    """
    Represents properties that can be obtained from the `PatchPattern` class.

    Usage example:

    ```
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
    ```
    """

    display_name: str = "display_name"
    description: str = "description"
    required: str = "required"
    enabled: str = "enabled"
    checksum_string: str = "checksum_string"
    replace_call_with: str = "replace_call_with"


@dataclass
class PatchPattern:
    """
    One patch from patterns.json. See patchers.auto_patch for how it is applied.

    checksum_string:   Regex for the official checksum string stored in the executable.
    replace_call_with: Hex bytes written over each `CALL strcmp` that uses that string (must be 5 bytes).
    """

    display_name: str
    description: str
    required: bool
    enabled: bool
    checksum_string: str
    replace_call_with: str

    @property
    def replacement_bytes(self) -> bytes:
        return bytes.fromhex(self.replace_call_with)


@dataclass
class PatchConfiguration:
    """Holds the complete user-selected patch configuration"""

    game: str
    version: str = KEY_VERSION_LATEST
    # Platform of the binary to patch. A Windows binary on Linux/macOS runs through Proton.
    platform: Platform = field(default_factory=Platform.detect_current)
    selected_patches: List[str] = field(default_factory=list)

    @property
    def is_proton(self) -> bool:
        """Patching the Windows binary on Linux/macOS (run through Proton)."""
        return not os_windows() and self.platform == Platform.WINDOWS

    @classmethod
    def create_default(cls, patcher, game: str = None) -> Optional["PatchConfiguration"]:
        """Latest version of `game` (or the first available game) for the native binary. None if no games."""
        games = patcher.get_available_games()
        selected_game = game or (games[0] if games else None)

        if not selected_game:
            log.error("No games available")
            return None

        return cls(game=selected_game)


@dataclass
class PlatformConfigProperties:
    """
    Represents properties that can be obtained from the `PlatformConfig` class.

    Usage example:

    ```
    for platform_key, platform_data in self.config.items():
        platforms[platform_key] = PlatformConfig(
            platform_name=platform_key,
            description=platform_data.get(PlatformConfigProperties.description, "N/A"),
            exe_filename=platform_data.get(PlatformConfigProperties.exe_filename, ""),
            path_postfix=platform_data.get(PlatformConfigProperties.path_postfix, ""),
            patches=self._parse_patches(platform_key, platform_data.get(PlatformConfigProperties.patches, {})),
        )
    ```
    """

    platform_name: str = "platform_name"
    description: str = "description"
    exe_filename: str = "exe_filename"
    path_postfix: str = "path_postfix"
    patches: str = "patches"


@dataclass
class PlatformConfig:
    """Represents platform-specific configuration"""

    platform_name: str
    description: str
    exe_filename: str
    path_postfix: str
    patches: Dict[str, PatchPattern]

    def bundle_root(self, binary_path: Path) -> Optional[Path]:
        """
        The app bundle folder holding `binary_path`, found by removing `path_postfix` from its end.

        Ex.: `Stellaris.app/Contents/MacOS/stellaris` with postfix `Contents/MacOS/stellaris` -> `Stellaris.app`.
        None if this platform has no `path_postfix` or `binary_path` doesn't end with it.
        """
        if not self.path_postfix:
            return None

        # Go up one folder for each part of the postfix: Contents/MacOS/stellaris -> 3 folders up
        fp_parts = len(Path(self.path_postfix).parts)
        if fp_parts > len(binary_path.parents):
            return None

        bundle_root = binary_path.parents[fp_parts - 1]

        # Only a bundle if the binary is at `path_postfix` inside it
        if bundle_root / self.path_postfix != binary_path:
            return None

        return bundle_root


@dataclass
class GameExecutable:
    """Represents a game executable information"""

    filename: str
    path_postfix: str

    def get_full_path(self, base_path: Path) -> Path:
        """Get the full path to the executable"""
        if self.path_postfix:
            # For macOS .app bundles with internal paths
            return base_path / self.filename / self.path_postfix
        return base_path / self.filename
