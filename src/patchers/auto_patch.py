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
1. Find the target string (the official checksum): a standalone string matching `target_string` (from patterns.json).
2. Find every instruction in the code that loads that string's address.
3. Take the first CALL right after each of those instructions.
4. Safety check: all those calls must go to the same function (strcmp). Calls elsewhere are skipped.
   If most checks are already patched, the calls left are confirmed by the code after them instead:
   it must read strcmp's result. See `_pick_compare_function()`.

Which patch each call belongs to
--------------------------------
Each check does something different (achievements, the yellow version text, the tooltip...), so patches can be
picked separately. `label_sites()` gives every site to one patch, using that patch's `SiteRule` from patterns.json:

1. `site_overrides`: call offsets listed for this exact build (keyed by its checksum). For emergencies only.
2. `near_strings`: game strings (UI names, localisation keys, file paths) loaded in the same function as the site.
   Closest wins.
3. The same strings in the functions that call the site's function, for checks inside small helper functions.
4. Sites still without a patch go to the patch with `takes_unmatched_sites` (the required Checksum patch),
   so a check that moved after a game update still gets patched.

Run this file directly to see a report without changing anything:

    python -m patchers.report path/to/stellaris.exe
"""

import bisect
import logging
import re
import struct
from collections import Counter
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Dict, List, Optional, Tuple

log = logging.getLogger("Auto Patch")

DEFAULT_TARGET_STRING = "[0-9a-f]{32}"
DEFAULT_REPLACEMENT = "31C00F1F00"  # XOR EAX,EAX + 3-byte NOP

CALL_OPCODE = 0xE8  # CALL rel32, always 5 bytes long
CALL_LENGTH = 5  # In bytes
CALL_PATTERN = re.compile(rb"\xe8")
MAX_CALL_DISTANCE = 16  # How many bytes after the string reference we look for the CALL

# LEA reg, [rip + displacement]: 48/4C 8D xx + 4-byte displacement
LEA_RIP_PATTERN = re.compile(rb"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]")
LEA_LENGTH = 7  # In bytes

# MOV reg32, address: B8..BF + 4-byte address
MOV_IMMEDIATE_PATTERN = re.compile(rb"[\xb8-\xbf]")
MOV_LENGTH = 5  # In bytes

# What code does right after `CALL strcmp`: read the result, a 32-bit number in EAX
#   85 C0             TEST EAX, EAX
#   [41] 89 C0..C7    MOV reg32, EAX
#   [44] 8B C8..F8    MOV reg32, EAX (the other way to write it)
RESULT_CHECK_PATTERN = re.compile(rb"\x85\xc0|\x41?\x89[\xc0-\xc7]|\x44?\x8b[\xc8\xd0\xd8\xe0\xe8\xf0\xf8]")

# Where to look for `near_strings` around the instruction that loads the target string,
# when the function holding it is unknown. Otherwise the whole function is searched
NEAR_STRINGS_BEFORE = 0x200  # In bytes
NEAR_STRINGS_AFTER = 0x400  # In bytes
MAX_STRING_LENGTH = 256  # In bytes, longer strings are cut off

PE_FUNCTION_ENTRY = "<III"  # Function start, function end, unwind info
ELF_PT_LOAD = 1  # Part of the file that gets loaded into memory
ELF_PT_GNU_EH_FRAME = 0x6474E550  # The function lookup table (.eh_frame_hdr)
# How the lookup table's fields are stored. Every x86-64 Linux linker writes this layout, others are not read
ELF_FUNCTION_TABLE_LAYOUT = b"\x1b\x03\x3b"
ELF_FUNCTION_ENTRY = "<ii"  # Function start, its unwind entry. Both relative to the table's address


class FILE_FORMAT:
    """Executable formats `detect_format()` returns."""

    PE: str = "pe"  # Windows
    ELF: str = "elf"  # Linux
    MACHO: str = "macho"  # macOS


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
        self._elf_function_table: Optional[Tuple[int, int]] = None  # (file offset, address)

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
            file_offset, address = struct.unpack_from("<QQ", self.data, header + 8)
            if segment_type == ELF_PT_GNU_EH_FRAME:
                self._elf_function_table = (file_offset, address)
            if segment_type != ELF_PT_LOAD:
                continue
            size = struct.unpack_from("<Q", self.data, header + 32)[0]
            if size:
                self.sections.append(Section(file_offset, address, size, executable=bool(flags & 1)))
        self.format = FILE_FORMAT.ELF

    @cached_property
    def functions(self) -> List[Tuple[int, int]]:
        """
        (start address, end address) of every function, sorted. Empty if they can't be read.

        Both formats list their functions, so the game can clean up after an error at any point in the code.
        Read on first use only: it takes a moment, and only `label_sites()` needs it.
        """
        try:
            if self.format == FILE_FORMAT.PE:
                return self._read_pe_functions()
            if self.format == FILE_FORMAT.ELF:
                return self._read_elf_functions()
        except (struct.error, IndexError) as e:
            log.warning(f"Could not read the executable's function table: {e}")
        return []

    def _read_pe_functions(self) -> List[Tuple[int, int]]:
        """Functions from the exception table (.pdata)."""
        pe = struct.unpack_from("<I", self.data, 0x3C)[0]
        image_base = struct.unpack_from("<Q", self.data, pe + 48)[0]
        # Entry 3 of the data directory, in the 64-bit (PE32+) layout
        table_address, table_size = struct.unpack_from("<II", self.data, pe + 24 + 112 + 3 * 8)
        table_offset = self.offset_of(image_base + table_address)
        if table_offset is None:
            return []

        entry_size = struct.calcsize(PE_FUNCTION_ENTRY)
        table = self.data[table_offset : table_offset + table_size - table_size % entry_size]

        functions = []
        for start, end, _ in struct.iter_unpack(PE_FUNCTION_ENTRY, table):
            if start:
                functions.append((image_base + start, image_base + end))
        return sorted(functions)

    def _read_elf_functions(self) -> List[Tuple[int, int]]:
        """Functions from the unwind lookup table (.eh_frame_hdr), which points to an unwind entry per function."""
        if self._elf_function_table is None:
            return []
        table_offset, table_address = self._elf_function_table

        # Header: version (1 byte), layout (3 bytes), a pointer we don't need (4 bytes), entry count (4 bytes)
        if self.data[table_offset + 1 : table_offset + 4] != ELF_FUNCTION_TABLE_LAYOUT:
            return []
        entry_count = struct.unpack_from("<I", self.data, table_offset + 8)[0]
        entries_offset = table_offset + 12
        entries = self.data[entries_offset : entries_offset + entry_count * struct.calcsize(ELF_FUNCTION_ENTRY)]

        functions = []
        for start, unwind_entry in struct.iter_unpack(ELF_FUNCTION_ENTRY, entries):
            unwind_entry_offset = self.offset_of(table_address + unwind_entry)
            if unwind_entry_offset is None:
                continue
            # Unwind entry: its length, its parent, function start, function size (4 bytes each)
            size = struct.unpack_from("<I", self.data, unwind_entry_offset + 12)[0]
            functions.append((table_address + start, table_address + start + size))
        return sorted(functions)

    def function_of(self, address: int) -> Optional[Tuple[int, int]]:
        """(start address, end address) of the function holding `address`. None if unknown."""
        # Last function starting at or before `address`
        index = bisect.bisect_right(self.functions, address, key=lambda function: function[0]) - 1
        if index < 0:
            return None

        start, end = self.functions[index]
        if address < end:
            return start, end
        return None

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

    def call_target(self, call_offset: int, call_address: Optional[int] = None) -> Optional[int]:
        """Address a `CALL rel32` at `call_offset` (loaded at `call_address`, looked up if not given) jumps to."""
        if call_address is None:
            call_address = self.address_of(call_offset)
        if call_address is None:
            return None
        return call_address + CALL_LENGTH + struct.unpack_from("<i", self.data, call_offset + 1)[0]

    def lea_target(self, lea_offset: int, lea_address: int) -> int:
        """Address a `LEA reg, [rip + displacement]` at `lea_offset` (loaded at `lea_address`) points to."""
        # The displacement is relative to the instruction after the LEA
        displacement = struct.unpack_from("<i", self.data, lea_offset + 3)[0]
        return lea_address + LEA_LENGTH + displacement


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
class TargetSite:
    """One place in the code that compares against the target string."""

    reference_offset: int  # Instruction that loads the target string's address
    call_offset: int  # The CALL strcmp we replace (or already replaced)
    patched: bool  # True if replacement bytes are already there
    patch_name: Optional[str] = None  # Patch this site belongs to, set by `label_sites()`
    matched_by: str = ""  # How `label_sites()` picked the patch, for logs and the report


@dataclass
class ScanResult:
    """Everything `scan()` found. Check `error` first."""

    target_text: Optional[str] = None  # The string that matched `target_string`, e.g. the official checksum
    compare_function: Optional[int] = None
    sites: List[TargetSite] = field(default_factory=list)
    skipped: List[int] = field(default_factory=list)  # String references with no CALL after them
    # CALLs after a string reference that don't go to the compare function, or can't be shown to. Never patched.
    unconfirmed: List[TargetSite] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def unpatched(self) -> List[TargetSite]:
        return [s for s in self.sites if not s.patched]

    @property
    def fully_patched(self) -> bool:
        return bool(self.sites) and not self.unpatched

    def sites_of(self, patch_name: str) -> List[TargetSite]:
        """Sites `label_sites()` gave to `patch_name`."""
        return [s for s in self.sites if s.patch_name == patch_name]

    def unconfirmed_of(self, patch_name: str) -> List[TargetSite]:
        """Unconfirmed sites `label_sites()` gave to `patch_name`."""
        return [s for s in self.unconfirmed if s.patch_name == patch_name]


def _find_target_strings(exe: Executable, target_string: str) -> Dict[int, str]:
    """Return {address: text} for every standalone string fully matching `target_string`."""
    # Must be surrounded by NULL bytes, so the checksum inside a longer string (e.g. the version banner) is ignored
    pattern = re.compile(b"(?<=\x00)(?:" + target_string.encode() + b")(?=\x00)")
    found = {}
    for match in pattern.finditer(exe.data):
        address = exe.address_of(match.start())
        if address is not None:
            found[address] = match.group().decode("latin-1")
    return found


def _find_references(exe: Executable, addresses: Dict[int, str]) -> List[Tuple[int, int]]:
    """
    Find instructions that load one of `addresses`. Returns (instruction offset, offset right after it).

    - Windows and modern Linux: LEA reg, [rip + displacement]
    - Older Linux (non-PIE):    MOV reg32, address
    """
    references = []

    for section in exe.sections:
        if not section.executable:
            continue
        start, end = section.file_offset, section.file_offset + section.size - 8

        for match in LEA_RIP_PATTERN.finditer(exe.data, start, end):
            offset = match.start()
            lea_address = section.address + (offset - start)
            if exe.lea_target(offset, lea_address) in addresses:
                references.append((offset, offset + LEA_LENGTH))

        if exe.format == FILE_FORMAT.ELF:
            for match in MOV_IMMEDIATE_PATTERN.finditer(exe.data, start, end):
                offset = match.start()
                if struct.unpack_from("<I", exe.data, offset + 1)[0] in addresses:
                    references.append((offset, offset + MOV_LENGTH))

    return sorted(references)


def _find_call_after(data: bytes, start: int, replacements: List[bytes]) -> Optional[int]:
    """Offset of the first CALL, or one of `replacements` (already patched), within MAX_CALL_DISTANCE of `start`."""
    for offset in range(start, start + MAX_CALL_DISTANCE):
        if data[offset : offset + CALL_LENGTH] in replacements:
            return offset
        if data[offset] == CALL_OPCODE:
            return offset
    return None


def _result_is_checked(data: bytes, call_offset: int) -> bool:
    """True if the instruction after the CALL at `call_offset` reads EAX as a number, as code does after strcmp."""
    return RESULT_CHECK_PATTERN.match(data, call_offset + CALL_LENGTH) is not None


def _pick_compare_function(
    data: bytes, candidates: List[Tuple[int, int, Optional[int]]], patched_count: int
) -> Optional[int]:
    """
    The compare function (strcmp) is the one called after most references, if it is at least half of all sites.
    `candidates` are (reference offset, call offset, call target) of each unpatched CALL.

    Already patched sites count towards the total, so once the real sites are patched a leftover
    call to some other function can't take over the vote.

    That also means the last checks can't win the vote when most are already patched (ex.: adding Tooltip later).
    They are then accepted if the code after each of them reads the result, as it does after strcmp.
    A leftover call to some other function (ex.: one that copies the checksum text) isn't followed by that.
    """
    if not candidates:
        return None

    call_targets = [target for _, _, target in candidates]
    target, count = Counter(call_targets).most_common(1)[0]
    total = len(candidates) + patched_count
    if count * 2 >= total:
        return target

    if patched_count == 0 or target is None:
        return None

    for _, call_offset, call_target in candidates:
        if call_target == target and not _result_is_checked(data, call_offset):
            return None
    return target


def scan(
    data: bytes, target_string: str = DEFAULT_TARGET_STRING, replacements: Optional[List[bytes]] = None
) -> ScanResult:
    """
    Find every comparison against the target string in an executable. Does not modify anything.

    `replacements` are the bytes patches write over a CALL. A site holding one of them counts as patched.
    """
    if not replacements:
        replacements = [bytes.fromhex(DEFAULT_REPLACEMENT)]
    result = ScanResult()
    exe = Executable(data)

    if not exe.sections:
        result.error = "Unsupported executable format (only Windows PE and Linux ELF 64-bit are supported)."
        return result

    # 1. The target string
    strings = _find_target_strings(exe, target_string)
    unique_strings = sorted(set(strings.values()))
    if not unique_strings:
        result.error = f"No target string matching '{target_string}' found."
        return result
    if len(unique_strings) > 1:
        result.error = f"Found more than one possible target string: {unique_strings}"
        return result
    result.target_text = unique_strings[0]

    # 2 + 3. Code referencing the string, and the first CALL (or already patched bytes) after each reference
    candidates = []  # (reference offset, call offset, call target) of each unpatched CALL
    for reference_offset, after_reference in _find_references(exe, strings):
        call_offset = _find_call_after(data, after_reference, replacements)

        if call_offset is None:
            result.skipped.append(reference_offset)
        elif data[call_offset : call_offset + CALL_LENGTH] in replacements:
            result.sites.append(TargetSite(reference_offset, call_offset, patched=True))
        else:
            candidates.append((reference_offset, call_offset, exe.call_target(call_offset)))

    # 4. Safety check: only patch calls to the compare function. At this point result.sites only holds patched sites.
    result.compare_function = _pick_compare_function(data, candidates, patched_count=len(result.sites))

    for reference_offset, call_offset, target in candidates:
        # A call whose target is unknown can't be shown to call the compare function.
        # Without this check it would match when there is no compare function, as both are None.
        if target is not None and target == result.compare_function:
            result.sites.append(TargetSite(reference_offset, call_offset, patched=False))
        else:
            result.unconfirmed.append(TargetSite(reference_offset, call_offset, patched=False))

    result.sites.sort(key=lambda s: s.call_offset)
    if not result.sites:
        result.error = "Found the target string, but no comparisons using it."
    return result


# ============================================================================
# Telling the sites apart
# ============================================================================


@dataclass
class SiteRule:
    """How to recognise the sites of one patch. See `label_sites()`."""

    near_strings: List[str] = field(default_factory=list)
    site_overrides: Dict[str, List[int]] = field(default_factory=dict)  # {build checksum: [call offsets]}
    takes_unmatched_sites: bool = False

    @property
    def has_rules(self) -> bool:
        return bool(self.near_strings or self.site_overrides)


def _function_range(exe: Executable, offset: int) -> Optional[Tuple[int, int]]:
    """(start offset, end offset) in the file of the function holding `offset`. None if unknown."""
    address = exe.address_of(offset)
    if address is None:
        return None

    function = exe.function_of(address)
    if function is None:
        return None

    start_address, end_address = function
    start = exe.offset_of(start_address)
    if start is None:
        return None
    return start, start + (end_address - start_address)


def nearby_strings(
    exe: Executable, offset: int, before: int = NEAR_STRINGS_BEFORE, after: int = NEAR_STRINGS_AFTER
) -> List[Tuple[int, str]]:
    """
    Readable strings loaded by LEA instructions in the function holding `offset`, as (distance in bytes, text),
    closest first. If that function is unknown, looks `before` and `after` bytes around `offset` instead.
    """
    found = []
    function_range = _function_range(exe, offset)
    if function_range:
        start, end = function_range
    else:
        start, end = max(0, offset - before), offset + after

    for match in LEA_RIP_PATTERN.finditer(exe.data, start, end):
        lea_offset = match.start()
        lea_address = exe.address_of(lea_offset)
        if lea_address is None:
            continue
        target = exe.offset_of(exe.lea_target(lea_offset, lea_address))
        if target is None:
            continue

        text = exe.data[target : target + MAX_STRING_LENGTH].split(b"\x00")[0]
        is_readable = len(text) >= 4 and all(32 <= c < 127 for c in text)
        if is_readable:
            found.append((abs(lea_offset - offset), text.decode()))

    found.sort()
    return found


def _patches_by_string(rules: Dict[str, SiteRule]) -> Dict[str, str]:
    """{near string: patch name}. A string listed by several patches belongs to the first."""
    patches_by_string = {}
    for patch_name, rule in rules.items():
        for text in rule.near_strings:
            if text not in patches_by_string:
                patches_by_string[text] = patch_name
    return patches_by_string


def _match_near_strings(exe: Executable, offset: int, patches_by_string: Dict[str, str]) -> Optional[Tuple[str, str]]:
    """
    (patch name, matched string) of the `near_strings` closest to `offset`, in the function holding it.
    None if that function loads no patch's strings.
    """
    for _, text in nearby_strings(exe, offset):
        patch_name = patches_by_string.get(text)
        if patch_name:
            return patch_name, text
    return None


def _find_callers(exe: Executable, sites: List[TargetSite]) -> Dict[int, List[int]]:
    """
    {site call offset: [offsets of CALLs to the function holding that site]}.
    Sites whose function is unknown get no callers.
    """
    callers = {site.call_offset: [] for site in sites}

    # {function start address: [call offsets of the sites inside that function]}
    sites_by_function = {}
    for site in sites:
        site_address = exe.address_of(site.call_offset)
        if site_address is None:
            continue
        function = exe.function_of(site_address)
        if function is None:
            continue
        function_start, _ = function
        sites_by_function.setdefault(function_start, []).append(site.call_offset)

    if not sites_by_function:
        return callers

    for section in exe.sections:
        if not section.executable:
            continue
        start, end = section.file_offset, section.file_offset + section.size - CALL_LENGTH

        for match in CALL_PATTERN.finditer(exe.data, start, end):
            call_offset = match.start()
            target = exe.call_target(call_offset, section.address + (call_offset - start))
            for site_offset in sites_by_function.get(target, []):
                callers[site_offset].append(call_offset)

    return callers


def _pick_catch_all(rules: Dict[str, SiteRule]) -> Optional[str]:
    """
    Patch that gets the sites no other patch matches: the first with `takes_unmatched_sites`.
    """
    flagged = [patch_name for patch_name, rule in rules.items() if rule.takes_unmatched_sites]
    if len(flagged) > 1:
        log.warning(f"Several patches have takes_unmatched_sites: {flagged}. Using '{flagged[0]}'.")
    if flagged:
        return flagged[0]

    for patch_name, rule in rules.items():
        if not rule.has_rules:
            return patch_name
    return None


def label_sites(data: bytes, result: ScanResult, rules: Dict[str, SiteRule]) -> None:
    """
    Give each site in `result` to one patch in `rules` ({patch name: rule}), setting `patch_name` and `matched_by`.
    Unconfirmed sites are labelled too, so a patch whose checks can't be confirmed can say so.
    Sites no rule matches keep `patch_name = None`. Order of `rules` decides ties.
    """
    if result.error or not rules:
        return

    exe = Executable(data)
    all_sites = result.sites + result.unconfirmed
    sites_by_offset = {site.call_offset: site for site in all_sites}
    patches_by_string = _patches_by_string(rules)

    # 1. Overrides for this exact build
    for patch_name, rule in rules.items():
        for call_offset in rule.site_overrides.get(result.target_text, []):
            site = sites_by_offset.get(call_offset)
            if site is None:
                log.warning(f"Override {call_offset:#x} for '{patch_name}' is not a checksum check. Ignoring it.")
                continue
            if site.patch_name is None:
                site.patch_name = patch_name
                site.matched_by = "override"

    # 2. Strings in the site's function
    for site in all_sites:
        if site.patch_name is not None:
            continue
        match = _match_near_strings(exe, site.reference_offset, patches_by_string)
        if match:
            site.patch_name, text = match
            site.matched_by = f"near '{text}'"

    # 3. Strings in the functions calling the site's function (ex.: a small IsChecksumOriginal() helper)
    unlabelled = [site for site in all_sites if site.patch_name is None]
    if unlabelled:
        callers = _find_callers(exe, unlabelled)
        for site in unlabelled:
            for caller_offset in callers[site.call_offset]:
                match = _match_near_strings(exe, caller_offset, patches_by_string)
                if match:
                    site.patch_name, text = match
                    site.matched_by = f"caller near '{text}'"
                    break

    # 4. Everything else
    catch_all = _pick_catch_all(rules)
    for site in all_sites:
        if site.patch_name is not None:
            continue
        if catch_all is None:
            log.warning(f"Checksum check at {site.call_offset:#x} doesn't belong to any patch. It won't be patched.")
            continue
        site.patch_name = catch_all
        site.matched_by = "unmatched"


# ============================================================================
# Patching
# ============================================================================


def patch_sites(path: Path, sites: List[TargetSite], replacement: bytes) -> None:
    """Overwrite the CALL at each of `sites` (from `scan()`) in place. Only the 5 bytes at each site are written."""
    if len(replacement) != CALL_LENGTH:
        raise ValueError(f"Replacement must be exactly {CALL_LENGTH} bytes, got {len(replacement)}")

    with open(path, "r+b") as f:
        for site in sites:
            f.seek(site.call_offset)
            f.write(replacement)
            site.patched = True
            log.info(f"Patched checksum compare at file offset {site.call_offset:#x} ({site.patch_name or 'all'})")
