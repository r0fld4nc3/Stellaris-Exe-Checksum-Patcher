import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ENTRY_POINT_NAME = "main"
BUILD_DIRS = (f"{ENTRY_POINT_NAME}.build", f"{ENTRY_POINT_NAME}.dist", f"{ENTRY_POINT_NAME}.onefile-build")


def main():
    SYS_PLATFORM = platform.system().lower()

    parser = argparse.ArgumentParser(description="Build Stellaris Checksum Patcher")

    parser.add_argument(
        "-p",
        "--platform",
        choices=["linux", "windows", "auto"],
        default="auto",
        help="Target platform for the build (default: auto-detect)",
    )

    parser.add_argument("-kb", "--keep-build", action="store_true", help="Keep build files after building.")

    args = parser.parse_args()

    FILENAME = "Stellaris-Checksum-Patcher"
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

    # Additional conditional arguments
    if arg_platform == "windows":
        cmd.extend(["--windows-icon-from-ico=src/ui/icons/checksum_patcher_icon.ico", "--windows-console-mode=attach"])
    else:
        if arg_platform == "linux":
            # Set compiler optimisation flags
            os.environ["CCFLAGS"] = "-O3"  # -march=native -flto
            # os.environ["LDFLAGS"] = "-Wl,-s"  # Strip symbols and Garbage
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
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed with error code {e.returncode}", file=sys.stderr)
        sys.exit(1)

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
