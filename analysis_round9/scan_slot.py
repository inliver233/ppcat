#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# scan_slot: find which functions LDR a given pool slot, by raw byte pattern.
# Calibrate against known fault-body loader (ref27673 @ 0x921080) first.
import json, struct
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN

BASE = r"E:/皮皮喵4/work/analysis/test3data"
ORIG = r"E:/皮皮喵4/work/libapp_orig.so"
data = open(ORIG, "rb").read()
pool = json.load(open(BASE + "/pool_deserialized.json", encoding="utf-8"))
xref = json.load(open(BASE + "/xref_db.json", encoding="utf-8"))
by_ref = pool["by_ref"]

md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)

# Build function range table from xref_db: sorted list of (start, end)
franges = []
for a_str, x in xref.items():
    a = int(a_str); e = x.get("end", a + 4)
    franges.append((a, e))
franges.sort()

def func_of(addr):
    # linear-ish; franges sorted. find function whose [start,end) contains addr.
    import bisect
    starts = [f[0] for f in franges]
    i = bisect.bisect_right(starts, addr) - 1
    if i >= 0 and franges[i][0] <= addr < franges[i][1]:
        return franges[i][0]
    return None

def slot_idx_of(ref):
    r = by_ref.get(str(ref))
    return r[0] if r else None

def decode_add_x27_page(ins):
    # ADD xR, x27, #imm12, lsl #12  -> returns (Rd, page_imm12) or None
    if ins.mnemonic == "add" and len(ins.operands) == 3:
        # operands: Rd, Rn(x27), imm shifted lsl 12
        ops = ins.operands
        if ops[1].type == 1 and ops[1].reg == 31:  # x27 = reg 31 in capstone arm64? Actually x27
            pass
    # Use raw: add imm with shift. Easier: match instruction word.
    w = ins.address
    return None

def scan_slot_loaders(ref, header=0):
    """Find all (ldr_addr, func) that load pool slot for ref, assuming slot_offset = idx*8 + header.
       Pattern: ADD xR, x27, #PAGE, lsl#12 ; LDR xD, [xR, #OFF].  (PAGE=slotoff>>12, OFF=(slotoff&0xfff)/8)
       Also single LDR xD,[x27,#OFF] when PAGE==0.
    """
    idx = slot_idx_of(ref)
    if idx is None:
        return [], None
    slotoff = idx * 8 + header
    page = slotoff >> 12
    off = (slotoff & 0xFFF) >> 3   # LDR imm12 (units of 8)
    print("  ref %d: slot idx=0x%x(%d) slotoff=0x%x(header=%d) page=0x%x LDR_off=0x%x" % (ref, idx, idx, slotoff, header, page, off))
    hits = []
    # Scan .text from 0x460000 for ADD xR,x27,#page,lsl12  (word: 0x91... with x27 as Rn)
    # ADD imm64 shifted: 0x91000000 base | sh=1(bit22) | imm12<<10 | Rn<<5 | Rd
    # We want Rn=27, imm12=page, shift(lsl12) -> bit22 set.
    TEXT = 0x460000
    end = len(data)
    a = TEXT
    found_addrs = []
    while a + 8 <= end:
        w1 = struct.unpack_from("<I", data, a)[0]
        # ADD (imm): bits 30:23 = 0010001 -> 0x91 in bits 31:23. opcode 0x91000000.
        if (w1 & 0xFF800000) == 0x91000000:  # ADD imm
            sh = (w1 >> 22) & 1   # shift bit
            imm12 = (w1 >> 10) & 0xFFF
            Rn = (w1 >> 5) & 0x1F
            Rd = w1 & 0x1F
            if Rn == 27 and sh == 1 and imm12 == page:
                # found ADD xRd,x27,#page,lsl12 ; look ahead for LDR xD,[xRd,#off]
                for k in range(1, 6):
                    if a + 4*k + 4 > end: break
                    w2 = struct.unpack_from("<I", data, a + 4*k)[0]
                    if (w2 & 0xFFC00000) == 0xF9400000:  # LDR (imm, 64bit): 0xF940xxxx
                        imm12b = (w2 >> 10) & 0xFFF
                        Rn2 = (w2 >> 5) & 0x1F
                        Rd2 = w2 & 0x1F
                        if Rn2 == Rd and imm12b == off:
                            ldr_addr = a + 4*k
                            f = func_of(ldr_addr)
                            hits.append((ldr_addr, f, "ADD+LDR"))
                            break
        a += 4
    # also: single LDR xD,[x27,#off] when page==0 (Rn=27 directly)
    if page == 0:
        a = TEXT
        while a + 4 <= end:
            w = struct.unpack_from("<I", data, a)[0]
            if (w & 0xFFC00000) == 0xF9400000:
                imm12b = (w >> 10) & 0xFFF
                Rn = (w >> 5) & 0x1F
                if Rn == 27 and imm12b == off:
                    f = func_of(a)
                    hits.append((a, f, "LDR-direct"))
            a += 4
    return hits, (idx, slotoff, page, off)

print("=" * 70)
print("CALIBRATION: ref27673 (fault body string) should load at/near 0x921080")
print("=" * 70)
for h in (0, 8, 16, 24, 32, 0x10, -8):
    hits, info = scan_slot_loaders(27673, header=h)
    addrs = [hex(x[0]) for x in hits]
    print("header=%d -> hits: %s" % (h, addrs))
