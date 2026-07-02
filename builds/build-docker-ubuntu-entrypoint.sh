#!/usr/bin/env bash
set -euo pipefail
cd /app

uv sync --locked --all-extras --dev

build_status=0
uv run python ./builds/build-nuitka.py "$@" || build_status=$?

# Restore ownership from root to user.
if [[ -n "${HOST_UID:-}" && -n "${HOST_GID:-}" ]]; then
    chown "${HOST_UID}:${HOST_GID}" \
        Stellaris-Checksum-Patcher-Nuitka-linux \
        nuitka-crash-report.xml \
        2>/dev/null || true
    chown -R "${HOST_UID}:${HOST_GID}" \
        main.build main.dist main.onefile-build \
        2>/dev/null || true
fi

exit "$build_status"
