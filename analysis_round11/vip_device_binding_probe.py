#!/usr/bin/env python3
"""Probe the VIP/device-binding chain on test1.

Goal:
- independently cross-check test3's "device-bound VIP" conclusion on test1
- keep the result narrow and reproducible
- avoid conflating the VIP chain with unrelated Java-side "expiresDate" strings
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

from capstone import CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, Cs


LIBAPP_CANDIDATES = [
    Path("lib/arm64-v8a/libapp.so"),
    Path("libapp.so"),
]
POOL_JSON = Path("pool_deserialized.json")
POOL_ACCESSES = Path("analysis_round6/pool_accesses.txt")
STRINGS = Path("unflutter_strings.txt")

KEY_REFS = [
    (2698, "hwMd5"),
    (4456, "bootTime"),
    (7406, "expiresDate"),
    (12022, "isFirstRun"),
    (16829, "https://ppcat.gentle.com/?i="),
    (26968, "remoteConfigSign"),
    (27170, "https://ppcat.gentle.com/?u="),
    (30874, "rule.bin"),
]

INTERESTING_FUNCS = [
    (0x8BC3C8, 0x8BC980, "rule.bin / bootTime / isFirstRun / remoteConfigSign 簇"),
    (0x8D10D0, 0x8D1300, "hwMd5 簇"),
    (0x911788, 0x911940, "共享状态门控 0x911788"),
    (0xB9FC84, 0xBA0A80, "VIP/绑定/reward 混合状态机 0xb9fc84"),
    (0xA54178, 0xA56800, "VIP 内容页 builder 0xa54178"),
    (0x871320, 0x871B60, "ppcat.gentle.com URL builder 0x871320"),
]

SNIPPETS = [
    (0x8BC650, 0x8BC710, "0x8bc3c8 内部: bootTime + remoteConfigSign"),
    (0x8BC730, 0x8BC760, "0x8bc3c8 内部: isFirstRun"),
    (0x8D65E0, 0x8D6630, "0x8d10d0 邻近: remoteConfigSign 回写"),
    (0x911840, 0x911890, "0x911788 内部: remoteConfigSign 取值"),
    (0xB9FCB4, 0xB9FE90, "0xb9fc84: 先过 0x911788 再进 0x8cf36c"),
    (0x871440, 0x8714C0, "0x871320 内部: ?u= URL 片段"),
    (0x871970, 0x871B50, "0x871320 内部: ?i= URL + deviceInfo/machine"),
]


def pick_libapp() -> Path:
    for path in LIBAPP_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError("libapp.so not found in expected locations")


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


def load_pool() -> tuple[dict[int, tuple[int, int]], dict[int, int]]:
    by_ref = {int(k): tuple(v) for k, v in json.loads(POOL_JSON.read_text())["by_ref"].items()}
    off_to_ref = {off: ref for ref, (_slot, off) in by_ref.items()}
    return by_ref, off_to_ref


def load_pool_accesses() -> tuple[dict[int, list[int]], list[tuple[int, int]]]:
    off_to_pcs: dict[int, list[int]] = {}
    pc_off_pairs: list[tuple[int, int]] = []
    for line in POOL_ACCESSES.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        pc_s, off_s, *_ = line.split()
        pc = int(pc_s, 16)
        off = int(off_s, 16)
        off_to_pcs.setdefault(off, []).append(pc)
        pc_off_pairs.append((pc, off))
    return off_to_pcs, pc_off_pairs


def find_func_start(data: bytes, pc: int) -> int | None:
    for addr in range(pc, max(0, pc - 0x8000), -4):
        if data[addr : addr + 4] == bytes.fromhex("fd79bfa9") and data[addr + 4 : addr + 8] == bytes.fromhex("fd030faa"):
            return addr
    return None


def bl_callers(data: bytes, target: int) -> list[int]:
    out: list[int] = []
    for addr in range(0x460000, len(data) - 4, 4):
        word = struct.unpack_from("<I", data, addr)[0]
        if (word >> 26) != 0b100101:
            continue
        imm26 = word & 0x03FFFFFF
        if imm26 & (1 << 25):
            imm26 -= 1 << 26
        if addr + (imm26 << 2) == target:
            out.append(addr)
    return out


def main() -> int:
    libapp = pick_libapp()
    data = libapp.read_bytes()
    strings = load_strings()
    by_ref, off_to_ref = load_pool()
    off_to_pcs, pc_off_pairs = load_pool_accesses()
    md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)

    print(f"# libapp = {libapp}")
    print("# note: Java-side p111/C1429.java also has an 'expiresDate' string,")
    print("# but that is the inappwebview cookie manager plugin, not the VIP chain.")

    print("\n== key refs ==")
    for ref, label in KEY_REFS:
        slot, off = by_ref[ref]
        pcs = off_to_pcs.get(off, [])
        funcs = sorted({find_func_start(data, pc) for pc in pcs if find_func_start(data, pc) is not None})
        print(
            f"ref={ref:>5} slot=0x{slot:x} off=0x{off:x} "
            f"pcs={[hex(x) for x in pcs[:12]]} funcs={[hex(x) for x in funcs[:8]]} "
            f"text={label}"
        )

    print("\n== selected function string hits ==")
    for start, end, label in INTERESTING_FUNCS:
        print(f"-- {label} @ 0x{start:x} --")
        for pc, off in pc_off_pairs:
            if not (start <= pc < end):
                continue
            ref = off_to_ref.get(off)
            if ref is None:
                continue
            text = strings.get(ref, "")
            if text:
                print(f"  0x{pc:x} off=0x{off:x} ref={ref} text={text}")

    print("\n== direct BL callers ==")
    for target, label in [
        (0x911788, "共享状态门控"),
        (0x8CF36C, "奖励特权状态对象"),
    ]:
        print(f"{label} 0x{target:x}: {[hex(x) for x in bl_callers(data, target)]}")

    print("\n== snippets ==")
    for start, end, label in SNIPPETS:
        print(f"-- {label} 0x{start:x}..0x{end:x} --")
        for ins in md.disasm(data[start:end], start):
            print(f"0x{ins.address:08x}  {ins.bytes.hex():<8} {ins.mnemonic:<7} {ins.op_str}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
