from pathlib import Path
from typing import Optional

from PySide6.QtCore import QCoreApplication, QEvent, QObject, QRect, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QIcon, QMouseEvent, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QPushButton,
    QTextBrowser,
)

from conf_globals import LOG_LEVEL, OS, SETTINGS
from logger import create_logger
from patchers import MultiGamePatcher
from patchers import models as patcher_models

log = create_logger("UI UTILS", LOG_LEVEL)


def set_icon_gray(icon: QIcon, size=(32, 32)):
    """
    Converts a QIcon to a grayed out version by applying a grayscale filter.

    :param icon: QIcon to be grayed out.
    :param size: Tuple (width, height) for the size of the QPixmap
    :return: QIcon with a grayscale effect
    """

    pixmap = icon.pixmap(size[0], size[1])

    gray_pixmap = QPixmap(pixmap.size())
    gray_pixmap.fill(QColor("transparent"))  # Background is transparent

    # QPainter to apply the filter
    painter = QPainter(gray_pixmap)
    painter.drawPixmap(0, 0, pixmap)  # Draw original
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(gray_pixmap.rect(), QColor("gray"))  # Apply the colour filter
    painter.end()

    return QIcon(gray_pixmap)


def get_screen_info(app: QApplication | QCoreApplication) -> tuple:
    # Get the primary screen
    screen = app.primaryScreen()

    # Screen resolution
    size = screen.size()
    width = size.width()
    height = size.height()

    # Scaling factor
    scale_f = screen.devicePixelRatio()

    return width, height, scale_f


class EventFilterOvr(QObject):
    def eventFilter(self, obj, event):
        return False


class EventFilterMoveResize(EventFilterOvr):
    MARGIN = 16

    def __init__(self, window):
        super().__init__()
        self.window = window
        self.resizing = False
        self.dragging = False
        self.start_pos = None
        self.window_start_pos = None
        self.mouse_press_area = None
        self.resize_start_geometry = None

    def eventFilter(self, obj, event):
        if not isinstance(event, QMouseEvent):
            return False

        if event.type() == QEvent.Type.MouseButtonPress:
            return self.handle_mouse_press(event)

        elif event.type() == QEvent.Type.MouseButtonRelease:
            return self.handle_mouse_release(event)

        elif event.type() == QEvent.Type.MouseMove:
            # Mouse move can mean dragging, resizing or just hovering
            if self.dragging or self.resizing:
                return self.handle_mouse_move(event)
            else:
                self.update_cursor(event)
                return False

        return False

    def handle_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # --- Prioritise resizing ---
            self.mouse_press_area = self.get_mouse_area(event)

            if self.mouse_press_area:
                self.start_pos = event.globalPosition().toPoint()
                self.resize_start_geometry = self.window.geometry()
                self.resizing = True
                self.update_cursor(event)
                return True

            # --- Check widget under mouse ---
            widget_under_mouse = self.window.childAt(event.pos())

            non_draggable_widgets = (QPushButton, QTextBrowser, QComboBox, QCheckBox)

            if widget_under_mouse is None or not isinstance(widget_under_mouse, non_draggable_widgets):
                self.start_pos = event.globalPosition().toPoint()
                self.window_start_pos = self.window.pos()
                self.dragging = True
                self.window.setCursor(Qt.CursorShape.ClosedHandCursor)

                # print(f"DRAG STARTED: mouse at {self.start_pos}, window at {self.window_start_pos}")

                return True

        return False

    def handle_mouse_move(self, event):
        if self.dragging and not (event.buttons() & Qt.MouseButton.LeftButton):
            # print("WARNING: Drag state out of sync, resetting")
            self.dragging = False
            self.restore_cursor()
            return False

        if self.resizing:
            self.resize_window(event)
            return True
        elif self.dragging:
            delta = event.globalPosition().toPoint() - self.start_pos
            new_pos = self.window_start_pos + delta
            # print(f"DRAGGING: delta={delta}, moving window to {new_pos}")
            self.window.move(new_pos)
            return True
        return False

    def handle_mouse_release(self, event):
        if event.button() == Qt.MouseButton.LeftButton and (self.dragging or self.resizing):
            self.dragging = False
            self.resizing = False
            self.mouse_press_area = None
            self.window_start_pos = None
            self.resize_start_geometry = None
            self.restore_cursor()
            return True
        return False

    def get_mouse_area(self, event):
        """Determine which edge/corner is being pressed for resizing"""
        rect = self.window.rect()
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        pos = event.pos()

        left = pos.x() <= self.MARGIN
        right = pos.x() >= w - self.MARGIN
        top = pos.y() <= self.MARGIN
        bottom = pos.y() >= h - self.MARGIN

        if left and top:
            return "top-left"
        elif right and top:
            return "top-right"
        elif left and bottom:
            return "bottom-left"
        elif right and bottom:
            return "bottom-right"
        elif left:
            return "left"
        elif right:
            return "right"
        elif top:
            return "top"
        elif bottom:
            return "bottom"
        return None

    def update_cursor(self, event):
        """Change cursor shape when hovering over resizable areas."""
        area = self.get_mouse_area(event)
        if area in ["top-left", "bottom-right"]:
            self.window.setCursor(Qt.SizeFDiagCursor)
        elif area in ["top-right", "bottom-left"]:
            self.window.setCursor(Qt.SizeBDiagCursor)
        elif area == "left" or area == "right":
            self.window.setCursor(Qt.SizeHorCursor)
        elif area == "top" or area == "bottom":
            self.window.setCursor(Qt.SizeVerCursor)
        else:
            self.restore_cursor()

    def restore_cursor(self):
        self.window.setCursor(Qt.ArrowCursor)

    def resize_window(self, event):
        """Resize window based on mouse movement."""
        rect = QRect(self.resize_start_geometry)

        if self.mouse_press_area == "top-left":
            rect.setTopLeft(event.globalPosition().toPoint())
        elif self.mouse_press_area == "top-right":
            rect.setTopRight(event.globalPosition().toPoint())
        elif self.mouse_press_area == "bottom-left":
            rect.setBottomLeft(event.globalPosition().toPoint())
        elif self.mouse_press_area == "bottom-right":
            rect.setBottomRight(event.globalPosition().toPoint())
        elif self.mouse_press_area == "left":
            rect.setLeft(event.globalPosition().x())
        elif self.mouse_press_area == "right":
            rect.setRight(event.globalPosition().x())
        elif self.mouse_press_area == "top":
            rect.setTop(event.globalPosition().y())
        elif self.mouse_press_area == "bottom":
            rect.setBottom(event.globalPosition().y())

        # Apply minimum size constraints to prevent the window from inverting
        min_width = 200  # Adjust as needed
        min_height = 100  # Adjust as needed

        if rect.width() < min_width:
            if self.mouse_press_area in ["left", "top-left", "bottom-left"]:
                rect.setLeft(rect.right() - min_width)
            else:
                rect.setRight(rect.left() + min_width)

        if rect.height() < min_height:
            if self.mouse_press_area in ["top", "top-left", "top-right"]:
                rect.setTop(rect.bottom() - min_height)
            else:
                rect.setBottom(rect.top() + min_height)

        self.window.setGeometry(rect)


def _restore_window_focus(window):
    window.raise_()
    window.activateWindow()
    window.setFocus()


def restore_window_focus(window):
    QTimer.singleShot(500, lambda: _restore_window_focus(window))


def find_game_path(patcher: MultiGamePatcher, configuration: patcher_models.PatchConfiguration) -> Optional[Path]:
    """
    Utility function to find the game path automatically.

    Attemps to find the game executable by:
    1. Checking saved path in settings
    2. Auto-locating via Steam detection

    Args:
        patcher: The multi-game patcher instance
        configuraiton: Patch Configuration

    Returns:
        Path to game executable if found, otherwise None
    """

    game_patcher = patcher.get_game_patcher(configuration.game, configuration.version)

    if not game_patcher:
        log.error(f"Failed to get patcher for {configuration.game} version {configuration.version}")
        return None

    # Determine platform and executable info
    platform = patcher_models.Platform.WINDOWS if configuration.is_proton else None
    exe_info = game_patcher.get_executable_info(platform)
    path_postfix = exe_info.path_postfix
    log.info(f"{exe_info=}", silent=True)
    log.info(f"Platform: {platform}", silent=True)
    log.info(f"Is Proton: {configuration.is_proton}", silent=True)

    # Check saved path in settings
    saved_path_str = (
        SETTINGS.game(configuration.game).proton_install_path
        if configuration.is_proton
        else SETTINGS.game(configuration.game).install_path
    )

    log.info(f"Retrieved saved path from settings: '{saved_path_str}'", silent=True)

    if saved_path_str:
        saved_path = Path(saved_path_str)
        if saved_path.exists() and saved_path.is_file():
            log.info(f"Retrieved game executable from settings: {saved_path}", silent=True)
            return saved_path
        else:
            log.warning(f"Saved game path found, but executable is invalid.")

    # Auto-locate
    log.info(f"Attempting to auto-locate game installation.")
    auto_located_path = game_patcher.locate_game_install()

    if OS.MACOS and not configuration.is_proton:
        auto_located_path = auto_located_path / path_postfix

    if auto_located_path:
        log.info(f"Auto-located path: {auto_located_path}")
        return auto_located_path

    log.error(f"Failed to locate {configuration.game} installation.")
    return None


def prompt_install_dir(game_name: str = "Game") -> Optional[Path]:
    qurl_install_dir: tuple[QUrl, str] = QFileDialog().getOpenFileUrl(
        caption=f"Please choose {game_name} executable binary..."
    )

    picked_path_str = qurl_install_dir[0].path()
    log.info(f"User picked path: {picked_path_str}", silent=True)

    # Handle potentially empty strings
    if picked_path_str and picked_path_str.strip():
        picked_path = Path(picked_path_str).absolute().resolve()

        # Verify path does exist
        if picked_path.exists():
            return picked_path
        else:
            log.warning(f"Selected path does not exist: {picked_path}")
            return None

    log.info(f"User cancelled file selection.", silent=True)
    return None
