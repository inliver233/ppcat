#!/usr/bin/env python3
"""Disassemble 0x8cf36c (privilege/ad-quota time checker) fully — find 已生效/已过期 bool decision."""
import sys; sys.path.insert(0,'analysis_workdir')
from taskA_deserialize import data, parse_pool
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
FS=0x8cf36c; FE=0x8cfb6c
reg={}
insns=list(md.disasm(d[FS:FE],FS))
for ins in insns:
    extra=''
    op=ins.op_str.replace(' ','')
    # track ADD Xn,X27,#imm,LSL#sh
    if ins.mnemonic=='add' and 'x27' in ins.op_str and 'lsl' in ins.op_str:
        try:
            parts=ins.op_str.split(','); dst=parts[0].strip()
            imm=int(parts[2].strip().replace('#',''),0); sh=int(parts[3].split('#')[1].strip(),0)
            if 'x27' in parts[1]: reg[dst]=imm<<sh; extra=' ; +%d'%(imm<<sh)
            else: reg.pop(dst,None)
        except: pass
    elif ins.mnemonic in ('ldr','ldur'):
        try:
            parts=ins.op_str.split(','); dst=parts[0].strip(); mem=parts[1].strip()
            base=mem.split('[')[1].split(',')[0].strip()
            imm=0
            if '#' in mem: imm=int(mem.split('#')[1].replace(']','').strip(),0)
            if base=='x27':
                off=imm; r=off2ref.get(off,-1); extra=' ; pool[0x%x]'%off+((' ref%d'%r+(' '+strings.get(r,'')[:18]) if r>0 else ''))
            elif base in reg:
                off=reg[base]+imm; r=off2ref.get(off,-1); extra=' ; pool[0x%x]'%off+((' ref%d'%r+(' '+strings.get(r,'')[:18]) if r>0 else ''))
            reg.pop(dst,None)
        except: pass
    else:
        try:
            dst=ins.op_str.split(',')[0].strip()
            if dst[0] in ('x','w','d','s','q','v'): reg.pop(dst,None)
        except: pass
    flag=''
    if ins.mnemonic in ('cmp','cbz','cbnz','tbz','tbnz','b.eq','b.ne','b.le','b.lt','b.ge','b.gt','b.ls','b.hs'): flag=' <<<BRANCH'
    if ins.mnemonic in ('ret','b'): flag=' <<<'+ins.mnemonic.upper()
    print('0x%08x: %-14s %-6s %s%s%s'%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,extra,flag))
