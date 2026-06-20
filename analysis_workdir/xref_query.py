#!/usr/bin/env python3
"""Shared query tool for xref_db.json (test3). Usable by test1/test2 without writing code.

Usage:
  python3 xref_query.py string <substring>        # funcs accessing a string
  python3 xref_query.py func 0xADDR               # a function's callers/callees/strings
  python3 xref_query.py bool <substring>          # bool-returning gates accessing a string
  python3 xref_query.py callers 0xADDR            # who calls a function
  python3 xref_query.py callees 0xADDR            # what a function calls
  python3 xref_query.py anchor <ref>              # ref -> slot/offset (uses pool_deserialized.json)
"""
import json, sys, os
HERE=os.path.dirname(os.path.abspath(__file__))
db=json.load(open(os.path.join(HERE,'xref_db.json')))
db={int(k):v for k,v in db.items()}
pool=json.load(open(os.path.join(HERE,'pool_deserialized.json')))
ref2off={int(k):v[1] for k,v in pool['by_ref'].items()}

def f_strings(f): return db.get(f,{}).get('strings',{})

cmd = sys.argv[1] if len(sys.argv)>1 else 'help'
arg = sys.argv[2] if len(sys.argv)>2 else ''

if cmd=='string':
    print(f"functions accessing '{arg}':")
    for f in sorted(db):
        for s in db[f]['strings']:
            if arg in s:
                print(f"  0x{f:x} (callers={len(db[f]['callers'])}, bool={int(db[f]['bool_ret'])}): {s!r}")
elif cmd=='func' or cmd=='callers' or cmd=='callees':
    a=int(arg,16)
    v=db.get(a)
    if not v: print('not a known function'); sys.exit()
    if cmd in('func','callers'):
        print(f'0x{a:x} CALLERS ({len(v["callers"])}):')
        for c in v['callers']: print(f'  0x{c:x}')
    if cmd in('func','callees'):
        print(f'0x{a:x} CALLEES ({len(v["callees"])}):')
        for c in v['callees']: print(f'  0x{c:x}', '<-- bool' if db.get(c,{}).get('bool_ret') else '')
    if cmd=='func':
        print(f'0x{a:x} bool_ret={v["bool_ret"]} strings:')
        for s,c in sorted(v['strings'].items(),key=lambda x:-x[1])[:20]: print(f'  {c}x {s!r}')
elif cmd=='bool':
    print(f"bool-returning gates accessing '{arg}':")
    for f in sorted(db):
        v=db[f]
        if not v['bool_ret']: continue
        hit=[s for s in v['strings'] if arg in s]
        if hit: print(f"  0x{f:x} (callers={len(v['callers'])}): {[s[:24] for s in hit[:5]]}")
elif cmd=='anchor':
    r=int(arg)
    off=ref2off.get(r)
    print(f'ref {r} -> slot 0x{off//8:x} offset 0x{off:x}' if off else f'ref {r} not in pool')
else:
    print(__doc__)
