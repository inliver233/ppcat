#!/usr/bin/env python3
"""Task A: Full ObjectPool deserialization for ppcat (custom Dart 2.19 AOT).

Entry format (verified against Dart 2.19.6 source + empirical anchors):
  entry_bits = 1 raw byte. TypeBits = bits[0:6], PatchableBit = bit7 (0x80).
  EntryType enum: 0=kTaggedObject,1=kImmediate,2=kNativeFunction,
                  3=kSwitchableCallMissEntryPoint,4=kMegamorphicCallEntryPoint,
                  5=kImmediate64,6=kImmediate128
  Byte consumption:
    0 kTaggedObject: + ReadUnsigned(ref)        [FillRefUnsigned=true, verified]
    1 kImmediate:    + Read<intptr_t> (LEB128, same byte-count as ReadUnsigned)
    2 kNativeFunction: + 0
    3 kSwitchableCallMissEntryPoint: + 0
    4 kMegamorphicCallEntryPoint: + 0
    5/6: TBD if encountered
ReadUnsigned: little-endian, low-first, 7 bits/byte, byte>0x7f = terminator (val=byte-0x80).
"""
import sys

PATH = 'libapp.so'
ISO = 0x3330

with open(PATH, 'rb') as f:
    data = f.read()

def read_unsigned(pos):
    r = 0; s = 0
    while True:
        b = data[pos]; pos += 1
        if b > 0x7f:
            r |= (b - 0x80) << s
            return r, pos
        r |= b << s
        s += 7

# Entry type names
TNAMES = {0:'TagObj',1:'Imm',2:'NatFunc',3:'SwMiss',4:'Mega',5:'Imm64',6:'Imm128'}

def parse_pool(fill_start_file, length, verbose=False, stop_at=None):
    """Parse `length` entries starting after the length bytes at fill_start_file.
    Returns list of (slot_index, entry_type, ref_or_value, entry_bits, file_offset_of_entry_bits)."""
    pos = fill_start_file
    # consume length
    L, pos = read_unsigned(pos)
    assert L == length, f"length mismatch: read {L} != expected {length}"
    entries = []
    idx = 0
    fail = None
    while idx < length:
        eb_off = pos
        if pos >= len(data):
            fail = f"EOF at idx {idx}"; break
        eb = data[pos]; pos += 1
        etype = eb & 0x7f
        patchable = (eb >> 7) & 1
        val = None
        if etype == 0:  # kTaggedObject
            val, pos = read_unsigned(pos)
        elif etype == 1:  # kImmediate
            val, pos = read_unsigned(pos)  # byte count same; sign handled by marker
        elif etype == 2:  # kNativeFunction
            val = None
        elif etype == 3:  # kSwitchableCallMissEntryPoint
            val = None
        elif etype == 4:  # kMegamorphicCallEntryPoint
            val = None
        elif etype == 5:  # kImmediate64 - guess: 8 raw bytes? or LEB128?
            fail = f"unhandled type 5 (Imm64) at idx {idx} off 0x{eb_off:x}"; break
        elif etype == 6:  # kImmediate128
            fail = f"unhandled type 6 (Imm128) at idx {idx} off 0x{eb_off:x}"; break
        else:
            fail = f"UNKNOWN type {etype} (bits=0x{eb:02x}) at idx {idx} off 0x{eb_off:x}"; break
        entries.append((idx, etype, val, eb, eb_off))
        idx += 1
        if stop_at and idx >= stop_at:
            break
    return entries, fail, pos

# Candidate fill starts (file offsets where 44 0f 83 = 51140 appears, followed by valid stream)
CANDIDATES = [0x2e7043]

ANCHOR_REFS = {26842, 30947, 29112, 27673, 30922, 21707, 22466}
SLOT_KNOWN = {26842:0x15b1, 30947:0x15b2, 27673:0x278d, 30922:0x2e2d}

for c in CANDIDATES:
    print(f"\n{'='*70}\nParsing pool from fill_start file 0x{c:x} (iso-rel 0x{c-ISO:x})\n{'='*70}")
    entries, fail, endpos = parse_pool(c, 51140)
    if fail:
        print(f"PARSE FAILED: {fail}")
        # show how far we got
        print(f"entries parsed before fail: {len(entries)}")
        if entries:
            last = entries[-1]
            print(f"last entry: idx={last[0]} type={TNAMES.get(last[1],last[1])} off=0x{last[4]:x}")
        continue
    print(f"SUCCESS: parsed {len(entries)} entries, end file 0x{endpos:x}")
    # Build index map for kTaggedObject entries
    by_idx = {e[0]: e for e in entries}
    # Verify anchors
    print("\n--- Anchor verification (ref -> slot index) ---")
    all_ok = True
    for ref, known_slot in SLOT_KNOWN.items():
        # find the entry whose val==ref
        found = [e for e in entries if e[1]==0 and e[2]==ref]
        if not found:
            print(f"  ref {ref}: NOT FOUND in pool"); all_ok=False; continue
        e = found[0]
        status = 'OK' if e[0]==known_slot else f'EXPECTED 0x{known_slot:x}'
        if e[0]!=known_slot: all_ok=False
        print(f"  ref {ref:>6}: slot_idx=0x{e[0]:x} (offset 0x{e[0]*8:x})  [{status}]  @file 0x{e[4]:x}")
    print(f"\n4-ANCHOR VERIFICATION: {'PASSED ✅' if all_ok else 'FAILED ❌'}")

    # Report the target refs (21707, 22466, 29112)
    print("\n--- Target refs (daily-feed / residual-fault) ---")
    for ref in [21707, 22466, 29112]:
        found = [e for e in entries if e[1]==0 and e[2]==ref]
        if found:
            e = found[0]
            print(f"  ref {ref:>6}: slot_idx=0x{e[0]:x} (offset 0x{e[0]*8:x})  @file 0x{e[4]:x}")
        else:
            print(f"  ref {ref:>6}: NOT FOUND")
    # entry type histogram
    from collections import Counter
    hc = Counter(e[1] for e in entries)
    print("\n--- Entry type histogram ---")
    for t in sorted(hc):
        print(f"  {TNAMES.get(t,t):8s}: {hc[t]}")
