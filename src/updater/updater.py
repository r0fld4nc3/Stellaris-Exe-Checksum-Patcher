import json
import logging
import ssl
import time
from typing import Optional

import certifi
import requests

from app_services import services
from config.definitions import APP_IS_PRERELEASE, APP_VERSION_STR

log = logging.getLogger("Updater")

_current: Optional["Updater"] = None


class Updater:
    def __init__(self, user: str = "github_username", repo_name: str = "you_repo_url"):
        # Sets the repo user, repo path and repo api url
        self.user, self.repo, self.api = self.set_github_repo(user, repo_name)

        self.pulled_releases: list[dict] = []
        self._api_releases = "/releases"
        self._releases_max_fill = 10  # Used to just fill the last 10 releases. -1 unlimited
        self._api_releases_latest = "/releases/latest"
        self._release_name = "name"
        self._release_tag = "tag_name"
        self._assets_tag = "assets"
        self._download_url = "browser_download_url"

        self.last_checked_timestamp: int = 0

        self.download_location = ""  # Local disk location to save the downloaded file.

        # Always the built-in version.
        self.local_version = self.construct_version_list_from_str(APP_VERSION_STR)
        self.local_is_prerelease = APP_IS_PRERELEASE

        self.has_new_version = False

    def check_for_update(self):
        if services().config.prevent_conn:
            log.info(f"Update turned off due to prevent connections argument being active.")
            return False

        log.info("Checking for Stellaris Checksum Patcher update...")

        self.pulled_releases = self.fetch_releases(max_fetch=self._releases_max_fill)

        include_prereleases = services().settings.settings.include_prerelease_updates
        release_idx = self.get_newest_release(self.pulled_releases, include_prereleases=include_prereleases)

        if release_idx is None:
            log.info(f"No {'' if include_prereleases else 'stable '}releases available")
            self.has_new_version = False
            return False

        has_new_version = self.has_new_release(self.local_version, self.pulled_releases[release_idx])
        self.has_new_version = has_new_version

        self.last_checked_timestamp = int(time.time())

        return has_new_version

    def fetch_releases(self, max_fetch: int = -1):
        log.info("Fetching releases...", silent=True)

        releases = []

        if services().config.prevent_conn:
            log.info(f"Update turned off due to prevent connections argument being active.")
            return releases

        # Force SSL context to fix Thread issues
        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
        except Exception as e:
            log.error(f"Failed to create SSL context: {e}", silent=True)

        try:
            api_call = f"{self.api}{self._api_releases}"
            log.info(f"CALL {api_call}", silent=True)
            response = requests.get(api_call, timeout=60, verify=certifi.where())
        except requests.ConnectionError as con_err:
            log.warning(f"Unable to establish connection to update repo.")
            log.error(con_err, silent=True)
            return False

        if not response.status_code == 200:
            log.error(f"Not a valid repository: {self.repo} ({self.api})")
        else:
            releases = response.json()[:max_fetch]

        log.debug("Dumping fetched releases.")
        log.debug(f"Releases: {json.dumps(releases, indent=2)}")

        return releases

    def get_newest_release(self, releases: list[dict], include_prereleases: bool = False) -> Optional[int]:
        """
        Index of the newest release in `releases` to compare against.
        Drafts are always skipped. Pre-releases are skipped unless `include_prereleases`.
        GitHub lists releases newest first. Returns None when no release passes.
        """
        if not isinstance(releases, list):
            return None

        kind = "release (pre-releases included)" if include_prereleases else "stable release"
        log.info(f"Getting newest {kind} from {len(releases)} supplied releases.", silent=True)

        for i, release in enumerate(releases):
            name = release.get("name")
            tag = release.get("tag_name")
            if release.get("draft"):
                log.info(f"Release number {i} {name} ({tag}) is a draft. Skipping.", silent=True)
                continue
            if release.get("prerelease") and not include_prereleases:
                log.info(f"Release number {i} {name} ({tag}) is a pre-release. Skipping.", silent=True)
                continue

            log.info(f"Release number {i} {name} ({tag}) is the newest {kind}. Comparing against it.", silent=True)
            return i

        return None

    def has_new_release(self, current: list[int], remote: dict, current_is_prerelease: Optional[bool] = None) -> bool:
        if current_is_prerelease is None:
            current_is_prerelease = self.local_is_prerelease

        log.info(f"Local version: {current}{' (pre-release)' if current_is_prerelease else ''}", silent=True)

        remote_release_name = self.construct_version_list_from_str(remote.get(self._release_name))
        remote_release_tag = self.construct_version_list_from_str(remote.get(self._release_tag))
        remote_is_prerelease = bool(remote.get("prerelease"))

        compare_iters = [remote_release_name, remote_release_tag]

        log.info(f"Remote Name:    {remote_release_name}", silent=True)
        log.info(f"Remote Tag:     {remote_release_tag}", silent=True)
        log.info(f"Remote is pre-release: {remote_is_prerelease}", silent=True)

        has_update = False

        current_key = self.version_sort_key(current, current_is_prerelease)
        for comp in compare_iters:
            if not comp:
                continue  # Name or tag without a version in it
            comp_key = self.version_sort_key(comp, remote_is_prerelease)
            if current_key < comp_key:
                log.debug(f"{current_key} < {comp_key}")
                has_update = True
                break

        log.debug(f"{has_update=}")

        if has_update:
            log.info(f"This release {current} is outdated with remote: {remote_release_name})")
            return True
        else:
            log.debug(
                f"This release {current} is up to date with remote {remote_release_name} ({remote_release_tag})",
                silent=True,
            )
            log.info("Up to date")

        return False

    @staticmethod
    def version_sort_key(version: list[int], is_prerelease: bool) -> tuple:
        """
        Key that orders versions correctly when compared (tuple comparison is lexicographical):
        1. Main version (major, minor, patch), missing parts count as 0
        2. Final release ranks above any pre-release of the same version
        3. Pre-releases only: any numbers after the main version (ex.: rc.2 -> 2) order them between themselves.
            Ignored for final releases, where they're usually unrelated (ex.: a name like "v2.2.2")

        EX.:
        v3.0.0-pre < v3.0.0-rc.2 < v3.0.0 < v3.0.1-pre
        """
        main_version = tuple((list(version[:3]) + [0, 0, 0])[:3])
        if is_prerelease:
            return main_version, 0, tuple(version[3:])
        return main_version, 1, ()

    @staticmethod
    def construct_version_list_from_str(version: str):
        # Collect the digits between dots
        digit = ""
        constructed_version = []

        for c in version or "":  # Release names can be empty
            log.debug(f"{digit=}")
            log.debug(f"-> '{c}'")

            if c.isdigit():
                log.debug(f"    - '{c}' is a digit.")
                digit += c
            else:
                log.debug(f"    - '{c}' is not a digit.")
                if digit:
                    constructed_version.append(int(digit))
                    digit = ""

        # Handle if last item(s) are digits and weren't appended
        if digit:
            constructed_version.append(int(digit))

        log.debug(f"{constructed_version=}")

        return constructed_version

    @staticmethod
    def set_github_repo(user: str, repo: str) -> tuple:
        _user = user
        _repo = f"{_user}/{repo}"
        _api = f"https://api.github.com/repos/{_repo}"

        log.info(f"User: {_user}", silent=True)
        log.info(f"Repository Name: {_repo}", silent=True)
        log.info(f"API: {_api}", silent=True)

        return _user, _repo, _api


def init(user: str = "", repo_name: str = "") -> Updater:
    global _current

    if _current:
        if isinstance(_current, Updater):
            return _current
        else:
            raise RuntimeError(f"Current Updater Instance is invalid: {_current}")

    _current = Updater(user=user, repo_name=repo_name)

    return _current


def get() -> Updater:
    global _current

    if not isinstance(_current, Updater):
        raise RuntimeError(f"Current Updater Instance is invalid: {_current}")

    if not _current or _current is None:
        raise RuntimeError(f"Updater is not valid or uninitialised: {_current}")

    return _current
