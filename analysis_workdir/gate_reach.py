#!/usr/bin/env python3
"""Map full caller reach of shared gate 0x911788 + find all functions returning canonical bool
via 'add Xn,x22,#0x20'(false) / 'add Xn,x22,#0x30'(true) that gate VIP/ad paths."""
import sys; sys.path.insert(0,'analysis_workdir')
from taskA_deserialize import parse_pool, data
import struct
entries,_,_=parse_pool(0x2e7043,51140)
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
d=data
def fstart(pc):
    for a in range(pc,max(0,pc-0x8000),-4):
        if d[a:a+4]==bytes.fromhex('fd79bfa9') and d[a+4:a+8]==bytes.fromhex('fd030faa'): return a
    return pc
def callers(fs):
    cs=[]
    for a in range(0x460000,len(d)-4,4):
        inst=struct.unpack_from('<I',d,a)[0]
        if (inst&0xFC000000)==0x94000000:
            imm=inst&0x03FFFFFF; imm=imm-(1<<26) if imm&0x02000000 else imm
            if a+imm*4==fs: cs.append(a)
    return cs

# 1) full callers of shared gate 0x911788
print('=== ALL callers of shared gate 0x911788 ===')
cs=callers(0x911788)
print('count:', len(cs))
for c in cs:
    fs=fstart(c)
    # what strings does that caller-func access?
    sset=set()
    for p,o in acc.items():
        if fs<=p<fs+0x800:
            r=off2ref.get(o,-1); s=strings.get(r,'')
            if s and len(s)<30: sset.add(s)
    vip_hits=[s for s in sset if any(k in s for k in ['VIP','vip','捐赠','特权','广告','reward','Reward','喵','生效','获得','绑定','expire','Expires','更新','故障','免广告'])]
    print('  caller 0x%x (func 0x%x): VIP/ad strings=%s'%(c,fs, vip_hits[:6]))

# 2) functions that BOTH (a) call 0x911788 AND (b) return canonical bool via add x..,x22,#0x30/0x20
# scan each caller-func for the canonical-bool pattern near its own return
print('\n=== caller-funcs that also gate (return canonical bool) ===')
# encode: ADD Xd,X22,#imm  = 0x91, imm12, X22(=22*32=0x2C0 shift5?), Xd  => add immediate
# ADD (immediate) 64-bit: sf=1 op=0 S=0 100010 sh imm12 Rn Rd -> 0x91000000 | (imm12<<10) | (Rn<<5) | Rd
# Rn=22 (0x16), imm=0x20 or 0x30
import capstone
md=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_LITTLE_ENDIAN)
caller_funcs=sorted(set(fstart(c) for c in cs))
for fs in caller_funcs:
    fe=fs+0x1000
    for a in range(fs+4,fs+0x1000,4):
        if d[a:a+8]==bytes.fromhex('fd79bfa9fd030faa'): fe=a;break
    has_bool=False
    for ins in md.disasm(d[fs:fe],fs):
        if ins.mnemonic=='add' and ('x22, #0x2' in ins.op_str or 'x22, #0x3' in ins.op_str):
            has_bool=True;break
    if has_bool:
        print('  func 0x%x: returns canonical bool (gates downstream)'%fs)
