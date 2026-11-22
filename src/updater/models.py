from dataclasses import dataclass


@dataclass
class SavedUpdateCheck:
    """Result of the last successful check for one build and release channel."""

    checked_at: int = 0
    update_available: bool = False
    latest_version: str = ""
    release_url: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "SavedUpdateCheck":
        """Build from a saved settings entry. Raises if the entry is damaged."""
        return cls(
            checked_at=int(data["checked_at"]),
            update_available=bool(data["update_available"]),
            latest_version=str(data["latest_version"]),
            release_url=str(data["release_url"]),
        )
