import json
import logging
import shutil
import time
from pathlib import Path

import certifi
import requests

from core import services
from core.definitions import REPO_BRANCH, REPO_NAME, REPO_OWNER

log = logging.getLogger("Patterns")  # isort: skip

PATTERNS_FILE_NAME = "patterns_v2.json"
PATTERNS_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/refs/heads/{REPO_BRANCH}/src/patch_patterns/{PATTERNS_FILE_NAME}"
PATTERNS_DISTRIBUTED_FILE = Path(__file__).parent / PATTERNS_FILE_NAME


def local_patterns_file() -> Path:
    """Patterns file in the app's config folder. Updated from remote, used for patching."""
    return services().config.config_dir / PATTERNS_FILE_NAME


def get_patterns_config_remote() -> dict:
    log.info(f"Fetching patterns from remote: {PATTERNS_URL}")

    config = services().config
    settings = services().settings

    _force_local_patterns = any(
        (config.prevent_conn, config.use_local_patterns, settings.app_settings.force_local_patterns)
    )

    if _force_local_patterns:
        log.info("Forced local patterns. Returning local patterns.", silent=True)
        return get_patterns_config_local()

    last_checked = settings.app_settings.patch_patterns_update_last_checked
    now = int(time.time())
    check_delta = now - last_checked

    if not last_checked:
        settings.app_settings.patch_patterns_update_last_checked = now

    if check_delta < config.update_check_cooldown:
        log.info(f"Update cooldown still in effect: {check_delta} seconds remaining")
        # Return local file
        return get_patterns_config_local()
    else:
        settings.app_settings.patch_patterns_update_last_checked = now

    try:
        response = requests.get(PATTERNS_URL, timeout=10, verify=certifi.where())

        response.raise_for_status()

        patterns_data: dict = response.json()

        log.info("Successfully fetched remote patterns.")
        log.info(json.dumps(patterns_data, indent=2), silent=True)

        # Save patterns file. Local patterns aren't forced here.
        log.info(f"Saving remote patterns to config dir: {local_patterns_file()}")
        with open(local_patterns_file(), "w", encoding="UTF-8") as f:
            f.write(json.dumps(patterns_data, indent=2))

        return patterns_data

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
    log.info(f"Fetching patterns from local: {local_patterns_file()}")

    config = services().config

    if not local_patterns_file().exists():
        log.error(f"Expected local patterns file does not exist: {local_patterns_file()}")

        # Copy from local distribution to config dir
        config_dir = config.config_dir
        copy_dest = config_dir / PATTERNS_FILE_NAME

        try:
            log.info(f"Copy distributed '{PATTERNS_FILE_NAME}' to config dir '{copy_dest}'")
            shutil.copy2(PATTERNS_DISTRIBUTED_FILE, copy_dest)
        except Exception as e:
            log.error(f"Failed to copy distributed '{PATTERNS_FILE_NAME}' to config directory '{copy_dest}': {e}")
            return {}

    # Load the config
    with open(local_patterns_file(), "r", encoding="UTF-8") as f:
        config: dict = json.load(f)
        log.info(f"Loaded patterns data\n{json.dumps(config, indent=2)}", silent=True)

    if not config:
        log.error("No local configuration found!")
        return {}

    return config


def update_local_config(key: str, content):
    log.info("Updating local patterns config.")

    if not local_patterns_file().exists():
        log.error(f"Expected local patterns file does not exist: {local_patterns_file()}")
        return False

    with open(local_patterns_file(), "r", encoding="UTF-8") as f:
        patterns_data = json.load(f)
        log.info(f"Loaded patterns data\n{json.dumps(patterns_data, indent=2)}", silent=True)

    patterns_data[key] = content

    with open(local_patterns_file(), "w", encoding="UTF-8") as f:
        f.write(json.dumps(patterns_data, indent=2))
        log.info(f"Updated local patterns data\n{json.dumps(patterns_data, indent=2)}", silent=True)
