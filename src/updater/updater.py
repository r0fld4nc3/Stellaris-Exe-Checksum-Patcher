import json  # isort: skip
import requests  # isort: skip
import time  # isort: skip

from conf_globals import LOG_LEVEL  # isort: skip
from logger import create_logger  # isort: skip

log = create_logger("Updater", LOG_LEVEL)


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

        self.local_version = [0, 0, 1]  # Default version, should be dynamically substituted.

        self.has_new_version = False

    def check_for_update(self):
        log.info("Checking for Stellaris Checksum Patcher update...")

        self.pulled_releases = self.fetch_releases(max_fetch=self._releases_max_fill)

        non_pre_idx = self.get_first_non_pre_release(self.pulled_releases)

        if self.pulled_releases:
            has_new_version = self.has_new_release(self.local_version, self.pulled_releases[non_pre_idx])
            self.has_new_version = has_new_version
        else:
            log.info("No releases available")
            self.has_new_version = False
            return False

        self.last_checked_timestamp = int(time.time())

        return has_new_version

    def fetch_releases(self, max_fetch: int = -1):
        log.info("Fetching releases...", silent=True)

        releases = []

        try:
            api_call = f"{self.api}{self._api_releases}"
            log.info(f"{api_call}", silent=True)
            response = requests.get(api_call, timeout=60)
        except requests.ConnectionError as con_err:
            log.error(f"Unable to establish connection to update repo.")
            log.error(con_err)
            return False

        if not response.status_code == 200:
            log.error("Not a valid repository.")
        else:
            releases = response.json()[:max_fetch]

        return releases

    def get_first_non_pre_release(self, releases: dict) -> int:
        # Return if releases not dict type
        if not isinstance(releases, dict):
            return 0

        # Get first non pre-release version index
        log.info(
            f"Getting first non pre-release available from list of supplied {len(releases)} releases.", silent=True
        )

        log.debug(f"{json.dumps(releases, indent=2)}", silent=True)

        for i, release in enumerate(self.pulled_releases):
            pre_release = release.get("prerelease")
            name = release.get("name")
            tag = release.get("tag_name")
            if not pre_release:
                log.info(f"Release number {i} {name} ({tag}) is not a pre-release. Comparing against it.", silent=True)
                return i
            else:
                log.debug(f"Release number {i} {name} ({tag}) is set as pre-release. Skipping.", silent=True)

        return 0  # Return first index, I guess

    def has_new_release(self, current: list[int], remote: dict) -> bool:
        log.info(f"Local version: {current}", silent=True)

        remote_release_name = self.construct_version_list_from_str(remote.get(self._release_name))
        remote_release_tag = self.construct_version_list_from_str(remote.get(self._release_tag))

        compare_iters = [remote_release_name, remote_release_tag]

        log.info(f"Remote Name:    {remote_release_name}", silent=True)
        log.info(f"Remote Tag:     {remote_release_tag}", silent=True)

        has_update = False

        # tuple comparison is lexicographical which is perfect for this case
        for comp in compare_iters:
            tuple_current = tuple(current)
            tuple_comp = tuple(comp)
            if tuple_current < tuple_comp:
                log.debug(f"{tuple_current} < {tuple_comp}", silent=True)
                has_update = True
                break

        log.debug(f"{has_update=}", silent=True)

        if has_update:
            log.info(f"This release {current} is outdated with remote {remote_release_name} ({remote_release_tag})")
            return True
        else:
            log.debug(
                f"This release {current} is up to date with remote {remote_release_name} ({remote_release_tag})",
                silent=True,
            )
            log.info("Up to date")

        return False

    @staticmethod
    def construct_version_list_from_str(version: str):
        # Collect the digits between dots
        digit = ""
        constructed_version = []

        for c in version:
            log.debug(f"{digit=}", silent=True)
            log.debug(f"-> '{c}'", silent=True)
            if c.isdigit():
                log.debug(f"    - '{c}' is a digit.", silent=True)
                digit += c
            else:
                log.debug(f"    - '{c}' is not a digit.", silent=True)
                if digit:
                    constructed_version.append(int(digit))
                    digit = ""

        # Handle if last item(s) are digits and weren't appended
        if digit:
            constructed_version.append(int(digit))

        log.debug(f"{constructed_version=}", silent=True)

        return constructed_version

    @staticmethod
    def set_github_repo(user: str, repo: str) -> tuple:
        _user = user
        _repo = f"{_user}/{repo}"
        _api = f"https://api.github.com/repos/{_repo}"

        log.info(f"User: {_user}\nRepository Name: {_repo}\nAPI: {_api}", silent=True)

        return _user, _repo, _api

    def set_local_version(self, version: str):
        self.local_version = self.construct_version_list_from_str(version)
        log.info(f"Set local version {version}", silent=True)
