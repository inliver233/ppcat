#!/usr/bin/env python3
"""Disassemble device-binding funcs 0x8d10d0 (hwMd5+remoteConfigSign) and 0x8bc3c8 (rule.bin+bootTime).
Characterize the sign/fingerprint verification."""
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
acc={}
for line in open('pool_accesses.txt'):
    line=line.strip()
    if line.startswith('#') or not line: continue
    p=line.split(); acc[int(p[0],16)]=int(p[1],16)
def fstart(pc):
    for a in range(pc,max(0,pc-0x8000),-4):
        if d[a:a+4]==bytes.fromhex('fd79bfa9') and d[a+4:a+8]==bytes.fromhex('fd030faa'): return a
    return pc
for target in [0x8d10d0, 0x8bc3c8, 0xcd9308]:
    fs=fstart(target); fe=fs+0x400
    for a in range(fs+4,fs+0x400,4):
        if d[a:a+8]==bytes.fromhex('fd79bfa9fd030faa'): fe=a;break
    print('\n=== func 0x%x (target 0x%x) sz 0x%x ==='%(fs,target,fe-fs))
    sacc=[(p,o,off2ref.get(o,-1)) for p,o in sorted(acc.items()) if fs<=p<fe and off2ref.get(o,-1)>0]
    for p,o,r in sacc[:30]:
        print('  0x%x ref%d %r'%(p,r,strings.get(r,'')[:38]))
