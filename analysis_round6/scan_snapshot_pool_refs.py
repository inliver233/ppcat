#!/usr/bin/env python3
"""Scan ppcat isolate snapshot for raw 0x80 + VLE(ref) anchor positions.

This script does not solve ref->slot deserialization. It only provides an
independent proof artifact for the seven critical string refs discussed in
analysis_round6 by locating the exact byte position of their tagged-object
entries inside the isolate snapshot.
"""

from __future__ import annotations

import argparse
from pathlib import Path


SNAPSHOT_FILE_OFFSET = 0x3330
SNAPSHOT_SIZE = 0x45C930

DEFAULT_TARGETS = [26842, 30947, 29112, 27673, 30922, 21707, 22466]
KNOWN_FILE_OFFSETS = {
    26842: 0x2EB53C,
    30947: 0x2EB540,
    29112: 0x2ECE05,
    27673: 0x2EEECA,
    30922: 0x2F0415,
    21707: 0x2F8C81,
    22466: 0x305C5A,
}


def encode_vle_unsigned(value: int) -> bytes:
    if value < 0:
        raise ValueError("value must be non-negative")
    out = bytearray()
    while True:
        chunk = value & 0x7F
        value >>= 7
        if value == 0:
            out.append(chunk | 0x80)
            return bytes(out)
        out.append(chunk)


def find_all(haystack: bytes, needle: bytes) -> list[int]:
    hits: list[int] = []
    pos = 0
    while True:
        pos = haystack.find(needle, pos)
        if pos < 0:
            return hits
        hits.append(pos)
        pos += 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "libapp",
        nargs="?",
        default="lib/arm64-v8a/libapp.so",
        help="Path to unpatched libapp.so (default: ./lib/arm64-v8a/libapp.so)",
    )
    parser.add_argument(
        "refs",
        nargs="*",
        type=int,
        default=DEFAULT_TARGETS,
        help="Ref ids to scan (default: known seven anchors)",
    )
    args = parser.parse_args()

    data = Path(args.libapp).read_bytes()
    snapshot = data[SNAPSHOT_FILE_OFFSET : SNAPSHOT_FILE_OFFSET + SNAPSHOT_SIZE]

    print("ref\tcount\trel_offset\tfile_offset\tstatus")
    bad = False
    for ref in args.refs:
        pattern = b"\x80" + encode_vle_unsigned(ref)
        hits = find_all(snapshot, pattern)
        if not hits:
            print(f"{ref}\t0\t-\t-\tMISS")
            bad = True
            continue

        expected = KNOWN_FILE_OFFSETS.get(ref)
        for i, rel in enumerate(hits):
            file_off = SNAPSHOT_FILE_OFFSET + rel
            status = "OK"
            if expected is not None and file_off != expected:
                status = f"EXPECTED 0x{expected:x}"
                bad = True
            if i == 0:
                print(f"{ref}\t{len(hits)}\t0x{rel:x}\t0x{file_off:x}\t{status}")
            else:
                print(f"{ref}\t{len(hits)}\t0x{rel:x}\t0x{file_off:x}\tEXTRA")
                bad = True
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
