#!/usr/bin/env python3
"""
Refined Dart object pool dumper.
Only extract strings from the IsolateSnapshotData range, and filter aggressively.
"""
import struct
import sys
import re

def is_cjk(ch):
    """Check if a character is CJK or extended."""
    cp = ord(ch)
    return (0x4E00 <= cp <= 0x9FFF or  # CJK Unified
            0x3400 <= cp <= 0x4DBF or  # CJK Extension A
            0x3000 <= cp <= 0x303F or  # CJK Symbols
            0xFF00 <= cp <= 0xFFEF)    # Halfwidth/Fullwidth

def main(libapp_path, output_path):
    with open(libapp_path, 'rb') as f:
        data = f.read()
    
    ISO_START = 0x3330
    ISO_END = 0x45fc60
    iso_data = data[ISO_START:ISO_END]
    
    print(f'File size: {len(data)}')
    print(f'Snapshot data: 0x{ISO_START:x}-0x{ISO_END:x} ({len(iso_data)} bytes)')
    
    # Find UTF-8 strings: 4+ printable ASCII chars
    # AND not preceded/followed by another ASCII byte (to find isolated strings)
    utf8_strings = {}
    for m in re.finditer(rb'[\x20-\x7e]{4,}', iso_data):
        off = ISO_START + m.start()
        s = m.group().decode('ascii')
        # Skip if previous or next char in original data is also ASCII (means we're in a larger string)
        # Actually, we want the FULL string. So check if the match boundary is at the edge.
        utf8_strings[off] = (len(s), s)
    
    # Find UTF-16LE strings: must have at least 2 chars where high byte indicates CJK
    utf16_strings = {}
    # Pattern: pairs of bytes where high byte is in CJK range (0x4E-0x9F for common CJK)
    # Use lookbehind/lookahead to ensure boundary
    for m in re.finditer(rb'(?:[\x00-\xff][\x4e-\x9f]){2,}', iso_data):
        off = ISO_START + m.start()
        try:
            s = m.group().decode('utf-16-le')
            if len(s) < 2:
                continue
            utf16_strings[off] = (len(s), s)
        except:
            pass
    
    # Also look for fullwidth punctuation and other CJK ranges as UTF-16LE
    # Pattern: pairs where high byte is 0x30, 0xFF (fullwidth), or 0x4E-0x9F
    for m in re.finditer(rb'(?:[\x00-\xff][\x30-\x30]){2,}', iso_data):
        off = ISO_START + m.start()
        try:
            s = m.group().decode('utf-16-le')
            if len(s) < 2: continue
            # Only keep CJK symbols
            if all(0x3000 <= ord(c) <= 0x303F for c in s):
                utf16_strings[off] = (len(s), s)
        except: pass
    
    for m in re.finditer(rb'(?:[\x00-\xff][\xff-\xff]){2,}', iso_data):
        off = ISO_START + m.start()
        try:
            s = m.group().decode('utf-16-le')
            if len(s) < 2: continue
            if all(0xFF00 <= ord(c) <= 0xFFEF for c in s):
                utf16_strings[off] = (len(s), s)
        except: pass
    
    print(f'UTF-8 strings in snapshot: {len(utf8_strings)}')
    print(f'UTF-16LE strings in snapshot: {len(utf16_strings)}')
    
    # Write output
    with open(output_path, 'w', encoding='utf-8') as out:
        out.write(f'# Object pool strings from {libapp_path}\n')
        out.write(f'# Snapshot data range: 0x{ISO_START:x}-0x{ISO_END:x}\n')
        out.write(f'# UTF-8: {len(utf8_strings)}, UTF-16LE: {len(utf16_strings)}\n\n')
        
        out.write('## UTF-16LE strings (Chinese / CJK)\n\n')
        for off in sorted(utf16_strings):
            length, s = utf16_strings[off]
            disp = s if len(s) <= 200 else s[:200] + '...'
            out.write(f'0x{off:08x} [{length:4}] {disp}\n')
        
        out.write('\n## UTF-8 strings (English / ASCII)\n\n')
        for off in sorted(utf8_strings):
            length, s = utf8_strings[off]
            # Filter out boring / noise strings
            if len(s) < 5: continue
            # Skip strings that look like random hex / hash
            if re.fullmatch(r'[0-9a-f]+', s) and len(s) > 16: continue
            disp = s if len(s) <= 300 else s[:300] + '...'
            disp = disp.replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
            out.write(f'0x{off:08x} [{length:4}] {disp}\n')
    
    print(f'Wrote {output_path}')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
