#!/usr/bin/env python3
"""Fast byte-pattern scanner: find all .text sites that load a given ObjectPool slot.
Dart AOT arm64, PP=X27. vaddr==file offset. Pure word decode (no capstone) -> robust+fast.

Encodings (32-bit little-endian words):
  LDR  (64bit,uns imm): (w>>22)==0x3E5 ; Rn=(w>>5)&0x1F ; imm12=(w>>10)&0xFFF ; off=imm12*8
  LDP  (64bit,signed/uns): (w>>22)==0x2A5 (post/pre uns) variants; base off=imm7*8
  ADD imm (64bit): (w>>24)&0x1F in {0x91(sh0),0x91..}; sh at bit22; imm12=(w>>10)&0xFFF
    add xM,x27,#hi,lsl12: (w & 0xFFC003E0)==0x91400360 ; hi=imm12 ; M=Rd
Strategy: find `add xM,x27,#hi,lsl12`; look at next 1-2 words for a load/add with base M;
  compute hi*4096 + lo and compare to target slot_off.
Also direct `ldr/ldp x_,[x27,#off]`.
"""
import sys, json, struct
PATH='/root/ppcat_repo/libapp.so'
with open(PATH,'rb') as f: DATA=f.read()
TS=0x460000
PROLOGUE=bytes.fromhex('fd79bfa9fd030faa')
XREF=json.load(open('/root/ppcat_repo/analysis_workdir/xref_db.json'))

# precompute function start table (all prologue positions) for func_of
FUNCS=[]
a=TS
while a < len(DATA)-8:
    if DATA[a:a+8]==PROLOGUE:
        FUNCS.append(a)
    a+=4
import bisect
def func_of(addr):
    i=bisect.bisect_right(FUNCS,addr)-1
    return FUNCS[i] if i>=0 else None

NWORDS=(len(DATA)-TS)//4

def decode_load_base_off(w):
    # returns (base_reg, offset, is_loadpair) or None
    op22=w>>22
    if op22==0x3E5:  # LDR 64 uns imm
        Rn=(w>>5)&0x1F; imm12=(w>>10)&0xFFF; return (Rn, imm12*8, False)
    if op22 in (0x2A5,0x2A6,0x2A7,0x6A5,0x6A6,0x6A7):  # LDP 64 (various pre/post/offset)
        # signed offset imm7*8
        imm7=(w>>15)&0x7F; off=(imm7-128 if imm7&0x40 else imm7)*8
        Rn=(w>>5)&0x1F; return (Rn, off, True)
    return None

def is_add_pp_lsl12(w):
    # add xM, x27, #hi, lsl#12
    if (w & 0xFFC003E0)==0x91400360:
        return (w&0x1F, ((w>>10)&0xFFF)<<12)  # (Rd, hi<<12)
    return None

def is_add_imm(w):
    # add xR, xM, #lo  (64bit, sh0): (w>>24)==0x91 and sh bit22==0
    if (w>>24)==0x91 and ((w>>22)&0x3)==0:
        Rd=w&0x1F; Rn=(w>>5)&0x1F; imm12=(w>>10)&0xFFF
        return (Rd, Rn, imm12)
    return None

def scan_slot(slot_off):
    hits=[]
    base=TS
    for i in range(NWORDS):
        w=struct.unpack_from('<I', DATA, base+i*4)[0]
        a=base+i*4
        # direct ldr/ldp [x27,#off]
        if i==0 or True:
            ld=decode_load_base_off(w)
            if ld and ld[0]==27:
                if ld[1]==slot_off:
                    hits.append((a,'direct',w))
        # add xM,x27,#hi,lsl12 then lookahead
        ap=is_add_pp_lsl12(w)
        if ap:
            M, hi = ap
            # look at next 1-2 words
            for k in (1,2):
                if i+k>=NWORDS: break
                w2=struct.unpack_from('<I', DATA, base+(i+k)*4)[0]
                ld2=decode_load_base_off(w2)
                if ld2 and ld2[0]==M:
                    if hi+ld2[1]==slot_off:
                        hits.append((base+(i+k)*4,'pair',w2))
                    break
                ai=is_add_imm(w2)
                if ai and ai[1]==M:  # add xR,xM,#lo -> then next word load
                    lo=ai[2]
                    if i+k+1<NWORDS:
                        w3=struct.unpack_from('<I', DATA, base+(i+k+1)*4)[0]
                        ld3=decode_load_base_off(w3)
                        if ld3 and ld3[0]==ai[0] and hi+lo+ld3[1]==slot_off:
                            hits.append((base+(i+k+1)*4,'addpair',w3))
                    break
    return hits

if __name__=='__main__':
    slot=int(sys.argv[1],0)
    slot_off=slot*8
    print(f'# slot 0x{slot:x} off 0x{slot_off:x}  ({len(FUNCS)} funcs indexed)')
    hits=scan_slot(slot_off)
    print(f'# {len(hits)} load sites')
    fmap={}
    for a,kind,w in hits:
        f=func_of(a); fmap.setdefault(f,[]).append((a,kind))
    for f in sorted(fmap, key=lambda x:(x is None,x)):
        info=XREF.get(str(f)) if f else None
        ss=info.get('strs',[])[:3] if info else []
        nc=len(info.get('callers',[])) if info else '?'
        print(f'\n== func 0x{f:x}  callers={nc} strs={[s[:28] for s in ss]} bool={info.get("bool_ret") if info else "?"} ==')
        for a,kind in fmap[f]:
            print(f'   0x{a:x} [{kind}]')
