#!/usr/bin/env python3
"""
Dump Dart object pool strings from libapp.so.
Works regardless of Dart version - just scans for OneByteString and TwoByteString
patterns in the snapshot data.
"""
import struct
import sys
import re

def main(libapp_path, output_path):
    with open(libapp_path, 'rb') as f:
        data = f.read()
    
    print(f'File size: {len(data)} bytes')
    
    # Snapshot data range
    ISO_DATA_START = 0x3330
    ISO_DATA_END = 0x45fc60
    
    # For each "string-looking" sequence in the snapshot, record it
    # Strategy: find sequences of printable ASCII OR valid UTF-16LE
    
    # Find all UTF-8 strings (printable ASCII)
    utf8_strings = {}  # offset -> (length, string)
    for m in re.finditer(rb'[\x20-\x7e]{3,}', data):
        off = m.start()
        # only record strings that are mostly within snapshot data
        if off < ISO_DATA_START or off >= ISO_DATA_END:
            # skip but track some for completeness
            if off < 0x460000 or off >= 0xf976b0:  # outside text section
                continue
        s = m.group().decode('ascii', errors='replace')
        utf8_strings[off] = (len(s), s)
    
    print(f'UTF-8 strings: {len(utf8_strings)}')
    
    # Find UTF-16LE strings (CJK or extended)
    utf16_strings = {}
    # Pattern: 2 or more consecutive UTF-16LE chars where high byte is non-zero (likely CJK or extended latin)
    # Or low byte is non-zero and high byte is 0 (likely ASCII-as-UTF-16)
    for m in re.finditer(rb'(?:[\x00-\xff][\x01-\xff]){2,}', data):
        off = m.start()
        if off < ISO_DATA_START or off >= ISO_DATA_END:
            continue
        try:
            s = m.group().decode('utf-16-le')
            # filter: only keep if it has actual content
            if len(s) < 2:
                continue
            # Check if mostly printable
            printable = sum(1 for c in s if c.isprintable() or c in '\n\t')
            if printable / len(s) < 0.7:
                continue
            utf16_strings[off] = (len(s), s)
        except:
            pass
    
    print(f'UTF-16LE strings: {len(utf16_strings)}')
    
    # Output
    with open(output_path, 'w', encoding='utf-8') as out:
        out.write(f'# Object pool strings from {libapp_path}\n')
        out.write(f'# File size: {len(data)} bytes\n')
        out.write(f'# Snapshot data range: 0x{ISO_DATA_START:x}-0x{ISO_DATA_END:x}\n')
        out.write(f'# UTF-8 strings: {len(utf8_strings)}\n')
        out.write(f'# UTF-16LE strings: {len(utf16_strings)}\n\n')
        
        # Sort by offset
        out.write('='*80 + '\n')
        out.write('UTF-8 strings (sorted by offset)\n')
        out.write('='*80 + '\n\n')
        for off in sorted(utf8_strings):
            length, s = utf8_strings[off]
            # Truncate very long strings
            disp = s if len(s) <= 200 else s[:200] + '...'
            # escape for output
            disp = disp.replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
            out.write(f'0x{off:08x} [{length:4}] {disp}\n')
        
        out.write('\n' + '='*80 + '\n')
        out.write('UTF-16LE strings (sorted by offset)\n')
        out.write('='*80 + '\n\n')
        for off in sorted(utf16_strings):
            length, s = utf16_strings[off]
            if all(ord(c) < 128 for c in s):
                continue  # skip pure ASCII as UTF-16
            disp = s if len(s) <= 200 else s[:200] + '...'
            out.write(f'0x{off:08x} [{length:4}] {disp!r}\n')
    
    print(f'Wrote {output_path}')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
