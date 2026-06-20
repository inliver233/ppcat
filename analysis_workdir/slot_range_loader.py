#!/usr/bin/env python3
"""Find which functions load the most pool slots in a given index range.
Uses pool_accesses.txt (pc, pool_offset, line). Groups by containing function."""
import sys, json, bisect, struct
from collections import defaultdict

# build function start table from libapp prologue scan
DATA=open('/root/ppcat_repo/libapp.so','rb').read()
TS=0x460000; PROL=bytes.fromhex('fd79bfa9fd030faa')
FUNCS=[]; a=TS
while a<len(DATA)-8:
    if DATA[a:a+8]==PROL: FUNCS.append(a)
    a+=4
XREF=json.load(open('xref_db.json'))

lo=int(sys.argv[1],0); hi=int(sys.argv[2],0)
looff=lo*8; hioff=hi*8
tally=defaultdict(list)   # func -> [slots]
seen=defaultdict(set)     # func -> set(slots) to dedupe
with open('/root/ppcat_repo/pool_accesses.txt') as f:
    for line in f:
        if not line.startswith('0x'): continue
        parts=line.split()
        pc=int(parts[0],16); off=int(parts[1],16)
        if looff<=off<hioff:
            slot=off//8
            i=bisect.bisect_right(FUNCS,pc)-1
            fn=FUNCS[i] if i>=0 else None
            if slot not in seen[fn]:
                seen[fn].add(slot); tally[fn].append(slot)
print(f'# slots 0x{lo:x}-0x{hi:x} ({hi-lo} slots): which funcs load most')
for fn in sorted(tally, key=lambda f:-len(tally[f]))[:12]:
    info=XREF.get(str(fn),{})
    slots=sorted(tally[fn])
    print(f'  func 0x{fn:x}  loads {len(slots)} slots: {[hex(s) for s in slots]}  callers={len(info.get("callers",[]))} bool={info.get("bool_ret")} strs={[s[:20] for s in info.get("strs",[])[:2]]}')
