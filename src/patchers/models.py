import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional

from conf_globals import LOG_LEVEL, OS
from logger import create_logger

log = create_logger("Patcher Models", LOG_LEVEL)

CONST_VERSION_LATEST_KEY = "latest"


class TRANSLATION_LAYER_ENUM:
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
    required: bool
    enabled: bool
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


# ============================================================================
# Save Patch Option Models
# ============================================================================


class SavePatchOptionType(Enum):
    """Types of save patch options available"""

    BOOLEAN = "boolean"  # On/Off toggle
    CHOICE = "choice"  # Multiple choice selection
    TEXT = "text"  # Text input


@dataclass
class SavePatchOption:
    """Represents a single patch option for a game"""

    id: str  # Unique id, e.g., "set_ironman_yes", "fix_achievements"
    display_name: str
    description: str
    option_type: SavePatchOptionType.BOOLEAN
    default_value: bool = False
    enabled: bool = True
    choices: List[str] = field(default_factory=list)  # For CHOICE types

    def __post_init__(self):
        """Validate options configuration"""
        if self.option_type == SavePatchOptionType.CHOICE and not self.choices:
            raise ValueError(f"SavePatchOption '{self.id}' of type CHOICE must have choices")


@dataclass
class GameSavePatchConfig:
    """Configuration for game-specific patching"""

    game_name: str
    display_name: str
    description: str
    patch_options: list[SavePatchOption]

    def get_option(self, option_id: str) -> Optional[SavePatchOption]:
        return next((opt for opt in self.patch_options if opt.id == option_id), None)

    def set_enabled(self, option_id: str, enabled: bool) -> Optional[SavePatchOption]:
        for opt in self.patch_options:
            if opt.id != option_id:
                continue

            opt.enabled = enabled

    def is_enabled(self, option_id: str) -> bool:
        option = self.get_option(option_id)

        return option.enabled if option else False

    def get_available_options(self) -> List[SavePatchOption]:
        return [opt for opt in self.patch_options]

    def get_enabled_options(self) -> List[SavePatchOption]:
        return [opt for opt in self.patch_options if opt.enabled]


# ============================================================================
# Game-Specific Configurations
# ============================================================================


def create_stellaris_config() -> GameSavePatchConfig:
    return GameSavePatchConfig(
        game_name="Stellaris",
        display_name="Stellaris Save Patch",
        description="Repair Stellaris save files",
        patch_options=[
            SavePatchOption(
                id="update_achievements",
                display_name="Update Achievements",
                description="Update achievement list to latest version from remote source.",
                option_type=SavePatchOptionType.BOOLEAN,
                default_value=True,
                enabled=True,
            ),
            SavePatchOption(
                id="set_ironman_yes",
                display_name="Convert to Ironman",
                description="Enable Ironman mode in the save file.",
                option_type=SavePatchOptionType.BOOLEAN,
                default_value=False,
                enabled=True,
            ),
            SavePatchOption(
                id="set_ironman_no",
                display_name="Convert to Regular Save",
                description="Convert the Ironman save file back to a regular save.",
                option_type=SavePatchOptionType.BOOLEAN,
                default_value=False,
                enabled=True,
            ),
            SavePatchOption(
                id="convert_ironman",
                display_name="Force Convert to Ironman",
                description="Force ironman flag such that the save file now becomes an Ironman save. Last resort option in case converting to ironman did not work.",
                option_type=SavePatchOptionType.BOOLEAN,
                default_value=False,
                enabled=True,
            ),
        ],
    )


# ============================================================================
# Configuration Registry
# ============================================================================


class SavePatchConfigRegistry:
    """Centralised registry from games save patches configuration"""

    _configs: Dict[str, Callable[[], GameSavePatchConfig]] = {
        "Stellaris": create_stellaris_config,
        # Add more game names as required. Also don't forget a dedicated method to create their config
    }

    @classmethod
    def get_config(cls, game_name: str) -> Optional[GameSavePatchConfig]:
        config_factory = cls._configs.get(game_name)
        if config_factory:
            return config_factory()
        return None

    @classmethod
    def get_supported_games(cls) -> List[str]:
        return list(cls._configs.keys())

    @classmethod
    def register_game(cls, game_name: str, config_factory: Callable[[], GameSavePatchConfig]):
        cls._configs[game_name] = config_factory

    @classmethod
    def is_game_supported(cls, game_name: str) -> bool:
        return game_name in cls._configs
