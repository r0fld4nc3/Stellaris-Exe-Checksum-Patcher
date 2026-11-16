"""
Report command: shows where each patch would be applied, without changing anything.

Run from the `src` folder:

    uv run python -m patchers.report path/to/stellaris.exe [path/to/patterns_v2.json]

Uses the bundled patterns_v2.json unless another patterns file is given.
"""

import sys
from pathlib import Path

from patch_patterns.patterns import PATTERNS_DISTRIBUTED_FILE
from patchers.auto_patch import TargetSite, Executable, ScanResult, nearby_strings
from patchers.models import PatchConfiguration, Platform
from patchers.pdx_patchers import Patcher

GAME = "Stellaris"
SHOWN_NEARBY_STRINGS = 4


def _print_site(exe: Executable, target_text: str, site: TargetSite, status: str) -> None:
    address = exe.address_of(site.call_offset) or 0
    patch_name = site.patch_name or "-"

    nearby = []
    for _, text in nearby_strings(exe, site.reference_offset):
        is_source_path = text.startswith("C:\\")
        if text != target_text and not is_source_path and text not in nearby:
            nearby.append(text)
    shown = ", ".join(nearby[:SHOWN_NEARBY_STRINGS])

    print(f"{site.call_offset:#12x}  {address:#12x}  {status:11}  {patch_name:17}  {site.matched_by:40}  {shown}")


def _print_result(exe: Executable, result: ScanResult) -> None:
    if result.error:
        print(f"ERROR:             {result.error}")
        return

    print(f"Target string:     {result.target_text}")
    if result.compare_function is not None:
        print(f"Compare function:  {result.compare_function:#x}")
    print(f"Sites:             {len(result.sites)} ({len(result.unpatched)} unpatched)")
    print()
    print(f"{'call offset':>12}  {'address':>12}  {'status':11}  {'patch':17}  {'matched by':40}  nearby strings")
    for site in result.sites:
        status = "patched" if site.patched else "original"
        _print_site(exe, result.target_text, site, status)

    # Calls that don't go to the compare function, or can't be shown to. Never patched.
    for site in result.unconfirmed:
        _print_site(exe, result.target_text, site, "unconfirmed")

    for offset in result.skipped:
        print(f"{'':>12}  skipped reference at {offset:#x} (no CALL after it)")


def report(path: Path, patterns_file: Path = PATTERNS_DISTRIBUTED_FILE) -> int:
    data = path.read_bytes()
    exe = Executable(data)
    platform = Platform.from_file_format(exe.format)

    print(f"File:              {path}")
    print(f"Format:            {exe.format}")
    print(f"Patterns:          {patterns_file}")

    if platform is None:
        print("ERROR:             Unsupported executable format (only Windows PE and Linux ELF 64-bit are supported).")
        return 1

    patcher = Patcher(patterns_file)
    configuration = PatchConfiguration(game=GAME, platform=platform)
    scans = patcher.scan_data(configuration, data)
    if not scans:
        print(f"ERROR:             No patches for {platform}.")
        return 1

    # Patches with the same target_string share one scan result. Print each result once
    printed = []
    failed = False
    for result in scans.values():
        already_printed = any(result is other for other in printed)
        if already_printed:
            continue
        printed.append(result)
        _print_result(exe, result)
        print()
        if result.error:
            failed = True

    for patch_name, patch in patcher.get_available_patches(configuration).items():
        count = len(scans[patch_name].sites_of(patch_name))
        print(f"{patch.display_name:17} {count} site(s)")

    if failed:
        return 1
    return 0


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        print("Usage: python -m patchers.report <executable> [patterns_file]")
        sys.exit(2)
    sys.exit(report(*(Path(arg) for arg in sys.argv[1:])))
