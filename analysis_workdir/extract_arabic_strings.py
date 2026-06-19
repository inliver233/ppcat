#!/usr/bin/env python3
"""
Extract all Arabic-encrypted strings (U+06D6-U+06EC) from 7 target plugin classes
in classes2.dex, plus search all strings for channel-name-like patterns.

Uses parse_dex_class.DexParser for DEX parsing.
"""
import sys
import struct
import os

sys.path.insert(0, '/root/ppcat')
from parse_dex_class import DexParser

# ─── Opcode size table (code units per instruction) ──────────────────────────
# Build minimal opcode-to-size table covering all DEX opcodes we might encounter.
def build_opcode_size_table():
    """Returns list of 256 entries: opcode -> size in code units (2 bytes each)."""
    sz = [1] * 256  # default to 1 for unrecognized/safety

    # Format 10x / 12x / 11n / 11x / 10t — all 1 code unit
    for op in [
        0x00,           # nop
        0x01, 0x04, 0x07, 0x0A, 0x0B, 0x0C, 0x0D,  # move variants
        0x0E, 0x0F, 0x10, 0x11,  # return
        0x12,           # const/4
        0x1D, 0x1E,     # monitor-enter/exit
        0x21,           # array-length
        0x27,           # throw
        0x28,           # goto
        0xF8, 0xF9, 0xFA, 0xFB, 0xFC, 0xFD, 0xFE, 0xFF,
    ]:
        sz[op] = 1

    # Format 22x / 21t / 21s / 21h / 21c / 23x / 22b / 22t / 22s / 22c — 2 units
    for op in [
        0x02, 0x05, 0x08,  # move/from16
        0x13, 0x15, 0x16, 0x19,  # const variants
        0x1A, 0x1C, 0x1F,  # const-string, const-class, check-cast
        0x20, 0x22, 0x23,  # instance-of, new-instance, new-array
        0x29,           # goto/16
        0x2D, 0x2E, 0x2F, 0x30, 0x31,  # cmp*
        0x32, 0x33, 0x34, 0x35, 0x36, 0x37,  # if-*
        0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D,  # if-*z
    ]:
        sz[op] = 2
    for op in range(0x44, 0x52): sz[op] = 2  # aget*
    for op in range(0x52, 0x60): sz[op] = 2  # aput*
    for op in range(0x60, 0x6E): sz[op] = 2  # iget*
    for op in range(0x6E, 0x7C): sz[op] = 2  # iput*
    for op in range(0x7C, 0x8A): sz[op] = 2  # sget*
    for op in range(0x8A, 0x98): sz[op] = 2  # sput*

    # Format 32x / 31i / 31t / 31c / 35c / 3rc — 3 code units
    for op in [
        0x03, 0x06, 0x09,  # move/16
        0x14, 0x17,        # const, const-wide/32
        0x1B,              # const-string/jumbo
        0x24, 0x25,        # filled-new-array
        0x26,              # fill-array-data
        0x2A,              # goto/32
        0x2B, 0x2C,        # packed-switch, sparse-switch
    ]:
        sz[op] = 3
    for op in range(0x98, 0xC0): sz[op] = 3   # invoke-*
    for op in range(0xC8, 0xF0): sz[op] = 3   # invoke-*/range
    for op in range(0xE0, 0xF0): sz[op] = 3   # invoke-static/range, etc.
    # (Some ranges overlap but that's fine — we just set 3 again.)

    # Format 51l — 5 code units
    sz[0x18] = 5  # const-wide

    return sz

OP_SIZES = build_opcode_size_table()

# ─── Arabic character range ──────────────────────────────────────────────────
ARABIC_MIN = 0x06D6
ARABIC_MAX = 0x06EC

def has_arabic_chars(s):
    """Check if string contains any characters in the Arabic encrypted range."""
    for c in s:
        cp = ord(c)
        if ARABIC_MIN <= cp <= ARABIC_MAX:
            return True
    return False

def extract_arabic_chars(s):
    """Extract all Arabic chars from string, showing positions."""
    result = []
    for i, c in enumerate(s):
        cp = ord(c)
        if ARABIC_MIN <= cp <= ARABIC_MAX:
            result.append((i, cp, c))
    return result

# ─── Payload helpers ─────────────────────────────────────────────────────────
def compute_payload_region(dp, code_off, inst_addr, payload_type):
    """
    Given a fill-array-data/packed-switch/sparse-switch instruction at inst_addr
    (code unit index relative to code_off+16), compute the payload region.

    The instruction is 3 code units (31t format):
      code_unit[0]: opcode in low 8 bits
      code_unit[1:3]: 32-bit signed branch offset (relative to inst_addr)

    Returns (payload_codeunit_offset, payload_codeunit_count) or None.
    """
    d = dp.data
    byte_base = code_off + 16 + inst_addr * 2
    if byte_base + 6 > len(d):
        return None

    # Read the 32-bit signed branch offset from code units 1-2
    branch_offset = struct.unpack_from('<i', d, byte_base + 2)[0]
    payload_addr = inst_addr + branch_offset  # in code units

    if payload_addr < 0:
        return None

    payload_byte = code_off + 16 + payload_addr * 2
    if payload_byte + 4 > len(d):
        return None

    ident = struct.unpack_from('<H', d, payload_byte)[0]

    if payload_type == 'fill-array-data':
        if ident != 0x0300:
            return None
        element_width = struct.unpack_from('<H', d, payload_byte + 2)[0]
        size = struct.unpack_from('<I', d, payload_byte + 4)[0]
        data_bytes = (size * element_width + 1) & ~1  # round up to even
        payload_bytes = 8 + data_bytes
    elif payload_type == 'packed-switch':
        if ident != 0x0100:
            return None
        size = struct.unpack_from('<H', d, payload_byte + 2)[0]
        payload_bytes = 8 + size * 4  # first_key(4) + targets(size*4)
    elif payload_type == 'sparse-switch':
        if ident != 0x0200:
            return None
        size = struct.unpack_from('<H', d, payload_byte + 2)[0]
        payload_bytes = 4 + size * 8  # keys(size*4) + targets(size*4)
    else:
        return None

    payload_units = (payload_bytes + 1) // 2
    return (payload_addr, payload_units)

# ─── Instruction decoder ─────────────────────────────────────────────────────
def scan_code_item_for_strings(dp, code_off, insns_size):
    """
    Parse a code_item at code_off, iterate through instructions, and
    collect all const-string and const-string/jumbo instructions.

    Returns list of (inst_offset, instruction_name, string_idx, is_arabic, string_value).
    """
    d = dp.data
    results = []

    # Compute payload skip regions first (for fill-array-data, switches)
    skip_units = {}  # code_unit_addr -> skip_to code_unit_addr (exclusive)

    # First pass: find payload-generating instructions
    inst_offset = 0  # in code units from code_off+16
    while inst_offset < insns_size:
        byte_off = code_off + 16 + inst_offset * 2
        if byte_off + 2 > len(d):
            break
        cu = struct.unpack_from('<H', d, byte_off)[0]
        opcode = cu & 0xFF

        if opcode == 0x26:  # fill-array-data
            region = compute_payload_region(dp, code_off, inst_offset, 'fill-array-data')
            if region:
                payload_start, payload_units = region
                skip_units[payload_start] = payload_start + payload_units
        elif opcode == 0x2B:  # packed-switch
            region = compute_payload_region(dp, code_off, inst_offset, 'packed-switch')
            if region:
                payload_start, payload_units = region
                skip_units[payload_start] = payload_start + payload_units
        elif opcode == 0x2C:  # sparse-switch
            region = compute_payload_region(dp, code_off, inst_offset, 'sparse-switch')
            if region:
                payload_start, payload_units = region
                skip_units[payload_start] = payload_start + payload_units

        size = OP_SIZES[opcode]
        inst_offset += size

    # Second pass: decode instructions and extract strings
    inst_offset = 0
    while inst_offset < insns_size:
        # Skip payload regions
        if inst_offset in skip_units:
            inst_offset = skip_units[inst_offset]
            continue

        byte_off = code_off + 16 + inst_offset * 2
        if byte_off + 2 > len(d):
            break

        cu = struct.unpack_from('<H', d, byte_off)[0]
        opcode = cu & 0xFF
        vAA = (cu >> 8) & 0xFF

        if opcode == 0x1A:  # const-string vAA, string@BBBB
            if inst_offset + 1 < insns_size:
                string_idx = struct.unpack_from('<H', d, byte_off + 2)[0]
                if string_idx < len(dp.strings):
                    s = dp.strings[string_idx][1]
                    entry = (inst_offset, 'const-string', vAA, string_idx, has_arabic_chars(s), s)
                    results.append(entry)

        elif opcode == 0x1B:  # const-string/jumbo vAA, string@BBBBBBBB
            if inst_offset + 2 < insns_size:
                string_idx = struct.unpack_from('<I', d, byte_off + 2)[0]
                if string_idx < len(dp.strings):
                    s = dp.strings[string_idx][1]
                    entry = (inst_offset, 'const-string/jumbo', vAA, string_idx, has_arabic_chars(s), s)
                    results.append(entry)

        size = OP_SIZES[opcode]
        inst_offset += size

    return results

# ─── Channel name search ─────────────────────────────────────────────────────
def find_channel_like_strings(dp):
    """
    Search all strings in the DEX for channel-name-like patterns.
    Returns list of (string_idx, string, reason).
    """
    results = []
    for idx, (off, s) in enumerate(dp.strings):
        if not s:
            continue
        reason = None
        # Pattern 1: contains "ppcat"
        if 'ppcat' in s.lower():
            reason = f'contains "ppcat"'
        # Pattern 2: looks like a method channel name: "domain/identifier"
        elif '/' in s and not s.startswith('L') and not s.startswith('['):
            # Filter out URLs (http://, https://)
            if '://' not in s and not s.startswith('http'):
                # Must have text on both sides of /
                parts = s.split('/')
                if len(parts) >= 2 and all(len(p) > 0 for p in parts):
                    # Look for common channel name patterns
                    if any(c.isalpha() for c in s) and any(c in s for c in '._'):
                        reason = 'channel-name-like (domain/path)'
                    elif '_' in s and '/' in s:
                        reason = 'channel-name-like (package/channel)'
        if reason:
            results.append((idx, s, reason))
    return results

# ─── Main extraction ─────────────────────────────────────────────────────────
def main():
    dex_path = '/root/ppcat/main_dex/classes2.dex'
    output_path = '/root/ppcat/analysis_workdir/arabic_strings_extract.txt'

    print(f"Loading DEX: {dex_path}")
    dp = DexParser(dex_path)
    print(f"Total strings: {len(dp.strings)}")
    print(f"Total type_ids: {dp.type_ids_size}")
    print(f"Total class_defs: {dp.class_defs_size}")

    # ── Target classes ───────────────────────────────────────────────────
    target_classes = {
        # class_name: (label, type_idx_expected)
        'Lสۥ۠ۦ/สۥ۟ۢ;': (
            'AdMob plugin', 4151, 'type@0x1037 in registerWith'
        ),
        'Lสۥ۠ۦۧ/สۥ۟۟ۡ;': (
            'Pangle/CSJ plugin', 4232, 'type@0x1088 in registerWith'
        ),
        'Lสۥ۠ۤۧ/สۥ۟۠ۢ;': (
            'Kwad plugin', 4053, 'type@0xfd5 in registerWith'
        ),
        'Lสۥۡۨ/สۥ۟۠ۢ;': (
            'GDT plugin', 4356, 'type@0x1104 in registerWith'
        ),
        'Lสۦ۟ۡۥ/สۥ۟۠ۢ;': (
            'Kwad sub plugin', 4556, 'type@0x11cc in registerWith'
        ),
        'Lสۦ۠ۦ/สۥ۟۠ۢ;': (
            'Candidate file_picker', 4914, 'type@0x1332 in registerWith'
        ),
        'Lสۥۡۨۥ/สۥ۟۠ۢ;': (
            'Candidate Pangle wrapper', 4427, 'type@0x114b in registerWith'
        ),
    }

    # Collect all output lines
    out_lines = []
    def w(line):
        out_lines.append(line)

    w("=" * 100)
    w("ARABIC-ENCRYPTED STRING EXTRACTION FROM 7 TARGET PLUGIN CLASSES")
    w("DEX file: classes2.dex")
    w("=" * 100)

    # ── Find each class ──────────────────────────────────────────────────
    class_info_list = []  # (class_name, label, note, class_def_idx, class_def, class_data)
    class_stats = []      # (label, total, arabic, plain) for final summary table

    for tname, (label, expected_type_idx, note) in target_classes.items():
        w(f"\n{'─' * 100}")
        w(f"LOOKING UP: {label}")
        w(f"  Type name: {repr(tname)}")
        w(f"  Expected type_idx: {expected_type_idx}, {note}")

        # Find type_idx
        found_type_idx = None
        for tidx in range(dp.type_ids_size):
            if dp.get_type_name(tidx) == tname:
                found_type_idx = tidx
                break

        if found_type_idx is None:
            w(f"  ERROR: Type name not found!")
            continue

        w(f"  Found at type[{found_type_idx}] (expected type[{expected_type_idx}])")

        # Find class_def
        found_cd_idx = None
        found_cd = None
        for cidx, cd in enumerate(dp.class_defs):
            if cd[0] == found_type_idx:
                found_cd_idx = cidx
                found_cd = cd
                break

        if found_cd_idx is None:
            w(f"  ERROR: No class_def with this class_idx!")
            continue

        class_idx, access_flags, superclass_idx, interfaces_off, \
            source_file_idx, annotations_off, class_data_off, static_values_off = found_cd

        w(f"  Found at class_def[{found_cd_idx}]")
        w(f"  access_flags: 0x{access_flags:04x}")
        w(f"  superclass: type[{superclass_idx}] = {dp.get_type_name(superclass_idx) if superclass_idx < 0xFFFFFFFF else 'NONE'}")
        w(f"  class_data_off: 0x{class_data_off:x}")

        if class_data_off == 0:
            w(f"  No class_data (external/interface class)")
            continue

        cd = dp.parse_class_data(class_data_off)
        if cd is None:
            w(f"  ERROR: Failed to parse class_data")
            continue

        w(f"  static_fields: {len(cd['static_fields'])}")
        w(f"  instance_fields: {len(cd['instance_fields'])}")
        w(f"  direct_methods: {len(cd['direct_methods'])}")
        w(f"  virtual_methods: {len(cd['virtual_methods'])}")

        class_info_list.append((label, tname, note, found_cd_idx, found_cd, cd))

    # ── Process each class ───────────────────────────────────────────────
    total_all_strings = 0
    total_all_arabic = 0
    total_all_plaintext = 0

    for label, tname, note, cd_idx, cd_tuple, cd in class_info_list:
        w(f"\n\n{'#' * 100}")
        w(f"# CLASS: {label}")
        w(f"# Type: {repr(tname)}")
        w(f"# class_def[{cd_idx}], {note}")
        w(f"{'#' * 100}")

        class_data_off = cd_tuple[6]

        # Collect all methods
        all_methods = []
        for category, method_list in [('direct', cd['direct_methods']),
                                       ('virtual', cd['virtual_methods'])]:
            for mi, af, co in method_list:
                mname = dp.get_method_name(mi)
                proto = dp.get_method_proto(mi)
                return_type = dp.get_type_name(proto[1]) if proto else "?"
                all_methods.append((category, mi, af, co, mname, return_type))

        w(f"\nTotal methods: {len(all_methods)} "
          f"(direct={len(cd['direct_methods'])}, virtual={len(cd['virtual_methods'])})")

        class_total_strings = 0
        class_arabic_strings = 0
        class_plaintext_strings = 0

        for category, mi, af, co, mname, return_type in all_methods:
            if co == 0:
                w(f"\n  [{category}] [{mi}] {mname} (access=0x{af:04x}, return={return_type})")
                w(f"    code_off=0x0 (no code — abstract/native method)")
                continue

            # Read code_item header
            d = dp.data
            try:
                registers_size = struct.unpack_from('<H', d, co)[0]
                ins_size = struct.unpack_from('<H', d, co + 2)[0]
                outs_size = struct.unpack_from('<H', d, co + 4)[0]
                tries_size = struct.unpack_from('<H', d, co + 6)[0]
                debug_info_off = struct.unpack_from('<I', d, co + 8)[0]
                insns_size = struct.unpack_from('<I', d, co + 12)[0]
            except:
                w(f"\n  [{category}] [{mi}] {mname} (access=0x{af:04x}, return={return_type})")
                w(f"    code_off=0x{co:x} — ERROR reading code_item header")
                continue

            w(f"\n  [{category}] [{mi}] {mname} (access=0x{af:04x}, return={return_type})")
            w(f"    code_off=0x{co:x}  regs={registers_size} ins={ins_size} "
              f"outs={outs_size} tries={tries_size} insns_size={insns_size}")

            # Scan for const-string instructions
            strings = scan_code_item_for_strings(dp, co, insns_size)
            w(f"    const-string instructions found: {len(strings)}")

            if not strings:
                continue

            for inst_offset, inst_name, vAA, sidx, is_arabic, sval in strings:
                class_total_strings += 1
                display = sval if len(sval) < 120 else sval[:120] + "..."
                if is_arabic:
                    class_arabic_strings += 1
                    arabic_chars = extract_arabic_chars(sval)
                    w(f"      [ARABIC] {inst_name} v{vAA}, string@{sidx} "
                      f"(inst@+{inst_offset}) -> \"{display}\"")
                    w(f"               Arabic chars: {[(cp, c) for _, cp, c in arabic_chars]}")
                else:
                    class_plaintext_strings += 1
                    w(f"      [plain] {inst_name} v{vAA}, string@{sidx} "
                      f"(inst@+{inst_offset}) -> \"{display}\"")

        w(f"\n  ── CLASS SUMMARY ──")
        w(f"  Total const-string references: {class_total_strings}")
        w(f"  Arabic-encrypted strings:      {class_arabic_strings}")
        w(f"  Plaintext strings:             {class_plaintext_strings}")

        class_stats.append((label, class_total_strings, class_arabic_strings, class_plaintext_strings))
        total_all_strings += class_total_strings
        total_all_arabic += class_arabic_strings
        total_all_plaintext += class_plaintext_strings

    # ── Channel-name-like strings in ALL strings ─────────────────────────
    w(f"\n\n{'#' * 100}")
    w(f"# GLOBAL SEARCH: Channel-name-like strings in ALL strings of classes2.dex")
    w(f"{'#' * 100}")

    channel_strings = find_channel_like_strings(dp)
    w(f"\nFound {len(channel_strings)} channel-name-like strings:")

    for sidx, s, reason in channel_strings:
        display = s if len(s) < 120 else s[:120] + "..."
        w(f"  string[{sidx}] ({reason}): \"{display}\"")

    # Also search specifically for "ppcat" in all strings
    w(f"\n\n{'#' * 100}")
    w(f"# GLOBAL SEARCH: Strings containing 'ppcat' (case-insensitive)")
    w(f"{'#' * 100}")

    ppcat_strings = [(idx, off, s) for idx, (off, s) in enumerate(dp.strings) if s and 'ppcat' in s.lower()]
    w(f"\nFound {len(ppcat_strings)} strings containing 'ppcat':")
    for idx, off, s in ppcat_strings:
        w(f"  string[{idx}] @0x{off:06x}: \"{s}\"")

    # Search for strings with '/' that look like Flutter channel names
    w(f"\n\n{'#' * 100}")
    w(f"# GLOBAL SEARCH: All strings with '/' (potential channel names, filtered)")
    w(f"{'#' * 100}")

    slash_strings = []
    for idx, (off, s) in enumerate(dp.strings):
        if not s or '/' not in s:
            continue
        if s.startswith('L') or s.startswith('['):
            continue  # type descriptors
        if '://' in s:
            continue  # URLs
        if s.count('/') == 1 and len(s) < 200:
            # Filter: one slash, reasonable length, looks like a channel name
            slash_strings.append((idx, off, s))

    w(f"\nFound {len(slash_strings)} strings with a single '/' (non-type, non-URL):")
    for idx, off, s in slash_strings:
        display = s if len(s) < 120 else s[:120] + "..."
        w(f"  string[{idx}] @0x{off:06x}: \"{display}\"")

    # ── Final summary ────────────────────────────────────────────────────
    w(f"\n\n{'#' * 100}")
    w(f"# FINAL SUMMARY")
    w(f"{'#' * 100}")
    w(f"")
    w(f"  DEX: classes2.dex")
    w(f"  Total strings in DEX: {len(dp.strings)}")
    w(f"  Total classes analyzed: {len(class_info_list)}")
    w(f"")
    w(f"  {'Class':<30s} {'Total':>6s} {'Arabic':>6s} {'Plain':>6s}")
    w(f"  {'─'*30} {'─'*6} {'─'*6} {'─'*6}")

    for label, total, arabic, plain in class_stats:
        w(f"  {label:<30s} {total:>6d} {arabic:>6d} {plain:>6d}")

    w(f"\n  GRAND TOTAL across all 7 classes:")
    w(f"    Total const-string references: {total_all_strings}")
    w(f"    Arabic-encrypted strings:      {total_all_arabic}")
    w(f"    Plaintext strings:             {total_all_plaintext}")
    w(f"")
    w(f"  Channel-name-like strings in entire DEX: {len(channel_strings)}")
    w(f"  Strings containing 'ppcat':              {len(ppcat_strings)}")
    w(f"  Non-type single-slash strings:           {len(slash_strings)}")

    # Write output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out_lines))
    print(f"\n\nOutput written to: {output_path}")
    print(f"Total lines: {len(out_lines)}")

if __name__ == '__main__':
    main()
