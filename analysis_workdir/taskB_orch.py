#!/usr/bin/env python3
"""Task B: find dialog-show BL points in daily-feed & fault orchestrators.
Pattern (safe NOP, per 关键教训 #7): BL preceded by 2x STP push, followed by add X15 pop.
NOP the BL (1f2003d5); return value overwritten by subsequent MOV X0,X22."""
import sys
sys.path.insert(0, 'analysis_workdir')
from taskA_deserialize import parse_pool, data
from capstone import *

entries,_,_ = parse_pool(0x2e7043,51140)
off2ref={e[0]*8:e[2] for e in entries if e[1]==0}

with open('libapp.so','rb') as f: d=f.read()
md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)

def find_func_start(pc):
    for a in range(pc,max(0,pc-0x8000),-4):
        if d[a:a+4]==bytes.fromhex('fd79bfa9') and d[a+4:a+8]==bytes.fromhex('fd030faa'): return a
    return pc

def analyze(func_starts, label):
    print(f"\n{'='*60}\n{label}\n{'='*60}")
    for fs in func_starts:
        # find func end (next prologue)
        fe=fs+0x10
        for a in range(fs+4, fs+0x4000, 4):
            if d[a:a+8]==bytes.fromhex('fd79bfa9fd030faa'):
                fe=a; break
        else: fe=fs+0x2000
        insns=list(md.disasm(d[fs:fe],fs))
        # find BL targets, flag dialog-show pattern
        print(f"\n--- func 0x{fs:x}..0x{fe:x} ({len(insns)} insns) ---")
        # show key pool accesses (string refs)
        for i,ins in enumerate(insns):
            pass
        # find BL instructions and check push/pop around them
        bls=[]
        for i,ins in enumerate(insns):
            if ins.mnemonic=='bl':
                tgt=int(ins.op_str.replace('#',''),16) if ins.op_str.startswith('#') else None
                if tgt:
                    # check preceding 2 STP push to X15 and following add x15
                    prev2 = insns[i-2] if i>=2 else None
                    prev1 = insns[i-1] if i>=1 else None
                    nxt1 = insns[i+1] if i+1<len(insns) else None
                    nxt2 = insns[i+2] if i+2<len(insns) else None
                    push = prev2 and prev2.mnemonic=='stp' and '[x15' in prev2.op_str.replace(' ','') and prev1 and prev1.mnemonic=='stp' and '[x15' in prev1.op_str.replace(' ','')
                    # add x15, x15, #imm  (pop equivalent)
                    pop = nxt1 and nxt1.mnemonic=='add' and 'x15, x15' in nxt1.op_str
                    # MOV X0, X22 after
                    movnull = (nxt1 and nxt1.mnemonic=='mov' and nxt1.op_str=='x0, x22') or (nxt2 and nxt2.mnemonic=='mov' and nxt2.op_str=='x0, x22')
                    if push and pop:
                        bls.append((ins.address, tgt, 'PUSH+POP', 'MOVX0X22' if movnull else 'no-mov'))
        # known dialog-show targets from 关键教训: 0x47369c, 0x4670b0, 0x485530, 0x472c98
        DIALOG_TGTS={0x47369c,0x4670b0,0x485530,0x472c98,0x4823e4,0x47acc0}
        for addr,tgt,why,mov in bls:
            mark=' <== DIALOG-SHOW' if tgt in DIALOG_TGTS else ''
            print(f"  0x{addr:x}: BL 0x{tgt:x} [{why} {mov}]{mark}")

# Daily-feed: title 21707 accessors + body 22466 accessor
analyze([0xae71bc, 0x846b1c, 0xb68234], "DAILY-FEED candidates (21707 title / 22466 body)")
# Fault body real builder
analyze([0x920d7c], "FAULT body builder (real, ref27673)")
