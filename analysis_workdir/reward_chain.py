#!/usr/bin/env python3
"""Map reward grant -> privilege -> ad-suppress chain. Find getRewardTime + reward grant + ad gate."""
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
d=data
acc={}
for line in open('pool_accesses.txt'):
    line=line.strip()
    if line.startswith('#') or not line: continue
    p=line.split(); acc[int(p[0],16)]=int(p[1],16)
off2pcs={}
for p,o in acc.items(): off2pcs.setdefault(o,[]).append(p)
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

# reward-related refs -> funcs
reward_refs=[8067,7606,6398,6808,2839,3236,5449,5512,25959,12372,16427,32387,30042,31760]
print('=== reward/privilege ref -> funcs -> callers ===')
for r in reward_refs:
    off=ref2off.get(r)
    if not off: continue
    pcs=off2pcs.get(off,[]); funcs=sorted(set(fstart(p) for p in pcs))
    print('ref %6d off 0x%x %r'%(r,off,strings.get(r,'')[:30]))
    for fs in funcs[:4]:
        cs=blcallers(fs)
        print('     func 0x%x callers(%d) %s'%(fs,len(cs),[hex(c) for c in cs[:6]]))
