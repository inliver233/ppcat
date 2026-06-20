#!/usr/bin/env python3
"""Summarize the VIP page / reward privilege chain confirmed on test1.

This is intentionally small and repeatable:
- print ref -> slot/off -> .text PCs for the VIP-page strings we care about
- normalize internal reward / anti-cheat hit PCs back to function entries
- show the local bind-text branch inside 0xb9fc84
"""

from __future__ import annotations

import json
from pathlib import Path

from capstone import CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, Cs


LIBAPP = Path("lib/arm64-v8a/libapp.so")
POOL_JSON = Path("pool_deserialized.json")
STRINGS = Path("unflutter_strings.txt")
POOL_ACCESSES = Path("analysis_round6/pool_accesses.txt")

KEY_REFS = [
    3877,   # 未登录
    8910,   # 通过捐赠绑定设备获取
    9292,   # 已获取
    10073,  # 已绑定账号
    11366,  # 可以捐赠
    12056,  # expires
    13169,  # 功能，通过捐赠绑定账号获取
    13928,  # 未获得特权将在0点重置浏览次数
    21707,  # 每日喂喵
    26299,  # 未获取
    28525,  # 喵喵饿了
    2878,   # 24小时内累计浏览
    3524,   # 已生效
]

ENTRY_HINTS = {
    0x88AD64: "onReward 内部字符串装载点",
    0x875EE8: "onReward Cheat Triggered! 内部装载点",
    0x89219C: "奖励配置侧 Cheat 装载点",
}

SNIPPETS = {
    "0xb9fc84 局部绑定文案分流": (0xBA005C, 0xBA0088),
    "0xa54178 VIP 内容页文案块": (0xA54D30, 0xA55158),
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


def print_refs(strings: dict[int, str], by_ref: dict[int, tuple[int, int]], off_to_pcs: dict[int, list[int]], data: bytes) -> None:
    print("== VIP / reward 关键 ref ==")
    for ref in KEY_REFS:
        slot, off = by_ref[ref]
        pcs = off_to_pcs.get(off, [])
        funcs = sorted({find_func_start(data, pc) for pc in pcs if find_func_start(data, pc) is not None})
        print(
            f"ref={ref:>5} slot=0x{slot:x} off=0x{off:x} "
            f"pcs={[hex(x) for x in pcs[:8]]} funcs={[hex(x) for x in funcs[:6]]} "
            f"text={strings.get(ref, '')}"
        )


def print_entry_hints(data: bytes) -> None:
    print("\n== 入口 / 内部命中点统一 ==")
    for pc, label in ENTRY_HINTS.items():
        start = find_func_start(data, pc)
        print(f"{label}: hit=0x{pc:x} entry={hex(start) if start is not None else 'N/A'}")


def print_snippets(data: bytes) -> None:
    md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    print("\n== 分支片段 ==")
    for label, (start, end) in SNIPPETS.items():
        print(f"-- {label} 0x{start:x}..0x{end:x} --")
        for ins in md.disasm(data[start:end], start):
            print(f"0x{ins.address:08x}  {ins.bytes.hex():<8} {ins.mnemonic:<6} {ins.op_str}")


def main() -> int:
    data = LIBAPP.read_bytes()
    strings = load_strings()
    by_ref, _off_to_ref = load_pool()
    off_to_pcs = load_pool_accesses()
    print_refs(strings, by_ref, off_to_pcs, data)
    print_entry_hints(data)
    print_snippets(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
