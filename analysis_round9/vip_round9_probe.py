#!/usr/bin/env python3
"""Round 9 focused VIP / reward / shared-state probe for ppcat.

Purpose:
- consolidate the stable slot/ref evidence after test3's pool breakthrough
- split the large VIP page builder into smaller, reportable sub-blocks
- keep the analysis narrow and repeatable on test1 without touching APK inputs
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

from capstone import CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, Cs


ROOT = Path(__file__).resolve().parents[1]
LIBAPP = ROOT / "libapp.so"
STRINGS = ROOT / "unflutter_strings.txt"
POOL_JSON = ROOT / "pool_deserialized.json"
POOL_ACCESSES = ROOT / "analysis_round6" / "pool_accesses.txt"
OUT_TXT = ROOT / "analysis_round9" / "vip_round9_probe.txt"


KEY_REFS = [
    3877,   # 未登录
    4505,   # 点击头像绑定账号
    7406,   # expiresDate
    7606,   # rewardTime
    8067,   # getRewardTime
    8910,   # 通过捐赠绑定设备获取
    9292,   # 已获取
    10073,  # 已绑定账号
    11366,  # 可以捐赠
    11545,  # onReward Cheat Triggered!
    12056,  # expires
    13169,  # 通过捐赠绑定账号获取
    13928,  # 未获得特权将在0点重置浏览次数
    17423,  # isDaily:
    21707,  # 每日喂喵
    22466,  # 每日喂喵正文
    26299,  # 未获取
    26968,  # remoteConfigSign
    28525,  # 喵喵饿了
    29112,  # 故障
]

FOCUS_FUNCS = [
    (0x911788, 0x1100, "共享状态门控"),
    (0x8CF36C, 0x600, "奖励特权状态对象"),
    (0xA54178, 0x2700, "VIP内容页主构造"),
    (0xA5796C, 0x400, "已绑定账号子块"),
    (0xB9FC84, 0x1200, "VIP/登录绑定/每日reward混合状态机"),
    (0x8A0FD4, 0x400, "可以捐赠提示"),
    (0x8BA3D0, 0x800, "expiresDate读取链"),
    (0x67994C, 0x1200, "expires/date/skipCount读取链"),
]

SNIPPETS = [
    (0xB9FCA0, 0xB9FDE0, "0xb9fc84 入口门控到前置字符串判定"),
    (0xBA005C, 0xBA0090, "0xb9fc84 绑定文案二选一"),
    (0xA55580, 0xA55CF0, "0xa54178 特权提示 + 每日喂喵子块"),
    (0x8CF7A0, 0x8CF8A0, "0x8cf36c 尾部 return / leaveTime 构造"),
    (0x875EB8, 0x875F24, "0x8758bc reward anti-cheat 分支"),
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
    obj = json.loads(POOL_JSON.read_text())
    by_ref = {int(k): tuple(v) for k, v in obj["by_ref"].items()}
    off_to_ref = {off: ref for ref, (_slot, off) in by_ref.items()}
    return by_ref, off_to_ref


def load_pool_accesses() -> tuple[dict[int, list[int]], list[tuple[int, int]]]:
    off_to_pcs: dict[int, list[int]] = {}
    pairs: list[tuple[int, int]] = []
    for line in POOL_ACCESSES.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        pc_s, off_s, *_ = line.split()
        pc = int(pc_s, 16)
        off = int(off_s, 16)
        off_to_pcs.setdefault(off, []).append(pc)
        pairs.append((pc, off))
    return off_to_pcs, pairs


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


def section(title: str) -> list[str]:
    return ["", f"== {title} =="]


def main() -> int:
    data = LIBAPP.read_bytes()
    strings = load_strings()
    by_ref, off_to_ref = load_pool()
    off_to_pcs, pairs = load_pool_accesses()
    md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)

    out: list[str] = []
    out.extend(section("key refs"))
    for ref in KEY_REFS:
        slot, off = by_ref[ref]
        pcs = off_to_pcs.get(off, [])
        funcs = sorted({find_func_start(data, pc) for pc in pcs if find_func_start(data, pc) is not None})
        out.append(
            f"ref={ref:>5} slot=0x{slot:x} off=0x{off:x} "
            f"pcs={[hex(x) for x in pcs[:10]]} funcs={[hex(x) for x in funcs[:8]]} "
            f"text={strings.get(ref, '')}"
        )

    out.extend(section("focus funcs: embedded string refs"))
    for start, span, label in FOCUS_FUNCS:
        out.append(f"-- {label} @ 0x{start:x} --")
        for pc, off in pairs:
            if not (start <= pc < start + span):
                continue
            ref = off_to_ref.get(off)
            if ref is None:
                continue
            text = strings.get(ref, "")
            if not text:
                continue
            if any(
                kw in text
                for kw in (
                    "捐赠", "绑定", "获取", "特权", "喂喵", "喵喵", "每日",
                    "训练", "浏览", "已生效", "未获得", "未登录", "expires",
                    "reward", "故障", "ignore", "remoteConfigSign", "非法篡改",
                    "forceVersion", "isDaily", "rewardTime", "已过期",
                )
            ):
                out.append(f"  0x{pc:x} off=0x{off:x} ref={ref:>5} text={text}")

    out.extend(section("direct BL callers"))
    for target, _span, label in FOCUS_FUNCS:
        out.append(f"0x{target:x} {label}: {[hex(x) for x in bl_callers(data, target)]}")

    out.extend(section("selected snippets"))
    for start, end, label in SNIPPETS:
        out.append(f"-- {label} 0x{start:x}..0x{end:x} --")
        for ins in md.disasm(data[start:end], start):
            out.append(f"0x{ins.address:08x}  {ins.bytes.hex():<8} {ins.mnemonic:<6} {ins.op_str}")

    OUT_TXT.write_text("\n".join(out) + "\n")
    print(f"wrote {OUT_TXT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
