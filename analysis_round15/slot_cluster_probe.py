#!/usr/bin/env python3
"""Probe the two competing pool-slot leads from test3:

- slot 0x59a4 / ref 121017: field-like shared state, noisy user set
- slot 0x59bd / ref 91705: function-like meow/reward/VIP cluster

Usage:
  python3 analysis_round15/slot_cluster_probe.py
  python3 analysis_round15/slot_cluster_probe.py --xref analysis_tmp/test3/xref_db.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def choose_xref_path(arg_path: str | None) -> Path:
    candidates = []
    if arg_path:
        candidates.append(Path(arg_path))
    candidates.extend(
        [
            ROOT / "analysis_tmp/test3/xref_db.json",
            ROOT / "analysis_workdir/xref_db.json",
        ]
    )
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(
        "xref_db.json not found; pass --xref or prepare analysis_tmp/test3/xref_db.json"
    )


def parse_pool_accesses(path: Path):
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        pc_s, off_s, *_ = line.split()
        out.append((int(pc_s, 16), int(off_s, 16)))
    return out


def build_fn_ranges(xref_db: dict):
    ranges = []
    for k, v in xref_db.items():
        try:
            start = int(k)
        except ValueError:
            continue
        end = v.get("end")
        if isinstance(end, int) and end > start:
            ranges.append((start, end))
    ranges.sort()
    return ranges


def owner_fn(pc: int, fn_ranges: list[tuple[int, int]]) -> int | None:
    lo, hi = 0, len(fn_ranges)
    while lo < hi:
        mid = (lo + hi) // 2
        start, end = fn_ranges[mid]
        if pc < start:
            hi = mid
        elif pc >= end:
            lo = mid + 1
        else:
            return start
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xref", help="path to test3 xref_db.json")
    args = ap.parse_args()

    named = load_json(ROOT / "analysis_round11_prepool/named.json")
    pool = load_json(ROOT / "pool_deserialized.json")
    xref = load_json(choose_xref_path(args.xref))
    accesses = parse_pool_accesses(ROOT / "analysis_round6/pool_accesses.txt")
    fn_ranges = build_fn_ranges(xref)

    by_ref = pool["by_ref"]
    named_by_ref = {row["ref_id"]: row for row in named}

    targets = {
        0x59A4: {"label": "field-like shared-state lead", "ref": 121017},
        0x59BD: {"label": "function-like meow/reward/VIP lead", "ref": 91705},
    }

    print("== ref structures ==")
    for off, meta in targets.items():
        ref = meta["ref"]
        print(f"\nslot=0x{off:x} ref={ref} label={meta['label']}")
        print("  pool.by_ref:", by_ref.get(str(ref)))
        row = named_by_ref.get(ref)
        print("  named:", row)

    print("\n== slot users ==")
    for off, meta in targets.items():
        print(f"\nslot=0x{off:x} ref={meta['ref']} ({meta['label']})")
        pcs = sorted(pc for pc, got_off in accesses if got_off == off * 8)
        if not pcs:
            print("  no users")
            continue
        for pc in pcs:
            fn = owner_fn(pc, fn_ranges)
            summary = xref.get(str(fn), {}) if fn is not None else {}
            strings = sorted(summary.get("strings", {}).keys())[:10]
            print(
                f"  pc={hex(pc)} fn={hex(fn) if fn is not None else '??'} "
                f"bool={summary.get('bool_ret')} strings={strings}"
            )

    print("\n== nearby sibling refs around 91705 ==")
    for ref in range(91703, 91707):
        row = named_by_ref.get(ref)
        print(f"  ref={ref}: {row}")


if __name__ == "__main__":
    main()
