#!/usr/bin/env python3
"""
Dart ObjectPool entry parser for ppcat custom VM (Dart 2.19, arm64, compressed-pointers).
Parses pool entries using the confirmed format: entry_byte = RAW uint8, type = eb & 3.

Entry types:
  eb & 3 == 0: kTaggedObject (VLE ref follows)
  eb & 3 == 1: kImmediate (payload follows; 4 or 8 bytes depending on bit7)
  eb & 3 >= 2: Native (zero payload)

VLE encoding: unsigned, LSB-first, high bit (0x80) marks last byte.

Verified anchors:
  ref=26842 → slot 5553 (0x15b1), tag@0x2eb53c
  ref=30947 → slot 5554 (0x15b2), tag@0x2eb540
  ref=27673 → slot 10125 (0x278d), tag@0x2eeeca
  ref=30922 → slot 11821 (0x2e2d), tag@0x2f0415
"""

import struct
import sys

def read_vle_unsigned(data, pos):
    """Read unsigned VLE value at pos. Returns (value, new_position)."""
    result = 0
    shift = 0
    while pos < len(data):
        b = data[pos]
        pos += 1
        result |= (b & 0x7f) << shift
        if b & 0x80:
            break
        shift += 7
    return result, pos

def parse_pool_entry(data, pos):
    """Parse one pool entry. Returns (new_pos, entry_type, value) or None."""
    if pos >= len(data):
        return None
    eb = data[pos]
    etype = eb & 3
    
    if etype == 0:  # kTaggedObject
        ref, new_pos = read_vle_unsigned(data, pos + 1)
        return (new_pos, 'TAG', ref)
    elif etype == 1:  # kImmediate
        if eb & 0x80:  # bit7=1 → 8-byte immediate
            val = struct.unpack_from('<q', data, pos + 1)[0]
            return (pos + 9, 'IMM', val)
        else:  # bit7=0 → 4-byte immediate (compressed)
            val = struct.unpack_from('<i', data, pos + 1)[0]
            return (pos + 5, 'IMM', val)
    else:  # Native (type 2 or 3)
        return (pos + 1, 'NAT', eb)

def parse_pool_entries(data, start_pos, count=None):
    """Parse pool entries from start_pos. If count is None, parse until data runs out."""
    pos = start_pos
    entries = []
    idx = 0
    while pos < len(data):
        result = parse_pool_entry(data, pos)
        if result is None:
            break
        pos, etype, val = result
        entries.append((idx, etype, val, pos))
        idx += 1
        if count and idx >= count:
            break
    return entries

# When run as standalone, find and verify pool entries near anchors
if __name__ == '__main__':
    libapp_path = sys.argv[1] if len(sys.argv) > 1 else 'libapp.so'
    with open(libapp_path, 'rb') as f:
        data = f.read()
    
    # Verify known anchors
    anchors = [
        (26842, 0x2eb53c, 5553),
        (30947, 0x2eb540, 5554),
        (27673, 0x2eeeca, 10125),
        (30922, 0x2f0415, 11821),
        (21707, 0x2f8c81, None),
        (22466, 0x305c5a, None),
        (29112, 0x2ece05, None),
    ]
    
    print("=== Anchor verification ===")
    for ref, tag_off, expected_slot in anchors:
        eb = data[tag_off]
        etype = eb & 3
        ref_read, _ = read_vle_unsigned(data, tag_off + 1)
        status = "✓" if ref_read == ref else f"MISMATCH(got {ref_read})"
        slot_str = f"slot={expected_slot}" if expected_slot else "slot=?"
        print(f"  ref={ref:6d} @ 0x{tag_off:x}: eb=0x{eb:02x} type={etype} {ref_read=} {slot_str} {status}")
    
    # Parse between known anchors to count entries
    print("\n=== Entry counts between anchors ===")
    pairs = [
        (0x2eb540, 0x2eeeca, 4571, "30947→27673"),
        (0x2eeeca, 0x2f0415, 1696, "27673→30922"),
    ]
    for start, end, expected, label in pairs:
        pos = start
        count = 0
        while pos < end:
            result = parse_pool_entry(data, pos)
            if result is None:
                break
            pos, _, _ = result
            count += 1
        err = count - expected
        print(f"  {label}: {count} entries, expected {expected}, error={err:+d} ({100*err/expected:.1f}%)")
