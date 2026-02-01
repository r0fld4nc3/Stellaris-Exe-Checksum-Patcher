import logging
import os
import subprocess
import time
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


def set_file_access_time(
    file_path: Path | str, access_timestamp: float | None = None, modified_timestamp: float | None = None
) -> float:
    if not isinstance(file_path, Path):
        file_path = Path(file_path)

    # Get file stat info
    stat_info = os.stat(file_path)

    if modified_timestamp is None:
        modified_timestamp = stat_info.st_mtime

    if access_timestamp is None:
        access_timestamp = time.time()

    # Set new access time while preserving modification time
    os.utime(file_path, (access_timestamp, modified_timestamp))

    log.info(f"Access time set to: {time.ctime(access_timestamp)}", silent=True)
    log.info(f"Modified time set to: {time.ctime(modified_timestamp)}", silent=True)

    return access_timestamp


def get_file_access_time(file_path: Path | str) -> float:
    if not isinstance(file_path, Path):
        file_path = Path(file_path)

    stat_info = os.stat(file_path)

    return stat_info.st_atime


def get_file_modified_time(file_path: Path | str) -> float:
    if not isinstance(file_path, Path):
        file_path = Path(file_path)

    stat_info = os.stat(file_path)

    return stat_info.st_mtime


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
