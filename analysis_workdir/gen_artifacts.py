#!/usr/bin/env python3
"""Generate deliverable artifacts: full ref->slot map + popup orchestrator survey."""
import sys; sys.path.insert(0,'analysis_workdir')
from taskA_deserialize import parse_pool, data
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
off2pcs={}
for p,o in acc.items(): off2pcs.setdefault(o,[]).append(p)
with open('libapp.so','rb') as f: d=f.read()
def fstart(pc):
    for a in range(pc,max(0,pc-0x8000),-4):
        if d[a:a+4]==bytes.fromhex('fd79bfa9') and d[a+4:a+8]==bytes.fromhex('fd030faa'): return a
    return pc

# 1) key refs map
KEY_REFS=[27673,29112,21707,22466,26842,30947,30922,  # anchors + dialogs
          14719,19944,12372,32387,16427,  # reward
          11366,8910,13169,7406,12056,  # vip/donate
          5520,23584,11225,20086,  # update
          23406,17612,11470]  # fault variants
with open('analysis_workdir/KEY_REFS_MAP.txt','w') as f:
    f.write("# ref -> slot -> offset -> .text accessor PCs (file offsets)\n")
    for r in KEY_REFS:
        off=None
        for e in entries:
            if e[1]==0 and e[2]==r: off=e[0]*8; break
        if off is None: f.write(f"ref {r}: NOT IN POOL\n"); continue
        pcs=off2pcs.get(off,[])
        funcs=sorted(set(fstart(p) for p in pcs))
        f.write(f"ref {r:>6} slot 0x{off//8:x} off 0x{off:x} | {strings.get(r,'')[:40]}\n")
        f.write(f"   .text PCs: {[hex(p) for p in pcs[:8]]}  funcs: {[hex(x) for x in funcs[:5]]}\n")
print("wrote KEY_REFS_MAP.txt")

# 2) popup survey: all functions accessing 2+ dialog-ish strings
DLG_KW=['故障','每日喂喵','喵喵饿了','无法','广告','失败','错误','升级','更新','版本','reward','捐赠','过期','expire','请']
func_strings={}
for off,pcs in off2pcs.items():
    r=off2ref.get(off,-1); s=strings.get(r,'')
    if not s: continue
    for p in pcs:
        fs=fstart(p)
        func_strings.setdefault(fs,{}).setdefault(r,s)
with open('analysis_workdir/POPUP_SURVEY.txt','w') as f:
    f.write("# Functions accessing dialog/popup/error strings (>=2 such strings)\n")
    cnt=0
    for fs in sorted(func_strings):
        hits={r:s for r,s in func_strings[fs].items() if any(k in s for k in DLG_KW)}
        if len(hits)>=2:
            cnt+=1
            f.write(f"\nfunc 0x{fs:x} ({len(hits)} dlg-strings):\n")
            for r,s in sorted(hits.items())[:12]:
                f.write(f"   ref {r:>6}: {s[:50]!r}\n")
    f.write(f"\n# total candidate popup orchestrators: {cnt}\n")
print(f"wrote POPUP_SURVEY.txt ({cnt} candidates)")
