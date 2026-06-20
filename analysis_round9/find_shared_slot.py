#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Cross-reference: pool slots loaded by cat-module functions that are ALSO loaded
# by reader-region functions => shared const widget = cat block, reader loader = builder.
import json, struct, bisect, re
BASE = r"E:/皮皮喵4/work/analysis/test3data"
ORIG = r"E:/皮皮喵4/work/libapp_orig.so"
data = open(ORIG, "rb").read()
pool = json.load(open(BASE + "/pool_deserialized.json", encoding="utf-8"))
xref = json.load(open(BASE + "/xref_db.json", encoding="utf-8"))
by_ref = pool["by_ref"]; entries = pool["entries"]
ref2str={}
for line in open(BASE+"/unflutter_strings.txt",encoding="utf-8"):
    m=re.search(r'\[ref=(\d+)\]\s*\(\d+b\)\s*"(.*)"$',line)
    if m: ref2str[int(m.group(1))]=m.group(2)
franges = sorted((int(a), x.get("end", int(a)+4)) for a,x in xref.items())
starts=[f[0] for f in franges]
def func_of(addr):
    i=bisect.bisect_right(starts,addr)-1
    return franges[i][0] if i>=0 and franges[i][0]<=addr<franges[i][1] else None

def slots_loaded_by(fstart, fend):
    """Return dict slot_idx -> list of ldr addrs within [fstart,fend)."""
    a=fstart; reg_page={}; out={}
    while a+4<=fend:
        w=struct.unpack_from("<I",data,a)[0]
        if (w&0xFF800000)==0x91000000:
            sh=(w>>22)&1; imm12=(w>>10)&0xFFF; Rn=(w>>5)&0x1F; Rd=w&0x1F
            if Rn==27 and sh==1: reg_page[Rd]=imm12<<12
        if (w&0xFFC00000)==0xF9400000:
            imm12b=(w>>10)&0xFFF; Rn=(w>>5)&0x1F
            if Rn in reg_page:
                slotoff=reg_page[Rn]+(imm12b<<3); idx=slotoff>>3
                out.setdefault(idx,[]).append(a)
            elif Rn==27:
                slotoff=imm12b<<3; idx=slotoff>>3
                out.setdefault(idx,[]).append(a)
        a+=4
    return out

def scan_slot_global(idx):
    """All loaders of slot idx across whole libapp -> [(ldr_addr, func)]."""
    slotoff=idx*8; page=slotoff>>12; off=(slotoff&0xFFF)>>3
    hits=[]; a=0x460000; end=len(data)
    while a+8<=end:
        w1=struct.unpack_from("<I",data,a)[0]
        if (w1&0xFF800000)==0x91000000:
            sh=(w1>>22)&1; imm12=(w1>>10)&0xFFF; Rn=(w1>>5)&0x1F; Rd=w1&0x1F
            if Rn==27 and sh==1 and imm12==page:
                for k in range(1,6):
                    if a+4*k+4>end: break
                    w2=struct.unpack_from("<I",data,a+4*k)[0]
                    if (w2&0xFFC00000)==0xF9400000:
                        i2=(w2>>10)&0xFFF; Rn2=(w2>>5)&0x1F
                        if Rn2==Rd and i2==off:
                            hits.append((a+4*k, func_of(a+4*k))); break
        a+=4
    return hits

cat_funcs = {
    0xae30e0:"cat menu", 0xa54178:"cat page build", 0xbc5dc8:"reward prompt",
    0xa56be4:"feed toast", 0xb68234:"daily-feed-fail", 0xb68308:"daily-feed helper",
    0xa570c0:"ad-fail narrow",
}
print("=== pool slots loaded by cat-module functions ===")
cat_slots = {}   # slot_idx -> set of cat funcs loading it
for cf, name in cat_funcs.items():
    fend = xref.get(str(cf),{}).get("end", cf+0x400)
    slots = slots_loaded_by(cf, fend)
    # keep only type-0 (object/const-widget) slots
    for idx in slots:
        if idx < len(entries) and entries[idx]["type"]==0:
            cat_slots.setdefault(idx, set()).add(cf)

print("cat-module loads %d distinct type-0 (object) slots" % len(cat_slots))

# config/util string refs to exclude (general getters, not widgets)
CONFIG_REFS = set()
for s in ("是否收费","forceVersion","fontSize","webBgColor","useWebView","upperLimit",
          "QMb","gXc","iXc","fVb","ruleSearchInit","adNum","bookSourceGroup","ruleFindList",
          "ruleBookUrlPattern","writeBytes","author","isDaily","upperLimit","alter"):
    for r in ref2str:
        if ref2str[r]==s: CONFIG_REFS.add(r)

def fsummary(f):
    x = xref.get(str(f),{})
    sz = x.get("end",f+4)-f
    return "0x%x(sz=%d,str=%d,call=%d)"%(f,sz,len(x.get("strings",{})),len(x.get("callees",[])))

print("\n=== REFINED: slots loaded by ref28525-loaders(0xae30e0/0xa54178), FEW loaders, specific ===")
found=0
for idx in sorted(cat_slots):
    cats_loading = cat_slots[idx]
    # only slots loaded by 0xae30e0 or 0xa54178 (the ref28525 loaders)
    if not (0xae30e0 in cats_loading or 0xa54178 in cats_loading): continue
    ref = entries[idx]["val"]
    if ref in CONFIG_REFS: continue
    loaders = scan_slot_global(idx)
    funcs = sorted(set(h[1] for h in loaders if h[1] is not None))
    if len(funcs) > 5: continue   # too many loaders = general utility, skip
    if len(funcs) < 2: continue   # only cat, not shared
    s = ref2str.get(ref, "<<obj%d>>"%ref)
    print("slot 0x%x ref=%d %r  (%d loaders)"%(idx,ref,s[:34],len(funcs)))
    for f in funcs:
        mark = " <CAT>" if f in cat_funcs else (" <reader>" if 0xb50000<=f<0xbd0000 else "")
        print("     %s%s"%(fsummary(f),mark))
    found+=1
print("total refined candidates:",found)

