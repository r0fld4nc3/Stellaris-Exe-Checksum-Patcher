import json
import logging
import re
import threading
import time
from dataclasses import asdict
from typing import Optional

import certifi
import requests

from core.definitions import APP_IS_PRERELEASE, APP_REVISION, APP_VERSION_STR
from core.services import services

from .models import SavedUpdateCheck

log = logging.getLogger("Updater")

_REVISION_PATTERN = re.compile(r"\.rev(\d+)$")

API_RELEASES = "/releases"
RELEASE_NAME_KEY = "name"
RELEASE_TAG_KEY = "tag_name"
RELEASE_PRERELEASE_KEY = "prerelease"
RELEASE_DRAFT_KEY = "draft"
RELEASE_URL_KEY = "html_url"

# API_RELEASES_LATEST = "/releases/latest"
# ASSETS_KEY = "assets"
# DOWNLOAD_URL_KEY = "browser_download_url"


class Updater:
    def __init__(
        self,
        github_user: str = "",
        repository_name: str = "",
        local_version: str = APP_VERSION_STR,
        is_prerelease: bool = APP_IS_PRERELEASE,
        local_revision: int = APP_REVISION,
    ):
        self._releases_max_fill = 10  # Used to just fill the last 10 releases. -1 unlimited
        self._lock = threading.Lock()  # Ensure one check at a time.
        self._checks: dict[str, SavedUpdateCheck] = {}

        # Sets the repo user, repo path and repo api url
        self.user, self.repo, self.api = self.set_github_repo(github_user, repository_name)
        self.pulled_releases: list[dict] = []

        # Always the built-in version.
        self._local_version: list[int] = []
        self.local_version = local_version
        self.is_prerelease: bool = is_prerelease
        self.local_revision: int = local_revision

        self._load_checks()

    @property
    def local_version(self) -> list[int]:
        return self._local_version

    @local_version.setter
    def local_version(self, local_version: str) -> None:
        self._local_version_str = local_version
        self._local_version = self.construct_version_list_from_str(local_version)

    @property
    def update_available(self) -> bool:
        """Last known answer witout checking."""
        saved_check = self._current_check()
        if saved_check is None:
            return False
        return saved_check.update_available

    @property
    def latest_version(self) -> str:
        """Newest release for the last check for this build and release channel."""
        saved_check = self._current_check()
        if saved_check is None:
            return ""
        return saved_check.latest_version

    @property
    def release_url(self) -> str:
        """Page of `latest_version`."""
        saved_check = self._current_check()
        if saved_check is None:
            return ""
        return saved_check.release_url

    def check_update_available(self) -> bool:
        """Blocking."""
        with self._lock:
            # Read once. It's possible to change this option while check is running.
            include_prereleases: bool = self._include_prereleases()
            version_key: str = self._build_check_version_key(include_prereleases)
            saved_check: SavedUpdateCheck = self._checks.get(version_key, None)

            if saved_check is not None and self._is_on_cooldown(version_key):
                if saved_check.update_available:
                    log.info(f"Cooldown in effect. Per last check, an update is available.")
                else:
                    log.info(f"Cooldown in effect. Per last check, no update is available.")
                return saved_check.update_available

            releases = self.fetch_releases(max_fetch=self._releases_max_fill)
            if releases is None:
                return saved_check is not None and saved_check.update_available

            new_check: SavedUpdateCheck = self._build_saved_check(
                releases, include_prereleases
            )  # Here checks if has new release available
            self._checks[version_key] = new_check
            self._save_checks()
            return new_check.update_available

    def _load_checks(self) -> None:
        """Load this build's saved checks. Other builds' checks are cleared on the next save."""
        saved_checks = services().settings.app_settings.update_checks

        for include_prereleases in (False, True):
            version_key = self._build_check_version_key(include_prereleases)
            if version_key not in saved_checks:
                continue

            try:
                self._checks[version_key] = SavedUpdateCheck.from_dict(saved_checks[version_key])
            except KeyError, TypeError, ValueError:
                log.warning(f"Ignoring damaged saved update check: {version_key}", silent=True)

    def _save_checks(self) -> None:
        saved_checks = {}
        for version_key, saved_check in self._checks.items():
            saved_checks[version_key] = asdict(saved_check)

        # Assign a new dict
        services().settings.app_settings.update_checks = saved_checks

    def _current_check(self) -> Optional[SavedUpdateCheck]:
        version_key = self._build_check_version_key(self._include_prereleases())
        return self._checks.get(version_key)

    def _is_on_cooldown(self, version_key: str) -> bool:
        saved_check: SavedUpdateCheck = self._checks.get(version_key, None)

        if saved_check is None:
            return False

        seconds_since_check = int(time.time()) - saved_check.checked_at
        # 10 < update_check_cooldown = True -> cooldown in effect
        # 189 < update_check_cooldown = False -> not on cooldown, can check for update
        on_cooldown = seconds_since_check < services().config.update_check_cooldown
        return on_cooldown

    @staticmethod
    def _include_prereleases() -> bool:
        return services().settings.app_settings.include_prerelease_updates

    def _build_check_version_key(self, include_prereleases: bool) -> str:
        """Each build and release channel keeps its own check and cooldown."""
        channel = "stable"
        if include_prereleases:
            channel = "prerelease"
        return f"{self._local_version_str}.rev{self.local_revision}:{channel}"

    def _build_saved_check(self, releases: list[dict], include_prereleases: bool) -> SavedUpdateCheck:
        saved_check = SavedUpdateCheck(checked_at=int(time.time()))

        release_idx = self.get_newest_release(releases, include_prereleases=include_prereleases)
        if release_idx is None:
            return saved_check

        release = releases[release_idx]
        saved_check.update_available = self.has_new_release(self.local_version, release)
        saved_check.latest_version = release.get(RELEASE_TAG_KEY, "")
        saved_check.release_url = release.get(RELEASE_URL_KEY, "")
        return saved_check

    def fetch_releases(self, max_fetch: int = -1) -> Optional[list[dict]]:
        """Newest releases first, at most `max_fetch` (-1 for all). None when they can't be fetched."""
        log.info("Fetching releases...", silent=True)

        if services().config.prevent_conn:
            log.info("Update turned off due to prevent connections argument being active.")
            return None

        try:
            api_call = f"{self.api}{API_RELEASES}"
            log.info(f"CALL {api_call}", silent=True)
            response = requests.get(api_call, timeout=60, verify=certifi.where())
        except requests.RequestException as request_err:
            # Covers connection errors and timeouts
            log.warning("Unable to establish connection to update repo.")
            log.error(str(request_err), silent=True)
            return None

        if not response.status_code == 200:
            log.error(f"Unable to fetch releases from {self.repo} ({self.api}): HTTP {response.status_code}")
            return None

        try:
            releases = response.json()
        except ValueError as json_err:
            log.error(f"Releases response is not valid JSON: {json_err}", silent=True)
            return None

        if not isinstance(releases, list):
            log.error("Releases response is not a list.", silent=True)
            return None

        if max_fetch > 0:
            releases = releases[:max_fetch]

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
            name = release.get(RELEASE_NAME_KEY)
            tag = release.get(RELEASE_TAG_KEY)
            if release.get(RELEASE_DRAFT_KEY):
                log.info(f"Release number {i} {name} ({tag}) is a draft. Skipping.", silent=True)
                continue
            if release.get(RELEASE_PRERELEASE_KEY) and not include_prereleases:
                log.info(f"Release number {i} {name} ({tag}) is a pre-release. Skipping.", silent=True)
                continue

            log.info(f"Release number {i} {name} ({tag}) is the newest {kind}. Comparing against it.", silent=True)
            return i

        return None

    def has_new_release(self, current: list[int], remote: dict, current_is_prerelease: Optional[bool] = None) -> bool:
        if current_is_prerelease is None:
            current_is_prerelease = self.is_prerelease

        log.info(f"Local version: {current}{' (pre-release)' if current_is_prerelease else ''}", silent=True)
        log.info(f"Local revision: {self.local_revision}", silent=True)

        remote_release = remote.get(RELEASE_NAME_KEY)
        remote_tag = remote.get(RELEASE_TAG_KEY)

        remote_release_version: list[int] = self.construct_version_list_from_str(self.strip_revision(remote_release))
        remote_release_tag: list[int] = self.construct_version_list_from_str(self.strip_revision(remote_tag))
        remote_revision: int = self.get_revision(remote_tag)
        remote_is_prerelease: bool = bool(remote.get(RELEASE_PRERELEASE_KEY))

        compare_iters = [remote_release_version, remote_release_tag]

        log.info(f"Remote Name:        {remote_release_version}", silent=True)
        log.info(f"Remote Tag:         {remote_release_tag}", silent=True)
        log.info(f"Remote Revision:    {remote_revision}", silent=True)
        log.info(f"Remote Pre-release: {remote_is_prerelease}", silent=True)

        has_update = False

        current_key = self.version_sort_key(current, current_is_prerelease, self.local_revision)
        for comp in compare_iters:
            if not comp:
                continue  # Name or tag without a version in it
            comp_key = self.version_sort_key(comp, remote_is_prerelease, remote_revision)
            if current_key < comp_key:
                log.debug(f"{current_key} < {comp_key}")
                has_update = True
                break

        log.debug(f"{has_update=}")

        if has_update:
            log.info(
                f"This release {current} (rev{self.local_revision}) is outdated with remote: {remote_release} (rev{remote_revision})"
            )
            return True
        else:
            log.debug(
                f"This release {current} (rev{self.local_revision}) is up to date with remote {remote_release} (rev{remote_revision})",
                silent=True,
            )
            log.info("Up to date")

        return False

    @staticmethod
    def version_sort_key(version: list[int], is_prerelease: bool, revision: int = 0) -> tuple:
        """
        Key that orders versions correctly when compared (tuple comparison is lexicographical):
        1. Main version (major, minor, patch), missing parts count as 0
        2. Final release ranks above any pre-release of the same version
        3. Pre-releases only: any numbers after the main version (ex.: rc.2 -> 2) order them between themselves.
            Ignored for final releases, where they're usually unrelated (ex.: a name like "v2.2.2")
        4. Revision (ex.: .rev2 -> 2), so re-releases of the same version order between themselves

        EX.:
        v3.0.0-pre < v3.0.0-rc.2 < v3.0.0 < v3.0.0.rev1 < v3.0.1-pre
        """
        main_version = tuple((list(version[:3]) + [0, 0, 0])[:3])
        if is_prerelease:
            return main_version, 0, tuple(version[3:]), revision
        return main_version, 1, (), revision

    @staticmethod
    def get_revision(version: str) -> int:
        match = _REVISION_PATTERN.search(version or "")
        if not match:
            return 0
        return int(match.group(1))

    @staticmethod
    def strip_revision(version: str) -> str:
        return _REVISION_PATTERN.sub("", version or "")

    @staticmethod
    def construct_version_list_from_str(version: str) -> list[int]:
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
