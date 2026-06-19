#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import csv
import re
from pathlib import Path


SECTION_RE = re.compile(r"^CODE_OFF (0x[0-9a-f]+): (.+)$", re.M)


def decode_with_repeated_tail(cipher: bytes, key: bytes) -> bytes:
    if cipher and cipher[-1] == 0:
        cipher = cipher[:-1]
    if key and key[-1] == 0:
        key = key[:-1]
    if len(key) > 1:
        repeated = key[1:]
    else:
        repeated = key
    if not repeated:
        return b""
    return bytes(c ^ repeated[i % len(repeated)] for i, c in enumerate(cipher))


def iter_sections(text: str):
    for chunk in text.split("=====\n"):
        match = SECTION_RE.search(chunk)
        if not match:
            continue
        code_off = match.group(1)
        method = match.group(2)
        arrays = []
        for line in chunk.splitlines():
            if "fill-array-data-payload" not in line:
                continue
            payload = line.split("fill-array-data-payload", 1)[1].strip().split(" | ")[0]
            arrays.append(ast.literal_eval(payload))
        yield code_off, method, arrays


def infer_plaintext(cipher: bytes, key: bytes) -> str:
    out = decode_with_repeated_tail(cipher, key)
    if out.endswith(b"\x00"):
        out = out[:-1]
    return out.decode("utf-8", errors="replace")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--input",
        default="analysis_round4/plugin_binding_methods.txt",
        help="binding method dump",
    )
    ap.add_argument(
        "--output",
        default="analysis_round4/plugin_binding_plaintexts.tsv",
        help="output TSV path",
    )
    args = ap.parse_args()

    text = Path(args.input).read_text(encoding="utf-8")
    rows = []
    for code_off, method, arrays in iter_sections(text):
        for idx in range(0, len(arrays) - 1, 2):
            cipher = arrays[idx]
            key = arrays[idx + 1]
            rows.append(
                {
                    "code_off": code_off,
                    "method": method,
                    "pair_index": str(idx // 2),
                    "cipher_len": str(len(cipher)),
                    "key_len": str(len(key)),
                    "plaintext": infer_plaintext(cipher, key),
                }
            )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["code_off", "method", "pair_index", "cipher_len", "key_len", "plaintext"],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
