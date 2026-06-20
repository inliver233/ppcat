#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: compare_prepool_outputs.py <old_dir> <new_dir>", file=sys.stderr)
        return 2

    old_dir = Path(sys.argv[1])
    new_dir = Path(sys.argv[2])

    old_named = load_json(old_dir / "named.json")
    new_named = load_json(new_dir / "named.json")
    old_codes = load_json(old_dir / "codes.json")
    new_codes = load_json(new_dir / "codes.json")

    rows = [
        ("named.name_nonempty", sum(1 for r in old_named if r["name"]), sum(1 for r in new_named if r["name"])),
        ("named.owner_name_nonempty", sum(1 for r in old_named if r["owner_name"]), sum(1 for r in new_named if r["owner_name"])),
        ("codes.name_nonempty", sum(1 for r in old_codes if r["name"]), sum(1 for r in new_codes if r["name"])),
        ("codes.owner_name_nonempty", sum(1 for r in old_codes if r["owner_name"]), sum(1 for r in new_codes if r["owner_name"])),
        ("codes.full_name_nonempty", sum(1 for r in old_codes if r["full_name"]), sum(1 for r in new_codes if r["full_name"])),
    ]

    width = max(len(name) for name, _, _ in rows)
    print(f"{'metric'.ljust(width)}  old   new   delta")
    for name, old, new in rows:
        print(f"{name.ljust(width)}  {old:>4}  {new:>4}  {new - old:>+5}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
