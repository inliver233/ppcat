#!/usr/bin/env python3
"""
Extract Dart object pool strings from libapp.so by direct parsing.
This works regardless of Dart version, by walking the IsolateSnapshotData
looking for OneByteString and TwoByteString objects.
"""
import struct
import sys
import re
from collections import defaultdict

def read_uleb128(data, pos):
    """Read unsigned LEB128, return (value, new_pos)."""
    result = 0
    shift = 0
    while True:
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7f) << shift
        if (byte & 0x80) == 0:
            break
        shift += 7
    return result, pos

def extract_strings(libapp_path):
    with open(libapp_path, 'rb') as f:
        data = f.read()
    
    print(f'File size: {len(data)}')
    
    # Known from libapp.so:
    # _kDartIsolateSnapshotData at vaddr 0x3330 (this is the data section)
    # The object pool is in this section
    # Strings in Dart are stored as objects with a header + length + UTF-8/UTF-16LE data
    
    # Simple approach: extract all UTF-8 printable strings (>=4 chars) and all UTF-16LE strings
    # Then categorize
    
    utf8_strings = {}  # offset -> string
    # Find ASCII strings >= 4 chars
    for m in re.finditer(rb'[\x20-\x7e]{4,}', data):
        utf8_strings[m.start()] = m.group().decode('ascii', errors='replace')
    
    print(f'Found {len(utf8_strings)} UTF-8 strings >= 4 chars')
    
    # Also extract UTF-16LE Chinese strings (filter to CJK range to reduce noise)
    utf16_strings = {}
    # Match sequences of >=2 chars in CJK range encoded as UTF-16LE
    cjk_pattern = re.compile(rb'(?:[\x00-\x7f][\x4e-\x9f]|[\xff-\xff][\xd8-\xd8]){2,}')
    # Actually simpler: look for sequences of 2-byte values where second byte is in CJK high range
    for m in re.finditer(rb'(?:[\x00-\xff][\x4e-\x9f]){2,}', data):
        try:
            s = m.group().decode('utf-16-le')
            if len(s) >= 2:
                utf16_strings[m.start()] = s
        except:
            pass
    
    print(f'Found {len(utf16_strings)} UTF-16LE strings >= 2 chars')
    
    return data, utf8_strings, utf16_strings

if __name__ == '__main__':
    data, utf8, utf16 = extract_strings(sys.argv[1])
    
    # Output file
    with open(sys.argv[2], 'w', encoding='utf-8') as out:
        out.write(f'# Object pool strings extracted from {sys.argv[1]}\n')
        out.write(f'# Total UTF-8 strings: {len(utf8)}, UTF-16LE strings: {len(utf16)}\n\n')
        
        # Search for key strings
        out.write('## Key strings (UTF-16LE) - related to startup dialog\n\n')
        key_chinese = ['应用已被非法篡改', '非法篡改', '第三方虚拟环境', '环境异常', '禁用某些模块', '特权', '捐赠', '会员']
        for kw in key_chinese:
            enc = kw.encode('utf-16-le')
            idx = data.find(enc)
            if idx != -1:
                # Read context: get the full string this is part of
                # The string in Dart has a length prefix; we just print the keyword with offset
                out.write(f'  - offset {hex(idx)}: {kw!r}\n')
        
        out.write('\n## UTF-16LE strings (sorted by offset, deduplicated by content)\n\n')
        seen = set()
        for off in sorted(utf16.keys()):
            s = utf16[off]
            if s in seen: continue
            seen.add(s)
            # Skip pure ASCII ones (we already have them)
            if all(ord(c) < 128 for c in s): continue
            out.write(f'  {hex(off)}: {s!r}\n')
