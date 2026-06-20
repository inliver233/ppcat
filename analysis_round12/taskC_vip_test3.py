#!/usr/bin/env python3
"""Task C: examine VIP branch 0xb9fc84 and ctor 0xa54178, find isVip force-true patch."""
import sys
from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent))
from taskA_deserialize import data, parse_pool
from capstone import *
entries,_,_=parse_pool(0x2e7043,51140)
off2ref={e[0]*8:e[2] for e in entries if e[1]==0}
d=data
md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)

# load strings
strings={}
for line in open(Path(__file__).resolve().parents[1] / 'unflutter_strings.txt'):
    if '[ref=' in line:
        try:
            r=int(line.split('[ref=')[1].split(']')[0]); q=line.split('"',1)[1].rsplit('"',1)[0]; strings[r]=q
        except: pass

def show(addr, n=0x60, label=""):
    print(f"\n=== {label} 0x{addr:x} ===")
    for ins in md.disasm(d[addr:addr+n], addr):
        ann=''
        print(f"0x{ins.address:08x}: {ins.bytes.hex():16s} {ins.mnemonic:6s} {ins.op_str}{ann}")
        # note CMP with W22 (null sentinel) often = isXxx checks
        if 'w22' in ins.op_str and ins.mnemonic in ('cmp','cbz','cbnz'): print('    ^^^ null/flag compare')

# VIP branch (decides isVip)
show(0xb9fc84, 0x40, "VIP branch 0xb9fc84")
# around ba0070/ba007c (branch targets)
show(0xba0070, 0x30, "VIP branch target 0xba0070")

# isVip: find functions accessing VIP-status strings. ref 7406 'expiresDate', 12056 'expires'
# the isVip likely reads a SharedPreferences bool. Let me find what 0xa54178 (VIP ctor) accesses re: vip
print("\n=== VIP ctor 0xa54178 string accesses (from pool) ===")
acc={}
for line in open(Path(__file__).resolve().parents[1] / 'analysis_round6' / 'pool_accesses.txt'):
    line=line.strip()
    if line.startswith('#') or not line: continue
    p=line.split()
    acc[int(p[0],16)]=int(p[1],16)
for p,o in sorted(acc.items()):
    if 0xa54178<=p<0xa55c80:
        r=off2ref.get(o,-1); s=strings.get(r,'')
        if s and ('vip' in s.lower() or 'expire' in s.lower() or 'VIP' in s or '会员' in s or '捐赠' in s or '每天' in s or '每日' in s or 'sign' in s.lower()):
            print(f"  0x{p:x} off 0x{o:x} ref {r} {s[:40]!r}")
