"""
Locating patch sites in a binary that has been hexlified into a string.

Pattern placeholders:
    %s  The bytes to patch (hex_find / hex_replace). Patching happens exactly here.
    %a  A 4-byte operand that must point to a string matching the patch's `anchor_string`.
        Either a RIP-relative displacement (e.g. `488D0D%a` = LEA RCX,[rip+disp32])
        or an absolute address (e.g. `BF%a` = MOV EDI,imm32 in non-PIE ELF builds).
"""

import logging
import re
import struct
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

log = logging.getLogger("Hex Matching")

TARGET_GROUP = "target"
ANCHOR_GROUP = "anchor"

_ANCHOR_REGEX = f"(?P<{ANCHOR_GROUP}>.{{8}})"
_MAX_STRING_LEN = 512


def build_regex(pattern: str, hex_value: str) -> re.Pattern:
    """Compile a pattern, turning `%s` into a named group holding `hex_value` and `%a` into the anchor group."""
    pattern_string = pattern.replace("%s", f"(?P<{TARGET_GROUP}>{hex_value})", 1)
    pattern_string = pattern_string.replace("%a", _ANCHOR_REGEX, 1)
    return re.compile(pattern_string, re.IGNORECASE)


def find_aligned(
    regex: re.Pattern, binary_hex: str, accept: Optional[Callable[[re.Match], bool]] = None
) -> Optional[re.Match]:
    """
    Return the first match that starts on a byte boundary (even hex index) and passes `accept`.

    A hex string regex can otherwise match "half a byte" off, which would patch the wrong bytes.
    Searches one character past each rejected match so overlapping candidates are not skipped.
    """
    pos = 0
    while True:
        match = regex.search(binary_hex, pos)
        if not match:
            return None

        target_ok = TARGET_GROUP not in regex.groupindex or match.start(TARGET_GROUP) % 2 == 0
        if match.start() % 2 == 0 and target_ok and (accept is None or accept(match)):
            return match

        pos = match.start() + 1


def target_span(match: re.Match, hex_find: str) -> Optional[Tuple[int, int]]:
    """Hex string span of the bytes to patch. Falls back to the legacy last-occurrence search for patterns without `%s`."""
    if TARGET_GROUP in match.re.groupindex and match.start(TARGET_GROUP) != -1:
        return match.span(TARGET_GROUP)

    index = match.group().upper().rfind(hex_find.upper())
    if index == -1 or (match.start() + index) % 2:
        return None
    return match.start() + index, match.start() + index + len(hex_find)


@dataclass
class _Segment:
    file_offset: int
    va: int
    size: int


class BinaryImage:
    """Minimal PE / ELF64 loader: maps file offsets to virtual addresses and reads strings."""

    def __init__(self, data: bytes):
        self.data = data
        self.segments: List[_Segment] = []
        self.format = "unknown"

        try:
            if data[:2] == b"MZ":
                self._parse_pe()
            elif data[:4] == b"\x7fELF" and data[4] == 2:
                self._parse_elf64()
        except (struct.error, IndexError) as e:
            log.warning(f"Failed to parse executable headers: {e}")
            self.segments = []

        if not self.segments:
            self.format = "unknown"

    @property
    def supported(self) -> bool:
        return bool(self.segments)

    def _parse_pe(self):
        pe = struct.unpack_from("<I", self.data, 0x3C)[0]
        if self.data[pe : pe + 4] != b"PE\0\0":
            return
        num_sections = struct.unpack_from("<H", self.data, pe + 6)[0]
        optional_size = struct.unpack_from("<H", self.data, pe + 20)[0]
        magic = struct.unpack_from("<H", self.data, pe + 24)[0]
        if magic == 0x20B:  # PE32+
            image_base = struct.unpack_from("<Q", self.data, pe + 24 + 24)[0]
        else:
            image_base = struct.unpack_from("<I", self.data, pe + 24 + 28)[0]

        for i in range(num_sections):
            header = pe + 24 + optional_size + i * 40
            virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from("<IIII", self.data, header + 8)
            size = min(virtual_size or raw_size, raw_size)
            if size:
                self.segments.append(_Segment(raw_offset, image_base + virtual_address, size))
        self.format = "pe"

    def _parse_elf64(self):
        endian = "<" if self.data[5] == 1 else ">"
        ph_offset = struct.unpack_from(endian + "Q", self.data, 0x20)[0]
        ph_size, ph_count = struct.unpack_from(endian + "HH", self.data, 0x36)
        for i in range(ph_count):
            header = ph_offset + i * ph_size
            p_type = struct.unpack_from(endian + "I", self.data, header)[0]
            if p_type != 1:  # PT_LOAD
                continue
            p_offset, p_vaddr = struct.unpack_from(endian + "QQ", self.data, header + 8)
            p_filesz = struct.unpack_from(endian + "Q", self.data, header + 32)[0]
            if p_filesz:
                self.segments.append(_Segment(p_offset, p_vaddr, p_filesz))
        self.format = "elf"

    def offset_to_va(self, offset: int) -> Optional[int]:
        for seg in self.segments:
            if seg.file_offset <= offset < seg.file_offset + seg.size:
                return seg.va + offset - seg.file_offset
        return None

    def va_to_offset(self, va: int) -> Optional[int]:
        for seg in self.segments:
            if seg.va <= va < seg.va + seg.size:
                return va - seg.va + seg.file_offset
        return None

    def read_cstring(self, va: int) -> Optional[str]:
        offset = self.va_to_offset(va)
        if offset is None:
            return None
        end = self.data.find(b"\0", offset, offset + _MAX_STRING_LEN)
        if end == -1:
            return None
        return self.data[offset:end].decode("latin-1")

    def anchor_strings(self, match: re.Match) -> List[str]:
        """Strings the `%a` operand could point to: as a RIP-relative displacement and as an absolute address."""
        value = struct.unpack("<I", bytes.fromhex(match.group(ANCHOR_GROUP)))[0]
        displacement = value - (1 << 32) if value & 0x80000000 else value

        candidates = [value]  # absolute address
        # RIP-relative: the operand is the last field, so RIP is the address right after it
        next_instruction_va = self.offset_to_va(match.end(ANCHOR_GROUP) // 2)
        if next_instruction_va is not None:
            candidates.insert(0, next_instruction_va + displacement)

        found = []
        for va in candidates:
            text = self.read_cstring(va)
            if text is not None:
                found.append(text)
        return found


def make_anchor_check(image: BinaryImage, anchor_string: str) -> Callable[[re.Match], bool]:
    """Build an `accept` callback that requires the `%a` operand to reference a string fully matching `anchor_string`."""
    anchor_regex = re.compile(anchor_string)

    def accept(match: re.Match) -> bool:
        return any(anchor_regex.fullmatch(text) for text in image.anchor_strings(match))

    return accept
