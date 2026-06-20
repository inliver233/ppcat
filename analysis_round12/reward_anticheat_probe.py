#!/usr/bin/env python3
"""Narrow probe for reward anti-cheat on test1.

Goal:
- keep the reward/noAd/VIP chain reproducible after borrowing test3 ideas
- isolate the dedicated 'onReward Cheat Triggered!' handler path
"""

from __future__ import annotations

import json
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
OUT_TXT = ROOT / "analysis_round12" / "reward_anticheat_probe.txt"

KEY_REFS = [
    5449,   # AdPgl_Reward
    6398,   # reward
    6808,   # onReward
    11545,  # onReward Cheat Triggered!
    32387,  # earned reward:
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


def main() -> int:
    libapp = pick_libapp()
    data = libapp.read_bytes()
    strings = load_strings()
    by_ref, _ = load_pool()
    off_to_pcs = load_pool_accesses()
    md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)

    lines: list[str] = []
    lines.append(f"# libapp = {libapp}")
    lines.append("# reward anti-cheat xrefs and focused disassembly")

    for ref in KEY_REFS:
        slot, off = by_ref[ref]
        pcs = off_to_pcs.get(off, [])
        lines.append("")
        lines.append(f"== ref={ref} {strings.get(ref, '')} ==")
        lines.append(f"slot=0x{slot:x} off=0x{off:x} pcs={[hex(x) for x in pcs]}")

    for start, end, label in [
        (0x875EB8, 0x875F48, "0x8758bc late dispatcher: No Type! / Cheat Triggered! tail"),
        (0x875F78, 0x876040, "0x875f78 dedicated cheat handler"),
        (0x8920D0, 0x892250, "0x8920d0 reward string bundle builder"),
        (0x88AACC, 0x88AE40, "0x88aacc onReward dispatcher"),
    ]:
        lines.append("")
        lines.append(f"== {label} ==")
        for ins in md.disasm(data[start:end], start):
            lines.append(f"0x{ins.address:08x} {ins.bytes.hex():<8} {ins.mnemonic:<7} {ins.op_str}")

    lines.append("")
    lines.append("== candidate bypass ==")
    lines.append("0x875efc: 40012037 -> 0a000014")
    lines.append("meaning: force branch to 0x875f24 generic callback path, skipping the dedicated 0x875f78 cheat-handler path")
    lines.append("confidence: medium; static control-flow is clear, but runtime behavior still needs device confirmation")

    OUT_TXT.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT_TXT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
