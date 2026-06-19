#!/usr/bin/env python3
"""Extract reproducible evidence for remaining dialog candidates.

This helper reads `unflutter_dump/asm.txt` and, optionally, a `pool_accesses.txt`
export, then prints:
1. direct BL targets with absolute addresses
2. pool accesses inside the function range
3. null-return tails / null-gate compares

It exists to avoid reusing the earlier mistaken interpretation that
`BL .+0xffff...` already printed an absolute target.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FunctionSpec:
    name: str
    start: int
    end: int


FUNCTIONS = [
    FunctionSpec("fault_orchestrator_patched", 0x00BC0F40, 0x00BC1394),
    FunctionSpec("fault_dialog_body_builder", 0x00BBC22C, 0x00BBC578),
    FunctionSpec("fault_dialog_sibling_builder", 0x00BBC5E0, 0x00BBC91C),
    FunctionSpec("fault_dialog_widget_builder", 0x008B6100, 0x008B646C),
    FunctionSpec("fault_dialog_residual_candidate", 0x00BD5A24, 0x00BD6314),
    FunctionSpec("reward_dialog_candidate", 0x007E1464, 0x007E1D64),
]

LINE_RE = re.compile(r"^(0x[0-9a-f]{8})\s+([0-9a-f ]+)\s+(.+)$")
BL_RE = re.compile(r"^(0x[0-9a-f]{8}).*\bBL \.\+(0x[0-9a-f]+)$")
POOL_RE = re.compile(r"^(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(.*)$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--asm",
        default="unflutter_dump/asm.txt",
        help="path to asm.txt",
    )
    parser.add_argument(
        "--pool-accesses",
        help="optional pool_accesses.txt path",
    )
    return parser.parse_args()


def resolve_branch_target(pc: int, offset_text: str) -> int:
    off = int(offset_text, 16)
    if off & (1 << 63):
        off -= 1 << 64
    return (pc + off) & ((1 << 64) - 1)


def load_lines(path: Path) -> list[str]:
    return path.read_text(errors="ignore").splitlines()


def index_function_starts(lines: list[str]) -> dict[int, int]:
    out: dict[int, int] = {}
    for idx, line in enumerate(lines):
        m = LINE_RE.match(line)
        if not m:
            continue
        pc = int(m.group(1), 16)
        out[pc] = idx
    return out


def extract_window(lines: list[str], func: FunctionSpec, starts: dict[int, int]) -> list[str]:
    idx = starts.get(func.start)
    if idx is None:
        raise SystemExit(f"function start not found: 0x{func.start:08x}")
    out: list[str] = []
    for line in lines[idx:]:
        m = LINE_RE.match(line)
        if not m:
            out.append(line)
            continue
        pc = int(m.group(1), 16)
        if pc > func.end:
            break
        out.append(line)
    return out


def load_pool_accesses(path: Path | None) -> list[tuple[int, int, str]]:
    if path is None:
        return []
    out: list[tuple[int, int, str]] = []
    for line in path.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        m = POOL_RE.match(line)
        if not m:
            continue
        out.append((int(m.group(1), 16), int(m.group(2), 16), line))
    return out


def print_function_report(func: FunctionSpec, lines: list[str], pool_rows: list[tuple[int, int, str]]) -> None:
    print(f"== {func.name} @ 0x{func.start:08x}-0x{func.end:08x} ==")
    print("entry:", "fd 79 bf a9 fd 03 0f aa -> e0 03 16 aa c0 03 5f d6")

    print("\nBL targets:")
    bl_count = 0
    for line in lines:
        m = BL_RE.match(line)
        if not m:
            continue
        pc = int(m.group(1), 16)
        target = resolve_branch_target(pc, m.group(2))
        print(f"  {m.group(1)} -> 0x{target:08x}")
        bl_count += 1
    if bl_count == 0:
        print("  (none)")

    print("\nNull gates / null returns:")
    gate_count = 0
    for line in lines:
        if "CMP W0, W22" in line or "MOV X0, X22" in line or "RET X30" in line:
            print(" ", line)
            gate_count += 1
    if gate_count == 0:
        print("  (none)")

    if pool_rows:
        print("\nPool accesses in range:")
        rows = [row for row in pool_rows if func.start <= row[0] <= func.end]
        if rows:
            for _, _, raw in rows:
                print(" ", raw)
        else:
            print("  (none)")
    print()


def main() -> None:
    args = parse_args()
    asm_path = Path(args.asm)
    pool_path = Path(args.pool_accesses) if args.pool_accesses else None
    lines = load_lines(asm_path)
    starts = index_function_starts(lines)
    pool_rows = load_pool_accesses(pool_path)
    for func in FUNCTIONS:
        window = extract_window(lines, func, starts)
        print_function_report(func, window, pool_rows)


if __name__ == "__main__":
    main()
