#!/usr/bin/env python3
"""Proper Dart snapshot parser."""
import struct

class Stream:
    def __init__(self, data, pos=0):
        self.data = data; self.pos = pos
    
    def read_unsigned(self):
        b = self.data[self.pos]; self.pos += 1
        if b > 127:
            return b - 128
        r = 0; shift = 0
        while True:
            r |= b << shift; shift += 7
            b = self.data[self.pos]; self.pos += 1
            if b > 127:
                r |= (b - 128) << shift
                return r
    
    def read_tagged64(self):
        b = self.data[self.pos]; self.pos += 1
        if b > 127:
            return b - 192
        r = 0; shift = 0
        while True:
            r |= b << shift; shift += 7
            b = self.data[self.pos]; self.pos += 1
            if b > 127:
                r |= (b - 192) << shift
                return r
    
    def read_bytes(self, n):
        b = self.data[self.pos:self.pos+n]; self.pos += n
        return b

# Per unflutter cid.go (with our profile's TopLevelCid16=true, OldPoolFormat=true):
# CID 84 (String): AllocString → skipStringAlloc
# Most other clusters: AllocSimple (count + per-element fixed refs)
# 
# I need to handle each cluster's alloc format.
# For now, let me just parse the FIRST cluster (String, cid=84) fully,
# which includes its alloc AND fill data. Then I can identify string refs.

CID_STRING = 84

def parse_full(data, cluster_start):
    s = Stream(data, cluster_start)
    nbo = s.read_unsigned()
    no = s.read_unsigned()
    nc = s.read_unsigned()
    itl = s.read_unsigned()
    itdo = s.read_unsigned()
    print(f'Header: nbo={nbo} no={no} nc={nc} itl={itl} itdo={itdo}')
    print(f'Header end pos: {s.pos:#x}')
    
    # First cluster: String (cid=84, canonical=1, count=32135)
    cid_val = s.read_tagged64()
    cid = (cid_val >> 1) & 0xffffffff
    canonical = cid_val & 1
    count = s.read_unsigned()
    print(f'\nFirst cluster: cid={cid} canonical={canonical} count={count}')
    print(f'After tag+count pos: {s.pos:#x}')
    
    if cid != CID_STRING:
        print(f'ERROR: First cluster is not String!')
        return None
    
    # String cluster alloc: count + per-string encoded length (length<<1|isTwoByte)
    # Wait - skipStringAlloc reads count AGAIN, then per-string encoded.
    # So count is read TWICE: once in ScanClusters (as cluster count), 
    # and once in skipStringAlloc (as alloc count).
    # These should be the same value.
    # 
    # Looking at unflutter code more carefully:
    # In ScanClusters, count comes from skipAllocV (which calls skipStringAlloc)
    # So count is NOT read separately in ScanClusters.
    # 
    # Let me re-check.

    # Actually re-reading: ScanClusters reads cidAndCanonical, then calls skipAllocV.
    # skipAllocV for String calls skipStringAlloc, which reads count.
    # 
    # So the format is:
    #   cidAndCanonical
    #   count (from skipStringAlloc)
    #   per-string encoded length
    #   canonical set data
    # 
    # NOT: cidAndCanonical, count, per-string encoded length
    # 
    # I read cidAndCanonical, then count. That count IS the skipStringAlloc count.
    # 
    # So after my count, there are count encoded length values, then canonical set.
    
    # Read per-string encoded length to skip alloc section
    encoded_lengths = []
    for i in range(count):
        encoded = s.read_unsigned()
        length = encoded >> 1
        is_two_byte = encoded & 1
        encoded_lengths.append((length, is_two_byte))
    
    print(f'After per-string encoded lengths: {s.pos:#x}')
    print(f'First 5 lengths: {encoded_lengths[:5]}')
    
    # Canonical set (for canonical=1)
    # skipCanonicalSet(s, count, true):
    #   reads count + 1 (or similar) for canonical set data
    # Per unflutter source: canonical set format depends on version
    # For now, let me try to find where fill section begins by checking string data
    # 
    # Actually, let me find fill section by searching for the first string's data.
    # The first string per unflutter_strings.txt is "useShouldInterceptRequest" at ref=1007.
    # ref=1 should be a different string. ref=1007 has length 25 (1 byte per char = ASCII).
    # Looking at first 5 lengths:
    
    # Find ref=1007 (index 1006 in cluster)
    if len(encoded_lengths) > 1006:
        l, tb = encoded_lengths[1006]
        print(f'\nref=1007 length={l} isTwoByte={tb}')
    
    # Find ref=6917 (short v1)
    if len(encoded_lengths) > 6916:
        l, tb = encoded_lengths[6916]
        print(f'ref=6917 (short v1) length={l} isTwoByte={tb}')
        # Expected: "应用已被非法篡改！请重新下载正版！" = 18 chars * 2 = 36 bytes
    
    # Find ref=26842 (short v2)
    if len(encoded_lengths) > 26841:
        l, tb = encoded_lengths[26841]
        print(f'ref=26842 (short v2) length={l} isTwoByte={tb}')
        # Expected: "无法更改设置，应用已被非法篡改！请重新下载正版！" = 22 chars * 2 = 44 bytes
    
    # Find ref=30922 (long dialog)
    if len(encoded_lengths) > 30921:
        l, tb = encoded_lengths[30921]
        print(f'ref=30922 (long dialog) length={l} isTwoByte={tb}')
        # Expected: ~140 chars * 2 = 280 bytes
    
    # Find ref=30947 (title "非法篡改")
    if len(encoded_lengths) > 30946:
        l, tb = encoded_lengths[30946]
        print(f'ref=30947 (title) length={l} isTwoByte={tb}')
        # Expected: 4 chars * 2 = 8 bytes
    
    # Now I need to skip canonical set, then start fill section
    # The canonical set format for ≥2.17:
    #   ReadUnsigned(first_element)
    #   ReadUnsigned(bitset_size)
    #   ReadBytes(ceil(bitset_size / 8))
    # 
    # Let me skip canonical set
    print(f'\nReading canonical set at {s.pos:#x}...')
    first_element = s.read_unsigned()
    bitset_size = s.read_unsigned()
    print(f'  first_element={first_element} bitset_size={bitset_size}')
    bitset_bytes = (bitset_size + 7) // 8
    s.read_bytes(bitset_bytes)
    print(f'After canonical set: {s.pos:#x}')
    
    # Now fill section begins
    # Fill format for String (OldStringFormat=false):
    #   for each string: encoded = ReadUnsigned(); length = encoded >> 1; isTwoByte = encoded & 1; bytes
    # 
    # WAIT - that's the SAME as alloc! No, alloc just records lengths,
    # fill reads the actual data.
    # 
    # Actually looking at unflutter's fill.go:
    # case AllocString: readFillStrings()
    # readFillStrings reads encoded (length + isTwoByte flag) AGAIN, then bytes
    # 
    # So fill is: count iterations of {ReadUnsigned; ReadBytes(n)}
    
    print(f'\n=== FILL section starts at {s.pos:#x} ===')
    
    target_refs = {6917, 26842, 30922, 30947}
    target_strings = {}
    
    for i in range(count):
        ref = 1 + i
        encoded = s.read_unsigned()
        length = encoded >> 1
        is_two_byte = encoded & 1
        nbytes = length * (2 if is_two_byte else 1)
        bytes_data = s.read_bytes(nbytes)
        
        if ref in target_refs:
            if is_two_byte:
                value = bytes_data.decode('utf-16-le', errors='replace')
            else:
                value = bytes_data.decode('utf-8', errors='replace')
            target_strings[ref] = value
            disp = value[:80] + ('...' if len(value) > 80 else '')
            print(f'  ref={ref}: ({len(value)} chars, {nbytes} bytes, isTwoByte={is_two_byte}) {disp!r}')
        
        if i % 5000 == 0 and i > 0:
            print(f'  parsed {i}/{count}...')
    
    print(f'\nFinal pos: {s.pos:#x}')
    return target_strings

if __name__ == '__main__':
    with open('lib/arm64-v8a/libapp.so', 'rb') as f:
        data = f.read()
    
    ISO_START = 0x3330
    features_off = ISO_START + 0x34
    features_end = data.find(b'\x00', features_off)
    cluster_start = features_end + 1
    
    print('=== Isolate snapshot ===')
    targets = parse_full(data, cluster_start)
