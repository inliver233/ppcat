#!/usr/bin/env python3
"""Query the master xref DB to attack unsolved questions."""
import json
db=json.load(open('xref_db.json'))
db={int(k):v for k,v in db.items()}

def funcs_with_strings(keywords, bool_only=False):
    """functions accessing ANY of these keyword-strings, optionally bool-returning."""
    out=[]
    for f,v in db.items():
        if bool_only and not v['bool_ret']: continue
        hit=[s for s in v['strings'] if any(k in s for k in keywords)]
        if hit:
            out.append((f,hit,v))
    return out

print("="*70)
print("Q1: bool-returning functions accessing VIP/privilege/ad-quota strings")
print("   (candidates for the ad-suppress / isPrivileged gate)")
print("="*70)
KW1=['rewardTime','adNum','expiresDate','已生效','已过期','特权','leaveTime','noAd','isVip','vipExpire']
for f,hit,v in funcs_with_strings(KW1, bool_only=True):
    print(f"  0x{f:x} (callers {len(v['callers'])}): {[h[:18] for h in hit[:5]]}")

print("\n"+"="*70)
print("Q2: who calls the privilege checker 0x8cf36c, and are THEY bool-returning?")
print("="*70)
if 0x8cf36c in db:
    callers=db[0x8cf36c]['callers']
    for c in callers:
        cv=db.get(c,{})
        print(f"  caller 0x{c:x} bool_ret={cv.get('bool_ret')} strings={[s[:14] for s in list(cv.get('strings',{}))[:4]]}")

print("\n"+"="*70)
print("Q3: bool-returning functions accessed by the ad-engine 0x8758bc and its caller 0x875794")
print("="*70)
for f in [0x8758bc,0x875794]:
    if f in db:
        v=db[f]
        print(f"  0x{f:x}: callees={[hex(c) for c in v['callees'] if db.get(c,{}).get('bool_ret')][:8]}")

print("\n"+"="*70)
print("Q4: bool-returning functions that gate the banner/feed ad path")
print("   (access 'banner'/'feed'/ad-channel strings AND return bool)")
print("="*70)
for f,hit,v in funcs_with_strings(['pangle','google_mobile_ads','banner','插屏','开屏','激励','fullscreen','Fullscreen'], bool_only=True):
    if len(v['callers'])>0:
        print(f"  0x{f:x}: {[h[:16] for h in hit[:4]]}")
