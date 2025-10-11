import json  # isort: skip
from pathlib import Path  # isort: skip
import time  # isort: skip
import requests  # isort: skip
from enum import Enum

from conf_globals import LOG_LEVEL, UPDATE_CHECK_COOLDOWN, OS, SETTINGS, updater  # isort: skip
from logger import create_logger  # isort: skip

log = create_logger("Patterns", LOG_LEVEL)  # isort: skip

PATTERNS_FILE_NAME = "patterns_v2.json"
PATTERNS_URL = f"https://raw.githubusercontent.com/{updater.repo}/refs/heads/26-incompatible-with-4xx/src/patch_patterns/{PATTERNS_FILE_NAME}"  # TODO: Change this to main repo
PATTERNS_LOCAL = SETTINGS.get_config_dir() / PATTERNS_FILE_NAME


# Also stated in pdx_patchers.py - keep in sync or import from there
class Platform(Enum):
    WINDOWS = "windows"
    LINUX_NATIVE = "linux"
    LINUX_PROTON = "linux_proton"  # Maps to windows in patterns
    MACOS = "macos"


def get_patterns_config_remote():
    log.info(f"Fetching patterns from remote: {PATTERNS_URL}")

    last_checked = SETTINGS.get_patch_patterns_update_last_checked()
    now = int(time.time())
    check_delta = now - last_checked

    if not last_checked:
        SETTINGS.set_patch_patterns_update_last_checked(now)

    if check_delta < UPDATE_CHECK_COOLDOWN:
        log.info(f"Update cooldown still in effect: {check_delta} seconds remaining")
        # Return local file
        return get_patterns_config_local()
    else:
        SETTINGS.set_patch_patterns_update_last_checked(now)

    try:
        response = requests.get(PATTERNS_URL, timeout=10)

        response.raise_for_status()

        patterns_data: dict = response.json()

        log.info(f"Successfully fetched remote patterns.")
        log.info(json.dumps(patterns_data, indent=2), silent=True)

        if OS.WINDOWS or (OS.LINUX and OS.LINUX_PROTON):
            config_key = Platform.WINDOWS
        elif OS.LINUX and not OS.LINUX_PROTON:
            config_key = Platform.LINUX_NATIVE
        elif OS.MACOS:
            config_key = Platform.MACOS
        else:
            log.warning("Unsupported OS detected. Defaulting to Windows patterns")
            config_key = Platform.WINDOWS

        # Save patterns file
        if not PATTERNS_LOCAL.exists():
            log.info(f"Saving remote patterns to config dir: {PATTERNS_LOCAL}")
            with open(PATTERNS_LOCAL, "w", encoding="UTF-8") as f:
                f.write(json.dumps(patterns_data, indent=2))

        log.info(f"Loading patterns for '{config_key.value}")

        return patterns_data.get(config_key.value)

    except requests.exceptions.Timeout:
        log.error("Request timed out.")
        return None
    except requests.exceptions.HTTPError as http_err:
        log.error(f"Error: HTTP error occurred: {http_err}")
        return None
    except requests.exceptions.RequestException as req_err:
        log.error(f"Error: A network error occurred: {req_err}")
        return None
    except json.JSONDecodeError:
        log.error("Error: Failed to decode JSON from the response.")
        return None


def get_patterns_config_local() -> dict:
    log.info(f"Fetching patterns from local: {PATTERNS_LOCAL}")

    if not PATTERNS_LOCAL.exists():
        log.error(f"Expected local patterns file does not exist: {PATTERNS_LOCAL}")
        return False

    if OS.WINDOWS or (OS.LINUX and OS.LINUX_PROTON):
        config_key = Platform.WINDOWS
    elif OS.LINUX and not OS.LINUX_PROTON:
        config_key = Platform.LINUX_NATIVE
    elif OS.MACOS:
        config_key = Platform.MACOS
    else:
        log.warning("Unsupported OS detected. Defaulting to Windows patterns")
        config_key = Platform.WINDOWS

    log.info(f"Loading patterns for '{config_key.value}")

    with open(PATTERNS_LOCAL, "r", encoding="UTF-8") as f:
        patterns_data = json.load(f)
        log.info(f"Loaded patterns data\n{json.dumps(patterns_data, indent=2)}", silent=True)

    config: dict = patterns_data.get(config_key.value, None)

    if not config:
        log.error(f"No configuration found for key '{config_key.value}' in patterns file '{PATTERNS_LOCAL}'.")
        return False

    return config


def update_local_config(key: str, content):
    log.info("Updating local patterns config.")

    if not PATTERNS_LOCAL.exists():
        log.error(f"Expected local patterns file does not exist: {PATTERNS_LOCAL}")
        return False

    with open(PATTERNS_LOCAL, "r", encoding="UTF-8") as f:
        patterns_data = json.load(f)
        log.info(f"Loaded patterns data\n{json.dumps(patterns_data, indent=2)}", silent=True)

    patterns_data[key] = content

    with open(PATTERNS_LOCAL, "w", encoding="UTF-8") as f:
        f.write(json.dumps(patterns_data, indent=2))
        log.info(f"Updated local patterns data\n{json.dumps(patterns_data, indent=2)}", silent=True)
