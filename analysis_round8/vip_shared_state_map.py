#!/usr/bin/env python3
"""Correlate VIP/page strings, shared_preferences wrappers, and key gate functions.

This is intentionally narrow:
- print selected ref -> slot -> accessor PCs
- show string accesses inside the main VIP/state functions
- show direct BL callers for a few high-value helpers
"""

from __future__ import annotations

import json
import struct
from pathlib import Path


LIBAPP = Path("libapp.so")
STRINGS = Path("unflutter_strings.txt")
POOL_JSON = Path("pool_deserialized.json")
POOL_ACCESSES = Path("analysis_round6/pool_accesses.txt")

TARGET_REFS = [
    3877,   # 未登录
    4505,   # 点击头像绑定账号
    7406,   # expiresDate
    7606,   # rewardTime
    8297,   # netFail
    8910,   # 通过捐赠绑定设备获取
    10073,  # 已绑定账号
    11366,  # 可以捐赠
    12056,  # expires
    13169,  # 功能，通过捐赠绑定账号获取
    14834,  # 验证失败
    20352,  # isBetaUser
    21707,  # 每日喂喵
    22466,  # 每日喂喵正文
    26299,  # 未获取
    26968,  # remoteConfigSign
    29112,  # 故障
]

FUNC_STRINGS = {
    0xA54178: 0x2680,  # VIP 内容页主构造区
    0xB9FC84: 0x1100,  # VIP 页面上层混合状态机
    0x911788: 0x1100,  # 共享状态门控器
    0x8BA3D0: 0x0800,  # expiresDate 读取链
    0x67994C: 0x1200,  # expires 判定 / 格式化链
}

CALL_TARGETS = [
    0x904DC4,  # shared_preferences clear/aux-ish
    0x905180,  # setStringList-ish
    0x9051CC,  # setString-ish
    0x905214,  # setInt-ish
    0x905260,  # setDouble-ish
    0x911788,  # shared gate
]


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


def bl_callers(data: bytes, target: int) -> list[int]:
    callers: list[int] = []
    for addr in range(0x460000, len(data) - 4, 4):
        word = struct.unpack_from("<I", data, addr)[0]
        if (word >> 26) != 0b100101:
            continue
        imm26 = word & 0x03FFFFFF
        if imm26 & (1 << 25):
            imm26 -= 1 << 26
        if addr + (imm26 << 2) == target:
            callers.append(addr)
    return callers


def main() -> int:
    strings = load_strings()
    by_ref, off_to_ref = load_pool()
    off_to_pcs, pc_off_pairs = load_pool_accesses()
    data = LIBAPP.read_bytes()

    print("== selected refs ==")
    for ref in TARGET_REFS:
        slot, off = by_ref[ref]
        pcs = [hex(x) for x in off_to_pcs.get(off, [])[:12]]
        print(f"ref={ref:>5} slot=0x{slot:x} off=0x{off:x} pcs={pcs} text={strings.get(ref, '')}")

    print("\n== string accesses inside high-value functions ==")
    for func, span in FUNC_STRINGS.items():
        print(f"-- func 0x{func:x} --")
        for pc, off in pc_off_pairs:
            if not (func <= pc < func + span):
                continue
            ref = off_to_ref.get(off)
            if ref is None:
                continue
            text = strings.get(ref, "")
            if text:
                print(f"  0x{pc:x} off=0x{off:x} ref={ref:>5} text={text}")

    print("\n== direct BL callers ==")
    for target in CALL_TARGETS:
        callers = [hex(x) for x in bl_callers(data, target)]
        print(f"0x{target:x}: {callers}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
