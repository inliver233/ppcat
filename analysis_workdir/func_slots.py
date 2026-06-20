import sys, json
fn=int(sys.argv[1],16)
# get next func start to bound range
DATA=open('/root/ppcat_repo/libapp.so','rb').read()
TS=0x460000; PROL=bytes.fromhex('fd79bfa9fd030faa')
FUNCS=[]; a=TS
while a<len(DATA)-8:
    if DATA[a:a+8]==PROL: FUNCS.append(a)
    a+=4
import bisect
i=bisect.bisect_right(FUNCS,fn)
end=FUNCS[i] if i<len(FUNCS) else len(DATA)
P=json.load(open('pool_deserialized.json'))
ENT={e['idx']:e for e in P['entries']}
slots={}
with open('/root/ppcat_repo/pool_accesses.txt') as f:
    for line in f:
        if not line.startswith('0x'): continue
        parts=line.split()
        pc=int(parts[0],16); off=int(parts[1],16)
        if fn<=pc<end:
            slots.setdefault(off//8,[]).append(pc)
print(f'# func 0x{fn:x} range [0x{fn:x},0x{end:x}) loads {len(slots)} unique slots:')
for s in sorted(slots):
    e=ENT.get(s)
    val=f'ref{e["val"]}' if e and e.get("val") is not None else f't{e["type"]}' if e else '?'
    print(f'  slot 0x{s:<5x} {val}  @0x{slots[s][0]:x}')
