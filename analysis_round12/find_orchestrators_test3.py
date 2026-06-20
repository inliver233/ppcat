#!/usr/bin/env python3
"""Find dialog orchestrators: functions accessing pairs of (title,body) slots."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from taskA_deserialize import parse_pool, data

entries, _, _ = parse_pool(0x2e7043, 51140)
off2ref = {e[0]*8: e[2] for e in entries if e[1]==0}
ref2off = {}
for e in entries:
    if e[1]==0: ref2off.setdefault(e[2], e[0]*8)
strings={}
for line in open(Path(__file__).resolve().parents[1] / 'unflutter_strings.txt'):
    if '[ref=' in line:
        try:
            r=int(line.split('[ref=')[1].split(']')[0]); q=line.split('"',1)[1].rsplit('"',1)[0]; strings[r]=q
        except: pass

acc={}
for line in open(Path(__file__).resolve().parents[1] / 'analysis_round6' / 'pool_accesses.txt'):
    line=line.strip()
    if line.startswith('#') or not line: continue
    parts=line.split()
    if len(parts)>=2:
        acc[int(parts[0],16)]=int(parts[1],16)

from pathlib import Path
with open(Path(__file__).resolve().parents[1] / 'libapp.so','rb') as f: d=f.read()
def find_func_start(pc):
    for a in range(pc, max(0,pc-0x6000), -4):
        if d[a:a+4]==bytes.fromhex('fd79bfa9') and d[a+4:a+8]==bytes.fromhex('fd030faa'):
            return a
    return pc

# For target offsets, find all accessing PCs and their functions
def find_accessors(off):
    pcs=[p for p,o in acc.items() if o==off]
    funcs={}
    for p in pcs:
        fs=find_func_start(p)
        funcs.setdefault(fs,[]).append(p)
    return pcs, funcs

print("=== Daily feed: title 21707 (off 0x%x) + body 22466 (off 0x%x) ===" % (ref2off[21707], ref2off[22466]))
for ref in [21707, 22466]:
    off=ref2off[ref]
    pcs, funcs = find_accessors(off)
    print(f"\nref {ref} '{strings[ref][:25]}' off 0x{off:x}: {len(pcs)} accessors")
    for fs, plist in funcs.items():
        print(f"  func 0x{fs:x}: PCs {[hex(p) for p in plist]}")

# Find functions accessing BOTH 21707 and 22466
t_off=ref2off[21707]; b_off=ref2off[22466]
_, tf = find_accessors(t_off)
_, bf = find_accessors(b_off)
common = set(tf.keys()) & set(bf.keys())
print(f"\n*** Functions accessing BOTH daily-feed title+body: {[hex(f) for f in common]} ***")
for fs in common:
    print(f"  => daily-feed dialog orchestrator candidate: 0x{fs:x}")

# Also: fault title 29112 (0xe7e8) + body 27673 (0x13b70)
print("\n=== Fault: title 29112 (off 0x%x) + body 27673 (off 0x%x) ===" % (ref2off[29112], ref2off[27673]))
for ref in [29112, 27673]:
    off=ref2off[ref]
    _, funcs = find_accessors(off)
    print(f"ref {ref} off 0x{off:x}: funcs {[hex(f) for f in funcs]}")
_, tf2 = find_accessors(ref2off[29112])
_, bf2 = find_accessors(ref2off[27673])
common2 = set(tf2.keys()) & set(bf2.keys())
print(f"*** Functions accessing BOTH fault title+body: {[hex(f) for f in common2]} ***")
