#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from capstone import CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, Cs
from capstone.arm64 import ARM64_OP_IMM, ARM64_OP_MEM, ARM64_OP_REG, ARM64_REG_X27


TARGETS = [
    (0xA52BB0, 0xE0, "meow_builder_core"),
    (0xA52C90, 0x80, "meow_children_aggregator"),
    (0xA52920, 0x90, "meow_builder_wrapper"),
    (0xB79C10, 0x68, "obj44988_member_store"),
    (0xF3A1DC, 0x38, "obj44988_getter"),
]


def load_strings(path: Path) -> dict[int, str]:
    out: dict[int, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r'\s*\[ref=(\d+)\]\s*\(([^)]*)\)\s*"(.*)"', line)
        if m:
            out[int(m.group(1))] = m.group(3)
    return out


def build_pool_ref_map(pool_json: Path) -> dict[int, int]:
    data = json.loads(pool_json.read_text(encoding="utf-8"))
    entries = data["entries"]
    return {e["idx"] * 8: e["val"] for e in entries if e["type"] == 0}


def annotate_pool_offsets(insns) -> dict[int, int]:
    reg_pages: dict[int, int] = {}
    out: dict[int, int] = {}
    for ins in insns:
        if ins.mnemonic == "add" and len(ins.operands) >= 3:
            ops = ins.operands
            if (
                ops[0].type == ARM64_OP_REG
                and ops[1].type == ARM64_OP_REG
                and ops[1].reg == ARM64_REG_X27
                and ops[2].type == ARM64_OP_IMM
            ):
                reg_pages[ops[0].reg] = ops[2].imm
        if ins.mnemonic == "ldr" and len(ins.operands) >= 2 and ins.operands[1].type == ARM64_OP_MEM:
            mem = ins.operands[1].mem
            if mem.base == ARM64_REG_X27:
                out[ins.address] = mem.disp
            elif mem.base in reg_pages:
                out[ins.address] = reg_pages[mem.base] + mem.disp
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--libapp",
        default="lib/arm64-v8a/libapp.so",
        help="path to libapp.so",
    )
    ap.add_argument(
        "--pool-json",
        default="/root/ppcat_repo/pool_deserialized.json",
        help="path to pool_deserialized.json",
    )
    ap.add_argument(
        "--strings",
        default="unflutter_strings.txt",
        help="path to unflutter_strings.txt",
    )
    args = ap.parse_args()

    libapp = Path(args.libapp)
    pool_json = Path(args.pool_json)
    strings_path = Path(args.strings)

    blob = libapp.read_bytes()
    strings = load_strings(strings_path)
    off2ref = build_pool_ref_map(pool_json)

    md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    md.detail = True

    for addr, size, name in TARGETS:
        code = blob[addr : addr + size]
        insns = list(md.disasm(code, addr))
        pool_map = annotate_pool_offsets(insns)
        print(f"== {name} 0x{addr:x} size=0x{size:x}")
        for ins in insns:
            extra = ""
            off = pool_map.get(ins.address)
            if off is not None:
                ref = off2ref.get(off)
                if ref is not None:
                    extra = f" ; pool_off=0x{off:x} slot=0x{off // 8:x} ref={ref}"
                    if ref in strings:
                        extra += f' "{strings[ref]}"'
            print(f"0x{ins.address:08x}: {ins.bytes.hex()}  {ins.mnemonic:7} {ins.op_str}{extra}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
