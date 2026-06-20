#!/usr/bin/env python3
"""Round 9 addendum: carve the VIP content page into smaller code-backed blocks.

Purpose:
- build on the now-stable ObjectPool parse without depending on untracked artifacts
- emit address-ranged snippets for the VIP content page and reward-privilege object
- keep the output narrow enough to cite directly in 分析报告6.md
"""

from __future__ import annotations

from pathlib import Path

from capstone import CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, Cs


ROOT = Path(__file__).resolve().parents[1]
LIBAPP = ROOT / "lib" / "arm64-v8a" / "libapp.so"
STRINGS = ROOT / "unflutter_strings.txt"
POOL_ACCESSES = ROOT / "analysis_round6" / "pool_accesses.txt"
OUT_TXT = ROOT / "analysis_round9" / "vip_content_blocks.txt"

FILL_START = 0x2E7043
POOL_LENGTH = 51140

BLOCKS = [
    (0xA54920, 0xA549A0, "VIP内容页 绑定块"),
    (0xA54D1C, 0xA54E88, "VIP内容页 获取状态块"),
    (0xA55580, 0xA55860, "VIP内容页 浏览次数/特权块"),
    (0xA55C70, 0xA56210, "VIP内容页 喵喵交互块"),
    (0xB9FE5C, 0xBA0090, "VIP混合状态机 奖励特权+绑定文案分流"),
    (0x8CF38C, 0x8CF7D0, "奖励特权状态对象 字段构造"),
    (0x6799D8, 0x679A04, "expires/date/skipCount 读取块"),
    (0x8BA8D8, 0x8BA93C, "expiresDate 读取块"),
]

HIGHLIGHT_REFS = {
    4505,
    24111,
    8910,
    9292,
    29757,
    2878,
    13199,
    13928,
    3524,
    21707,
    28525,
    21925,
    31475,
    17788,
    17423,
    26299,
    3877,
    13169,
    7406,
    12056,
    20877,
    26144,
    21490,
    3599,
    25994,
    22322,
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


def parse_pool(data: bytes) -> dict[int, int]:
    pos = FILL_START
    length, pos = read_unsigned(data, pos)
    if length != POOL_LENGTH:
        raise ValueError(f"unexpected pool length {length} != {POOL_LENGTH}")

    off_to_ref: dict[int, int] = {}
    for idx in range(length):
        entry_bits = data[pos]
        pos += 1
        entry_type = entry_bits & 0x7F
        if entry_type in (0, 1):
            value, pos = read_unsigned(data, pos)
            if entry_type == 0:
                off_to_ref[idx * 8] = value
        elif entry_type in (2, 3, 4):
            pass
        else:
            raise ValueError(
                f"unknown entry type {entry_type} bits=0x{entry_bits:02x} idx={idx} pos=0x{pos-1:x}"
            )
    return off_to_ref


def load_pool_accesses() -> dict[int, int]:
    out: dict[int, int] = {}
    for line in POOL_ACCESSES.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        pc_s, off_s, *_ = line.split()
        out[int(pc_s, 16)] = int(off_s, 16)
    return out


def format_ref(strings: dict[int, str], ref: int, off: int) -> str:
    text = strings.get(ref, "")
    return f"ref={ref} off=0x{off:x} text={text}"


def main() -> int:
    data = LIBAPP.read_bytes()
    strings = load_strings()
    off_to_ref = parse_pool(data)
    pc_to_off = load_pool_accesses()
    md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)

    lines: list[str] = []
    for start, end, label in BLOCKS:
        lines.append(f"== {label} 0x{start:x}..0x{end:x} ==")
        for ins in md.disasm(data[start:end], start):
            note = ""
            off = pc_to_off.get(ins.address)
            if off is not None:
                ref = off_to_ref.get(off)
                if ref in HIGHLIGHT_REFS:
                    note = " ; " + format_ref(strings, ref, off)
            lines.append(
                f"0x{ins.address:08x}  {ins.bytes.hex():<8} {ins.mnemonic:<6} {ins.op_str}{note}"
            )
        lines.append("")

    OUT_TXT.write_text("\n".join(lines))
    print(f"wrote {OUT_TXT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
