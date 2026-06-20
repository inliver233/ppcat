#!/usr/bin/env python3
"""Verify shared_preferences bridge strings and nearby Dart AOT access sites.

Purpose:
- prove Flutter shared_preferences plugin exists in dex
- map Dart-side method-name strings (getAll/setBool/...) to ObjectPool slots and .text PCs
- highlight higher-value state keys that already flow through the same wrappers
"""

from __future__ import annotations

import json
from pathlib import Path

from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN


LIBAPP = Path("libapp.so")
STRINGS = Path("unflutter_strings.txt")
POOL_ACCESSES = Path("analysis_round6/pool_accesses.txt")
POOL_JSON = Path("pool_deserialized.json")
JADX_SP = Path("analysis_round6/out/jadx_classes2/sources/p026/C0659.java")
JADX_REG = Path("analysis_round6/out/jadx_classes2/sources/p026/C0661.java")

SP_METHODS = [
    "getAll",
    "setBool",
    "setDouble",
    "setInt",
    "setString",
    "setStringList",
    "remove",
    "clear",
    "commit",
]

STATE_KEYS = [
    "rewardTime",
    "favGridSortInt",
    "验证失败",
    "expiresDate",
    "expires",
]

INTERESTING_CALLS = {
    0xA56CC8: "0x9051cc wrapper: favGridSortInt",
    0xA576AC: "0x904dc4 wrapper: local state read before dialog",
    0xA7FDE8: "0x9051cc wrapper: rewardTime",
    0x8A1D10: "0x904dc4 wrapper: 验证失败 path",
    0xA65428: "0x905214 wrapper",
    0xA654BC: "0x905260 wrapper",
    0xA65670: "0x905180 wrapper",
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


def load_pool_map() -> tuple[dict[int, tuple[int, int]], dict[int, int]]:
    by_ref_raw = json.loads(POOL_JSON.read_text())["by_ref"]
    by_ref = {int(k): tuple(v) for k, v in by_ref_raw.items()}
    off_to_ref = {off: ref for ref, (_idx, off) in by_ref.items()}
    return by_ref, off_to_ref


def load_pool_accesses() -> dict[int, list[int]]:
    out: dict[int, list[int]] = {}
    for line in POOL_ACCESSES.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        pc_s, off_s, *_ = line.split()
        pc = int(pc_s, 16)
        off = int(off_s, 16)
        out.setdefault(off, []).append(pc)
    return out


def main() -> int:
    strings = load_strings()
    by_ref, off_to_ref = load_pool_map()
    off_to_pcs = load_pool_accesses()
    lib = LIBAPP.read_bytes()
    md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)

    print("== dex side plugin proof ==")
    print(f"{JADX_SP}: exists={JADX_SP.exists()}")
    print(f"{JADX_REG}: exists={JADX_REG.exists()}")
    if JADX_SP.exists():
        text = JADX_SP.read_text(errors="ignore")
        print('contains "FlutterSharedPreferences" =', "FlutterSharedPreferences" in text)
        print('contains "getAll" =', '"getAll"' in text)
        print('contains "setBool" =', '"setBool"' in text)

    print("\n== Dart method strings -> slot -> PCs ==")
    for ref, text in strings.items():
        if text not in SP_METHODS:
            continue
        idx, off = by_ref[ref]
        pcs = [hex(x) for x in off_to_pcs.get(off, [])[:12]]
        print(f"{text:14s} ref={ref:>5} slot=0x{idx:x} off=0x{off:x} pcs={pcs}")

    print("\n== state-key strings -> slot -> PCs ==")
    for ref, text in strings.items():
        if text not in STATE_KEYS:
            continue
        idx, off = by_ref[ref]
        pcs = [hex(x) for x in off_to_pcs.get(off, [])[:12]]
        print(f"{text:14s} ref={ref:>5} slot=0x{idx:x} off=0x{off:x} pcs={pcs}")

    print("\n== interesting wrapper call sites ==")
    for addr, label in INTERESTING_CALLS.items():
        print(f"0x{addr:x}: {label} bytes={lib[addr:addr+4].hex()}")

    print("\n== nearby pool annotations for interesting call sites ==")
    pc_to_off = {}
    for off, pcs in off_to_pcs.items():
        for pc in pcs:
            pc_to_off[pc] = off
    for addr in INTERESTING_CALLS:
        start = max(0, addr - 0x10)
        end = min(len(lib), addr + 0x18)
        print(f"\n-- around 0x{addr:x} --")
        for ins in md.disasm(lib[start:end], start):
            extra = ""
            off = pc_to_off.get(ins.address)
            if off is not None:
                ref = off_to_ref.get(off)
                if ref is not None:
                    extra = f" ; pool[0x{off:x}] ref={ref} {strings.get(ref, '')!r}"
                else:
                    extra = f" ; pool[0x{off:x}]"
            print(f"0x{ins.address:08x}: {ins.bytes.hex():16s} {ins.mnemonic:7s} {ins.op_str}{extra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
