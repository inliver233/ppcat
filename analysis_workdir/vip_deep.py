#!/usr/bin/env python3
"""Deep VIP chain analysis. Goal: find the isVip master getter that gates ads + features.
Hypothesis: force isVip=true -> ads auto-disappear + features unlock (user's insight)."""
import sys; sys.path.insert(0,'analysis_workdir')
from taskA_deserialize import parse_pool, data

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
acc={}
for line in open('pool_accesses.txt'):
    line=line.strip()
    if line.startswith('#') or not line: continue
    p=line.split(); acc[int(p[0],16)]=int(p[1],16)
off2pcs={}
for p,o in acc.items(): off2pcs.setdefault(o,[]).append(p)
with open('libapp.so','rb') as f: d=f.read()
def fstart(pc):
    for a in range(pc,max(0,pc-0x8000),-4):
        if d[a:a+4]==bytes.fromhex('fd79bfa9') and d[a+4:a+8]==bytes.fromhex('fd030faa'): return a
    return pc

# 1) ALL VIP/privilege/donation related strings -> slot -> .text
KW=['vip','VIP','Vip','捐赠','特权','expire','Expires','premium','Premium','pro',
    '生效','获得','绑定','解绑','浏览次数','0点','解锁','unlock','donate','sponsor',
    '会员','会员费','赞助','赞助商','开通','payVip','isVip','isVipUser']
print("="*70)
print("1) VIP/privilege strings -> slot -> .text accessors")
print("="*70)
hits=[]
for r,s in strings.items():
    if any(k in s for k in KW) and len(s)<60:
        off=ref2off.get(r)
        if off is None: continue
        pcs=off2pcs.get(off,[])
        funcs=sorted(set(fstart(p) for p in pcs))
        hits.append((r,s,off,pcs,funcs))
hits.sort(key=lambda x:x[2])
for r,s,off,pcs,funcs in hits:
    print(f"ref {r:>6} slot 0x{off//8:x} off 0x{off:x} | {s[:45]!r}")
    if pcs: print(f"          .text: {[hex(p) for p in pcs[:6]]} funcs {[hex(x) for x in funcs[:5]]}")

# 2) SharedPreferences-style keys (camelCase) likely holding VIP state
print("\n"+"="*70)
print("2) SharedPreferences-key-like strings (vip/expire/isVip) -> getters")
print("="*70)
SP_KW=['vipExpire','isVip','isVIP','vipLevel','vipStatus','vipTime','vipInfo','vipData',
       'isPro','isPremium','proUser','vipUser','payVip','hasVip','vip_type','vip_end',
       'vipExpireTime','vipExpireDate','expireTime','expireDate','isDonor','isDonation']
for r,s in strings.items():
    if any(k.lower() in s.lower() for k in SP_KW) and len(s)<50:
        off=ref2off.get(r)
        pcs=off2pcs.get(off,[]) if off else []
        funcs=sorted(set(fstart(p) for p in pcs)) if pcs else []
        print(f"  ref {r:>6} '{s}': off {hex(off) if off else None} funcs {[hex(x) for x in funcs[:5]]}")
