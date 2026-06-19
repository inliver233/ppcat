#!/usr/bin/env python3
"""
Full disassembly of .text section with capstone.
Output: function entries, full disasm, and BL targets.
"""
import struct
import sys
import re
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

def main(libapp_path, outdir):
    with open(libapp_path, 'rb') as f:
        data = f.read()
    
    TEXT_START = 0x464ce0
    TEXT_SIZE = 0xb329d0
    # First valid instruction is at 0x464d18 (56 bytes into section)
    CODE_START = 0x464d18
    code = data[CODE_START:TEXT_START + TEXT_SIZE]
    
    md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    md.detail = True
    
    print(f'Disassembling {len(code)} bytes from {hex(CODE_START)}...')
    
    # Collect: prologue addresses, BL targets, all instructions
    prologues = []
    bl_targets = {}  # target -> count
    bl_calls = []  # (from_addr, to_addr)
    
    count = 0
    for ins in md.disasm(code, CODE_START):
        count += 1
        if count % 500000 == 0:
            print(f'  ...{count} instructions processed')
        if ins.mnemonic == 'stp' and 'x29' in ins.op_str and 'x30' in ins.op_str:
            if '!' in ins.op_str or '], #' in ins.op_str:
                prologues.append(ins.address)
        elif ins.mnemonic == 'bl':
            # bl target is in op_str
            try:
                target = int(ins.op_str.lstrip('#'), 16) if ins.op_str.startswith('#') else int(ins.op_str, 16)
                bl_targets[target] = bl_targets.get(target, 0) + 1
                bl_calls.append((ins.address, target))
            except ValueError:
                pass
    print(f'Total instructions: {count}')
    print(f'Prologues: {len(prologues)}')
    print(f'Unique BL targets: {len(bl_targets)}')
    
    # Write outputs
    with open(outdir + '/functions.txt', 'w') as f:
        f.write(f'# Function entries in {libapp_path}\n')
        f.write(f'# Range: 0x{CODE_START:x}-0x{TEXT_START+TEXT_SIZE:x}\n')
        f.write(f'# Prologues: {len(prologues)}\n\n')
        for addr in prologues:
            f.write(f'0x{addr:08x}\n')
    
    with open(outdir + '/bl_targets.txt', 'w') as f:
        f.write(f'# BL call targets, sorted by call count\n')
        f.write(f'# Total unique targets: {len(bl_targets)}\n\n')
        # Sort by count descending
        sorted_targets = sorted(bl_targets.items(), key=lambda x: -x[1])
        for target, count in sorted_targets:
            f.write(f'0x{target:08x} called {count} times\n')
    
    with open(outdir + '/bl_calls.txt', 'w') as f:
        f.write(f'# BL calls (from -> to)\n')
        for from_addr, to_addr in bl_calls:
            f.write(f'0x{from_addr:08x} -> 0x{to_addr:08x}\n')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
