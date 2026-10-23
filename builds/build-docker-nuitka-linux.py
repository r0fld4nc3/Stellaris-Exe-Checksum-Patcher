#!/usr/bin/env python3
# builds/build-docker-nuitka-linux.py
"""
Single entry point to build the Docker image and run the Nuitka Linux build
inside it. Works from both Linux and macOS hosts, always producing an
x86_64 (linux/amd64) Linux binary regardless of host architecture.

Run from the project root (only needs the Python standard library):
    python3 builds/build-docker-nuitka-linux.py                         # defaults to Dockerfile CMD (-p linux)
    python3 builds/build-docker-nuitka-linux.py -p linux --keep-build   # arguments go to build-nuitka.py
    python3 builds/build-docker-nuitka-linux.py --rebuild               # rebuild the image without Docker's cache

Every argument except --rebuild is passed to build-nuitka.py inside the container.
"""

import os
import platform
import subprocess
import sys
from pathlib import Path

IMAGE_NAME = "stellaris-linux-builder"
# Container name so only one build can exist at a given time.
# This would break otherwise because builds share the project's main.build folder, so two at once break each other.
CONTAINER_NAME = "stellaris-linux-build"
TARGET_PLATFORM = "linux/amd64"  # To force output regardless of host arch
CACHE_VOLUMES = {
    "stellaris-nuitka-cache": "/root/.cache/Nuitka",
    "stellaris-ccache": "/root/.cache/ccache",
    "stellaris-uv-cache": "/root/.cache/uv",
}


def run(cmd: list[str]) -> None:
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def check_docker_available() -> None:
    try:
        subprocess.run(["docker", "info"], check=True, capture_output=True)
    except FileNotFoundError:
        print("Error: 'docker' CLI not found in PATH.", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError:
        hint = ""
        if platform.system().lower() == "darwin":
            hint = "Docker Desktop running? Must be started manually on macOS."
        print(f"Error: Docker daemon is not reachable. {hint}", file=sys.stderr)
        sys.exit(1)


def check_no_running_build() -> None:
    """Exit if a build container is already running, and clear out a stopped leftover."""
    result = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"name=^{CONTAINER_NAME}$", "--format", "{{.State}}"],
        capture_output=True,
        text=True,
    )
    state = result.stdout.strip()
    if not state:
        return

    if state in ("running", "restarting", "paused"):
        print(
            f"Error: a build is already running in container '{CONTAINER_NAME}'.\n"
            "Wait for it to finish, or stop it with:\n"
            f"    docker stop {CONTAINER_NAME}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Stopped but not removed (ex.: Docker restarted mid-build). Safe to remove.
    subprocess.run(["docker", "rm", CONTAINER_NAME], capture_output=True)


def stop_build_container() -> None:
    print(f"\nInterrupted. Stopping container '{CONTAINER_NAME}'...", file=sys.stderr)
    subprocess.run(["docker", "stop", "--time", "5", CONTAINER_NAME], capture_output=True)


def main() -> None:
    check_docker_available()
    check_no_running_build()

    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent
    dockerfile = script_dir / "build-docker-ubuntu"

    host_system = platform.system()
    host_arch = platform.machine()
    # Our commands first. Forward everything else to the container entrypoint
    extra_args = sys.argv[1:]
    rebuild = "--rebuild" in extra_args
    extra_args = [arg for arg in extra_args if arg != "--rebuild"]

    print(f"Host OS/Arch: {host_system}/{host_arch}")
    print(f"Target: {TARGET_PLATFORM} (forced, regardless of host)")
    print(f"Project root: {project_root}")
    print(f"Dockerfile:    {dockerfile}")

    if host_system.lower() == "darwin" and host_arch == "arm64":
        print(
            "\nNote: Building x86_64 image on Apple Silicon uses emulation "
            "(QEMU or Rosetta) and will be slower than native builds.\n"
            "To get better performance, enable 'Use Rosetta for x86_64/amd64 "
            "emulation on Apple Silicon' in Docker Desktop > Settings > General."
        )

    print(f"\n==> Building image {IMAGE_NAME}{' (no cache)' if rebuild else ''}...")
    build_cmd = ["docker", "build", "--platform", TARGET_PLATFORM]
    if rebuild:
        build_cmd.append("--no-cache")
    build_cmd.extend(["-t", IMAGE_NAME, "-f", str(dockerfile), str(project_root)])
    try:
        run(build_cmd)
    except KeyboardInterrupt:
        print("\nInterrupted while building the image.", file=sys.stderr)
        sys.exit(130)

    print("\n==> Running build container...")
    # --name: Docker refuses a second container with the same name, so overlapping builds can't start.
    # --init: runs a small init process as PID 1 so stop signals reach the build.
    docker_run_cmd = [
        "docker",
        "run",
        "--rm",
        "--init",
        "--name",
        CONTAINER_NAME,
        "--platform",
        TARGET_PLATFORM,
        "-v",
        f"{project_root}:/app",
    ]

    for volume, mount in CACHE_VOLUMES.items():
        docker_run_cmd.extend(["-v", f"{volume}:{mount}"])

    docker_run_cmd.extend(["-e", "NUITKA_CACHE_DIR=/root/.cache/Nuitka"])

    # Pass host UID/GID to restore file ownership
    if hasattr(os, "getuid"):
        docker_run_cmd.extend(["-e", f"HOST_UID={os.getuid()}"])
        docker_run_cmd.extend(["-e", f"HOST_GID={os.getgid()}"])

    docker_run_cmd.append(IMAGE_NAME)
    docker_run_cmd.extend(extra_args)

    try:
        run(docker_run_cmd)
    except KeyboardInterrupt:
        # Ctrl+C only stops the docker client. The container keeps running unless stopped.
        stop_build_container()
        sys.exit(130)
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed with error code {e.returncode}", file=sys.stderr)
        sys.exit(1)

    print(f"\n==> Done. Check {project_root} for output binaries.")


if __name__ == "__main__":
    main()
