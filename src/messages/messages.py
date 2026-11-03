"""
Remote message shown to users on startup.

The message is a Markdown file in the repository (`messages/message.md` on `REPO_BRANCH`).
It is downloaded to a cache folder in the config directory and there is no copy bundled with the application.

What a fetch does with the cache:

- Remote file has text: save to cache.
- Remote file empty or removed: delete cache, no message.
- `--no-conn` or within cooldown: don't download. use cache as it is.

A message counts as new when its fingerprint mismatches from the last one.
"""

import hashlib
import logging
import time
from dataclasses import dataclass
from enum import Enum

import certifi
import requests

from app_services import services
from config.definitions import REPO_BRANCH, REPO_NAME, REPO_OWNER

log = logging.getLogger("Messages")

MESSAGE_FILE_NAME = "message.md"
MESSAGE_URL = (
    f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/refs/heads/{REPO_BRANCH}/messages/{MESSAGE_FILE_NAME}"
)
MESSAGE_CACHE = services().config.config_dir / "messages" / MESSAGE_FILE_NAME


class RemoteErrorIds(str, Enum):
    HTTP_NOT_FOUND = 404


class MessageStatus(str, Enum):
    AVAILABLE = "available"  # There is a message to show
    NO_MESSAGE = "no_message"  # Remote file is empty or removed
    DOWNLOAD_FAILED = "download_failed"  # Unable to download and nothing cached
    NETWORK_BLOCKED = "network_blocked"  # `--no-conn` or nothing is cached


@dataclass
class Message:
    status: MessageStatus
    text: str = ""

    @property
    def fingerprint(self) -> str:
        """
        Identifies this message's content.
        Empty if there is no message.
        """

        if not self.text:
            return ""
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()

    def is_new(self, last_seen_fingerprint: str) -> bool:
        """
        True if there is a message and user has not closed this version if it.
        """
        is_new = self.status == MessageStatus.AVAILABLE and self.fingerprint != last_seen_fingerprint
        log.info(
            f"Current message fingerprint '{self.fingerprint}' {'differs from' if is_new else 'equals'} last seen '{last_seen_fingerprint}'."
        )
        return is_new


def _normalise(text: str) -> str:
    """Same line endings and no surrounding blank spaces, so neither changes fingerprint."""
    return text.replace("\r\n", "\n").strip()


def fetch_message() -> Message:
    """
    Download the remote message and update the cache.
    Blocking: best ran in a thread.

    Returns the message to show which can come from cache when the download is skipped or failed.
    """

    config = services().config
    settings = services().settings.settings

    if config.prevent_conn:
        log.info("Network access is blocked. using cached message.", silent=True)
        return read_cached_message(status_if_missing=MessageStatus.NETWORK_BLOCKED)

    seconds_since_check = int(time.time()) - settings.message_last_checked
    if seconds_since_check < config.update_check_cooldown:
        log.debug(f"Message check cooldown still in effect ({seconds_since_check})s since. Using cached message.")
        return read_cached_message()

    log.info(f"Fetching message from remote: {MESSAGE_URL}")

    try:
        response = requests.get(MESSAGE_URL, timeout=10, verify=certifi.where())
    except requests.exceptions.RequestException as e:
        log.warning(f"Unable to download the message: {e}")
        return read_cached_message(status_if_missing=MessageStatus.DOWNLOAD_FAILED)

    if response.status_code == RemoteErrorIds.HTTP_NOT_FOUND:
        # Message file was removed
        text = ""
    elif response.ok:
        text = response.content.decode("utf-8", errors="replace")
        log.info(f"Successfully fetched and decoded message.")
    else:
        log.warning(f"Unable to download the message: HTTP {response.status_code}")
        return read_cached_message(status_if_missing=MessageStatus.DOWNLOAD_FAILED)

    # Cooldown only starts after a definitive answer.
    # Failed attempts don't count so it can be retried.
    message = _update_cache(text)
    log.info(f"Message:\nFingerprint: {message.fingerprint}\n{message.text}", silent=True)
    return message


def _update_cache(text: str) -> Message:
    """Save `text` to cache or delete if empty."""
    text = _normalise(text)

    if not text:
        log.debug("No remote message. Removing cached message.")
        try:
            MESSAGE_CACHE.unlink(missing_ok=True)
        except OSError as e:
            log.warning(f"Unable to delete the cached message '{MESSAGE_CACHE}': {e}")
        return Message(MessageStatus.NO_MESSAGE)

    try:
        MESSAGE_CACHE.parent.mkdir(parents=True, exist_ok=True)
        MESSAGE_CACHE.write_text(text, encoding="utf-8")
        log.debug(f"Saved message to: {MESSAGE_CACHE}")
    except OSError as e:
        log.warning(f"Unable to save the message to '{MESSAGE_CACHE}': {e}")

    return Message(MessageStatus.AVAILABLE, text)


def read_cached_message(status_if_missing: MessageStatus = MessageStatus.NO_MESSAGE) -> Message:
    """
    Cached message, without downloading.
    `status_if_missing` explains why there is none.
    """

    try:
        text = _normalise(MESSAGE_CACHE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return Message(status_if_missing)
    except OSError as e:
        log.warning(f"Unable to read the cached message '{MESSAGE_CACHE}': {e}")
        return Message(status_if_missing)

    if not text:
        return Message(status_if_missing)

    return Message(MessageStatus.AVAILABLE, text)
