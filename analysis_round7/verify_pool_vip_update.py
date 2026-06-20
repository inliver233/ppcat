#!/usr/bin/env python3
"""Round 7 verification helper for ObjectPool, VIP content strings, and update dialog sites.

This script is intentionally narrow:
- deserialize the ObjectPool with the independently re-verified raw-entry format
- print the 7 critical anchors
- print the VIP-content-page string refs / slots / accessor PCs
- print the two safer update-dialog BL->NOP candidates
"""

from __future__ import annotations

from pathlib import Path


LIBAPP = Path("lib/arm64-v8a/libapp.so")
STRINGS = Path("unflutter_strings.txt")
POOL_ACCESSES = Path("analysis_round6/pool_accesses.txt")
FILL_START = 0x2E7043
POOL_LENGTH = 51140

ANCHOR_REFS = [21707, 22466, 26842, 27673, 29112, 30922, 30947]
VIP_REFS = [
    8910,   # 通过捐赠绑定设备获取
    13169,  # 功能，通过捐赠绑定账号获取
    9292,   # 已获取
    29757,  # 未获得
    4505,   # 点击头像绑定账号
    24111,  # 解绑
    2878,   # 24小时内累计浏览
    13199,  # 次推荐信息，即可获取
    13928,  # 未获得特权将在0点重置浏览次数
    3524,   # 已生效
    10073,  # 已绑定账号
    11366,  # 可以捐赠
    7406,   # expiresDate
    12056,  # expires
]

UPDATE_DIALOG_SITES = {
    0x8667A8: "发现新版本 caller@0x866778 的 dialog-show BL",
    0x8675BC: "发现新版本 caller@0x86758c 的 dialog-show BL",
}

VIP_FUNC_LINES = {
    0xA54178: "VIP 内容页主构造区",
    0xB9FC84: "VIP 页面上层混合状态机",
    0x8A0FD4: "“可以捐赠”提示构造器",
    0x8BA3D0: "expiresDate 读取链",
    0x67994C: "expires 判定/格式化链",
}


def read_strings() -> dict[int, str]:
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


def read_unsigned(data: bytes, pos: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        b = data[pos]
        pos += 1
        if b > 0x7F:
            value |= (b - 0x80) << shift
            return value, pos
        value |= b << shift
        shift += 7


def parse_pool(data: bytes) -> tuple[dict[int, int], dict[int, int]]:
    pos = FILL_START
    length, pos = read_unsigned(data, pos)
    if length != POOL_LENGTH:
        raise ValueError(f"unexpected pool length {length} != {POOL_LENGTH}")

    ref_to_off: dict[int, int] = {}
    off_to_ref: dict[int, int] = {}
    for idx in range(length):
        entry_bits = data[pos]
        pos += 1
        entry_type = entry_bits & 0x7F
        if entry_type in (0, 1):
            value, pos = read_unsigned(data, pos)
            if entry_type == 0:
                off = idx * 8
                ref_to_off.setdefault(value, off)
                off_to_ref[off] = value
        elif entry_type in (2, 3, 4):
            pass
        else:
            raise ValueError(
                f"unknown entry type {entry_type} bits=0x{entry_bits:02x} idx={idx} pos=0x{pos-1:x}"
            )
    return ref_to_off, off_to_ref


def read_pool_accesses() -> dict[int, list[int]]:
    off_to_pcs: dict[int, list[int]] = {}
    for line in POOL_ACCESSES.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        pc_s, off_s = line.split()[:2]
        pc = int(pc_s, 16)
        off = int(off_s, 16)
        off_to_pcs.setdefault(off, []).append(pc)
    return off_to_pcs


def decode_bl_targets(data: bytes, targets: set[int]) -> dict[int, list[int]]:
    out: dict[int, list[int]] = {target: [] for target in targets}
    text_start = 0x460000
    text_end = len(data) - 4
    for addr in range(text_start, text_end, 4):
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
    strings = read_strings()
    ref_to_off, _ = parse_pool(data)
    off_to_pcs = read_pool_accesses()

    print("== 7 critical anchors ==")
    for ref in ANCHOR_REFS:
        off = ref_to_off.get(ref)
        pcs = off_to_pcs.get(off, []) if off is not None else []
        print(
            f"ref={ref} slot=0x{(off // 8):x} off=0x{off:x} pcs={[hex(x) for x in pcs[:6]]} text={strings.get(ref, '')[:80]!r}"
        )

    print("\n== VIP content page strings ==")
    for ref in VIP_REFS:
        off = ref_to_off.get(ref)
        pcs = off_to_pcs.get(off, []) if off is not None else []
        print(
            f"ref={ref} slot=0x{(off // 8):x} off=0x{off:x} pcs={[hex(x) for x in pcs[:8]]} text={strings.get(ref, '')}"
        )

    print("\n== VIP function lines ==")
    for addr, desc in VIP_FUNC_LINES.items():
        print(f"0x{addr:x}: {desc}")

    print("\n== Shared gate 0x911788 direct callers ==")
    callers = decode_bl_targets(data, {0x911788})[0x911788]
    print([hex(x) for x in callers])

    print("\n== Update dialog BL candidates ==")
    for addr, desc in UPDATE_DIALOG_SITES.items():
        print(
            f"{desc}: addr=0x{addr:x} orig={data[addr:addr+4].hex()} patch=1f2003d5"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
