import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List

from conf_globals import LOG_LEVEL, OS
from logger import create_logger

log = create_logger("Patcher Models", LOG_LEVEL)

CONST_VERSION_LATEST_KEY = "latest"


class LINUX_VERSIONS_ENUM:
    NATIVE = "Native"
    PROTON = "Proton"


# Also stated in patterns.py - keep in sync or import from there
class Platform(Enum):
    WINDOWS = "windows"
    LINUX_NATIVE = "linux"
    LINUX_PROTON = "linux_proton"  # Maps to windows in patterns
    MACOS = "macos"

    @classmethod
    def detect_current(cls) -> "Platform":
        if OS.LINUX:
            return cls.LINUX_NATIVE
        elif OS.WINDOWS:
            return cls.WINDOWS
        elif OS.MACOS:
            return cls.MACOS
        else:
            return cls.WINDOWS  # Default


@dataclass
class PatchPattern:
    """Represents a patch pattern"""

    display_name: str
    description: str
    hex_find: str
    hex_replace: str
    patch_pattern: str

    def compile_regex(self) -> re.Pattern:
        """Compile the regex pattern with the hex_find value"""
        pattern_string = self.patch_pattern.replace("%s", self.hex_find)
        return re.compile(pattern_string, re.IGNORECASE)


@dataclass
class PatchConfiguration:
    """Holds the complete user-selected patch configuration"""

    game: str
    version: str
    is_proton: bool
    selected_patches: List[str] = field(default_factory=list)

    @classmethod
    def create_default(cls, patcher, game: str = None) -> "PatchConfiguration":
        games = patcher.get_available_games()
        selected_game = game or (games[0] if games else None)

        if not selected_game:
            raise ValueError("No games available")

        return cls(
            game=selected_game,
            version=CONST_VERSION_LATEST_KEY,
            platform=(OS.WINDOWS or OS.LINUX_PROTON),
            selected_patches=[],
        )

    def with_game(self, game: str) -> "PatchConfiguration":
        return PatchConfiguration(
            game=game, version=CONST_VERSION_LATEST_KEY, is_proton=self.is_proton, selected_patches=[]
        )


@dataclass
class PlatformConfig:
    """Represents platform-specific configuration"""

    platform_name: str
    description: str
    exe_filename: str
    path_postfix: str
    patches: Dict[str, PatchPattern]


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
