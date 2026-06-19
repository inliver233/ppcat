#!/usr/bin/env python3
"""Probe aligned 0x80+ReadUnsigned(ref) runs in isolate snapshot data.

This is a lightweight, repo-local companion to the temporary unflutter tests.
It does not try to parse the full ObjectPool. It only demonstrates that several
known anchor refs appear in aligned `0x80 + unsigned-vle(ref)` runs in the tail
of isolate snapshot data.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIBAPP = ROOT / "lib/arm64-v8a/libapp.so"
SNAPSHOT_JSON = ROOT / "unflutter_dump/snapshot.json"

TARGET_REFS = [
    21707,
    22466,
    26842,
    27673,
    29112,
    30922,
    30947,
]

KNOWN_SLOT_INDEX = {
    26842: 0x15B1,
    30947: 0x15B2,
    27673: 0x278D,
    30922: 0x2E2D,
}

RELAXED_OLD_POOL_NOP_TYPES = {2, 3, 27, 28}

ORDERED_ANCHORS = [
    26842,
    30947,
    29112,
    27673,
    30922,
    21707,
    22466,
]


def encode_unsigned(value: int) -> bytes:
    out = bytearray()
    x = value
    while x >= 0x80:
        out.append(x & 0x7F)
        x >>= 7
    out.append(x + 0x80)
    return bytes(out)


def read_unsigned(data: bytes, pos: int) -> tuple[int, int]:
    b = data[pos]
    pos += 1
    if b > 127:
        return b - 128, pos
    result = 0
    shift = 0
    while True:
        result |= b << shift
        shift += 7
        b = data[pos]
        pos += 1
        if b > 127:
            result |= (b - 128) << shift
            return result, pos


def read_tagged64(data: bytes, pos: int) -> tuple[int, int]:
    b = data[pos]
    pos += 1
    if b > 127:
        return b - 192, pos
    result = 0
    shift = 0
    while True:
        result |= b << shift
        shift += 7
        b = data[pos]
        pos += 1
        if b > 127:
            result |= (b - 192) << shift
            return result, pos


def parse_relaxed_old_pool_entry(data: bytes, pos: int) -> tuple[str, int | tuple[int, int] | None, int, int]:
    entry_pos = pos
    bits = data[pos]
    pos += 1
    type_bits = bits & 0x7F

    if type_bits in (0, 4):
        ref, pos = read_unsigned(data, pos)
        return "ref", ref, pos, bits
    if type_bits == 1:
        imm, pos = read_tagged64(data, pos)
        return "imm", imm, pos, bits
    if type_bits in RELAXED_OLD_POOL_NOP_TYPES:
        return "nop", None, pos, bits
    if type_bits == 29:
        lo, pos = read_tagged64(data, pos)
        hi, pos = read_tagged64(data, pos)
        return "imm128", (lo, hi), pos, bits
    raise ValueError(f"unsupported old-pool type_bits={type_bits} bits=0x{bits:02x} at 0x{entry_pos:x}")


def count_relaxed_entries(data: bytes, start: int, end: int) -> int:
    pos = start
    count = 0
    while pos < end:
        _, _, next_pos, _ = parse_relaxed_old_pool_entry(data, pos)
        if next_pos > end:
            raise ValueError(
                f"entry from 0x{pos:x} crosses end 0x{end:x} (next=0x{next_pos:x})"
            )
        pos = next_pos
        count += 1
    if pos != end:
        raise ValueError(f"misaligned relaxed parse: end pos=0x{pos:x}, want 0x{end:x}")
    return count


def main() -> None:
    snapshot_info = json.loads(SNAPSHOT_JSON.read_text())
    iso_start = int(snapshot_info["isolate_data"]["file_offset"])
    iso_size = int(snapshot_info["isolate_data"]["data_size"])
    lib = LIBAPP.read_bytes()
    iso = lib[iso_start : iso_start + iso_size]

    print(f"isolate_data: file_offset=0x{iso_start:x} size=0x{iso_size:x}")
    print()

    found: dict[int, int] = {}
    for ref in TARGET_REFS:
        pat = b"\x80" + encode_unsigned(ref)
        pos = iso.find(pat)
        found[ref] = pos
        if pos < 0:
            print(f"ref={ref} hit=NONE")
            continue
        print(
            f"ref={ref} rel=0x{pos:x} file=0x{pos + iso_start:x} "
            f"bytes={pat.hex(' ')}"
        )
    print()

    for ref in TARGET_REFS:
        pos = found[ref]
        if pos < 0:
            continue
        print(f"== ref={ref} neighborhood ==")
        for delta in range(-4, 5):
            start = pos + delta
            if start < 0 or start >= len(iso):
                continue
            tag = iso[start]
            if tag == 0x80:
                value, end = read_unsigned(iso, start + 1)
                print(
                    f"  rel=0x{start:x} delta={delta:+d} "
                    f"tag=0x80 ref={value} next=0x{end:x}"
                )
            elif tag == 0x81:
                value, end = read_tagged64(iso, start + 1)
                print(
                    f"  rel=0x{start:x} delta={delta:+d} "
                    f"tag=0x81 imm={value} next=0x{end:x}"
                )
            else:
                print(f"  rel=0x{start:x} delta={delta:+d} tag=0x{tag:02x}")
        print()

    print("== relaxed old-pool counts ==")
    for left, right in zip(ORDERED_ANCHORS, ORDERED_ANCHORS[1:]):
        start = found[left]
        end = found[right]
        if start < 0 or end < 0:
            continue
        parsed = count_relaxed_entries(iso, start, end)
        msg = (
            f"{left:>5} -> {right:<5} parsed_entries={parsed:<5} "
            f"rel=0x{start:x}->0x{end:x}"
        )
        if left in KNOWN_SLOT_INDEX and right in KNOWN_SLOT_INDEX:
            known_delta = KNOWN_SLOT_INDEX[right] - KNOWN_SLOT_INDEX[left]
            msg += f"  known_slot_delta={known_delta:<5} diff={parsed - known_delta:+d}"
        print(msg)

    if all(ref in found and found[ref] >= 0 for ref in (30947, 29112, 27673, 30922)):
        count_30947_29112 = count_relaxed_entries(iso, found[30947], found[29112])
        low = KNOWN_SLOT_INDEX[30947] + count_30947_29112
        high = low + 31
        print()
        print(
            "candidate slot window for ref=29112: "
            f"slot_idx=0x{low:x}..0x{high:x} "
            f"(slot_off=0x{low * 8:x}..0x{high * 8:x})"
        )
        total = count_relaxed_entries(iso, found[30947], found[30922])
        known_total = KNOWN_SLOT_INDEX[30922] - KNOWN_SLOT_INDEX[30947]
        print(
            "phase-shift check 30947->30922: "
            f"parsed_entries={total} known_slot_delta={known_total} diff={total - known_total:+d}"
        )


if __name__ == "__main__":
    main()
