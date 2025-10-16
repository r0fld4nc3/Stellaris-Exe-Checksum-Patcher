import random
from enum import Enum
from pathlib import Path

from PySide6.QtGui import QFontDatabase, QIcon
from PySide6.QtWidgets import QApplication

from conf_globals import LOG_LEVEL
from logger import create_logger

log = create_logger("Resource Manager", LOG_LEVEL)

# --- Base Paths ---
# Determines root path for resources
BASE_PATH = Path(__file__).parent
ICONS_PATH = BASE_PATH / "icons"
FONTS_PATH = BASE_PATH / "fonts"
STYLES_PATH = BASE_PATH / "styles"
ACHIEVEMENTS_LOCKED_PATH = ICONS_PATH / "achievements" / "locked"
ACHIEVEMENTS_UNLOCKED_PATH = ICONS_PATH / "achievements" / "unlocked"


class IconAchievementState(Enum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"


class AppIcon(Enum):
    WINDOW_WIN = "stellaris_checksum_patcher_icon.ico"
    WINDOW_UNIX = "stellaris_checksum_patcher_icon.png"
    PATCH_ICON = "patch_icon.png"
    SAVE_PATCH_ICON = "save_patch_icon.png"
    CONFIGURE_ICON = "configure_icon_big.png"


class AppFont(Enum):
    ORBITRON_BOLD = "Orbitron-Bold.ttf"


class AppStyle(Enum):
    STELLARIS = "stellaris.qss"


class ResourceManager:
    def __init__(self):
        self._icon_cache = {}
        self._icon_achievement_cache = {}
        self._font_cache = {}

        self.cache_startup()

    def get_icon(self, icon: AppIcon) -> QIcon:
        if icon in self._icon_cache:
            return self._icon_cache[icon]

        file_path = ICONS_PATH / icon.value
        if not file_path.exists():
            log.warning(f"Icon file not found: {file_path}", silent=True)
            return QIcon()

        q_icon = QIcon(str(file_path))
        self._icon_cache[icon] = q_icon
        return q_icon

    def cache_startup(self):
        for icon_path in ACHIEVEMENTS_LOCKED_PATH.iterdir():
            icon_name_locked = icon_path.name
            icon_name_unlocked = icon_name_locked.replace("_locked", "")
            icon_path_unlocked = ACHIEVEMENTS_UNLOCKED_PATH / icon_name_unlocked

            q_icon_locked = QIcon((str(icon_path)))
            q_icon_unlocked = QIcon(str(icon_path_unlocked))

            self._icon_achievement_cache.setdefault(
                icon_name_unlocked,
                {
                    IconAchievementState.LOCKED.value: q_icon_locked,
                    IconAchievementState.UNLOCKED.value: q_icon_unlocked,
                },
            )

    def get_random_icon_achievement(self) -> dict[IconAchievementState, QIcon]:
        """Get an achievement icon cache entry that supports picked from `locked` and `unlocked` keys"""
        achievment_name = random.choice(tuple(self._icon_achievement_cache.keys()))

        return self._icon_achievement_cache.get(achievment_name)

    def load_font(self, font: AppFont) -> str:
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
        return font_family

    def get_stylesheet(self, style: AppStyle) -> str:
        file_path = STYLES_PATH / style.value
        if not file_path.exists():
            log.warning(f"Stylesheet not found: {file_path}", silent=True)
            return ""

        with open(file_path, "r", encoding="UTF-8") as f:
            return f.read()
