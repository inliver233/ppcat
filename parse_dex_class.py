#!/usr/bin/env python3
"""
DEX file parser to find class L了/了; and its fields/methods.
Parses classes2.dex (and checks classes.dex, classes3.dex) directly from DEX binary format.

DEX format reference:
- Header layout (little-endian):
  0x00: magic (8 bytes) + checksum (4) + signature (20) + file_size (4)
  0x20: header_size (4) + endian_tag (4)
  0x28: link_size (4) + link_off (4)
  0x30: map_off (4)
  0x38: string_ids_size (4)
  0x3c: string_ids_off (4)
  0x40: type_ids_size (4)
  0x44: type_ids_off (4)
  0x48: proto_ids_size (4) + proto_ids_off (4)
  0x50: field_ids_size (4)
  0x54: field_ids_off (4)
  0x58: method_ids_size (4)
  0x5c: method_ids_off (4)
  0x60: class_defs_size (4)
  0x64: class_defs_off (4)
  0x68: data_size (4) + data_off (4)

- string_id_item: string_data_off (4 bytes, offset into DEX)
- string_data_item: uleb128 utf16_size, then <size> bytes of MUTF-8 data, then null terminator
- type_id_item: descriptor_idx (4 bytes -> index into string_ids)
- field_id_item: class_idx(2) + type_idx(2) + name_idx(4)  (8 bytes)
- method_id_item: class_idx(2) + proto_idx(2) + name_idx(4)  (8 bytes)
- class_def_item: 32 bytes:
  class_idx(4) + access_flags(4) + superclass_idx(4) + interfaces_off(4) +
  source_file_idx(4) + annotations_off(4) + class_data_off(4) + static_values_off(4)
- class_data_item:
  uleb128 static_fields_size
  uleb128 instance_fields_size
  uleb128 direct_methods_size
  uleb128 virtual_methods_size
  then encoded_field list (each: uleb128 field_idx_diff + uleb128 access_flags)
  then encoded_method list (each: uleb128 method_idx_diff + uleb128 access_flags + uleb128 code_off)
"""

import struct
import sys
import os
from io import BytesIO

def read_uleb128(data, offset):
    """Read unsigned LEB128 from data at offset. Returns (value, new_offset)."""
    result = 0
    shift = 0
    while True:
        if offset >= len(data):
            return None, offset
        byte = data[offset]
        offset += 1
        result |= (byte & 0x7f) << shift
        if (byte & 0x80) == 0:
            break
        shift += 7
    return result, offset

def read_uleb128p1(data, offset):
    """Read unsigned LEB128 minus 1 (used for method/field indices in encoded lists). Returns (value, new_offset)."""
    val, offset = read_uleb128(data, offset)
    if val is None:
        return None, offset
    return val - 1, offset

def read_sleb128(data, offset):
    """Read signed LEB128 from data at offset. Returns (value, new_offset)."""
    result = 0
    shift = 0
    while True:
        if offset >= len(data):
            return None, offset
        byte = data[offset]
        offset += 1
        result |= (byte & 0x7f) << shift
        shift += 7
        if (byte & 0x80) == 0:
            if byte & 0x40:
                result |= -(1 << (shift - 1))
            break
    return result, offset

def read_mutf8_string(data, offset):
    """Read MUTF-8 string from data at offset. Returns (string, new_offset).
    string_data_item: uleb128 utf16_size, then MUTF-8 bytes, then \0 terminator.
    """
    utf16_size, offset = read_uleb128(data, offset)
    if utf16_size is None:
        return None, offset

    # Find null terminator
    end = data.find(b'\x00', offset)
    if end == -1:
        return None, offset

    mutf8_bytes = data[offset:end]
    offset = end + 1

    # Decode MUTF-8 to Python string
    result = []
    i = 0
    while i < len(mutf8_bytes):
        b = mutf8_bytes[i]
        if b == 0xc0 and i + 1 < len(mutf8_bytes) and mutf8_bytes[i+1] == 0x80:
            # MUTF-8 encodes U+0000 as 0xC0 0x80
            result.append('\x00')
            i += 2
        elif b < 0x80:
            # ASCII
            result.append(chr(b))
            i += 1
        elif b < 0xe0:
            # 2-byte sequence
            if i + 1 < len(mutf8_bytes):
                cp = ((b & 0x1f) << 6) | (mutf8_bytes[i+1] & 0x3f)
                result.append(chr(cp))
                i += 2
            else:
                i += 1
        elif b < 0xf0:
            # 3-byte sequence
            if i + 2 < len(mutf8_bytes):
                cp = ((b & 0x0f) << 12) | ((mutf8_bytes[i+1] & 0x3f) << 6) | (mutf8_bytes[i+2] & 0x3f)
                result.append(chr(cp))
                i += 3
            else:
                i += 1
        else:
            # 4-byte sequence (supplementary plane) - split into surrogate pair for MUTF-8
            if i + 3 < len(mutf8_bytes):
                # MUTF-8 encodes supplementary chars as 2 x 3-byte surrogates
                cp1 = ((b & 0x07) << 12) | ((mutf8_bytes[i+1] & 0x3f) << 6) | (mutf8_bytes[i+2] & 0x3f)
                i += 3
                if i + 2 < len(mutf8_bytes) and mutf8_bytes[i] >= 0xe0:
                    cp2 = ((mutf8_bytes[i] & 0x07) << 12) | ((mutf8_bytes[i+1] & 0x3f) << 6) | (mutf8_bytes[i+2] & 0x3f)
                    i += 3
                    # Combine surrogates to get the real codepoint
                    hi = cp1 - 0xD800
                    lo = cp2 - 0xDC00
                    cp = 0x10000 + (hi << 10) + lo
                    result.append(chr(cp))
                else:
                    result.append(chr(cp1))
            else:
                i += 1
    return ''.join(result), offset

class DexParser:
    def __init__(self, filepath):
        self.filepath = filepath
        with open(filepath, 'rb') as f:
            self.data = f.read()
        self.fsize = len(self.data)
        self.strings = []       # list of (offset, string)
        self.type_ids = []      # list of (type_idx, descriptor_string_idx)
        self.field_ids = []     # list of (class_idx, type_idx, name_idx)
        self.method_ids = []    # list of (class_idx, proto_idx, name_idx)
        self.proto_ids = []     # list of (shorty_idx, return_type_idx, parameters_off)
        self.class_defs = []    # list of (class_idx, access_flags, superclass_idx, interfaces_off,
                                #           source_file_idx, annotations_off, class_data_off, static_values_off)
        self._parse_header()
        self._parse_strings()
        self._parse_type_ids()
        self._parse_proto_ids()
        self._parse_field_ids()
        self._parse_method_ids()
        self._parse_class_defs()

    def _parse_header(self):
        d = self.data
        # Read the main header fields
        self.string_ids_size = struct.unpack_from('<I', d, 0x38)[0]
        self.string_ids_off  = struct.unpack_from('<I', d, 0x3c)[0]
        self.type_ids_size   = struct.unpack_from('<I', d, 0x40)[0]
        self.type_ids_off    = struct.unpack_from('<I', d, 0x44)[0]
        self.proto_ids_size  = struct.unpack_from('<I', d, 0x48)[0]
        self.proto_ids_off   = struct.unpack_from('<I', d, 0x4c)[0]
        self.field_ids_size  = struct.unpack_from('<I', d, 0x50)[0]
        self.field_ids_off   = struct.unpack_from('<I', d, 0x54)[0]
        self.method_ids_size = struct.unpack_from('<I', d, 0x58)[0]
        self.method_ids_off  = struct.unpack_from('<I', d, 0x5c)[0]
        self.class_defs_size = struct.unpack_from('<I', d, 0x60)[0]
        self.class_defs_off  = struct.unpack_from('<I', d, 0x64)[0]
        self.data_size       = struct.unpack_from('<I', d, 0x68)[0]
        self.data_off        = struct.unpack_from('<I', d, 0x6c)[0]

        print(f"DEX file: {self.filepath}")
        print(f"  Size: {self.fsize} bytes")
        print(f"  string_ids: {self.string_ids_size} @ 0x{self.string_ids_off:x}")
        print(f"  type_ids:   {self.type_ids_size} @ 0x{self.type_ids_off:x}")
        print(f"  proto_ids:  {self.proto_ids_size} @ 0x{self.proto_ids_off:x}")
        print(f"  field_ids:  {self.field_ids_size} @ 0x{self.field_ids_off:x}")
        print(f"  method_ids: {self.method_ids_size} @ 0x{self.method_ids_off:x}")
        print(f"  class_defs: {self.class_defs_size} @ 0x{self.class_defs_off:x}")
        print(f"  data:       {self.data_size} @ 0x{self.data_off:x}")

    def _parse_strings(self):
        print(f"\nParsing {self.string_ids_size} string IDs...")
        d = self.data
        for i in range(self.string_ids_size):
            off = self.string_ids_off + i * 4
            str_data_off = struct.unpack_from('<I', d, off)[0]
            try:
                s, _ = read_mutf8_string(d, str_data_off)
                self.strings.append((str_data_off, s if s is not None else ""))
            except Exception as e:
                self.strings.append((str_data_off, f"<ERROR: {e}>"))
        print(f"  Parsed: {len(self.strings)}")

    def _parse_type_ids(self):
        d = self.data
        for i in range(self.type_ids_size):
            off = self.type_ids_off + i * 4
            desc_idx = struct.unpack_from('<I', d, off)[0]
            self.type_ids.append(desc_idx)

    def _parse_proto_ids(self):
        d = self.data
        for i in range(self.proto_ids_size):
            off = self.proto_ids_off + i * 12
            shorty_idx, return_type_idx, params_off = struct.unpack_from('<III', d, off)
            self.proto_ids.append((shorty_idx, return_type_idx, params_off))

    def _parse_field_ids(self):
        d = self.data
        for i in range(self.field_ids_size):
            off = self.field_ids_off + i * 8
            class_idx, type_idx, name_idx = struct.unpack_from('<HHI', d, off)
            self.field_ids.append((class_idx, type_idx, name_idx))

    def _parse_method_ids(self):
        d = self.data
        for i in range(self.method_ids_size):
            off = self.method_ids_off + i * 8
            class_idx, proto_idx, name_idx = struct.unpack_from('<HHI', d, off)
            self.method_ids.append((class_idx, proto_idx, name_idx))

    def _parse_class_defs(self):
        d = self.data
        for i in range(self.class_defs_size):
            off = self.class_defs_off + i * 32
            vals = struct.unpack_from('<IIIIIIII', d, off)
            self.class_defs.append(vals)

    def get_string(self, idx):
        if idx < len(self.strings):
            return self.strings[idx][1]
        return f"<INVALID:{idx}>"

    def get_type_name(self, type_idx):
        if type_idx < len(self.type_ids):
            return self.get_string(self.type_ids[type_idx])
        return f"<INVALID:{type_idx}>"

    def get_field_name(self, field_idx):
        if field_idx < len(self.field_ids):
            _, _, name_idx = self.field_ids[field_idx]
            return self.get_string(name_idx)
        return f"<INVALID:{field_idx}>"

    def get_field_type(self, field_idx):
        if field_idx < len(self.field_ids):
            _, type_idx, _ = self.field_ids[field_idx]
            return self.get_type_name(type_idx)
        return "?"

    def get_method_name(self, method_idx):
        if method_idx < len(self.method_ids):
            _, _, name_idx = self.method_ids[method_idx]
            return self.get_string(name_idx)
        return f"<INVALID:{method_idx}>"

    def get_method_proto(self, method_idx):
        if method_idx < len(self.method_ids):
            _, proto_idx, _ = self.method_ids[method_idx]
            if proto_idx < len(self.proto_ids):
                return self.proto_ids[proto_idx]
        return None

    def parse_class_data(self, class_data_off):
        """Parse class_data_item at given offset.
        Returns dict with static_fields, instance_fields, direct_methods, virtual_methods.
        Each field: (field_idx, access_flags)
        Each method: (method_idx, access_flags, code_off)
        """
        if class_data_off == 0:
            return None

        d = self.data
        off = class_data_off

        result = {
            'static_fields': [],
            'instance_fields': [],
            'direct_methods': [],
            'virtual_methods': [],
        }

        try:
            static_fields_size, off = read_uleb128(d, off)
            instance_fields_size, off = read_uleb128(d, off)
            direct_methods_size, off = read_uleb128(d, off)
            virtual_methods_size, off = read_uleb128(d, off)

            # Static fields
            prev_field_idx = 0
            for _ in range(static_fields_size):
                diff, off = read_uleb128(d, off)
                if diff is None: break
                field_idx = prev_field_idx + diff
                access_flags, off = read_uleb128(d, off)
                if access_flags is None: break
                result['static_fields'].append((field_idx, access_flags))
                prev_field_idx = field_idx

            # Instance fields
            prev_field_idx = 0
            for _ in range(instance_fields_size):
                diff, off = read_uleb128(d, off)
                if diff is None: break
                field_idx = prev_field_idx + diff
                access_flags, off = read_uleb128(d, off)
                if access_flags is None: break
                result['instance_fields'].append((field_idx, access_flags))
                prev_field_idx = field_idx

            # Direct methods
            prev_method_idx = 0
            for _ in range(direct_methods_size):
                diff, off = read_uleb128(d, off)
                if diff is None: break
                method_idx = prev_method_idx + diff
                access_flags, off = read_uleb128(d, off)
                if access_flags is None: break
                code_off, off = read_uleb128(d, off)
                if code_off is None: break
                result['direct_methods'].append((method_idx, access_flags, code_off))
                prev_method_idx = method_idx

            # Virtual methods
            prev_method_idx = 0
            for _ in range(virtual_methods_size):
                diff, off = read_uleb128(d, off)
                if diff is None: break
                method_idx = prev_method_idx + diff
                access_flags, off = read_uleb128(d, off)
                if access_flags is None: break
                code_off, off = read_uleb128(d, off)
                if code_off is None: break
                result['virtual_methods'].append((method_idx, access_flags, code_off))
                prev_method_idx = method_idx
        except Exception as e:
            print(f"  ERROR parsing class_data: {e}")

        return result

    def parse_encoded_method(self, off):
        """Parse a single encoded_method for accessing the code_item."""
        d = self.data
        diff, off = read_uleb128(d, off)
        if diff is None: return None
        method_idx_diff = diff
        access_flags, off = read_uleb128(d, off)
        if access_flags is None: return None
        code_off, off = read_uleb128(d, off)
        return (method_idx_diff, access_flags, code_off, off)

    def print_class_info(self, class_def, class_def_idx):
        class_idx, access_flags, superclass_idx, interfaces_off, \
        source_file_idx, annotations_off, class_data_off, static_values_off = class_def

        class_name = self.get_type_name(class_idx)
        superclass_name = self.get_type_name(superclass_idx) if superclass_idx != 0xFFFFFFFF else "NONE"

        print(f"\n{'='*80}")
        print(f"CLASS_DEF #{class_def_idx}: {class_name}")
        print(f"{'='*80}")
        print(f"  class_idx: {class_idx} -> {class_name}")
        print(f"  access_flags: 0x{access_flags:04x}")
        print(f"  superclass_idx: {superclass_idx} -> {superclass_name}")
        print(f"  interfaces_off: 0x{interfaces_off:x}")
        print(f"  source_file_idx: {source_file_idx} -> {self.get_string(source_file_idx) if source_file_idx < 0xFFFFFFFF else 'NONE'}")
        print(f"  annotations_off: 0x{annotations_off:x}")
        print(f"  class_data_off: 0x{class_data_off:x}")
        print(f"  static_values_off: 0x{static_values_off:x}")

        # Parse class data
        if class_data_off:
            cd = self.parse_class_data(class_data_off)
            if cd:
                print(f"\n  --- Static Fields ({len(cd['static_fields'])}) ---")
                for fi, af in cd['static_fields']:
                    fname = self.get_field_name(fi)
                    ftype = self.get_field_type(fi)
                    # Get the defining class for this field
                    if fi < len(self.field_ids):
                        fic, _, _ = self.field_ids[fi]
                        fic_name = self.get_type_name(fic)
                    else:
                        fic_name = "?"
                    print(f"    [{fi}] {fname}: {ftype}  (access=0x{af:04x}, defining_class={fic_name})")

                print(f"\n  --- Instance Fields ({len(cd['instance_fields'])}) ---")
                for fi, af in cd['instance_fields']:
                    fname = self.get_field_name(fi)
                    ftype = self.get_field_type(fi)
                    if fi < len(self.field_ids):
                        fic, _, _ = self.field_ids[fi]
                        fic_name = self.get_type_name(fic)
                    else:
                        fic_name = "?"
                    print(f"    [{fi}] {fname}: {ftype}  (access=0x{af:04x}, defining_class={fic_name})")

                print(f"\n  --- Direct Methods ({len(cd['direct_methods'])}) ---")
                for mi, af, co in cd['direct_methods']:
                    mname = self.get_method_name(mi)
                    proto = self.get_method_proto(mi)
                    return_type = self.get_type_name(proto[1]) if proto else "?"
                    print(f"    [{mi}] {mname} (access=0x{af:04x}, code_off=0x{co:x}, return={return_type})")

                print(f"\n  --- Virtual Methods ({len(cd['virtual_methods'])}) ---")
                for mi, af, co in cd['virtual_methods']:
                    mname = self.get_method_name(mi)
                    proto = self.get_method_proto(mi)
                    return_type = self.get_type_name(proto[1]) if proto else "?"
                    print(f"    [{mi}] {mname} (access=0x{af:04x}, code_off=0x{co:x}, return={return_type})")
        else:
            print(f"  (no class_data — likely an external/interface class with no members)")

    def find_strings_with(self, chars_or_bytes, search_name=""):
        """Find all strings containing the given characters or bytes.
        Returns list of (string_id_idx, offset, string)."""
        results = []
        for idx, (off, s) in enumerate(self.strings):
            if search_name:
                # search by name: check if any of the chars is in the string
                if any(ch in s for ch in chars_or_bytes):
                    results.append((idx, off, s))
            else:
                if chars_or_bytes in s:
                    results.append((idx, off, s))
        return results

    def search_related_types_and_classes(self, target_string_ids):
        """Given a set of string_id indices, find all type_ids pointing to them,
        and then all class_defs whose class_idx is one of those type_ids."""
        # Find type_ids pointing to these strings
        matching_type_ids = set()
        for tidx, desc_idx in enumerate(self.type_ids):
            if desc_idx in target_string_ids:
                matching_type_ids.add(tidx)

        # Find class_defs with class_idx in matching_type_ids
        matching_classes = []
        for cidx, cd in enumerate(self.class_defs):
            if cd[0] in matching_type_ids:
                matching_classes.append((cidx, cd))

        return matching_type_ids, matching_classes


def analyze_dex_for_了(dex_path, label=""):
    print(f"\n{'#'*80}")
    print(f"# ANALYZING: {dex_path}")
    print(f"{'#'*80}")

    dp = DexParser(dex_path)

    # U+4E86 in UTF-8: 0xE4 0xBA 0x86
    target_char = '了'  # U+4E86
    target_utf8 = b'\xe4\xba\x86'

    # Find all strings containing 了
    print(f"\n{'='*80}")
    print(f"Searching for strings containing '了' (U+4E86) in {label}...")
    print(f"{'='*80}")

    strings_with_了 = dp.find_strings_with([target_char], search_name="了")
    print(f"\nFound {len(strings_with_了)} strings containing '了':")
    for sidx, off, s in strings_with_了:
        # Show the string, but truncate if too long
        display = s if len(s) < 100 else s[:100] + "..."
        # Show hex bytes around the 了 character
        hex_repr = s.encode('utf-8', errors='replace').hex()
        if len(hex_repr) > 60:
            hex_repr = hex_repr[:60] + "..."
        print(f"  string[{sidx}] @0x{off:06x}: \"{display}\"  (hex: {hex_repr})")

    # Collect string IDs that contain 了
    了_string_ids = set(sidx for sidx, _, _ in strings_with_了)

    # Also search for other interesting patterns
    print(f"\nAlso searching for other interesting patterns in type descriptors containing 了:")
    for sidx, off, s in strings_with_了:
        if s.startswith('L') or '/' in s or '.' in s:
            print(f"  TYPE-LIKE: string[{sidx}] \"{s}\"")

    # Find type_ids pointing to these strings
    matching_type_ids, matching_classes = dp.search_related_types_and_classes(了_string_ids)

    print(f"\nType IDs pointing to 了-containing strings:")
    for tidx in sorted(matching_type_ids):
        desc = dp.get_type_name(tidx)
        print(f"  type[{tidx}] -> string[{dp.type_ids[tidx]}] = \"{desc}\"")

    print(f"\nClass definitions with class_idx pointing to 了-containing types:")
    for cidx, cd in matching_classes:
        dp.print_class_info(cd, cidx)

    # Also search for any class that references 了 in its fields
    print(f"\n{'='*80}")
    print(f"Searching for fields named '了' or of type containing '了' in ALL classes...")
    print(f"{'='*80}")

    # Go through all field_ids to find ones whose name is 了
    for fidx, (class_idx, type_idx, name_idx) in enumerate(dp.field_ids):
        fname = dp.get_string(name_idx)
        ftype = dp.get_type_name(type_idx)
        fclass = dp.get_type_name(class_idx)
        if '了' in fname:
            print(f"  FIELD[{fidx}]: name='{fname}' type='{ftype}' class='{fclass}'")

    return dp, strings_with_了, matching_type_ids, matching_classes


if __name__ == '__main__':
    dex_files = [
        ('/root/ppcat/main_dex/classes2.dex', 'classes2.dex'),
        ('/root/ppcat/main_dex/classes.dex', 'classes.dex'),
        ('/root/ppcat/main_dex/classes3.dex', 'classes3.dex'),
    ]

    for path, label in dex_files:
        if not os.path.exists(path):
            print(f"Skipping missing {path}")
            continue
        try:
            analyze_dex_for_了(path, label)
        except Exception as e:
            print(f"ERROR analyzing {path}: {e}")
            import traceback
            traceback.print_exc()
