import requests
import time

from utils.global_defines import LOG_LEVEL
from logger import create_logger

updlog = create_logger("Updater", LOG_LEVEL)

class Updater:
    def __init__(self, user: str="github_username", repo_name:str = "you_repo_url"):
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

        self.local_version = "0.0.1"  # Default version, should be dynamically substituted.

        self.has_new_version = False

    def check_for_update(self):
        updlog.info("Checking for Stellaris Checksum Patcher update...")

        self.pulled_releases = self.list_releases()
        if self.pulled_releases:
            has_new_version = self.has_new_release(self.local_version, self.pulled_releases[0])
            self.has_new_version = has_new_version
        else:
            updlog.info("No releases available")
            self.has_new_version = False
            return False

        self.last_checked_timestamp = int(time.time())

        return has_new_version

    def list_releases(self):
        releases = []

        try:
            api_call = f"{self.api}{self._api_releases}"
            response = requests.get(api_call, timeout=60)
        except requests.ConnectionError as con_err:
            updlog.error(f"Unable to establish connection to update repo.")
            updlog.error(con_err)
            return False

        if not response.status_code == 200:
            updlog.error("Not a valid repository.")
        else:
            releases = response.json()[:self._releases_max_fill]

        return releases

    def has_new_release(self, current: str, remote: dict) -> bool:
        if current != remote.get(self._release_name) and current != remote.get(self._release_tag):
            updlog.info(f"This release {current} is outdated with remote {remote.get(self._release_name)} ({remote.get(self._release_tag)})")
            return True
        else:
            updlog.info(f"This release {current} is up to date with remote {remote.get(self._release_name)} ({remote.get(self._release_tag)})")

        return False

    @staticmethod
    def set_github_repo(user: str, repo: str) -> tuple:
        _user = user
        _repo = f"{_user}/{repo}"
        _api = f"https://api.github.com/repos/{_repo}"

        updlog.debug(f"User: {_user}\nRepository Name: {_repo}\nAPI: {_api}")

        return _user, _repo, _api

    def set_local_version(self, version: str):
        self.local_version = version
        updlog.debug(f"Set local version {version}")
