#!/usr/bin/env python3
"""Summarize reward / anti-cheat / noAd / hidden-test-panel chains on test1.

Outputs:
- key ref -> slot/off -> PCs/functions
- function entry callers
- selected disassembly windows around known branch / string-hit sites
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

from capstone import CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, Cs


LIBAPP = Path("lib/arm64-v8a/libapp.so")
POOL_JSON = Path("pool_deserialized.json")
STRINGS = Path("unflutter_strings.txt")
POOL_ACCESSES = Path("analysis_round6/pool_accesses.txt")

KEY_REFS = [
    5996,   # noAdAllowSourceList
    6278,   # noAdRegex
    6808,   # onReward
    7606,   # rewardTime
    8067,   # getRewardTime
    11366,  # 可以捐赠
    11545,  # onReward Cheat Triggered!
    12372,  # 展示RewardVideo广告失败
    14719,  # rewardVideo
    16427,  # rewardItem
    21707,  # 每日喂喵
    22466,  # 每日喂喵正文
    28346,  # JsTest
    32387,  # earned reward:
]

ENTRY_POINTS = [
    0x59D964,
    0x8758BC,
    0x88AACC,
    0x891930,
    0x8920D0,
    0x8CF36C,
    0x839E80,
    0x890C6C,
    0x920A60,
    0xAA5848,
]

WINDOWS = {
    "cheat-hit in 0x8758bc": (0x875EB8, 0x875F24),
    "cheat-hit in 0x8920d0": (0x892170, 0x8921D8),
    "reward privilege call in 0xb9fc84": (0xB9FE5C, 0xB9FE84),
    "reward privilege call in 0xa54178": (0xA541BC, 0xA541D4),
    "hidden test panel strings": (0xAA62B0, 0xAA6318),
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


def load_pool() -> tuple[dict[int, tuple[int, int]], dict[int, int]]:
    obj = json.loads(POOL_JSON.read_text())
    by_ref = {int(k): tuple(v) for k, v in obj["by_ref"].items()}
    off_to_ref = {off: ref for ref, (_slot, off) in by_ref.items()}
    return by_ref, off_to_ref


def load_pool_accesses() -> dict[int, list[int]]:
    off_to_pcs: dict[int, list[int]] = {}
    for line in POOL_ACCESSES.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        pc_s, off_s, *_ = line.split()
        pc = int(pc_s, 16)
        off = int(off_s, 16)
        off_to_pcs.setdefault(off, []).append(pc)
    return off_to_pcs


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


def print_refs(strings: dict[int, str], by_ref: dict[int, tuple[int, int]], off_to_pcs: dict[int, list[int]], data: bytes) -> None:
    print("== reward / anti-cheat / noAd 关键 ref ==")
    for ref in KEY_REFS:
        slot, off = by_ref[ref]
        pcs = off_to_pcs.get(off, [])
        funcs = sorted({find_func_start(data, pc) for pc in pcs if find_func_start(data, pc) is not None})
        print(
            f"ref={ref:>5} slot=0x{slot:x} off=0x{off:x} "
            f"pcs={[hex(x) for x in pcs[:8]]} funcs={[hex(x) for x in funcs[:6]]} "
            f"text={strings.get(ref, '')}"
        )


def print_callers(data: bytes) -> None:
    print("\n== 高价值函数直接 BL 调用者 ==")
    for entry in ENTRY_POINTS:
        callers = bl_callers(data, entry)
        print(f"0x{entry:x}: callers={len(callers)} {[hex(x) for x in callers[:24]]}")


def print_windows(data: bytes) -> None:
    md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    print("\n== 关键片段 ==")
    for label, (start, end) in WINDOWS.items():
        print(f"-- {label} 0x{start:x}..0x{end:x} --")
        for ins in md.disasm(data[start:end], start):
            print(f"0x{ins.address:08x}  {ins.bytes.hex():<8} {ins.mnemonic:<6} {ins.op_str}")


def main() -> int:
    data = LIBAPP.read_bytes()
    strings = load_strings()
    by_ref, _off_to_ref = load_pool()
    off_to_pcs = load_pool_accesses()
    print_refs(strings, by_ref, off_to_pcs, data)
    print_callers(data)
    print_windows(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
