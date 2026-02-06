import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ENTRY_POINT_NAME = "main"
BUILD_DIRS: set[int] = {"build", "dist"}
SPEC_FILE: str = f"{ENTRY_POINT_NAME}.spec"
BUILD_SOURCE: str = "PyInstaller"


def check_bootloader_exists() -> bool:
    try:
        result = subprocess.run(
            ["uv", "run", "python", "-c", "import PyInstaller; print(PyInstaller.__path__[0])"],
            capture_output=True,
            text=True,
            check=True,
        )
        pyinstaller_path = Path(result.stdout.strip())
        bootloader_path = pyinstaller_path / "bootloader"

        # Check platform-specific bootloader
        system = platform.system().lower()
        if system == "windows":
            bootloader_file = bootloader_path / "Windows-64bit" / "run.exe"
        else:
            bootloader_file = bootloader_path / "Linux-64bit" / "run"

        return bootloader_file.exists()
    except Exception as e:
        print(f"Error: {e}")
        return False


def build_custom_bootloader(project_root: Path) -> bool:
    print("\n" + "+" * 40)
    print("Building custom PyInstaller bootloader...")
    print("This is a one-time process that can take a few minutes.")
    print("+" * 40)

    bootloader_build_dir = project_root / ".pyinstaller-bootloader"

    try:
        # Clone PyInstaller
        if not bootloader_build_dir.exists():
            print("Cloning PyInstaller repository...")

            subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth=1",
                    "https://github.com/pyinstaller/pyinstaller.git",
                    str(bootloader_build_dir),
                ],
                check=True,
            )

        bootloader_src = bootloader_build_dir / "bootloader"

        # Check for required build tools
        system = platform.system().lower()

        if system == "linux":
            print("Checking for Linux build tools...")
            try:
                subprocess.run(["gcc", "--version"], capture_output=True, check=True)
            except FileNotFoundError:
                print(f"WARNING: gcc not found.")
                print("Install common build devel packages to be able to proceed.")
                return False

        # Build bootloader
        print(f"\nBuilding bootloader in: {bootloader_src}")
        subprocess.run(["python", "waf", "distclean", "all"], cwd=bootloader_src, check=True)

        # Install PyInstaller for local source with custom bootloader
        print("\nInstalling PyInstaller with custom bootloader...")
        subprocess.run(["uv", "pip", "install", "--force-reinstall", str(bootloader_build_dir)], check=True)

        print("\nCustom bootloader built and installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: Bootloader build failed: {e}")
        print("\nRevert back to installing with standard PyInstaller bootloader...")
    except Exception as e:
        print(f"\nERROR: Unexpected error during bootloader build: {e}")


def process_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Stellaris Checksum Patcher with PyInstaller")

    parser.add_argument(
        "-p",
        "--platform",
        choices=["linux", "windows", "auto"],
        default="auto",
        help="Target platform for the build (default: auto-detect)",
    )

    parser.add_argument("-kb", "--keep-build", action="store_true", help="Keep build files after building.")

    parser.add_argument(
        "--skip-bootloader",
        action="store_true",
        help="Skip custom PyInstaller bootloader build (use standard PyInstaller bootloader)",
    )

    parser.add_argument(
        "--force-bootloader", action="store_true", help="Force rebuild of custom bootloader even if one exists"
    )

    args = parser.parse_args()

    return args


def main():
    SYS_PLATFORM = platform.system().lower()

    args = process_args()

    # Handle custom bootloader
    if not args.skip_bootloader:
        if args.force_bootloader or not check_bootloader_exists():
            print("Custom bootloader not found or rebuild requested.")

            # Project root
            script_dir = Path(__file__).parent
            project_root = script_dir.parent

            if not build_custom_bootloader(project_root):
                print("\nWARNING: Continuing with standard bootloader...")
        else:
            print("Detected custom bootloader; using existing.")
    else:
        print("Skipping custom bootloader build.")

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
        "pyinstaller",
        "--onefile",
        "--clean",
        "--noconfirm",
        f"--name={output_filename}",
        # Add data files
        "--add-data=src/ui/fonts:ui/fonts",
        "--add-data=src/ui/icons:ui/icons",
        "--add-data=src/ui/styles:ui/styles",
        "--add-data=src/achievements:achievements",
        "--add-data=src/patch_patterns/patterns.json:patch_patterns",
        # PySide6 hooks
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=PySide6.QtWidgets",
        "--collect-submodules=PySide6",
    ]

    # Additional conditional arguments
    if arg_platform == "windows":
        cmd.extend(
            [
                "--icon=src/ui/icons/checksum_patcher_icon.ico",
                "--noconsole",
                # Disabling UPX compression could reduce false positives
                "--noupx",
            ]
        )
    else:
        cmd.extend(["--noupx"])  # Disabling UPX compression could reduce false positives

    cmd.append(str(entry_point))

    # Run the build
    try:
        subprocess.run(cmd, cwd=project_root, check=True)
        print(f"\nBuild process finished: {output_filename}")

        # PyInstaller outputs to dist/ folder
        dist_path = project_root / "dist" / output_filename

        if dist_path.exists():
            # Cut the file to the main project folder
            shutil.move(dist_path, project_root / output_filename)
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
            elif item.name == SPEC_FILE and item.is_file():
                print(f"  Removing: {item.name}")
                try:
                    item.unlink()
                except Exception as e:
                    print(f"  Error removing {item.name}: {e}")
    else:
        print(f"\nKeeping build files (--keep-build specified)")


if __name__ == "__main__":
    main()
