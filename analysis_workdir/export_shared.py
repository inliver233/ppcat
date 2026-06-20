#!/usr/bin/env python3
"""Export xref_db.json into human-readable shared artifacts for test1/test2 collaboration:
1. STRING_INDEX.txt  : every string -> list of funcs that access it (reverse index)
2. FUNC_TABLE.txt    : every function -> size, caller count, callee count, bool_ret, top strings
3. BOOL_GATES.txt    : all bool-returning funcs (the gate candidates) with their key strings
"""
import json, sys
sys.path.insert(0,'analysis_workdir')
db=json.load(open('xref_db.json'))
db={int(k):v for k,v in db.items()}

# 1) STRING reverse index
sindex={}
for f,v in db.items():
    for s,c in v['strings'].items():
        sindex.setdefault(s,[]).append((f,c))
with open('analysis_workdir/SHARED_STRING_INDEX.txt','w') as out:
    out.write('# SHARED (test3): string -> functions that access it (reverse index)\n')
    out.write(f'# {len(sindex)} unique strings, {len(db)} functions\n')
    out.write('# format: STRING | func1:count func2:count ...\n\n')
    for s in sorted(sindex):
        funcs=sindex[s]
        out.write(f'{s!r} | {" ".join(f"0x{f:x}:{c}" for f,c in sorted(funcs)[:20])}\n')
print(f'SHARED_STRING_INDEX.txt: {len(sindex)} strings')

# 2) FUNC TABLE
with open('analysis_workdir/SHARED_FUNC_TABLE.txt','w') as out:
    out.write('# SHARED (test3): function table from fully-deserialized pool\n')
    out.write('# format: func  end  ncallers  ncallees  bool_ret  top_strings\n\n')
    for f in sorted(db):
        v=db[f]
        ts=sorted(v['strings'].items(), key=lambda x:-x[1])[:5]
        ts_s=' '.join(f'{s[:18]!r}({c})' for s,c in ts)
        out.write(f'0x{f:x}  end0x{v["end"]:x}  callers{len(v["callers"])}  callees{len(v["callees"])}  bool={int(v["bool_ret"])}  | {ts_s}\n')
print(f'SHARED_FUNC_TABLE.txt: {len(db)} functions')

# 3) BOOL GATES (candidates for isXxx switches)
KW=['广告','ad','Ad','reward','Reward','vip','VIP','特权','生效','过期','expire','捐赠',
    'noAd','NoAd','Lock','isNoAd','喵','喂','才能','forceVersion','remoteConfig','sign','Sign',
    'isVip','isPro','版本','更新','update','banner','插屏','开屏','激励','fullscreen']
with open('analysis_workdir/SHARED_BOOL_GATES.txt','w') as out:
    out.write('# SHARED (test3): bool-returning functions accessing ad/VIP/privilege strings\n')
    out.write('# These are the gate/switch candidates (canonical-bool: x22+0x30=true, x22+0x20=false)\n\n')
    cnt=0
    for f in sorted(db):
        v=db[f]
        if not v['bool_ret']: continue
        hit=[(s,c) for s,c in v['strings'].items() if any(k in s for k in KW)]
        if not hit: continue
        cnt+=1
        hit.sort(key=lambda x:-x[1])
        out.write(f'0x{f:x} (callers={len(v["callers"])}): '+' '.join(f'{s[:20]!r}' for s,c in hit[:6])+'\n')
        out.write(f'   callers: {[hex(c) for c in v["callers"][:10]]}\n')
print(f'SHARED_BOOL_GATES.txt: {cnt} gate candidates')
