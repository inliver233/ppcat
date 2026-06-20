#!/usr/bin/env python3
"""Independently decompile 0x911788 (shared time-threshold gate per test1).
Goal: verify CSEL return convention (x22+0x30=pass bit4 set / x22+0x20=fail) and find patch point."""
import sys; sys.path.insert(0,'analysis_workdir')
from taskA_deserialize import parse_pool, data
from capstone import *
entries,_,_=parse_pool(0x2e7043,51140)
off2ref={e[0]*8:e[2] for e in entries if e[1]==0}
strings={}
for line in open('unflutter_strings.txt'):
    if '[ref=' in line:
        try:
            r=int(line.split('[ref=')[1].split(']')[0]); q=line.split('"',1)[1].rsplit('"',1)[0]; strings[r]=q
        except: pass
d=data; md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
reg={}
FS=0x911788; FE=FS+0x400
for a in range(FS+4,FS+0x400,4):
    if d[a:a+8]==bytes.fromhex('fd79bfa9fd030faa'): FE=a; break
print('func 0x911788 .. 0x%x (%d bytes)'%(FE,FE-FS))
for ins in md.disasm(d[FS:FE],FS):
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
            if o2 is not None and o2 in off2ref:
                r=off2ref[o2]; s=strings.get(r,'')
                if s: ex=' ; pool[0x%x] ref%d %r'%(o2,r,s[:22])
            reg.pop(dst,None)
        except: pass
    elif ins.mnemonic in ('csel','csinc','cset'):
        ex=' <<<CSEL'
    else:
        try:
            dst=ins.op_str.split(',')[0].strip()
            if dst and dst[0] in 'xwdsvq': reg.pop(dst,None)
        except: pass
    fl=' <<<' if (ins.mnemonic in('cmp','cbz','cbnz','tbz','tbnz') or ins.mnemonic.startswith('b.') or ins.mnemonic in('ret','blr')) else ''
    print('0x%08x %-13s %-6s %s%s%s'%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,ex,fl))
