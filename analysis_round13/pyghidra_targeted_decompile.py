#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import pyghidra


ROOT = Path(__file__).resolve().parents[1]
LIBAPP = ROOT / "libapp.so"
PROJECT_DIR = ROOT / "analysis_round13" / "pyghidra_targeted_project"
OUT = ROOT / "analysis_round13" / "pyghidra_targeted_decompile.txt"

TARGETS = [
    (0x8758BC, 0x876154),
    (0x911788, 0x911B28),
    (0x8CF36C, 0x8CF8F0),
    (0xA54178, 0xA56824),
    (0xB9FC84, 0xBA46EC),
]


def main() -> int:
    PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    with pyghidra.open_program(
        LIBAPP,
        project_location=PROJECT_DIR,
        project_name="ppcat_pg_targeted",
        analyze=False,
        nested_project_location=False,
    ) as api:
        from ghidra.app.decompiler import DecompInterface
        from ghidra.program.model.address import AddressSet
        from ghidra.program.model.symbol import SourceType

        listing = api.currentProgram.getListing()
        fm = api.currentProgram.getFunctionManager()

        decomp = DecompInterface()
        decomp.toggleCCode(True)
        decomp.toggleSyntaxTree(True)
        decomp.setSimplificationStyle("decompile")
        decomp.openProgram(api.currentProgram)

        lines: list[str] = []
        lines.append(f"program={api.currentProgram.getName()}")
        lines.append(f"image_base=0x{api.currentProgram.getImageBase().getOffset():x}")

        for start_int, next_int in TARGETS:
            start = api.toAddr(start_int)
            end = api.toAddr(next_int).subtract(4)
            api.disassemble(start)
            body = AddressSet(start, end)
            fn = fm.getFunctionAt(start)
            if fn is None:
                try:
                    fn = listing.createFunction(None, start, body, SourceType.USER_DEFINED)
                except Exception:
                    fn = fm.getFunctionAt(start)
            lines.append("")
            lines.append(f"=== target 0x{start_int:x}..0x{end.getOffset():x} ===")
            lines.append(f"create_fn={fn.getName() if fn else None}")
            ins = listing.getInstructionAt(start)
            lines.append(f"first_ins={ins}")
            if fn is None:
                continue
            res = decomp.decompileFunction(fn, 60, api.getMonitor())
            lines.append(f"decompile_completed={res.decompileCompleted()}")
            if res.decompileCompleted() and res.getDecompiledFunction() is not None:
                c_src = res.getDecompiledFunction().getC().splitlines()
                for line in c_src[:80]:
                    lines.append(line)
            else:
                lines.append(f"last_message={decomp.getLastMessage()}")

        OUT.write_text("\n".join(lines), encoding="utf-8")
        print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
