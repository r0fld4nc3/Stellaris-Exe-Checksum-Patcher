import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar, Dict, List, Optional

from core.paths import OS_TYPE, os_windows, system
from patchers.auto_patch import FILE_FORMAT, SiteRule

log = logging.getLogger("Patcher Models")

KEY_VERSION_LATEST = "latest"


class TRANSLATION_LAYER_ENUM(str, Enum):
    NATIVE = "Native"
    PROTON = "Proton"


class Platform(str, Enum):
    """
    Platform values for the application's own data. These values can be similar to `OS_TYPE` but their similarity is coincidental.

    These values are mapped against `OS_TYPE` returns to correctly pull required data from the patters file.
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
class PatchPattern:
    """
    One patch from patterns.json. See patchers.auto_patch for how it is applied.

    target_string:             Regex for the string whose comparisons are patched (the official checksum in Stellaris).
    replace_call_with:         Hex bytes written over each `CALL strcmp` that uses that string (must be 5 bytes).
    site_rule:                 How to tell this patch's checks apart from the others'. See `auto_patch.label_sites()`.
        near_strings:          Game strings close to this patch's checksum checks. Used to tell the checks apart.
        site_overrides:        {build checksum: [call offsets]}. Fallback sites for that exact build, when strings fail.
        takes_unmatched_sites: Also patch checks that no other patch's strings or overrides match.
    """

    display_name: str
    display_name_key: ClassVar[str] = "display_name"

    description: str
    description_key: ClassVar[str] = "description"

    required: bool
    required_key: ClassVar[str] = "required"

    enabled: bool
    enabled_key: ClassVar[str] = "enabled"

    target_string: str
    target_string_key: ClassVar[str] = "target_string"

    replace_call_with: str
    replace_call_with_key: ClassVar[str] = "replace_call_with"

    # Keys of `site_rule`'s fields. They sit at the top level of each patch in the patterns file
    near_strings_key: ClassVar[str] = "near_strings"
    site_overrides_key: ClassVar[str] = "site_overrides"
    takes_unmatched_sites_key: ClassVar[str] = "takes_unmatched_sites"

    site_rule: SiteRule = field(default_factory=SiteRule)

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
class PatchOutcome:
    """What `Patcher.patch_game()` did."""

    platform: Platform  # Platform the executable was patched for, read from the file
    patches_to_apply: List[str] = field(default_factory=list)  # Patch names that were applied. Empty if none.
    results: Dict[str, bool] = field(default_factory=dict)  # {patch name: success}. Empty if nothing was tried

    @property
    def any_applied(self) -> bool:
        return any(self.results.values())


@dataclass
class PlatformConfig:
    """Represents platform-specific configuration"""

    platform_name: str  # The platform's key in the patterns file (ex.: "windows"), not a value inside it

    description: str
    description_key: ClassVar[str] = "description"

    exe_filename: str
    exe_filename_key: ClassVar[str] = "exe_filename"

    path_postfix: str
    path_postfix_key: ClassVar[str] = "path_postfix"

    patches: Dict[str, PatchPattern]
    patches_key: ClassVar[str] = "patches"

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
