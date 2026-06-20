#!/usr/bin/env python3
"""Find the reward anti-cheat decision: where 'onReward Cheat Triggered!' branch gates reward grant."""
import sys; sys.path.insert(0,'analysis_workdir')
from taskA_deserialize import parse_pool, data
from capstone import *
import struct
entries,_,_=parse_pool(0x2e7043,51140)
off2ref={e[0]*8:e[2] for e in entries if e[1]==0}
ref2off={}
for e in entries:
    if e[1]==0: ref2off.setdefault(e[2],e[0]*8)
strings={}
for line in open('unflutter_strings.txt'):
    if '[ref=' in line:
        try:
            r=int(line.split('[ref=')[1].split(']')[0]); q=line.split('"',1)[1].rsplit('"',1)[0]; strings[r]=q
        except: pass
acc={}
for line in open('pool_accesses.txt'):
    line=line.strip()
    if line.startswith('#') or not line: continue
    p=line.split(); acc[int(p[0],16)]=int(p[1],16)
d=data; md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
def fstart(pc):
    for a in range(pc,max(0,pc-0x8000),-4):
        if d[a:a+4]==bytes.fromhex('fd79bfa9') and d[a+4:a+8]==bytes.fromhex('fd030faa'): return a
    return pc

# find all accesses to ref 11545 'onReward Cheat Triggered!'
print("ref 11545 'onReward Cheat Triggered!':")
off=ref2off[11545]
print("  slot off 0x%x"%off)
pcs=[p for p,o in acc.items() if o==off]
print("  loaded at PCs:", [hex(p) for p in pcs])
for pc in pcs:
    fs=fstart(pc)
    print("\n  === in func 0x%x, around cheat-load 0x%x ==="%(fs,pc))
    # disasm around it, annotate pool loads
    reg={}
    for ins in md.disasm(d[pc-0x40:pc+0x40], pc-0x40):
        ex=''
        if ins.mnemonic=='add' and 'x27' in ins.op_str and 'lsl' in ins.op_str:
            try:
                parts=ins.op_str.split(','); dst=parts[0].strip()
                imm=int(parts[2].strip().replace('#',''),0); sh=int(parts[3].split('#')[1].strip(),0)
                if 'x27' in parts[1]: reg[dst]=imm<<sh
                else: reg.pop(dst,None)
            except: pass
        elif ins.mnemonic in ('ldr','ldur'):
            try:
                parts=ins.op_str.split(','); dst=parts[0].strip(); mem=parts[1].strip()
                base=mem.split('[')[1].split(',')[0].strip(); imm=0
                if '#' in mem: imm=int(mem.split('#')[1].replace(']','').strip(),0)
                o2=None
                if base=='x27': o2=imm
                elif base in reg: o2=reg[base]+imm
                if o2 is not None:
                    r=off2ref.get(o2,-1); s=strings.get(r,'')
                    if s: ex=' ; ref%d %r'%(r,s[:22])
                reg.pop(dst,None)
            except: pass
        else:
            try:
                dst=ins.op_str.split(',')[0].strip()
                if dst and dst[0] in 'xwdsvq': reg.pop(dst,None)
            except: pass
        fl=' <<<' if (ins.mnemonic in('cmp','cbz','cbnz','tbz','tbnz') or ins.mnemonic.startswith('b.') or ins.mnemonic in('ret','blr')) else ''
        print("    0x%08x %-13s %-6s %s%s%s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,ex,fl))
