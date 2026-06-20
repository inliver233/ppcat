#!/usr/bin/env python3
"""Cross-check ad/VIP SharedPreferences key semantics on test1.

Focus:
- verify test3's correction that isNoAdLock is not SP-readable input
- verify showSplashAd is read through the SP getAll bridge
- keep the output local and reproducible on test1
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

from capstone import CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, Cs


ROOT = Path(__file__).resolve().parents[1]
LIBAPP_CANDIDATES = [
    ROOT / "libapp.so",
    ROOT / "lib" / "arm64-v8a" / "libapp.so",
]
POOL_JSON = ROOT / "pool_deserialized.json"
POOL_ACCESSES = ROOT / "analysis_round6" / "pool_accesses.txt"
STRINGS = ROOT / "unflutter_strings.txt"
OUT_TXT = ROOT / "analysis_round12" / "sp_key_semantics_probe.txt"

KEY_REFS = [
    (19035, "isNoAdLock"),
    (2855, "showSplashAd"),
    (18367, "noAdDisableSourceList"),
    (5996, "noAdAllowSourceList"),
    (11283, "noAdSourceNumLimit"),
    (6278, "noAdRegex"),
    (7606, "rewardTime"),
    (8067, "getRewardTime"),
    (11191, "checkDaily"),
    (7406, "expiresDate"),
]


def pick_libapp() -> Path:
    for path in LIBAPP_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError("libapp.so not found")


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
        off_to_pcs.setdefault(int(off_s, 16), []).append(int(pc_s, 16))
    return off_to_pcs


def find_func_start(data: bytes, pc: int) -> int | None:
    for addr in range(pc, max(0, pc - 0x8000), -4):
        if data[addr : addr + 4] == bytes.fromhex("fd79bfa9") and data[addr + 4 : addr + 8] == bytes.fromhex("fd030faa"):
            return addr
    return None


def find_func_end(data: bytes, start: int, max_span: int = 0x4000) -> int:
    lo = start + 8
    hi = min(len(data) - 8, start + max_span)
    for addr in range(lo, hi, 4):
        if data[addr : addr + 4] == bytes.fromhex("fd79bfa9") and data[addr + 4 : addr + 8] == bytes.fromhex("fd030faa"):
            return addr
    return hi


def bl_targets(data: bytes, start: int, end: int) -> list[int]:
    out: list[int] = []
    for addr in range(start, end, 4):
        word = struct.unpack_from("<I", data, addr)[0]
        if (word & 0xFC000000) != 0x94000000:
            continue
        imm26 = word & 0x03FFFFFF
        if imm26 & (1 << 25):
            imm26 -= 1 << 26
        out.append(addr + (imm26 << 2))
    return out


def getter_targets(ts: list[int]) -> list[int]:
    out: list[int] = []
    for t in ts:
        if 0x4EA000 <= t < 0x4EB000:
            out.append(t)
        elif 0x904000 <= t < 0x905180:
            out.append(t)
    return out


def setter_targets(ts: list[int]) -> list[int]:
    out: list[int] = []
    for t in ts:
        if 0x905180 <= t < 0x906000:
            out.append(t)
    return out


def main() -> int:
    libapp = pick_libapp()
    data = libapp.read_bytes()
    strings = load_strings()
    by_ref, _ = load_pool()
    off_to_pcs = load_pool_accesses()
    md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)

    lines: list[str] = []
    lines.append(f"# libapp = {libapp}")
    lines.append("# ref -> accessor funcs -> SP bridge classification")

    for ref, label in KEY_REFS:
        slot, off = by_ref[ref]
        pcs = off_to_pcs.get(off, [])
        funcs = sorted({find_func_start(data, pc) for pc in pcs if find_func_start(data, pc) is not None})
        lines.append("")
        lines.append(f"== ref={ref} {label} ==")
        lines.append(f"slot=0x{slot:x} off=0x{off:x} pcs={[hex(x) for x in pcs]} funcs={[hex(x) for x in funcs]}")
        verdict = "WRITE-ONLY / computed"
        if not funcs:
            verdict = "INDIRECT / virtual accessor unresolved"
        for func in funcs:
            end = find_func_end(data, func)
            targets = bl_targets(data, func, end)
            getters = getter_targets(targets)
            setters = setter_targets(targets)
            if getters:
                verdict = "READ (getter/getAll bridge present)"
            elif setters and verdict != "READ (getter/getAll bridge present)":
                verdict = "WRITE / manager(setter bridge present)"
            lines.append(
                f"func 0x{func:x}..0x{end:x} "
                f"getters={[hex(x) for x in getters]} setters={[hex(x) for x in setters]}"
            )
        lines.append(f"verdict={verdict}")

    lines.append("")
    lines.append("== local proof snippets ==")
    lines.append("-- 0x7e8534: isNoAdLock only appears on the true-path object-construction side --")
    for ins in md.disasm(data[0x7E85DC:0x7E86E8], 0x7E85DC):
        lines.append(f"0x{ins.address:08x} {ins.bytes.hex():<8} {ins.mnemonic:<7} {ins.op_str}")
    lines.append("-- 0x8863e8: showSplashAd accessor calls getAll bridge 0x4ea988 --")
    for ins in md.disasm(data[0x8864C0:0x88653C], 0x8864C0):
        lines.append(f"0x{ins.address:08x} {ins.bytes.hex():<8} {ins.mnemonic:<7} {ins.op_str}")

    lines.append("")
    lines.append("== patch candidate ==")
    lines.append("0x7e8540: 501f40f9 -> 69000014")
    lines.append("reason: branch directly to 0x7e86e4 canonical true-return inside 0x7e8534")
    lines.append("caveat: this bypasses side-effect object construction; logic is locally consistent but still needs runtime confirmation")

    OUT_TXT.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT_TXT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
