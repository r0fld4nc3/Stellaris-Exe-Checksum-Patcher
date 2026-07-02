#!/usr/bin/env python3
# builds/docker-build-linux.py
"""
Single entry point to build the Docker image and run the Nuitka Linux build
inside it.

Usage:
    uv run builds/docker-build-linux.py -- -p linux --keep-build
    uv run builds/docker-build-linux.py             # defaults to Dockerfile CMD
"""

import os
import subprocess
import sys
from pathlib import Path

IMAGE_NAME = "stellaris-linux-builder"
CACHE_VOLUMES = {
    "stellaris-nuitka-cache": "/root/.cache/Nuitka",
    "stellaris-ccache": "/root/.cache/ccache",
    "stellaris-uv-cache": "/root/.cache/uv",
}


def run(cmd: list[str]) -> None:
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def main() -> None:
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent
    dockerfile = script_dir / "build-docker-ubuntu"

    # Forward all arguments to the container entrypoint
    extra_args = sys.argv[1:]

    print(f"Project root: {project_root}")
    print(f"Dockerfile:    {dockerfile}")

    print(f"\n==> Building image {IMAGE_NAME}...")
    run(["docker", "build", "--no-cache", "-t", IMAGE_NAME, "-f", str(dockerfile), str(project_root)])

    print("\n==> Running build container...")

    docker_run_cmd = ["docker", "run", "--rm", "-v", f"{project_root}:/app"]

    for volume, mount in CACHE_VOLUMES.items():
        docker_run_cmd.extend(["-v", f"{volume}:{mount}"])

    docker_run_cmd.extend(["-e", "NUITKA_CACHE_DIR=/root/.cache/Nuitka"])

    # Pass host UID/GID to restore file ownership
    if hasattr(os, "getuid"):
        docker_run_cmd.extend(["-e", f"HOST_UID={os.getuid()}"])
        docker_run_cmd.extend(["-e", f"HOST_GID={os.getuid()}"])

    docker_run_cmd.append(IMAGE_NAME)
    docker_run_cmd.extend(extra_args)

    try:
        run(docker_run_cmd)
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed with error code {e.returncode}", file=sys.stderr)
        sys.exit(1)

    print(f"\n==> Done. Check {project_root} for output binaries.")


if __name__ == "__main__":
    main()
