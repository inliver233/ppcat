#!/usr/bin/env python3
"""Master mapping: for important UI/dialog/VIP strings, find ref->slot->offset->.text PCs."""
import sys
sys.path.insert(0, 'analysis_workdir')
from taskA_deserialize import parse_pool, data
import re

entries, _, _ = parse_pool(0x2e7043, 51140)
off2ref = {e[0]*8: e[2] for e in entries if e[1]==0}
ref2off = {}
for e in entries:
    if e[1]==0: ref2off.setdefault(e[2], e[0]*8)
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
    parts=line.split()
    if len(parts)>=2: acc[int(parts[0],16)]=int(parts[1],16)
off2pcs={}
for p,o in acc.items(): off2pcs.setdefault(o,[]).append(p)

with open('libapp.so','rb') as f: d=f.read()
def find_func_start(pc):
    for a in range(pc, max(0,pc-0x6000), -4):
        if d[a:a+4]==bytes.fromhex('fd79bfa9') and d[a+4:a+8]==bytes.fromhex('fd030faa'):
            return a
    return pc

# Keywords to find dialog/popup/VIP/reward/update related strings
KW = ['故障','每日喂喵','喵喵饿了','无法加载','无法正常联网','广告','VIP','vip','捐赠','更新','版本','reward',
      'isVip','isVIP','vipLevel','expire','过期','会员','签到','奖励','激励','去广告','购买','赞助','sponsor',
      '请升级','屏蔽','network','Network','请稍后']

print("=== Strings matching keywords -> slot -> .text accessors ===")
found=[]
for r,s in strings.items():
    if any(k in s for k in KW):
        off = ref2off.get(r)
        if off is None: continue
        pcs = off2pcs.get(off, [])
        funcs = sorted(set(find_func_start(p) for p in pcs))
        found.append((r,s,off,pcs,funcs))

# print the most interesting (those with accessors)
found.sort(key=lambda x: x[2])
for r,s,off,pcs,funcs in found:
    if pcs:
        print(f"ref {r:>6} off 0x{off:05x} slot 0x{off//8:x} | {s[:30]!r}")
        print(f"          .text PCs: {[hex(p) for p in pcs[:6]]} funcs: {[hex(f) for f in funcs[:4]]}")

# VIP-specific: 0xa54178 is VIP constructor; list ALL pool accesses in it
print("\n=== VIP constructor 0xa54178 — all string pool accesses ===")
fs_vip = 0xa54178
for p,o in sorted(acc.items()):
    if fs_vip <= p < fs_vip+0x1000:
        r=off2ref.get(o,-1); s=strings.get(r,'')
        if s: print(f"  0x{p:x} off 0x{o:05x} ref {r:>6} {s[:40]!r}")
