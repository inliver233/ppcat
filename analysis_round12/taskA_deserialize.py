#!/usr/bin/env python3
"""Compatibility shim for test3 analysis_workdir scripts.

This lets test3's helper scripts run inside test1's repo layout without
copy-pasting the full analysis_workdir tree. It exposes:

- ``data``: raw libapp.so bytes
- ``parse_pool(fill_start, length)``: returns test3-style entry tuples
  ``(slot_index, entry_type, value, entry_bits, entry_bits_off)``

The parser follows the already-verified raw-entry ObjectPool layout used by
ppcat's custom Dart 2.19 snapshot.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIBAPP_CANDIDATES = [
    ROOT / "lib" / "arm64-v8a" / "libapp.so",
    ROOT / "libapp.so",
]


def _pick_libapp() -> Path:
    for path in LIBAPP_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError("libapp.so not found")


LIBAPP = _pick_libapp()
data = LIBAPP.read_bytes()


def read_unsigned(buf: bytes, pos: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        b = buf[pos]
        pos += 1
        if b > 0x7F:
            value |= (b - 0x80) << shift
            return value, pos
        value |= b << shift
        shift += 7


def parse_pool(fill_start: int, length: int) -> tuple[list[tuple[int, int, int | None, int, int]], int, int]:
    pos = fill_start
    actual_len, pos = read_unsigned(data, pos)
    if actual_len != length:
        raise ValueError(f"unexpected pool length {actual_len} != {length}")

    entries: list[tuple[int, int, int | None, int, int]] = []
    for idx in range(length):
        eb_off = pos
        eb = data[pos]
        pos += 1
        entry_type = eb & 0x7F
        val: int | None = None
        if entry_type in (0, 1):
            val, pos = read_unsigned(data, pos)
        elif entry_type in (2, 3, 4):
            val = None
        else:
            raise ValueError(
                f"unknown entry type {entry_type} bits=0x{eb:02x} idx={idx} off=0x{eb_off:x}"
            )
        entries.append((idx, entry_type, val, eb, eb_off))
    return entries, fill_start, pos


if __name__ == "__main__":
    entries, start, end = parse_pool(0x2E7043, 51140)
    print(f"# parsed {len(entries)} entries from 0x{start:x}..0x{end:x}")
