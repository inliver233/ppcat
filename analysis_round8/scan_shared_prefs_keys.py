#!/usr/bin/env python3
"""Scan likely shared_preferences wrapper callsites and recover nearby key strings."""

from __future__ import annotations

import json
from pathlib import Path

from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN


LIBAPP = Path("libapp.so")
STRINGS = Path("unflutter_strings.txt")
POOL_JSON = Path("pool_deserialized.json")
POOL_ACCESSES = Path("analysis_round6/pool_accesses.txt")

# Semantics are inferred from the shared_preferences method-name bridge sites around 0x599xxx.
WRAPPERS = {
    0x9052AC: "setBool-ish",
    0x905260: "setDouble-ish",
    0x905214: "setInt-ish",
    0x9051CC: "setString-ish",
    0x905180: "setStringList-ish",
    0x904DC4: "clear/aux-ish",
    0x4EA988: "getAll-ish",
}


def load_strings() -> dict[int, str]:
    out: dict[int, str] = {}
    for line in STRINGS.read_text(errors="ignore").splitlines():
        if "[ref=" not in line:
            continue
        try:
            ref = int(line.split("[ref=")[1].split("]")[0])
            text = line.split('"', 1)[1].rsplit('"', 1)[0]
        except Exception:
            continue
        out[ref] = text
    return out


def load_pool_maps() -> tuple[dict[int, tuple[int, int]], dict[int, int]]:
    by_ref = {int(k): tuple(v) for k, v in json.loads(POOL_JSON.read_text())["by_ref"].items()}
    off_to_ref = {off: ref for ref, (_idx, off) in by_ref.items()}
    return by_ref, off_to_ref


def load_pc_to_off() -> dict[int, int]:
    out: dict[int, int] = {}
    for line in POOL_ACCESSES.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        pc_s, off_s, *_ = line.split()
        out[int(pc_s, 16)] = int(off_s, 16)
    return out


def decode_bl_targets(data: bytes, targets: set[int]) -> dict[int, list[int]]:
    out = {t: [] for t in targets}
    for addr in range(0x460000, len(data) - 4, 4):
        word = int.from_bytes(data[addr : addr + 4], "little")
        if (word >> 26) != 0b100101:
            continue
        imm26 = word & 0x03FFFFFF
        if imm26 & (1 << 25):
            imm26 -= 1 << 26
        target = addr + (imm26 << 2)
        if target in out:
            out[target].append(addr)
    return out


def main() -> int:
    data = LIBAPP.read_bytes()
    strings = load_strings()
    _by_ref, off_to_ref = load_pool_maps()
    pc_to_off = load_pc_to_off()
    md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)

    xrefs = decode_bl_targets(data, set(WRAPPERS))
    for target, label in WRAPPERS.items():
        print(f"== wrapper 0x{target:x} {label} ==")
        for callsite in xrefs[target]:
            refs = []
            for ins in md.disasm(data[max(0, callsite - 0x40) : callsite], max(0, callsite - 0x40)):
                off = pc_to_off.get(ins.address)
                if off is None:
                    continue
                ref = off_to_ref.get(off)
                if ref is None:
                    continue
                text = strings.get(ref, "")
                refs.append((ins.address, ref, text))
            # de-duplicate while preserving order
            seen = set()
            uniq = []
            for addr, ref, text in refs:
                key = (ref, text)
                if key in seen:
                    continue
                seen.add(key)
                uniq.append((addr, ref, text))
            if not uniq:
                continue
            print(f"  callsite 0x{callsite:x}")
            for addr, ref, text in uniq:
                print(f"    pc=0x{addr:x} ref={ref:>6} text={text!r}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
