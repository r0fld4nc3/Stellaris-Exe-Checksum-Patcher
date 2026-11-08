APP_VERSION = [3, 0, 0]
APP_IS_PRERELEASE: bool = True

# Display form of APP_VERSION, ex.:
# [3, 0, 0] -> "v3.0.0"
# [3, 0, 0] + APP_IS_PRERELEASE -> "v3.0.0-pre"
# [3, 0, 0, "beta", 1] -> "v3.0.0-beta-1"
APP_VERSION_STR: str = "v" + ".".join(str(v) for v in APP_VERSION[0:3])
if len(APP_VERSION) > 3:
    APP_VERSION_STR += "-" + "-".join(str(v) for v in APP_VERSION[3:])
elif APP_IS_PRERELEASE:
    APP_VERSION_STR += "-pre"

REPO_BRANCH: str = "v3"  # Used for APIs and remote requests
TRACKING_BRANCH: str = "v3"  # Used for local tracking and visual indicators. No remote impact.

# Bump when re-releasing the same `APP_VERSION`. Reset to 0 when `APP_VERSION` changes.
APP_REVISION: int = 5
APP_REVISION_STR: str = f".rev{APP_REVISION}" if APP_REVISION else ""

HOST: str = "r0fld4nc3"
APP_FOLDER: str = "Apps"
APP_NAME: str = "StellarisChecksumPatcher"

SUPPORTED_GAMES = ("Stellaris",)

# --- Updater ---
REPO_OWNER = HOST
REPO_NAME = "Stellaris-Exe-Checksum-Patcher"
