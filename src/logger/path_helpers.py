import os
import platform
from pathlib import Path

WINDOWS = "windows"
LINUX = "linux"
UNIX = "unix"
DARWIN = "darwin"
MAC = "mac"

def win_get_appdata() -> Path:
    if os_windows():
        return Path(os.getenv("appdata"))
    else:
        return unix_get_share_folder()


def win_get_localappdata() -> Path:
    if os_windows():
        return Path(os.getenv("localappdata"))
    else:
        return unix_get_share_folder()


def win_get_documents_folder() -> Path:
    if os_windows():
        return get_home_folder() / "Documents"
    else:
        return unix_get_share_folder()


def unix_get_share_folder() -> Path:
    if not os_windows():
        return unix_get_local_folder() / "share"
    else:
        return win_get_localappdata()


def unix_get_local_folder() -> Path:
    if not os_windows():
        return get_home_folder() / ".local"
    else:
        return win_get_localappdata()


def unix_get_config_folder() -> Path:
    if not os_windows():
        return get_home_folder() / ".config"
    else:
        return win_get_localappdata()


def get_home_folder() -> Path:
    return Path(os.path.expanduser('~'))


def get_env_tempdir() -> Path:
    if os_windows():
        _tempdir = win_get_localappdata() / "Temp"
    else:
        _tempdir = unix_get_share_folder() / "temp"

    # Ensure path exists
    ensure_paths(_tempdir)

    return _tempdir


def get_os_env_config_folder() -> Path:
    if os_windows():
        _config_folder = win_get_localappdata()
    elif os_linux():
        _config_folder = unix_get_share_folder()
    elif os_darwin():
        # Write to user-writable locations, like ~/.local/share
        _config_folder = unix_get_share_folder()
    else:
        _config_folder = Path.cwd()

    ensure_paths(_config_folder)

    return _config_folder


def ensure_paths(to_path: Path):
    if isinstance(to_path, Path):
        if not to_path.exists():
            if to_path.suffix:
                # It's a file
                os.makedirs(to_path.parent, exist_ok=True)
                with open(to_path, 'w') as f:
                    if to_path.suffix == ".json":
                        f.write('{}')
                    else:
                        f.write('')
            else:
                # It's a directory
                os.makedirs(to_path, exist_ok=True)
    elif isinstance(to_path, str):
        if not os.path.exists(to_path):
            if str(to_path).rpartition('.')[-1]:
                # We have a file
                os.makedirs(to_path.rpartition('.')[0])
                with open(to_path, 'w') as f:
                    if to_path.endswith(".json") == ".json":
                        f.write('{}')
                    else:
                        f.write('')
            else:
                os.makedirs(to_path)

    return Path(to_path)


def get_system_drive() -> Path:
    _drive = os.getenv("SystemDrive")
    if os_windows():
        _drive += "/"
    else:
        _drive = get_home_folder()
    return Path(_drive)


def get_temp_dir() -> Path:
    if os_windows():
        tmp_dir = Path(os.path.expandvars("%TEMP%"))
    elif os_linux() or os_darwin():
        tmp_dir = Path("/tmp")
    else:
        tmp_dir = Path(os.path.expanduser('~'))

    return tmp_dir


def os_linux() -> bool:
    return system() in [LINUX, UNIX]


def os_darwin() -> bool:
    return system() in [DARWIN, MAC]


def os_windows() -> bool:
    return system() in [WINDOWS]


def system() -> str:
    return platform.system().lower()
