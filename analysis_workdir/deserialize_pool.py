#!/usr/bin/env python3
"""
ppcat ObjectPool deserializer (Task A deliverable) — custom Dart 2.19 AOT, arm64.

Fully deserializes the single ObjectPool (51140 entries) from the isolate snapshot.
Verified against 4 hard anchors + function-access cross-check (see report).

Entry format (from Dart 2.19.6 source: object_pool_builder.h TypeBits/PatchableBit,
app_snapshot.cc ObjectPoolDeserializationCluster::ReadFill, datastream.h Read<T>):
  entry_bits = 1 raw byte: TypeBits = bits[0:6], PatchableBit = bit 7 (0x80)
  EntryType: 0=kTaggedObject,1=kImmediate,2=kNativeFunction,
             3=kSwitchableCallMissEntryPoint,4=kMegamorphicCallEntryPoint
  ReadUnsigned (used for kTaggedObject ref AND FillRefUnsigned=true):
    little-endian, 7 data bits/byte, byte>0x7f = terminator (contrib = byte-0x80)
  kImmediate value: Read<intptr_t> = same LEB128 byte layout (byte count identical)
  types 2/3/4: no extra payload (just the entry_bits byte)

Pool fill region: file 0x2e7043 (length=51140 ReadUnsigned, then 51140 entries).
slot_offset = slot_index * 8. vaddr == file offset.
"""
import sys, json

PATH = sys.argv[1] if len(sys.argv) > 1 else 'libapp.so'
FILL_START = 0x2e7043
LENGTH = 51140
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
        r |= b << s; s += 7

def deserialize():
    pos = FILL_START
    L, pos = read_unsigned(pos)
    assert L == LENGTH, f"length {L} != {LENGTH}"
    out = []
    for idx in range(LENGTH):
        eb_off = pos
        eb = data[pos]; pos += 1
        etype = eb & 0x7f
        val = None
        if etype == 0:        # kTaggedObject
            val, pos = read_unsigned(pos)
        elif etype == 1:      # kImmediate
            val, pos = read_unsigned(pos)
        elif etype in (2, 3, 4):  # kNativeFunction / SwitchableCallMiss / Megamorphic: no payload
            val = None
        else:
            raise ValueError(f"unknown entry type {etype} (bits=0x{eb:02x}) at idx {idx} off 0x{eb_off:x}")
        out.append({'idx': idx, 'type': etype, 'val': val, 'eb': eb, 'off': eb_off})
    return out, pos

if __name__ == '__main__':
    entries, endpos = deserialize()
    # anchors
    ANCHORS = {26842:0x15b1, 30947:0x15b2, 27673:0x276e, 30922:0x2e2d}
    print(f"# Pool deserialized: {len(entries)} entries, fill 0x{FILL_START:x}..0x{endpos:x}")
    ok=True
    for e in entries:
        if e['type']==0 and e['val'] in ANCHORS:
            exp=ANCHORS[e['val']]; s='OK' if e['idx']==exp else f'FAIL(exp 0x{exp:x})'
            if e['idx']!=exp: ok=False
            print(f"#   ref {e['val']:>6} -> slot 0x{e['idx']:x} (off 0x{e['idx']*8:x})  [{s}]")
    print(f"# 4-anchor verification: {'PASSED' if ok else 'FAILED'}")

    # emit ref -> (slot, offset) for all TaggedObject, and full json
    by_ref = {}
    for e in entries:
        if e['type']==0:
            by_ref[e['val']] = (e['idx'], e['idx']*8)
    json.dump({'entries':entries, 'by_ref':{str(k):list(v) for k,v in by_ref.items()},
               'fill_start':FILL_START,'length':LENGTH,'end':endpos},
              open('pool_deserialized.json','w'))
    print(f"# wrote pool_deserialized.json ({len(entries)} entries, {len(by_ref)} unique refs)")
