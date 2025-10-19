import random
from enum import Enum
from pathlib import Path
from typing import Optional

from PySide6.QtGui import QFontDatabase, QIcon

from conf_globals import LOG_LEVEL
from logger import create_logger

log = create_logger("Resource Manager", LOG_LEVEL)

# --- Base Paths ---
# Determines root path for resources
BASE_PATH = Path(__file__).parent
ICONS_PATH = BASE_PATH / "icons"
FONTS_PATH = BASE_PATH / "fonts"
STYLES_PATH = BASE_PATH / "styles"


class IconAchievementState(Enum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"


class AppIcon(Enum):
    WINDOW_WIN = "checksum_patcher_icon.ico"
    WINDOW_UNIX = "checksum_patcher_icon.png"
    PATCH_ICON = "patch_icon.png"
    SAVE_PATCH_ICON = "save_patch_icon.png"
    CONFIGURE_ICON = "configure_icon_big.png"


class AppFont(Enum):
    ORBITRON_BOLD = "Orbitron-Bold.ttf"


class AppStyle(Enum):
    STELLARIS = "stellaris"
    CK3 = "ck3"


class ResourceManager:
    def __init__(self, default_game: Optional[str] = None):
        self._current_game = default_game or AppStyle.STELLARIS.value  # Add a default

        self._icon_cache = {}
        self._icon_achievement_cache = {}
        self._font_cache = {}
        self._stylesheet_cache = {}

        self.cache_startup()

    @property
    def current_game(self) -> str:
        return self._current_game

    def set_game(self, game: str):
        if self._current_game != game:
            log.info(f"Switching game context from {self._current_game} to {game}")
            self._current_game = game
            self._cache_game_achievements(game)

    def _get_game_paths(self, game: str) -> dict[str, Path]:
        game_base = ICONS_PATH / game

        return {
            "achievements_locked": game_base / "achievements" / IconAchievementState.LOCKED.value,
            "achievements_unlocked": game_base / "achievements" / IconAchievementState.UNLOCKED.value,
            "icons": game_base,
            "styles": STYLES_PATH / game,
        }

    def get_icon(self, icon: AppIcon, game: Optional[str] = None) -> QIcon:
        """
        Get an application icon, optionally for a specific game.
        Falls back to common icons if game-specific icon not found.
        """

        target_game = (game or self._current_game).lower()
        cache_key = (icon, target_game)

        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]

        # Try game-specific icon
        game_icon_path = ICONS_PATH / target_game / icon.value
        if game_icon_path.exists():
            q_icon = QIcon(str(game_icon_path))
            self._icon_cache[cache_key] = q_icon
            return q_icon

        common_icon_path = ICONS_PATH / icon.value
        if common_icon_path.exists():
            q_icon = QIcon(str(common_icon_path))
            self._icon_cache[cache_key] = q_icon
            return q_icon

        log.warning(f"Icon not found: '{icon.value}' for game {target_game}", silent=True)
        return QIcon()

    def cache_startup(self):
        """Cache resources for the current game at startup."""
        self._cache_game_achievements(self._current_game)

    def _cache_game_achievements(self, game: str):
        """Cache achievement icons for a specific game."""
        if game in self._icon_achievement_cache:
            return  # Already cached

        paths = self._get_game_paths(game)
        locked_path = paths["achievements_locked"]
        unlocked_path = paths["achievements_unlocked"]

        if not locked_path.exists():
            log.warning(f"Achievement path not found for {game}: {locked_path}", silent=True)
            self._icon_achievement_cache[game] = {}
            return

        game_cache = {}
        for icon_path in locked_path.iterdir():
            if not icon_path.is_file():
                continue

            icon_name_locked = icon_path.name
            icon_name_unlocked = icon_name_locked.replace("_locked", "")
            icon_path_unlocked = unlocked_path / icon_name_unlocked

            q_icon_locked = QIcon(str(icon_path))
            q_icon_unlocked = QIcon(str(icon_path_unlocked)) if icon_path_unlocked.exists() else QIcon()

            game_cache[icon_name_unlocked] = {
                IconAchievementState.LOCKED: q_icon_locked,
                IconAchievementState.UNLOCKED: q_icon_unlocked,
            }

        self._icon_achievement_cache[game] = game_cache
        log.info(f"Cached {len(game_cache)} achievement icons for {game}")

    def get_random_achievement_icon(self, game: Optional[str] = None) -> dict[IconAchievementState, QIcon]:
        """Get an achievement icon cache entry that supports picked from `locked` and `unlocked` keys"""
        target_game = (game or self._current_game).lower()

        if target_game not in self._icon_achievement_cache:
            self._cache_game_achievements(target_game)

        game_achievements = self._icon_achievement_cache.get(target_game, {})
        if not game_achievements:
            log.warning(f"No achievement icons available for {target_game}.", silent=True)

            # Fallback
            game_achievements = self._icon_achievement_cache.get(AppStyle.STELLARIS.value, {})

            if not game_achievements:
                return {IconAchievementState.LOCKED: QIcon(), IconAchievementState.UNLOCKED: QIcon()}

        achievement_name = random.choice(list(game_achievements.keys()))
        return game_achievements[achievement_name]

    def get_achievement_icon(
        self, achievement_name: str, game: Optional[str] = None
    ) -> dict[IconAchievementState, QIcon]:
        target_game = (game or self._current_game).lower()

        if target_game not in self._icon_achievement_cache:
            self._cache_game_achievements(target_game)

        return self._icon_achievement_cache.get(target_game, {}).get(
            achievement_name, {IconAchievementState.LOCKED: QIcon(), IconAchievementState.UNLOCKED: QIcon()}
        )

    def load_font(self, font: AppFont) -> str:
        """Load a font and return its family name."""
        if font in self._font_cache:
            return self._font_cache[font]

        file_path = FONTS_PATH / font.value
        if not file_path.exists():
            log.warning(f"Font file not found: {file_path}", silent=True)
            return ""

        font_id = QFontDatabase.addApplicationFont(str(file_path))
        if font_id == -1:
            log.warning(f"Failed to load font: {file_path}", silent=True)
            return ""

        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        self._font_cache[font] = font_family
        log.info(f"Loaded font: {font_family}")
        return font_family

    def get_stylesheet(self, game: Optional[str] = None) -> str:
        """Get the stylesheet for the specified game."""
        target_game = (game or self._current_game).lower()

        if target_game in self._stylesheet_cache:
            return self._stylesheet_cache[target_game]

        file_path = STYLES_PATH / f"{target_game}.qss"
        if not file_path.exists():
            log.warning(f"Stylesheet not found: {file_path}", silent=True)

            # Fallback
            file_path = STYLES_PATH / f"{AppStyle.STELLARIS.value}.qss"
            if not file_path.exists():
                return ""

        with open(file_path, "r", encoding="UTF-8") as f:
            stylesheet = f.read()

        self._stylesheet_cache[target_game] = stylesheet
        return stylesheet

    def get_available_games(self) -> list[str]:
        """Get list of games that have resource folders."""
        available_games = []

        if ICONS_PATH.exists():
            for item in ICONS_PATH.iterdir():
                if item.is_dir() and (item / "achievements").exists():
                    available_games.append(item.name)

        return sorted(available_games)
