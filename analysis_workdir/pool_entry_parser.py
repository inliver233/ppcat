#!/usr/bin/env python3
"""
Dart ObjectPool entry parser for ppcat custom VM (Dart 2.19, arm64, compressed-pointers).

CORRECTED FORMAT (cross-validated with test3 + Dart 2.19.6 source):
  entry_bits = 1 raw uint8_t byte
  TypeBits = eb & 0x7f (lower 7 bits = EntryType enum)
  PatchableBit = eb & 0x80 (bit 7)

  EntryType: 0=kTaggedObject, 1=kImmediate, 2=kNativeFunction,
             3=kSwitchableCallMissEntryPoint, 4=kMegamorphicCallEntryPoint

  kTaggedObject(0): VLE-encoded ref follows (ReadUnsigned)
  kImmediate(1): VLE-encoded value follows (ReadUnsigned, NOT fixed bytes!)
  types 2/3/4: no payload (just the entry_bits byte)

VLE (ReadUnsigned) encoding: LSB-first, 7 data bits/byte, byte > 0x7f = terminator
  Contribution of terminator byte = byte - 0x80

Pool fill: file offset 0x2e7043, length = 51140 entries (VLE-encoded at start)
slot_offset = slot_index * 8

Verified anchors (test3 + test2 confirmed):
  ref=26842 -> slot 5553 (0x15b1), tag@0x2eb53c
  ref=30947 -> slot 5554 (0x15b2), tag@0x2eb540
  ref=27673 -> slot 10094 (0x276e), tag@0x2eeeca
  ref=30922 -> slot 11821 (0x2e2d), tag@0x2f0415
"""

import struct, sys, json

def read_unsigned(data, pos):
    """Read unsigned VLE (ReadUnsigned from datastream.h). LSB-first, byte>0x7f terminates."""
    result = 0
    shift = 0
    while pos < len(data):
        b = data[pos]
        pos += 1
        if b > 0x7f:
            result |= (b - 0x80) << shift
            return result, pos
        result |= b << shift
        shift += 7
    return result, pos

def deserialize_pool(data, fill_start=0x2e7043, length=51140):
    """Deserialize entire ObjectPool."""
    pos = fill_start
    pool_len, pos = read_unsigned(data, pos)
    if pool_len != length:
        print(f"Warning: pool length {pool_len} != expected {length}")

    entries = []
    for idx in range(min(pool_len, length)):
        eb_off = pos
        eb = data[pos]
        pos += 1
        etype = eb & 0x7f  # TypeBits

        if etype == 0:      # kTaggedObject
            val, pos = read_unsigned(data, pos)
        elif etype == 1:    # kImmediate (also VLE!)
            val, pos = read_unsigned(data, pos)
        elif etype in (2, 3, 4):  # Native: no payload
            val = None
        else:
            raise ValueError(f"Unknown entry type {etype} (eb=0x{eb:02x}) at idx {idx} off 0x{eb_off:x}")

        entries.append({'idx': idx, 'type': etype, 'val': val, 'eb': eb, 'off': eb_off})

    return entries, pos

if __name__ == '__main__':
    libapp_path = sys.argv[1] if len(sys.argv) > 1 else 'libapp.so'
    with open(libapp_path, 'rb') as f:
        data = f.read()

    entries, end_pos = deserialize_pool(data)

    anchors = {26842: 0x15b1, 30947: 0x15b2, 27673: 0x276e, 30922: 0x2e2d}
    print(f"# Pool: {len(entries)} entries, 0x{0x2e7043:x}..0x{end_pos:x}")
    all_ok = True
    for e in entries:
        if e['type'] == 0 and e['val'] in anchors:
            exp = anchors[e['val']]
            s = 'OK' if e['idx'] == exp else f'FAIL(expected 0x{exp:x})'
            if e['idx'] != exp: all_ok = False
            print(f"#   ref {e['val']:6d} -> slot 0x{e['idx']:x} [{s}]")
    print(f"# 4-anchor: {'PASSED' if all_ok else 'FAILED'}")

    by_ref = {}
    for e in entries:
        if e['type'] == 0:
            by_ref[e['val']] = (e['idx'], e['idx'] * 8)
    print(f"# Unique refs: {len(by_ref)}")

    # Lookup mode
    for arg in sys.argv[2:]:
        try:
            ref = int(arg)
            if ref in by_ref:
                slot, off = by_ref[ref]
                print(f"# lookup ref={ref}: slot 0x{slot:x} offset 0x{off:x}")
            else:
                print(f"# lookup ref={ref}: NOT FOUND")
        except ValueError:
            pass
