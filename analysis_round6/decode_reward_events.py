#!/usr/bin/env python3
from __future__ import annotations

import ast
import re
from pathlib import Path


TARGETS = [
    ("Pangle_events", "analysis_round6/out/jadx_classes2/sources/p095/C1292.java", "C0983.m2834"),
    ("Pangle_reward_map", "analysis_round6/out/jadx_classes2/sources/p059/C0988.java", "C0983.m2834"),
    ("Pangle_error_map", "analysis_round6/out/jadx_classes2/sources/p059/C0986.java", "C0983.m2834"),
    ("Pangle_base_map", "analysis_round6/out/jadx_classes2/sources/p059/C0989.java", "C0983.m2834"),
    ("Pangle_reward_bundle", "analysis_round6/out/jadx_classes2/sources/p098/C1312.java", "C0983.m2834"),
    ("GDT_events", "analysis_round6/out/jadx_classes2/sources/p073/C1083.java", "C1084.m3254"),
    ("Kwad_events", "analysis_round6/out/jadx_classes2/sources/p066/C1041.java", "C0801.m2423"),
]


def decode_repeated_tail_xor(cipher: list[int], key: list[int]) -> str:
    if cipher and cipher[-1] == 0:
        cipher = cipher[:-1]
    if key and key[-1] == 0:
        key = key[:-1]
    repeated = key[1:] if len(key) > 1 else key
    out = bytes((c ^ repeated[i % len(repeated)]) & 0xFF for i, c in enumerate(cipher))
    return out.decode("utf-8", errors="replace")


def decode_file(label: str, path: str, callee: str) -> list[str]:
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    pattern = re.escape(callee) + r"\(new byte\[\]\{([^}]*)\}, new byte\[\]\{([^}]*)\}\)"
    decoded: list[str] = []
    for raw_cipher, raw_key in re.findall(pattern, text):
        cipher = [x & 0xFF for x in ast.literal_eval("[" + raw_cipher + "]")]
        key = [x & 0xFF for x in ast.literal_eval("[" + raw_key + "]")]
        plain = decode_repeated_tail_xor(cipher, key)
        if plain not in decoded:
            decoded.append(plain)
    return decoded


def main() -> None:
    for label, path, callee in TARGETS:
        print(f"=== {label} ===")
        for plain in decode_file(label, path, callee):
            print(plain)
        print()


if __name__ == "__main__":
    main()
