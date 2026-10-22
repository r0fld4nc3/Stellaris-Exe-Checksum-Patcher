"""
Automatic checksum patching. No Ghidra and no per-version byte patterns needed.

How the game checks its checksum
--------------------------------
The executable stores the official checksum as a plain text MD5 string, e.g. "32709cf254181b032b1b309a6ea09776".
Every place that checks whether the game files are unmodified does the same thing:

    LEA   RCX, [official_checksum]      ; load the address of the official checksum string
    CALL  strcmp                        ; compare it with the checksum calculated at runtime
    ...                                 ; strcmp returns 0 in EAX when they are equal

What we patch
-------------
We replace every one of those `CALL strcmp` instructions (5 bytes) with:

    XOR   EAX, EAX                      ; 31 C0     -> EAX = 0, i.e. "strings are equal"
    NOP                                 ; 0F 1F 00  -> 3-byte no-op so the size stays at 5 bytes

So every check sees "checksum matches", no matter how the compiler arranged the code around it.

How we find the calls
---------------------
1. Find the official checksum string: a standalone string matching `checksum_string` (from patterns.json).
2. Find every instruction in the code that loads that string's address.
3. Take the first CALL right after each of those instructions.
4. Safety check: all those calls must go to the same function (strcmp). Calls elsewhere are skipped.

Run this file directly to see a report without changing anything:

    python -m patchers.report path/to/stellaris.exe
"""

import logging
import re
import struct
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from config.definitions import FILE_FORMAT

log = logging.getLogger("Auto Patch")

DEFAULT_CHECKSUM_STRING = "[0-9a-f]{32}"
DEFAULT_REPLACEMENT = "31C00F1F00"  # XOR EAX,EAX + 3-byte NOP

CALL_OPCODE = 0xE8  # CALL rel32, always 5 bytes long
CALL_LENGTH = 5
MAX_CALL_DISTANCE = 16  # How many bytes after the string reference we look for the CALL

MACHO_MAGICS = (
    b"\xfe\xed\xfa\xce",  # 32-bit
    b"\xfe\xed\xfa\xcf",  # 64-bit
    b"\xce\xfa\xed\xfe",  # 32-bit, byte-swapped
    b"\xcf\xfa\xed\xfe",  # 64-bit, byte-swapped
    b"\xca\xfe\xba\xbe",  # Universal (fat) binary
)


# ============================================================================
# Reading the executable
# ============================================================================


@dataclass
class Section:
    """A part of the file that gets loaded into memory at `address`."""

    file_offset: int
    address: int
    size: int
    executable: bool


class Executable:
    """
    Minimal reader for Windows (PE) and Linux (ELF 64-bit) executables.

    Instructions refer to memory addresses, not file positions, so we need the section table
    to convert between the two.
    """

    def __init__(self, data: bytes):
        self.data = data
        self.format = "unknown"
        self.sections: List[Section] = []

        try:
            if data[:2] == b"MZ":
                self._read_pe()
            elif data[:4] == b"\x7fELF" and data[4] == 2:
                self._read_elf()
        except (struct.error, IndexError) as e:
            log.warning(f"Could not read executable headers: {e}")
            self.sections = []

    def _read_pe(self):
        pe = struct.unpack_from("<I", self.data, 0x3C)[0]
        if self.data[pe : pe + 4] != b"PE\0\0":
            return
        section_count = struct.unpack_from("<H", self.data, pe + 6)[0]
        optional_header_size = struct.unpack_from("<H", self.data, pe + 20)[0]
        image_base = struct.unpack_from("<Q", self.data, pe + 48)[0]  # 64-bit (PE32+) layout

        for i in range(section_count):
            header = pe + 24 + optional_header_size + i * 40
            virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from("<IIII", self.data, header + 8)
            flags = struct.unpack_from("<I", self.data, header + 36)[0]
            size = min(virtual_size or raw_size, raw_size)
            if size:
                executable = bool(flags & 0x20000000)  # IMAGE_SCN_MEM_EXECUTE
                self.sections.append(Section(raw_offset, image_base + virtual_address, size, executable))
        self.format = FILE_FORMAT.PE

    def _read_elf(self):
        header_offset = struct.unpack_from("<Q", self.data, 0x20)[0]
        header_size, header_count = struct.unpack_from("<HH", self.data, 0x36)

        for i in range(header_count):
            header = header_offset + i * header_size
            segment_type, flags = struct.unpack_from("<II", self.data, header)
            if segment_type != 1:  # PT_LOAD
                continue
            file_offset, address = struct.unpack_from("<QQ", self.data, header + 8)
            size = struct.unpack_from("<Q", self.data, header + 32)[0]
            if size:
                self.sections.append(Section(file_offset, address, size, executable=bool(flags & 1)))
        self.format = FILE_FORMAT.ELF

    def address_of(self, offset: int) -> Optional[int]:
        """File offset -> memory address."""
        for s in self.sections:
            if s.file_offset <= offset < s.file_offset + s.size:
                return s.address + offset - s.file_offset
        return None

    def offset_of(self, address: int) -> Optional[int]:
        """Memory address -> file offset."""
        for s in self.sections:
            if s.address <= address < s.address + s.size:
                return address - s.address + s.file_offset
        return None

    def call_target(self, call_offset: int) -> Optional[int]:
        """Address a `CALL rel32` at `call_offset` jumps to."""
        address = self.address_of(call_offset)
        if address is None:
            return None
        return address + CALL_LENGTH + struct.unpack_from("<i", self.data, call_offset + 1)[0]


def detect_format(path: Path) -> Optional[str]:
    """Executable format from the file's first bytes: "pe" (Windows), "elf" (Linux), "macho" (macOS) or None."""
    with open(path, "rb") as f:
        magic = f.read(4)

    if magic[:2] == b"MZ":
        return FILE_FORMAT.PE
    if magic == b"\x7fELF":
        return FILE_FORMAT.ELF
    if magic in MACHO_MAGICS:
        return FILE_FORMAT.MACHO
    return None


# ============================================================================
# Finding the checksum checks
# ============================================================================


@dataclass
class ChecksumSite:
    """One place in the code that compares against the official checksum."""

    reference_offset: int  # Instruction that loads the checksum string's address
    call_offset: int  # The CALL strcmp we replace (or already replaced)
    patched: bool  # True if the replacement bytes are already there


@dataclass
class ScanResult:
    checksum: Optional[str] = None
    compare_function: Optional[int] = None
    sites: List[ChecksumSite] = field(default_factory=list)
    skipped: List[int] = field(default_factory=list)  # String references with no matching CALL after them
    error: Optional[str] = None

    @property
    def unpatched(self) -> List[ChecksumSite]:
        return [s for s in self.sites if not s.patched]

    @property
    def fully_patched(self) -> bool:
        return bool(self.sites) and not self.unpatched


def _find_checksum_strings(exe: Executable, checksum_string: str) -> dict:
    """Return {address: text} for every standalone string fully matching `checksum_string`."""
    # Must be surrounded by NULL bytes, so the checksum inside a longer string (e.g. the version banner) is ignored
    pattern = re.compile(b"(?<=\x00)(?:" + checksum_string.encode() + b")(?=\x00)")
    found = {}
    for match in pattern.finditer(exe.data):
        address = exe.address_of(match.start())
        if address is not None:
            found[address] = match.group().decode("latin-1")
    return found


def _find_references(exe: Executable, addresses: dict) -> List[tuple]:
    """
    Find instructions that load one of `addresses`. Returns (instruction offset, offset right after it).

    - Windows and modern Linux: LEA reg, [rip + displacement]  (48/4C 8D xx + 4-byte displacement)
    - Older Linux (non-PIE):    MOV reg32, address             (B8..BF + 4-byte address)
    """
    references = []
    lea = re.compile(rb"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]", re.DOTALL)
    mov = re.compile(rb"[\xb8-\xbf]", re.DOTALL)

    for section in exe.sections:
        if not section.executable:
            continue
        start, end = section.file_offset, section.file_offset + section.size - 8

        for match in lea.finditer(exe.data, start, end):
            offset = match.start()
            next_instruction = section.address + (offset - start) + 7
            if next_instruction + struct.unpack_from("<i", exe.data, offset + 3)[0] in addresses:
                references.append((offset, offset + 7))

        if exe.format == FILE_FORMAT.ELF:
            for match in mov.finditer(exe.data, start, end):
                offset = match.start()
                if struct.unpack_from("<I", exe.data, offset + 1)[0] in addresses:
                    references.append((offset, offset + 5))

    return sorted(references)


def scan(data: bytes, checksum_string: str = DEFAULT_CHECKSUM_STRING, replacement: bytes = None) -> ScanResult:
    """Find every checksum comparison in an executable. Does not modify anything."""
    replacement = replacement or bytes.fromhex(DEFAULT_REPLACEMENT)
    result = ScanResult()
    exe = Executable(data)

    if not exe.sections:
        result.error = "Unsupported executable format (only Windows PE and Linux ELF 64-bit are supported)."
        return result

    # The official checksum string
    strings = _find_checksum_strings(exe, checksum_string)
    if not strings:
        result.error = f"No checksum string matching '{checksum_string}' found."
        return result
    if len(set(strings.values())) > 1:
        result.error = f"Found more than one possible checksum string: {sorted(set(strings.values()))}"
        return result
    result.checksum = next(iter(strings.values()))

    # + 3. Code referencing it, and the first CALL (or already patched bytes) after each reference
    candidates = []
    for reference_offset, after in _find_references(exe, strings):
        for offset in range(after, after + MAX_CALL_DISTANCE):
            if data[offset : offset + CALL_LENGTH] == replacement:
                result.sites.append(ChecksumSite(reference_offset, offset, patched=True))
                break
            if data[offset] == CALL_OPCODE:
                candidates.append((reference_offset, offset, exe.call_target(offset)))
                break
        else:
            result.skipped.append(reference_offset)

    # Safety check: the compare function (strcmp) is the one called after most references.
    # Already patched sites count towards the total, so once the real sites are patched a leftover
    # call to some other function can't take over the vote.
    if candidates:
        target, count = Counter(target for _, _, target in candidates).most_common(1)[0]
        total = len(candidates) + len(result.sites)  # result.sites only holds patched sites at this point
        if count * 2 >= total:
            result.compare_function = target
        for reference_offset, call_offset, target in candidates:
            if target == result.compare_function:
                result.sites.append(ChecksumSite(reference_offset, call_offset, patched=False))
            else:
                result.skipped.append(reference_offset)

    result.sites.sort(key=lambda s: s.call_offset)
    if not result.sites:
        result.error = "Found the checksum string, but no comparisons using it."
    return result


def patch_file(path: Path, checksum_string: str = DEFAULT_CHECKSUM_STRING, replacement: bytes = None) -> ScanResult:
    """
    Scan `path` and overwrite every unpatched CALL in place. Only the 5 bytes at each site are written.
    Check `result.error` afterwards; on error nothing is written.
    """
    replacement = replacement or bytes.fromhex(DEFAULT_REPLACEMENT)
    if len(replacement) != CALL_LENGTH:
        raise ValueError(f"Replacement must be exactly {CALL_LENGTH} bytes, got {len(replacement)}")

    result = scan(path.read_bytes(), checksum_string, replacement)
    if result.error:
        return result

    with open(path, "r+b") as f:
        for site in result.unpatched:
            f.seek(site.call_offset)
            f.write(replacement)
            site.patched = True
            log.info(f"Patched checksum compare at file offset {site.call_offset:#x}")
    return result
