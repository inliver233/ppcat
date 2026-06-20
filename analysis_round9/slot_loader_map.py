#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Single pass over .text: build slot -> set(loaders). Find slots loaded by exactly ONE
# reader-region function (reader-unique widgets). The cat block const widget is one.
import json, struct, bisect, re
BASE = r"E:/皮皮喵4/work/analysis/test3data"
ORIG = r"E:/皮皮喵4/work/libapp_orig.so"
data = open(ORIG, "rb").read()
pool = json.load(open(BASE + "/pool_deserialized.json", encoding="utf-8"))
xref = json.load(open(BASE + "/xref_db.json", encoding="utf-8"))
entries = pool["entries"]
ref2str={}
for line in open(BASE+"/unflutter_strings.txt",encoding="utf-8"):
    m=re.search(r'\[ref=(\d+)\]\s*\(\d+b\)\s*"(.*)"$',line)
    if m: ref2str[int(m.group(1))]=m.group(2)
franges = sorted((int(a), x.get("end", int(a)+4)) for a,x in xref.items())
starts=[f[0] for f in franges]
def func_of(addr):
    i=bisect.bisect_right(starts,addr)-1
    return franges[i][0] if i>=0 and franges[i][0]<=addr<franges[i][1] else None

# single pass: record (slot_idx, func) for every ADD+LDR pool load
slot2funcs = {}   # slot_idx -> set(func)
a = 0x460000; end=len(data)
reg_page={}  # reg -> page (from most recent ADD xR,x27,#page,lsl12)
while a+8<=end:
    w=struct.unpack_from("<I",data,a)[0]
    if (w&0xFF800000)==0x91000000:
        sh=(w>>22)&1; imm12=(w>>10)&0xFFF; Rn=(w>>5)&0x1F; Rd=w&0x1F
        if Rn==27 and sh==1: reg_page[Rd]=imm12<<12
    elif (w&0xFFC00000)==0xF9400000:
        imm12b=(w>>10)&0xFFF; Rn=(w>>5)&0x1F
        base = reg_page.get(Rn) if Rn in reg_page else (0 if Rn==27 else None)
        if base is not None:
            slotoff=base+(imm12b<<3); idx=slotoff>>3
            f=func_of(a)
            if f is not None:
                slot2funcs.setdefault(idx,set()).add(f)
    a+=4

print("total slots with loaders:", len(slot2funcs))
# reader-region funcs
def is_reader(f): return 0xb50000<=f<0xbd0000
def fsummary(f):
    x=xref.get(str(f),{}); sz=x.get("end",f+4)-f
    return "0x%x(sz=%d,str=%d)"%(f,sz,len(x.get("strings",{})))

# slots loaded by EXACTLY ONE function, that function in reader region, slot is type-0 object
print("\n=== reader-unique type-0 object slots (1 loader, in reader region) ===")
cands=[]
for idx, funcs in slot2funcs.items():
    if len(funcs)!=1: continue
    f=next(iter(funcs))
    if not is_reader(f): continue
    if idx>=len(entries): continue
    if entries[idx]["type"]!=0: continue  # only object/widget slots
    ref=entries[idx]["val"]
    cands.append((f, idx, ref))
# group by loader function
from collections import defaultdict
by_func=defaultdict(list)
for f,idx,ref in cands: by_func[f].append((idx,ref))
print("reader funcs with unique object slots: %d"%len(by_func))
# show funcs that have a SMALL number of unique object slots (focused widget builders)
# and prefer medium-sized funcs
ranked=sorted(by_func.items(), key=lambda kv: len(kv[1]))
for f, slots in ranked[:50]:
    print("  %s : %d unique-obj-slots"%(fsummary(f),len(slots)))
