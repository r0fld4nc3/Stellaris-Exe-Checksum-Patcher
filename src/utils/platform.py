import logging
import os
import subprocess
from pathlib import Path

from config.path_helpers import os_darwin, os_linux, os_windows

log = logging.getLogger("utils.platform")

WAYLAND: str = "wayland"
X11: str = "xcb"


def open_in_file_manager(path: Path):
    path = path.resolve()

    try:
        if os_windows():
            subprocess.run(["explorer.exe", "/select,", str(path)])
        elif os_linux():
            if path.is_file():
                # On UNIX open the directory not file itself
                path = path.parent
            subprocess.run(["xdg-open", str(path)])
        elif os_darwin():
            subprocess.run(["open", "-R", str(path)])
        else:
            log.warning("No known Operating System")
    except Exception as e:
        log.error(f"Failed to open game folder: {e}")


def is_backend_wayland() -> bool:
    # Common wayland flags
    wayland_display: str = os.environ.get("WAYLAND_DISPLAY")
    xdg_session_type: str = os.environ.get("XDG_SESSION_TYPE", "").lower()
    qpa_platform: str = os.environ.get("QT_QPA_PLATFORM", "").lower()

    return bool(wayland_display) or xdg_session_type == WAYLAND or qpa_platform == WAYLAND


def is_backend_x11() -> bool:
    xdg_session_type: str = os.environ.get("XDG_SESSION_TYPE", "").lower()
    qpa_platform: str = os.environ.get("QT_QPA_PLATFORM", "").lower()

    return xdg_session_type == X11 or qpa_platform == X11


def set_backend_x11() -> None:
    if os_linux():
        os.environ["QT_QPA_PLATFORM"] = "xcb"
        log.warning("Set QT_QPA_PLATFORM=xcb")
