import requests

from utils.global_defines import logger


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

        self.download_location = ""  # Local disk location to save the downloaded file.

        self.local_version = "0.0.1"  # Default version, should be dynamically substituted.

    def check_for_update(self):
        logger.info("Checking for Stellaris Checksum Patcher update...")

        self.pulled_releases = self.list_releases()
        if self.pulled_releases:
            has_new_version = self.has_new_release(self.local_version, self.pulled_releases[0])
        else:
            logger.info("No releases available")
            return False

        return has_new_version

    def list_releases(self):
        releases = []

        try:
            api_call = f"{self.api}{self._api_releases}"
            response = requests.get(api_call, timeout=60)
        except requests.ConnectionError as con_err:
            logger.error(f"Unable to establish connection to update repo.")
            logger.error(con_err)
            return False

        if not response.status_code == 200:
            logger.error("Not a valid repository.")
        else:
            releases = response.json()[:self._releases_max_fill]

        return releases

    def has_new_release(self, current: str, remote: dict) -> bool:
        if current != remote.get(self._release_name) and current != remote.get(self._release_tag):
            logger.info(f"This release {current} is outdated with remote {remote.get(self._release_name)} ({remote.get(self._release_tag)})")
            return True
        else:
            logger.info(f"This release {current} is up to date with remote {remote.get(self._release_name)} ({remote.get(self._release_tag)})")

        return False

    @staticmethod
    def set_github_repo(user: str, repo: str) -> tuple:
        _user = user
        _repo = f"{_user}/{repo}"
        _api = f"https://api.github.com/repos/{_repo}"

        logger.debug(f"User: {_user}\nRepository Name: {_repo}\nAPI: {_api}")

        return _user, _repo, _api

    def set_local_version(self, version: str):
        self.local_version = version
        logger.info(f"Set local version {version}")
