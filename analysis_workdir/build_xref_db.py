#!/usr/bin/env python3
"""Master cross-ref DB (optimized). Bucket BL sites + pool accesses by function via bisect."""
import sys, json, struct, bisect
sys.path.insert(0,'analysis_workdir')
from taskA_deserialize import parse_pool, data
entries,_,_=parse_pool(0x2e7043,51140)
off2ref={e[0]*8:e[2] for e in entries if e[1]==0}
strings={}
for line in open('unflutter_strings.txt'):
    if '[ref=' in line:
        try:
            r=int(line.split('[ref=')[1].split(']')[0]); q=line.split('"',1)[1].rsplit('"',1)[0]; strings[r]=q
        except: pass
d=data; N=len(d); TEXT=0x460000
acc={}
for line in open('pool_accesses.txt'):
    line=line.strip()
    if line.startswith('#') or not line: continue
    p=line.split(); acc[int(p[0],16)]=int(p[1],16)

# function starts
funcs=[]
a=TEXT
while a<N-8:
    if d[a:a+4]==bytes.fromhex('fd79bfa9') and d[a+4:a+8]==bytes.fromhex('fd030faa'):
        funcs.append(a)
    a+=4
funcs.sort()
print('functions:', len(funcs))
def func_of(pc):
    i=bisect.bisect_right(funcs,pc)-1
    return funcs[i] if i>=0 else None

# BL sites bucketed by containing function
callees_by_func={f:set() for f in funcs}
bl_callers_of_target={}  # target -> list of caller funcs
for a in range(TEXT,N-4,4):
    inst=struct.unpack_from('<I',d,a)[0]
    if (inst&0xFC000000)==0x94000000:
        imm=inst&0x03FFFFFF; imm=imm-(1<<26) if imm&0x02000000 else imm
        tgt=a+imm*4
        cf=func_of(a)
        if cf is not None:
            callees_by_func[cf].add(tgt)
        bl_callers_of_target.setdefault(tgt,[]).append(cf)

# pool accesses bucketed by function
strs_by_func={f:{} for f in funcs}
for p,o in acc.items():
    cf=func_of(p)
    if cf is None: continue
    r=off2ref.get(o)
    if r is not None and r in strings:
        s=strings[r]
        strs_by_func[cf][s]=strs_by_func[cf].get(s,0)+1

# bool-return scan: find all 'add Xd,x22,#0x30' (true) PCs, bucket by func
bool_pcs=[]
for a in range(TEXT,N-4,4):
    inst=struct.unpack_from('<I',d,a)[0]
    if (inst&0xFF800000)==0x91000000:
        rn=(inst>>5)&0x1f; imm=(inst>>10)&0xfff
        if rn==22 and imm==0x30: bool_pcs.append(a)
bool_funcs=set(func_of(p) for p in bool_pcs)

# build db
db={}
for i,f in enumerate(funcs):
    fe=funcs[i+1] if i+1<len(funcs) else f+0x4000
    callers=sorted(set(c for c in bl_callers_of_target.get(f,[]) if c is not None))
    db[f]={'end':fe,'callees':sorted(callees_by_func[f]),
           'callers':callers,'strings':strs_by_func[f],
           'bool_ret': f in bool_funcs}
json.dump({str(k):v for k,v in db.items()}, open('xref_db.json','w'))
print('wrote xref_db.json | funcs:',len(db),'| bool_ret:',sum(1 for v in db.values() if v['bool_ret']))
print('BL sites:',sum(len(v) for v in bl_callers_of_target.values()))
