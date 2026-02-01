from __future__ import annotations

import os
import platform
from functools import lru_cache
from pathlib import Path

from .definitions import OS_TYPE

# ---------- OS Detection ----------


@lru_cache(maxsize=1)
def system() -> str:
    return platform.system()


def os_windows() -> bool:
    return system() == OS_TYPE.WINDOWS


def os_linux() -> bool:
    return system() == OS_TYPE.LINUX


def os_darwin() -> bool:
    return system() == OS_TYPE.DARWIN


# ---------- Core Paths ----------


def get_home_folder() -> Path:
    # Prefer pathlib's home() over expanduser
    return Path.home()


def ensure_dir(path: os.PathLike | str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _env_path(var_name: str, fallback: Path) -> Path:
    value = os.environ.get(var_name)
    return Path(value) if value else fallback


# ----- Platform-specific folders -----


def windows_appdata() -> Path:
    # Roaming AppData
    return _env_path("APPDATA", get_home_folder() / "AppData" / "Roaming")


def windows_localappdata() -> Path:
    # Local AppData
    return _env_path("LOCALAPPDATA", get_home_folder() / "AppData" / "Local")


def unix_local_folder() -> Path:
    # ~/.local
    return get_home_folder() / ".local"


def unix_share_folder() -> Path:
    # ~/.local/share
    return unix_local_folder() / "share"


def unix_config_folder() -> Path:
    # ~/.config
    return get_home_folder() / ".config"


# ---------- API's ----------


def get_appdata_folder() -> Path:
    """Return AppData folder on Windows and ~/.local/share on Unix-like systems."""
    # “App data” root (roaming on Windows, share on Unix-like)
    return windows_appdata() if os_windows() else unix_share_folder()


def get_localappdata_folder() -> Path:
    """Return Local AppData folder on Windows and ~/.local/share on Unix-like systems."""
    return windows_localappdata() if os_windows() else unix_share_folder()


def get_documents_folder() -> Path:
    # Simplified cross-platform approximation
    return (get_home_folder() / "Documents") if os_windows() else unix_share_folder()


def get_env_tempdir() -> Path:
    # local app data temp on Windows; ~/.local/share/temp elsewhere
    temp_dir = (get_localappdata_folder() / "Temp") if os_windows() else (unix_share_folder() / "temp")
    return ensure_dir(temp_dir)


def get_os_env_config_folder() -> Path:
    # Windows -> LOCALAPPDATA, Linux/Darwin -> ~/.local/share
    if os_windows():
        config_dir = windows_localappdata()
    elif os_linux() or os_darwin():
        config_dir = unix_share_folder()
    else:
        config_dir = Path.cwd()

    return ensure_dir(config_dir)


def get_system_drive() -> Path:
    # Return the drive root on Windows, otherwise home
    if os_windows():
        drive = os.environ.get("SystemDrive", "C:")
        return Path(drive + os.sep)
    return get_home_folder()


def get_temp_dir() -> Path:
    # Keep /tmp for Unix-like, and uses Windows TEMP if available
    if os_windows():
        return Path(os.environ.get("TEMP", str(windows_localappdata() / "Temp")))
    if os_linux() or os_darwin():
        return Path("/tmp")
    return get_home_folder()
