#!/usr/bin/env python3
"""Disassemble ad-gate functions: noAdRegex(0x890c6c/0x920a60), noAdAllowSourceList(0x839e80),
getRewardTime, and find the reward-privilege boolean getter."""
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
acc={}
for line in open('pool_accesses.txt'):
    line=line.strip()
    if line.startswith('#') or not line: continue
    p=line.split(); acc[int(p[0],16)]=int(p[1],16)
def fstart(pc):
    for a in range(pc,max(0,pc-0x8000),-4):
        if d[a:a+4]==bytes.fromhex('fd79bfa9') and d[a+4:a+8]==bytes.fromhex('fd030faa'): return a
    return pc

def blcallers(fs):
    cs=[]
    for a in range(0x460000,len(d)-4,4):
        inst=struct.unpack_from('<I',d,a)[0]
        if (inst&0xFC000000)==0x94000000:
            imm=inst&0x03FFFFFF; imm=imm-(1<<26) if imm&0x02000000 else imm
            if a+imm*4==fs: cs.append(a)
    return cs

for label,pc in [('noAdRegex 0x890c6c',0x890c6c),('noAdRegex 0x920a60',0x920a60),
                 ('noAdAllowSourceList 0x839e80',0x839e80)]:
    fs=fstart(pc); fe=fs+0x500
    for a in range(fs+4,fs+0x500,4):
        if d[a:a+8]==bytes.fromhex('fd79bfa9fd030faa'): fe=a; break
    print('\n===== %s: func 0x%x..0x%x ====='%(label,fs,fe))
    sacc=[(p,o,off2ref.get(o,-1)) for p,o in sorted(acc.items()) if fs<=p<fe]
    sacc=[(p,o,r) for p,o,r in sacc if r>0 and strings.get(r,'')]
    for p,o,r in sacc[:25]:
        print('  0x%x off 0x%x ref %6d %r'%(p,o,r,strings.get(r,'')[:40]))
    cs=blcallers(fs)
    print('  callers(%d): %s'%(len(cs),[hex(c) for c in cs[:15]]))
