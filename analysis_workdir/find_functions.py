#!/usr/bin/env python3
"""Find function prologues using capstone."""
import struct
import sys
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

def main(libapp_path, output_path):
    with open(libapp_path, 'rb') as f:
        data = f.read()
    
    TEXT_START = 0x464ce0
    TEXT_SIZE = 0xb329d0
    
    md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    md.detail = False
    
    prologues = []
    
    # Scan in 4-byte aligned steps, decode each instruction
    # Look for prologue patterns:
    #   stp x29, x30, [sp, #-N]!
    #   stp x29, x30, [x15, #-N]!    (Dart uses x15 as shadow stack in some configs)
    #   sub sp, sp, #N (sometimes a prologue)
    
    code = data[TEXT_START:TEXT_START + TEXT_SIZE]
    
    prologue_count = 0
    # Iterate instructions efficiently
    for ins in md.disasm(code, TEXT_START):
        mn = ins.mnemonic
        op = ins.op_str
        if mn == 'stp' and ('x29, x30' in op or 'x29, x30,' in op):
            if '!' in op or '], #' in op:  # pre-index or post-index
                prologues.append(ins.address)
                prologue_count += 1
    
    print(f'Found {prologue_count} STP x29, x30 prologues')
    
    with open(output_path, 'w') as f:
        f.write(f'# Function entries in {libapp_path}\n')
        f.write(f'# Range: 0x{TEXT_START:x}-0x{TEXT_START+TEXT_SIZE:x}\n')
        f.write(f'# Prologues found: {len(prologues)}\n\n')
        for addr in prologues:
            f.write(f'0x{addr:08x}\n')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
