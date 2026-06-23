import argparse
import os
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ENTRY_POINT_NAME = "main"
BUILD_DIRS: set[str] = {f"{ENTRY_POINT_NAME}.build", f"{ENTRY_POINT_NAME}.dist", f"{ENTRY_POINT_NAME}.onefile-build"}
BUILD_SOURCE: str = "Nuitka"
LINUX_BUILD_ARGS: str = "-march=x86-64-v2 -mtune=generic -Wno-deprecated-declarations"


def process_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Stellaris Checksum Patcher with Nuitka")

    parser.add_argument(
        "-p",
        "--platform",
        choices=["linux", "windows", "auto"],
        default="auto",
        help="Target platform for the build (default: auto-detect)",
    )

    parser.add_argument("-kb", "--keep-build", action="store_true", help="Keep build files after building.")

    args = parser.parse_args()

    return args


def create_compiler_wrapper(compiler: str, build_args: str = LINUX_BUILD_ARGS) -> Path:
    """
    Create a temporary compiler wrapper script that is used
    to inject -march and -mtune flags into EVERY gcc/cc call
    Nuitka makes, including onefile bootstrap builds, regardless
    of which SCons path triggered it.
    This works around a known Nuitka bug where CCFLAGS are not
    propagated to the bootstrap compilation step.

    A separate wrapper is needed for CC (gcc) and CXX (g++) because Nuitka
    compiles .c static source files with gcc and .cpp translation units with
    g++. Mixing them causes void* implicit conversion errors in C-mode files.
    """

    wrapper_content = f"""#!/bin/sh
# Nuitka compiler wrapper: forces ISA Level for all compilation steps
# including onefile bootstrap binary.
exec {compiler} {build_args} "$@"
"""

    # Write to a temp file that persists for the duration of the build
    fd, tmp_path = tempfile.mkstemp(prefix=f"nuitka_{compiler}_wrapper_", suffix=".sh")
    os.close(fd)

    wrapper = Path(tmp_path)
    wrapper.write_text(wrapper_content)
    wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return wrapper


def verify_binary_isa(binary_path: Path) -> None:
    """
    Run readelf on the final binary and report the ISA level.
    """
    print("\nVerifying binary ISA level...")
    try:
        result = subprocess.run(["readelf", "-n", str(binary_path)], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if "isa" in line.lower() or "x86" in line.lower():
                print(f"  {line.strip()}")
    except FileNotFoundError:
        print("  readelf not found — skipping ISA verification (install binutils)")


def main():
    SYS_PLATFORM = platform.system().lower()

    args = process_args()

    FILENAME = f"Stellaris-Checksum-Patcher-{BUILD_SOURCE}"
    OUTPUT_FILENAME_LINUX = f"{FILENAME}-linux"
    OUTPUT_FILENAME_WIN = f"{FILENAME}-win.exe"

    arg_platform = args.platform.lower()

    # Auto-detect platform if needed
    if arg_platform == "auto":
        if SYS_PLATFORM == "linux":
            arg_platform = "linux"
        elif SYS_PLATFORM == "windows":
            arg_platform = "windows"
        else:
            print(f"Warning: Unsupported platform '{SYS_PLATFORM}', defaulting to Linux")
            arg_platform = "linux"

    # Determine output filename
    if arg_platform == "linux":
        output_filename = OUTPUT_FILENAME_LINUX
    elif arg_platform == "windows":
        output_filename = OUTPUT_FILENAME_WIN
    else:
        output_filename = FILENAME

    print(f"Detected system platform: {SYS_PLATFORM}")
    print(f"Building for platform: {arg_platform}")
    print(f"Output filename: {output_filename}")

    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    entry_point = project_root / "src" / f"{ENTRY_POINT_NAME}.py"

    # Build command
    cmd = [
        "uv",
        "run",
        "nuitka",
        "--standalone",
        "--onefile",
        "--enable-plugin=pyside6",
        # "--include-qt-plugins=sensible",
        "--include-data-dir=src/ui/fonts=ui/fonts",
        "--include-data-dir=src/ui/icons=ui/icons",
        "--include-data-dir=src/ui/styles=ui/styles",
        "--include-data-dir=src/achievements=achievements/",
        "--include-data-file=src/patch_patterns/patterns.json=patch_patterns/patterns.json",
        f"--output-filename={output_filename}",
    ]

    cc_wrapper: None | Path = None
    cxx_wrapper: None | Path = None

    # Additional conditional arguments
    if arg_platform == "windows":
        cmd.extend(["--windows-icon-from-ico=src/ui/icons/checksum_patcher_icon.ico", "--windows-console-mode=attach"])
    else:
        if arg_platform == "linux":
            # Create compiler wrapper that injects -march into ALL compilation
            # steps, including onefile build.
            # Setting only CCFLAGS is insufficient due to a known Nuitka bug
            # where CCFLAGS is not propagated to the bootstrap SCons call.
            cc_wrapper = create_compiler_wrapper(compiler="gcc", build_args=LINUX_BUILD_ARGS)
            cxx_wrapper = create_compiler_wrapper(compiler="g++", build_args=LINUX_BUILD_ARGS)
            print(f"Using CC wrapper: {cc_wrapper}")
            print(f"Using CXX wrapper: {cxx_wrapper}")

            os.environ["CC"] = str(cc_wrapper)
            os.environ["CXX"] = str(cxx_wrapper)
            # CCFLAGS
            os.environ["CCFLAGS"] = f"-O3 {LINUX_BUILD_ARGS}"
        cmd.extend(
            [
                "--product-name=Stellaris-Checksum-Patcher",
                "--file-description=Patches the Stellaris binary for Ironman mode with mods",
            ]
        )

    # Add the entry point after all optional args have been added
    cmd.append(entry_point)

    # Run the build
    try:
        subprocess.run(cmd, cwd=project_root, check=True)
        print(f"\nBuild process finished: {output_filename}")

        if arg_platform == "linux":
            verify_binary_isa(project_root / output_filename)
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed with error code {e.returncode}", file=sys.stderr)
        sys.exit(1)
    finally:
        for c in (cc_wrapper, cxx_wrapper):
            if c and c.exists():
                c.unlink()

    # Handle build files cleanup
    args_keep_build_files = args.keep_build
    if not args_keep_build_files:
        print(f"\nCleaning up build files...")
        for item in project_root.iterdir():
            if item.name in BUILD_DIRS and item.is_dir():
                print(f"  Removing: {item.name}")
                try:
                    shutil.rmtree(item)
                except Exception as e:
                    print(f"  Error removing {item.name}: {e}")
    else:
        print(f"\nKeeping build files (--keep-build specified)")


if __name__ == "__main__":
    main()
