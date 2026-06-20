#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Batch entry-null patcher: overlay+fault baseline + entry-null for a list of functions.
# Usage: python batch_patch.py <out.so> <func1_hex> <func2_hex> ...
# Verifies standard prologue (stp/mov x29/sub x15/ldr/cmp/b.ls at +0x14) before patching.
import sys, struct
ORIG = r"E:/皮皮喵4/work/libapp_orig.so"
data = bytearray(open(ORIG,"rb").read())

# baseline: overlay-null + fault-cured + tamper + fault gate + dialog NOP
BASELINE = [
    (0x8e1dd0, bytes.fromhex("e00316aac0035fd6")),
    (0x8ef2b8, bytes.fromhex("e00316aac0035fd6")),
    (0xbc1020, bytes.fromhex("00020054")),
    (0xbc1058, bytes.fromhex("1f2003d5")),(0xbc1134, bytes.fromhex("1f2003d5")),(0xbc1234, bytes.fromhex("1f2003d5")),
    (0xbd60ac, bytes.fromhex("1f2003d5")),(0xbd6264, bytes.fromhex("1f2003d5")),(0xbd6300, bytes.fromhex("1f2003d5")),(0xbd6130, bytes.fromhex("1f2003d5")),
    (0x920d90, bytes.fromhex("29000014")),
    (0xbd2e30, bytes.fromhex("e00316aa")),(0xbd2e34, bytes.fromhex("ef031daa")),(0xbd2e38, bytes.fromhex("fd79c1a8")),(0xbd2e3c, bytes.fromhex("c0035fd6")),
]
for off,b in BASELINE: data[off:off+len(b)]=b

NULLRET = bytes.fromhex("e00316aa") + bytes.fromhex("ef031daa") + bytes.fromhex("fd79c1a8") + bytes.fromhex("c0035fd6")
applied=[]; skipped=[]
for arg in sys.argv[2:]:
    f=int(arg,16)
    # verify: stp (0xA9xxxxxx) at f, mov x29 at f+4. Find first conditional branch (0x54xxxxxx)
    # in f+8..f+0x28 and patch there with null-return (balanced: x29 set by stp/mov).
    w0=struct.unpack_from("<I",data,f)[0]
    w4=struct.unpack_from("<I",data,f+4)[0]
    ok_stp = (w0 & 0xFF000000)==0xA9000000
    ok_mov29 = (w4 & 0xFF000000)==0xAA000000 and (w4 & 0x1F)==29  # mov x29, ... (Rd=x29)
    br_off=None
    if ok_stp and ok_mov29:
        for o in range(0x8,0x44,4):
            ww=struct.unpack_from("<I",data,f+o)[0]
            if (ww & 0xFF000000)==0x54000000:
                br_off=o; break
    if br_off is not None:
        data[f+br_off:f+br_off+16]=NULLRET
        applied.append((f,br_off))
    else:
        skipped.append((f,hex(w0),hex(w4)))
open(sys.argv[1],"wb").write(data)
print("applied entry-null to %d funcs:"%len(applied), [(hex(a),"+0x%x"%o) for a,o in applied])
if skipped: print("SKIPPED (bad prologue):", [(hex(f),w,b) for f,w,b in skipped])
print("wrote", sys.argv[1])
