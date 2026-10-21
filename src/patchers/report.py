"""
Report command: shows where the checksum patch would be applied, without changing anything.

Run from the `src` folder:

    uv run python -m patchers.report path/to/stellaris.exe
"""

import re
import struct
import sys
from pathlib import Path
from typing import List

from patchers.auto_patch import CALL_LENGTH, DEFAULT_CHECKSUM_STRING, Executable, scan

def _nearby_strings(exe: Executable, offset: int, before: int = 0x200, after: int = 0x400) -> List[str]:
    """Readable strings referenced by LEA instructions around `offset`. Helps tell the sites apart."""
    found = []
    start = max(0, offset - before)
    for match in re.finditer(rb"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]", exe.data[start : offset + after]):
        at = start + match.start()
        address = exe.address_of(at)
        if address is None:
            continue
        target = exe.offset_of(address + 7 + struct.unpack_from("<i", exe.data, at + 3)[0])
        if target is None:
            continue
        text = exe.data[target : target + 64].split(b"\x00")[0]
        if len(text) >= 6 and all(32 <= c < 127 for c in text) and not text.startswith(b"C:\\"):
            found.append(text.decode())
    return list(dict.fromkeys(found))[:5]


def report(path: Path, checksum_string: str = DEFAULT_CHECKSUM_STRING) -> int:
    data = path.read_bytes()
    exe = Executable(data)
    result = scan(data, checksum_string)

    print(f"File:              {path}")
    print(f"Format:            {exe.format}")
    if result.error:
        print(f"ERROR:             {result.error}")
        return 1

    print(f"Checksum string:   {result.checksum}")
    if result.compare_function is not None:
        print(f"Compare function:  {result.compare_function:#x}")
    print(f"Sites:             {len(result.sites)} ({len(result.unpatched)} unpatched)")
    print()
    print(f"{'call offset':>12}  {'address':>12}  {'status':9}  {'next bytes':35}  nearby strings")
    for site in result.sites:
        status = "patched" if site.patched else "original"
        address = exe.address_of(site.call_offset) or 0
        next_bytes = data[site.call_offset + CALL_LENGTH : site.call_offset + CALL_LENGTH + 12].hex(" ").upper()
        nearby = ", ".join(s for s in _nearby_strings(exe, site.reference_offset) if s != result.checksum)
        print(f"{site.call_offset:#12x}  {address:#12x}  {status:9}  {next_bytes:35}  {nearby}")
    for offset in result.skipped:
        print(f"{'':>12}  skipped reference at {offset:#x} (no CALL to the compare function after it)")
    return 0


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        print("Usage: python -m patchers.report <executable> [checksum_string_regex]")
        sys.exit(2)
    sys.exit(report(Path(sys.argv[1]), *sys.argv[2:]))
