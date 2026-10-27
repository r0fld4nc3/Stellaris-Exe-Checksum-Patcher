"""
Convert images (PNG, JPEG, ICO or anything macOS 'sips' can read) to macOS .icns.
macOS only: uses the built-in 'sips' and 'iconutil' tools. Needs only the Python standard library.

Usage:
    python3 tools/make-icns.py icon.png                       # writes icon.icns next to the source
    python3 tools/make-icns.py a.png b.png c.ico              # converts each file
    python3 tools/make-icns.py src/ui/icons/*.png -o out/     # writes into another folder

Sizes larger than the source image are skipped rather than upscaled.
Recommended 1024x1024 source for an icon that stays sharp at every size.
"""

import argparse
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SUPPORTED_PLATFORMS = ("darwin",)

# Base sizes of an .iconset. Each also has a @2x variant at double the pixels.
ICONSET_SIZES = (16, 32, 128, 256, 512)


def image_size(path: Path) -> tuple[int, int]:
    result = subprocess.run(
        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    values = {}
    for line in result.stdout.splitlines():
        key, _, value = line.strip().partition(": ")
        if key in ("pixelWidth", "pixelHeight"):
            values[key] = int(value)
    if len(values) != 2:
        raise ValueError("could not read image size (not an image?)")
    return values["pixelWidth"], values["pixelHeight"]


def convert(source: Path, output: Path) -> None:
    width, height = image_size(source)
    if width != height:
        print(f"  Warning: {source.name} is {width}x{height}, not square. It will be stretched.")
    largest = min(width, height)

    with tempfile.TemporaryDirectory() as tmp:
        iconset = Path(tmp) / "icon.iconset"
        iconset.mkdir()

        written = 0
        largest_written = 0
        for size in ICONSET_SIZES:
            for scale, suffix in ((1, ""), (2, "@2x")):
                pixels = size * scale
                if pixels > largest and written:
                    continue  # never upscale, but always write at least the smallest size
                subprocess.run(
                    [
                        "sips",
                        "-s",
                        "format",
                        "png",
                        "-z",
                        str(pixels),
                        str(pixels),
                        str(source),
                        "--out",
                        str(iconset / f"icon_{size}x{size}{suffix}.png"),
                    ],
                    capture_output=True,
                    check=True,
                )
                written += 1
                largest_written = max(largest_written, pixels)

        output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(output)], check=True)

    print(f"  {source} -> {output} (up to {largest_written}px)", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert images to macOS .icns icons.")
    parser.add_argument("images", nargs="+", type=Path, help="Image files to convert")
    parser.add_argument(
        "-o", "--output-dir", type=Path, help="Folder for the .icns files (default: next to each source)"
    )
    args = parser.parse_args()

    if platform.system().lower() not in SUPPORTED_PLATFORMS or not (shutil.which("sips") and shutil.which("iconutil")):
        print("Error: this script needs macOS ('sips' and 'iconutil').", file=sys.stderr)
        sys.exit(1)

    failed = 0
    outputs: dict[Path, Path] = {}  # output -> source, to handle name clashes like icon.png + icon.ico
    for source in args.images:
        if not source.is_file():
            print(f"  Skipping {source}: file not found", file=sys.stderr, flush=True)
            failed += 1
            continue

        output_dir = args.output_dir or source.parent
        output = (output_dir / f"{source.stem}.icns").resolve()
        if output in outputs:
            if outputs[output] != source.resolve():
                print(
                    f"  Skipping {source}: {output.name} already made from {outputs[output]}",
                    file=sys.stderr,
                    flush=True,
                )
                failed += 1
            continue
        outputs[output] = source.resolve()
        try:
            convert(source, output)
        except (subprocess.CalledProcessError, ValueError) as e:
            print(f"  Failed {source}: {e}", file=sys.stderr, flush=True)
            failed += 1

    if failed:
        print(f"\n{failed} of {len(args.images)} file(s) failed.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
