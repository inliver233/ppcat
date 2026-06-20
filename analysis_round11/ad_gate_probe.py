#!/usr/bin/env python3
"""Probe the ad-gate / noAd / VIP-content connection on test1.

Purpose:
- independently verify test2/test3's "0x7e8534 is the main ad gate" claim on test1
- anchor the noAd SharedPreferences keys to concrete Dart AOT PCs
- connect that gate back to the VIP content-page chain without overclaiming a single isVip branch
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

from capstone import CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, Cs


ROOT = Path(__file__).resolve().parents[1]
LIBAPP_CANDIDATES = [
    ROOT / "lib" / "arm64-v8a" / "libapp.so",
    ROOT / "libapp.so",
]
POOL_JSON = ROOT / "pool_deserialized.json"
POOL_ACCESSES = ROOT / "analysis_round6" / "pool_accesses.txt"
STRINGS = ROOT / "unflutter_strings.txt"
OUT_TXT = ROOT / "analysis_round11" / "ad_gate_probe.txt"

KEY_REFS = [
    (19035, "isNoAdLock"),
    (2855, "showSplashAd"),
    (18367, "noAdDisableSourceList"),
    (5996, "noAdAllowSourceList"),
    (11283, "noAdSourceNumLimit"),
    (6278, "noAdRegex"),
    (7559, "adNum:"),
    (11244, "readCount"),
    (21707, "每日喂喵"),
    (28525, "喵喵饿了"),
    (8910, "通过捐赠绑定设备获取"),
    (13169, "功能，通过捐赠绑定账号获取"),
    (7406, "expiresDate"),
    (26968, "remoteConfigSign"),
]

INTERESTING_FUNCS = [
    (0x7E8534, 0x7E8704, "广告总闸 0x7e8534"),
    (0x7E8054, 0x7E83F4, "广告门控 caller 0x7e8054"),
    (0x839E80, 0x839F60, "noAdAllowSourceList helper 0x839e80"),
    (0x83A060, 0x83A140, "noAdDisableSourceList helper 0x83a060"),
    (0x838C74, 0x838D28, "noAdSourceNumLimit helper 0x838c74"),
    (0x890C6C, 0x890DA0, "noAdRegex + showSplashAd helper 0x890c6c"),
    (0x920A60, 0x920AB0, "noAdRegex companion 0x920a60"),
    (0x8863E8, 0x886520, "showSplashAd object builder 0x8863e8"),
    (0x8CF36C, 0x8CF830, "奖励特权状态对象 0x8cf36c"),
    (0xA54178, 0xA56220, "VIP 内容页 builder 0xa54178"),
    (0xB9FC84, 0xBA0A20, "VIP/绑定/reward 混合状态机 0xb9fc84"),
]

SNIPPETS = [
    (0x7E85DC, 0x7E8620, "0x7e8534 内部：0x911788 -> 0x8cf36c -> 分支"),
    (0x7E8640, 0x7E8698, "0x7e8534 内部：isNoAdLock + adNum:"),
    (0x7E80F8, 0x7E8148, "0x7e8054 caller：先过广告总闸，再过奖励特权对象"),
    (0x839F34, 0x839F44, "0x839e80：noAdAllowSourceList 装载"),
    (0x83A114, 0x83A124, "0x83a060：noAdDisableSourceList 装载"),
    (0x838D08, 0x838D18, "0x838c74：noAdSourceNumLimit 装载"),
    (0x890D00, 0x890D90, "0x890c6c：noAdRegex + showSplashAd 装载"),
    (0x8864F0, 0x886508, "0x8863e8：showSplashAd 装载"),
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
        if (word & 0xFC000000) != 0x94000000:
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

    lines: list[str] = []
    lines.append(f"# libapp = {libapp.relative_to(ROOT) if libapp.is_relative_to(ROOT) else libapp}")
    lines.append("# focus: ad gate / noAd settings / VIP content-page connection")
    lines.append("# note: this probe does not collapse VIP into a single bool; it only anchors the shared ad-control path")

    lines.append("\n== key refs ==")
    for ref, label in KEY_REFS:
        slot, off = by_ref[ref]
        pcs = off_to_pcs.get(off, [])
        funcs = sorted({find_func_start(data, pc) for pc in pcs if find_func_start(data, pc) is not None})
        lines.append(
            f"ref={ref:>5} slot=0x{slot:x} off=0x{off:x} "
            f"pcs={[hex(x) for x in pcs[:12]]} funcs={[hex(x) for x in funcs[:10]]} "
            f"text={label}"
        )

    lines.append("\n== selected function string hits ==")
    for start, end, label in INTERESTING_FUNCS:
        lines.append(f"-- {label} @ 0x{start:x} --")
        for pc, off in pc_off_pairs:
            if not (start <= pc < end):
                continue
            ref = off_to_ref.get(off)
            if ref is None:
                continue
            text = strings.get(ref, "")
            if text:
                lines.append(f"  0x{pc:x} off=0x{off:x} ref={ref} text={text}")

    lines.append("\n== direct BL callers ==")
    for target, label in [
        (0x7E8534, "广告总闸"),
        (0x8CF36C, "奖励特权状态对象"),
        (0x839E80, "noAdAllowSourceList helper"),
        (0x83A060, "noAdDisableSourceList helper"),
        (0x838C74, "noAdSourceNumLimit helper"),
        (0x890C6C, "noAdRegex helper"),
    ]:
        lines.append(f"{label} 0x{target:x}: {[hex(x) for x in bl_callers(data, target)]}")

    lines.append("\n== branch bytes ==")
    for addr, note in [
        (0x7E85F4, "ad gate 内：0x911788 返回后的 tbz"),
        (0x7E8610, "ad gate 内：0x7e41c0 返回后的 tbz"),
        (0x7E861C, "ad gate 内：0x8cf36c 返回后的 tbz"),
        (0x7E80FC, "caller 0x7e8054：广告总闸返回后的 tbz"),
        (0x7E8140, "caller 0x7e8054：奖励特权对象返回后的 tbz"),
    ]:
        lines.append(f"0x{addr:x} {data[addr:addr+4].hex()} {note}")

    lines.append("\n== snippets ==")
    for start, end, label in SNIPPETS:
        lines.append(f"-- {label} 0x{start:x}..0x{end:x} --")
        for ins in md.disasm(data[start:end], start):
            lines.append(f"0x{ins.address:08x}  {ins.bytes.hex():<8} {ins.mnemonic:<7} {ins.op_str}")

    OUT_TXT.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT_TXT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
