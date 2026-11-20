import logging
import random
from enum import Enum
from functools import cache
from pathlib import Path
from typing import Optional

from PySide6.QtGui import QFontDatabase, QIcon

log = logging.getLogger("Resource Manager")

# --- Base Paths ---
# Determines root path for resources
BASE_PATH = Path(__file__).parent
ICONS_PATH = BASE_PATH / "icons"
FONTS_PATH = BASE_PATH / "fonts"
STYLES_PATH = BASE_PATH / "styles"
GUIDES_PATH = BASE_PATH / "guides"


class IconAchievementState(str, Enum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"


class AppIcon(str, Enum):
    WINDOW_WIN = "checksum_patcher_icon.ico"
    WINDOW_UNIX = "checksum_patcher_icon.png"
    PATCH_ICON = "patch_icon.png"
    SAVE_PATCH_ICON = "save_patch_icon.png"
    CONFIGURE_ICON = "configure_icon_big.png"


class AppFont(str, Enum):
    ORBITRON_BOLD = "Orbitron-Bold.ttf"


class AppStyle(str, Enum):
    STELLARIS = "stellaris"
    CK3 = "ck3"


class AppGuide(str, Enum):
    FAQ = "faq.md"
    WELCOME = "welcome.md"


@cache
def load_guide(guide: AppGuide) -> str:
    """Markdown text of a guide shown in the app. Empty if the file is missing."""
    file_path = GUIDES_PATH / guide

    if not file_path.exists():
        log.error(f"Guide not found: {file_path}")
        return ""

    return file_path.read_text(encoding="utf-8-sig")


@cache
def _load_icon(icon: AppIcon, game: str) -> QIcon:
    """`icon` for `game` or the common one if game has none. Empty QIcon if neither exists."""
    game_icon_path: Path = ICONS_PATH / game / icon
    if game_icon_path.exists():
        return QIcon(str(game_icon_path))

    common_icon_path: Path = ICONS_PATH / icon
    if common_icon_path.exists():
        return QIcon(str(common_icon_path))

    log.warning(f"Icon not found: '{icon}' for game '{game}'", silent=True)
    return QIcon()


@cache
def _load_achievement_icons(game: str) -> dict[str, dict[IconAchievementState, QIcon]]:
    """
    {
        icon name: {
            locked: QIcon, unlocked: QIcon
        }
    }
    for every achievement icon of `game`.

    Empty if the game has no achievement icons.
    """

    achievements_folder = ICONS_PATH / game / "achievements"
    locked_path = achievements_folder / IconAchievementState.LOCKED
    unlocked_path = achievements_folder / IconAchievementState.UNLOCKED

    if not locked_path.exists():
        log.warning(f"Achievement path not found for {game}: {locked_path}", silent=True)
        return {}

    achievement_icons = {}
    for icon_path in locked_path.iterdir():
        if not icon_path.is_file():
            continue

        icon_name_locked = icon_path.name
        icon_name_unlocked = icon_name_locked.replace("_locked", "")
        icon_path_unlocked = unlocked_path / icon_name_unlocked

        q_icon_locked = QIcon(str(icon_path))
        q_icon_unlocked = QIcon(str(icon_path_unlocked)) if icon_path_unlocked.exists() else QIcon()

        achievement_icons[icon_name_unlocked] = {
            IconAchievementState.LOCKED: q_icon_locked,
            IconAchievementState.UNLOCKED: q_icon_unlocked,
        }

    log.info(f"Cached {len(achievement_icons)} achievement icons for {game}")
    return achievement_icons


@cache
def _load_font(font: AppFont) -> str:
    """Load `font` into Qt and return its family name. Empty if it can't be loaded."""
    file_path = FONTS_PATH / font
    if not file_path.exists():
        log.warning(f"Font file not found: {file_path}", silent=True)
        return ""

    font_id = QFontDatabase.addApplicationFont(str(file_path))
    if font_id == -1:
        log.warning(f"Failed to load font: {file_path}", silent=True)
        return ""

    font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
    log.info(f"Loaded font: {font_family}")
    return font_family


@cache
def _load_stylesheet(game: str) -> str:
    """Stylesheet of `game`, or the Stellaris one if the game has none. Empty if neither exists."""
    file_path = STYLES_PATH / f"{game}.qss"
    if not file_path.exists():
        log.warning(f"Stylesheet not found: {file_path}", silent=True)

        # Fallback
        file_path = STYLES_PATH / f"{AppStyle.STELLARIS}.qss"
        if not file_path.exists():
            return ""

    with open(file_path, "r", encoding="utf-8-sig") as f:
        return f.read()


class ResourceManager:
    def __init__(self, default_game: Optional[str] = None):
        self._current_game = default_game or AppStyle.STELLARIS  # Add a default

        self.cache_startup()

    @property
    def current_game(self) -> str:
        return self._current_game

    def cache_startup(self):
        """Cache resources for the current game at startup."""
        _load_achievement_icons(self._current_game.lower())

    def set_game(self, game: str):
        if self._current_game != game:
            log.info(f"Switching game context from {self._current_game} to {game}")
            self._current_game = game
            _load_achievement_icons(game.lower())

    def get_icon(self, icon: AppIcon, game: Optional[str] = None) -> QIcon:
        """
        Get an application icon, optionally for a specific game.
        Falls back to common icons if game-specific icon not found.
        """

        target_game = (game or self.current_game).lower()
        return _load_icon(icon, target_game)

    def get_random_achievement_icon(self, game: Optional[str] = None) -> dict[IconAchievementState, QIcon]:
        """Get an achievement icon cache entry that supports picked from `locked` and `unlocked` keys"""
        target_game = (game or self._current_game).lower()

        game_achievements = _load_achievement_icons(target_game)
        if not game_achievements:
            log.warning(f"No achievement icons available for {target_game}.", silent=True)

            # Fallback
            game_achievements = _load_achievement_icons(AppStyle.STELLARIS)

            if not game_achievements:
                return {IconAchievementState.LOCKED: QIcon(), IconAchievementState.UNLOCKED: QIcon()}

        achievement_name = random.choice(list(game_achievements.keys()))
        return game_achievements[achievement_name]

    def get_achievement_icon(
        self, achievement_name: str, game: Optional[str] = None
    ) -> dict[IconAchievementState, QIcon]:
        target_game = (game or self._current_game).lower()

        return _load_achievement_icons(target_game).get(
            achievement_name, {IconAchievementState.LOCKED: QIcon(), IconAchievementState.UNLOCKED: QIcon()}
        )

    def load_font(self, font: AppFont) -> str:
        """Load a font and return its family name."""
        return _load_font(font)

    def get_stylesheet(self, game: Optional[str] = None) -> str:
        """Get the stylesheet for the specified game."""
        target_game = (game or self._current_game).lower()
        return _load_stylesheet(target_game)

    def get_available_games(self) -> list[str]:
        """Get list of games that have resource folders."""
        available_games = []

        if ICONS_PATH.exists():
            for item in ICONS_PATH.iterdir():
                if item.is_dir() and (item / "achievements").exists():
                    available_games.append(item.name)

        return sorted(available_games)
