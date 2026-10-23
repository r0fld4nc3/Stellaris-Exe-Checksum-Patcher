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

    # Open directories directly and not just select/reveal them.
    # Reveal (select) files and macOS bundles in their parent(s).
    # .app is technically a directory but `open` would launch the app.

    # `-R` and `/select` is the command to reveal the files. Use this
    # on files, not on directories

    reveal = path.is_file() or (os_darwin() and path.suffix.lower() == ".app")

    if os_windows():
        # The trailing comma is part of the flag: `/select,<path>`. Windows... :eyeroll:
        args = ["explorer.exe", "/select,"] if reveal else ["explorer.exe"]
    elif os_linux():
        # xdg-open can't select a file, so open its folder instead
        args = ["xdg-open"]
        if path.is_file():
            path = path.parent
    elif os_darwin():
        args = ["open", "-R"] if reveal else ["open"]
    else:
        log.warning("No known Operating System")
        return

    args.append(str(path))

    try:
        subprocess.run(args)
    except Exception as e:
        log.error(f"Failed to open '{path}' in file manager: {e}")


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
