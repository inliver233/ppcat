#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

import pyghidra


ROOT = Path(__file__).resolve().parents[1]
LIBAPP = ROOT / "libapp.so"
PROJECT_DIR = ROOT / "analysis_round13" / "pyghidra_project"
TARGETS = [
    0x8758BC,
    0x911788,
    0x8CF36C,
    0xA54178,
    0xB9FC84,
]


def main() -> int:
    if not LIBAPP.exists():
        print(f"missing libapp: {LIBAPP}", file=sys.stderr)
        return 1

    PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    with pyghidra.open_program(
        LIBAPP,
        project_location=PROJECT_DIR,
        project_name="ppcat_pyghidra",
        analyze=True,
        nested_project_location=False,
    ) as flat_api:
        from ghidra.program.model.address import AddressSet
        from ghidra.program.model.symbol import SourceType

        program = flat_api.currentProgram
        listing = program.getListing()
        fm = program.getFunctionManager()
        print(f"program={program.getName()}")
        print(f"image_base=0x{program.getImageBase().getOffset():x}")
        for addr_int in TARGETS:
            addr = flat_api.toAddr(addr_int)
            fn = fm.getFunctionAt(addr)
            ins = listing.getInstructionAt(addr)
            if ins is None:
                flat_api.disassemble(addr)
                ins = listing.getInstructionAt(addr)
            if fn is None and ins is not None:
                body = AddressSet(addr, addr.add(0x40))
                try:
                    fn = listing.createFunction(None, addr, body, SourceType.USER_DEFINED)
                except Exception:
                    fn = fm.getFunctionAt(addr)
            print(
                f"target=0x{addr_int:x} fn={fn.getName() if fn else None} "
                f"ins={ins.getMnemonicString() if ins else None}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
