#!/usr/bin/env python3
"""Task B precise: disassemble around daily-feed title accesses to find dialog-show BLs."""
import sys
from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent))
from taskA_deserialize import data
from capstone import *
d=data; md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
# daily-feed title load PCs in 0xae71bc: 0xae72b0, 0xae72f8, 0xae7524
for pc in [0xae72b0, 0xae72f8, 0xae7524]:
    print(f"\n===== around daily-feed title load 0x{pc:x} =====")
    start=pc-0x30
    for ins in md.disasm(d[start:start+0x70], start):
        mark=''
        if ins.address==pc: mark=' <== TITLE LOAD'
        if ins.mnemonic=='bl': mark+=' [BL ->'+ins.op_str+']'
        # STP x..,[x15] or add x15,x15 = push/pop markers
        if ins.mnemonic=='stp' and '[x15' in ins.op_str.replace(' ',''): mark+=' PUSH'
        if ins.mnemonic in ('ldp',) and '[x15' in ins.op_str.replace(' ',''): mark+=' POP(ldp)'
        if ins.mnemonic=='add' and 'x15, x15' in ins.op_str: mark+=' POP(add)'
        print(f"0x{ins.address:08x}: {ins.bytes.hex():16s} {ins.mnemonic:6s} {ins.op_str}{mark}")
