#!/usr/bin/env python3
"""Disassemble 0x8758bc (ad-engine decision: reads AdMob_Reward/AdPgl_Reward/noAdRegex).
Find the boolean that gates whether to show ads."""
import sys; sys.path.insert(0,'analysis_workdir')
from taskA_deserialize import parse_pool, data
from capstone import *
import struct
entries,_,_=parse_pool(0x2e7043,51140)
off2ref={e[0]*8:e[2] for e in entries if e[1]==0}
strings={}
for line in open('unflutter_strings.txt'):
    if '[ref=' in line:
        try:
            r=int(line.split('[ref=')[1].split(']')[0]); q=line.split('"',1)[1].rsplit('"',1)[0]; strings[r]=q
        except: pass
d=data; md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
def fstart(pc):
    for a in range(pc,max(0,pc-0x8000),-4):
        if d[a:a+4]==bytes.fromhex('fd79bfa9') and d[a+4:a+8]==bytes.fromhex('fd030faa'): return a
    return pc
FS=fstart(0x8758bc); FE=FS+0x700
for a in range(FS+4,FS+0x700,4):
    if d[a:a+8]==bytes.fromhex('fd79bfa9fd030faa'): FE=a; break
print('func 0x8758bc -> 0x%x..0x%x'%(FS,FE))
# collect string pool accesses with base tracking
acc={}
for line in open('pool_accesses.txt'):
    line=line.strip()
    if line.startswith('#') or not line: continue
    p=line.split(); acc[int(p[0],16)]=int(p[1],16)
print('string accesses in func:')
for p,o in sorted(acc.items()):
    if FS<=p<FE:
        r=off2ref.get(o,-1)
        print('  0x%x off 0x%x ref %6d %r'%(p,o,r,strings.get(r,'')[:38]))
# callers of 0x8758bc and ITS callers
def blcallers(fs):
    cs=[]
    for a in range(0x460000,len(d)-4,4):
        inst=struct.unpack_from('<I',d,a)[0]
        if (inst&0xFC000000)==0x94000000:
            imm=inst&0x03FFFFFF; imm=imm-(1<<26) if imm&0x02000000 else imm
            if a+imm*4==fs: cs.append(a)
    return cs
print('callers of 0x8758bc:', [hex(c) for c in blcallers(FS)])
print('callers of caller (0x875794 func):', [hex(c) for c in blcallers(fstart(0x875794))])
