import json
import logging
import shutil
import ssl
import time
from enum import Enum
from pathlib import Path

import certifi
import requests

from app_services import services
from config.definitions import REPO_BRANCH, REPO_NAME, REPO_OWNER
from config.path_helpers import os_darwin, os_linux, os_windows
from patchers.models import Platform

log = logging.getLogger("Patterns")  # isort: skip

PATTERNS_FILE_NAME = "patterns.json"
PATTERNS_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/refs/heads/{REPO_BRANCH}/src/patch_patterns/{PATTERNS_FILE_NAME}"
PATTERNS_LOCAL = services().config.config_dir / PATTERNS_FILE_NAME
PATTERNS_DISTRIBUTED_FILE = Path(__file__).parent / PATTERNS_FILE_NAME


def get_patterns_config_remote() -> dict:
    log.info(f"Fetching patterns from remote: {PATTERNS_URL}")

    config = services().config
    settings = services().settings

    _force_local_patterns = any(
        (config.prevent_conn, config.use_local_patterns, settings.settings.force_local_patterns)
    )

    if _force_local_patterns:
        log.info("Forced local patterns. Returning local patterns.", silent=True)
        return get_patterns_config_local()

    last_checked = settings.settings.patch_patterns_update_last_checked
    now = int(time.time())
    check_delta = now - last_checked

    if not last_checked:
        settings.settings.patch_patterns_update_last_checked = now

    # Force SSL context to fix Thread issues
    try:
        ssl_context = ssl.create_default_context(cafile=certifi.where())
    except Exception as e:
        log.error(f"Failed to create SSL context: {e}", silent=True)

    if check_delta < config.update_check_cooldown:
        log.info(f"Update cooldown still in effect: {check_delta} seconds remaining")
        # Return local file
        return get_patterns_config_local()
    else:
        settings.settings.patch_patterns_update_last_checked = now

    try:
        response = requests.get(PATTERNS_URL, timeout=10, verify=certifi.where())

        response.raise_for_status()

        patterns_data: dict = response.json()

        log.info(f"Successfully fetched remote patterns.")
        log.info(json.dumps(patterns_data, indent=2), silent=True)

        if os_windows() or (os_linux() and config.use_proton):
            config_key = Platform.WINDOWS
        elif os_linux() and not config.use_proton:
            config_key = Platform.WINDOWS
        elif os_darwin:
            config_key = Platform.DARWIN
        else:
            log.warning("Unsupported OS detected. Defaulting to Windows patterns")
            config_key = Platform.WINDOWS

        # Save patterns file
        if not config.use_local_patterns or not settings.settings.force_local_patterns:
            log.info(f"Saving remote patterns to config dir: {PATTERNS_LOCAL}")
            with open(PATTERNS_LOCAL, "w", encoding="UTF-8") as f:
                f.write(json.dumps(patterns_data, indent=2))

        log.info(f"[Remote] Loading patterns for '{config_key}'")

        return patterns_data.get(config_key)

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

    config = services().config

    if not PATTERNS_LOCAL.exists():
        log.error(f"Expected local patterns file does not exist: {PATTERNS_LOCAL}")

        # Copy from local distribution to config dir
        config_dir = config_dir
        copy_dest = config_dir / PATTERNS_FILE_NAME

        try:
            log.info(f"Copy distributed '{PATTERNS_FILE_NAME}' to config dir '{copy_dest}'")
            shutil.copy2(PATTERNS_DISTRIBUTED_FILE, copy_dest)
        except Exception as e:
            log.error(f"Failed to copy distributed '{PATTERNS_FILE_NAME}' to config directory '{copy_dest}': {e}")
            return {}

    # Load the config
    with open(PATTERNS_LOCAL, "r", encoding="UTF-8") as f:
        config: dict = json.load(f)
        log.info(f"Loaded patterns data\n{json.dumps(config, indent=2)}", silent=True)

    if not config:
        log.error(f"No local configuration found!")
        return {}

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
