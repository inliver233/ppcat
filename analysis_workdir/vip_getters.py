#!/usr/bin/env python3
"""Find VIP getter candidates + disassemble the most promising (expires/skipCount)."""
import sys; sys.path.insert(0,'analysis_workdir')
from taskA_deserialize import parse_pool, data
from capstone import *
import struct
entries,_,_=parse_pool(0x2e7043,51140)
ref2off={}
for e in entries:
    if e[1]==0: ref2off.setdefault(e[2],e[0]*8)
off2ref={e[0]*8:e[2] for e in entries if e[1]==0}
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
off2pcs={}
for p,o in acc.items(): off2pcs.setdefault(o,[]).append(p)
def fstart(pc):
    for a in range(pc,max(0,pc-0x8000),-4):
        if data[a:a+4]==bytes.fromhex('fd79bfa9') and data[a+4:a+8]==bytes.fromhex('fd030faa'): return a
    return pc

# Show the actual matching strings clearly
KW=['gentle.com','?i=','?u=','/meta','/store','version','ppcat_store','ghostgzt','invite','inviteCode','userId','uid','deviceId','signCode','activeCode','激活','邀请码','兑换码','cdkey','giftCode','vip','VIP','特权','生效','获得','绑定','skipCount','expires']
print('=== VIP/server/privilege strings ===')
shown=set()
for r,s in sorted(strings.items()):
    if any(k in s for k in KW) and len(s)<80 and r not in shown:
        shown.add(r); off=ref2off.get(r); pcs=off2pcs.get(off,[]) if off else []
        funcs=sorted(set(fstart(p) for p in pcs)) if pcs else []
        print('  ref %6d off %s | %r'%(r, hex(off) if off else 'N/A', s[:58]))
        if funcs: print('             funcs %s'%[hex(x) for x in funcs[:5]])
