#!/usr/bin/env python3
"""
Dart AOT Snapshot entry point extractor.
Uses dart_parser.Stream for correct VLE decoding.
Parses alloc (with gap-based canonical set), then fill to extract:
  String data, Function(name→code_index), Code(owner_ref, payload_info).
Cross-references to output function name → entry point mappings.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'analysis_workdir'))
from dart_parser import Stream


# ---- Constants ----
CID_STRING = 84
CID_FUNCTION = 7
CID_CODE = 17
CID_CLASS = 5
CID_INSTANCE = 43
NUM_PREDEFINED_CIDS = 154

FILL_REF_UNSIGNED = False  # Dart >= 2.18 uses ReadRefId for fill refs


def skip_canonical_set(s, count):
    """Gap-based canonical set format (Dart 2.17-2.19, CompressedPointers)."""
    table_length = s.read_unsigned()
    first_elem = s.read_unsigned()
    num_gaps = count - first_elem
    if num_gaps < 0:
        num_gaps = 0
    for _ in range(num_gaps):
        s.read_unsigned()


def read_ref_id(s):
    """ReadRefId: big-endian signed-byte accumulation (fill refs for Dart >= 2.18)."""
    result = 0
    for _ in range(6):
        b_raw = s.data[s.pos]
        s.pos += 1
        b_signed = b_raw - 256 if b_raw & 0x80 else b_raw
        result = b_signed + (result << 7)
        if b_raw & 0x80:
            return result + 128
    raise OverflowError("ReadRefId overflow")


def read_ref(s):
    """Version-aware ref read (fill phase)."""
    if FILL_REF_UNSIGNED:
        return s.read_unsigned()
    else:
        return read_ref_id(s)


# Simple alloc CIDs — checked BEFORE Instance fallback
_SIMPLE_ALLOC = {
    56,  # Double
    58,  # Float32x4
    59,  # Int32x4
    60,  # Float64x2
    7,   # Function
    9,   # ClosureData
    11,  # Field
    12,  # Script
    13,  # Library
    14,  # Namespace
    15,  # KernelProgramInfo
    51,  # Closure
    31,  # UnlinkedCall
    34,  # ICData
    35,  # MegamorphicCache
    36,  # SubtypeTestCache
    37,  # LoadingUnit
    72,  # WeakProperty
    44,  # LibraryPrefix
    40,  # LanguageError
    41,  # UnhandledException
    6,   # PatchClass
    10,  # FfiTrampolineData
    8,   # TypeParameters
    29,  # Sentinel
    30,  # SingleTargetCache
    32,  # MonomorphicSmiableCall
    33,  # CallSiteData
    69,  # SendPort
    70,  # StackTrace
    67,  # Capability
    68,  # ReceivePort
    74,  # FutureOr
    76,  # TransferableTypedData
    75,  # UserTag
    77,  # Map
    78,  # ConstMap
    79,  # Set
    80,  # ConstSet
    83,  # GrowableObjectArray
    71,  # RegExp
    16,  # WeakSerializationReference
    64,  # TypedDataView
    63,  # ExternalTypedData
    49,  # TypeRef
}

_CANONICAL_SET_ALLOC = {50, 47, 48}  # TypeParameter, Type, FunctionType


def skip_alloc_data(s, cid, count, canonical):
    """Skip per-cluster alloc data. Returns adjusted count (e.g. for Code deferred)."""
    if cid == CID_STRING:
        for _ in range(count):
            s.read_unsigned()
        if canonical:
            skip_canonical_set(s, count)
    elif cid == 55:  # Mint
        for _ in range(count):
            s.read_tagged64()
    elif cid in _CANONICAL_SET_ALLOC:
        if canonical:
            skip_canonical_set(s, count)
    elif cid == 45:  # TypeArguments
        for _ in range(count):
            s.read_unsigned()
        if canonical:
            skip_canonical_set(s, count)
    elif cid in (82, 81):  # Array, ImmutableArray
        for _ in range(count):
            s.read_unsigned()
    elif cid == CID_CODE:
        for _ in range(count):
            s.read_tagged64()  # state_bits
        deferred = s.read_unsigned()
        for _ in range(deferred):
            s.read_tagged64()
        count += deferred
    elif cid == CID_CLASS:
        # count from caller IS the predefined_count
        predefined = count
        # Check for extra total_class_count prefix (some Dart builds)
        if predefined > NUM_PREDEFINED_CIDS:
            predefined = s.read_unsigned()
        for _ in range(predefined):
            s.read_tagged64()
        new_count = s.read_unsigned()
        # Return total count (predefined + new) so next_ref is correct
        # But we need to track main_count separately
        # Store main_count in a mutable container
        # Actually, we'll return predefined+new_count and set main_count in the caller
        count = predefined + new_count
    elif cid == 21:  # ObjectPool
        for _ in range(count):
            s.read_unsigned()
    elif cid in (22, 23, 24):  # ROData
        for _ in range(count):
            s.read_unsigned()
        if canonical:
            skip_canonical_set(s, count)
    elif cid in (26, 27, 28):  # ExcHandlers, Context, CtxScope
        for _ in range(count):
            s.read_unsigned()
    elif cid in _SIMPLE_ALLOC:
        pass  # simple alloc: just count
    elif cid >= CID_INSTANCE:
        # Instance check MUST come AFTER all known simple/canonical CIDs
        # because some predefined CIDs >= 43 (e.g. Closure=51, Double=56, Map=77)
        # use simple alloc
        if count > 0:
            s.read_tagged64()  # next_field_offset
            s.read_tagged64()  # instance_size
    else:
        pass  # unknown, treat as simple
    return count


def main():
    libapp_path = '/root/ppcat/lib/arm64-v8a/libapp.so'
    with open(libapp_path, 'rb') as f:
        data = f.read()

    ISO_START = 0x3330
    iso_data = data[ISO_START:]

    # Find cluster start
    feat_start = 0x34
    feat_end = iso_data.find(b'\x00', feat_start)
    cluster_start = feat_end + 1

    # ---- Parse alloc (all 588 clusters) ----
    s = Stream(iso_data, cluster_start)
    num_base = s.read_unsigned()
    num_objs = s.read_unsigned()
    nc = s.read_unsigned()
    instr_table_len = s.read_unsigned()
    instr_data_off = s.read_unsigned()

    print(f"Snapshot header: base={num_base} objects={num_objs} clusters={nc}")
    print(f"  instr_table_len={instr_table_len} instr_data_off={instr_data_off}")

    clusters = []  # list of {cid, count, start_ref, main_count, is_str}
    next_ref = num_base + 1

    for ci in range(nc):
        cid_val = s.read_tagged64()
        cid = int((cid_val >> 1) & 0xFFFFFFFF)
        canonical = (cid_val & 1) != 0

        count = s.read_unsigned()

        # Save original count for Code main_count tracking
        orig_count = count

        # Skip per-cluster alloc data
        count = skip_alloc_data(s, cid, count, canonical)

        main_count = orig_count  # for non-special clusters
        if cid == CID_CLASS:
            # orig_count = predefined_count (from caller's read)
            # skip_alloc_data returned total = predefined + new_count
            main_count = orig_count
        elif cid == CID_CODE:
            main_count = orig_count  # count was already adjusted for deferred

        clusters.append({
            'cid': cid, 'count': count, 'start_ref': next_ref,
            'main_count': main_count, 'is_str': (cid == CID_STRING),
            'canonical': canonical
        })
        next_ref += count

        if ci < 8 or cid in (CID_STRING, CID_CODE, CID_FUNCTION, CID_CLASS, 55, 47, 45, 21):
            names = {84: 'Str', 55: 'Mint', 56: 'Dbl', 50: 'TP', 47: 'Type',
                     45: 'TA', 17: 'Code', 7: 'Func', 51: 'Clos', 5: 'Class',
                     21: 'Pool', 48: 'FT', 78: 'CMap', 80: 'CSet', 82: 'IArr',
                     43: 'Inst', 11: 'Field', 12: 'Script', 13: 'Lib',
                     6: 'PatCl', 8: 'TPs', 9: 'CD', 10: 'Ffi', 14: 'NS',
                     15: 'KPI', 16: 'WSR', 22: 'PcD', 23: 'CSM', 24: 'StkM',
                     26: 'EH', 27: 'Ctx', 28: 'CtxS', 29: 'Sent', 30: 'STC',
                     31: 'UC', 34: 'ICD', 35: 'MC', 36: 'STC2', 37: 'LU',
                     40: 'LE', 41: 'UHE', 44: 'LP', 67: 'Cap', 68: 'RP',
                     69: 'SP', 70: 'ST', 71: 'RE', 72: 'WP', 74: 'FO',
                     75: 'UT', 76: 'TTD', 77: 'Map', 79: 'Set',
                     81: 'Arr', 83: 'GOA'}
            name = names.get(cid, f'C{cid}')
            print(f"  alloc[{ci:3d}] {name:6s} cid={cid:4d} count={count:6d} canon={canonical} refs={clusters[-1]['start_ref']}..{clusters[-1]['start_ref']+count-1}")

    fill_start = s.pos
    print(f"\nAlloc done: {len(clusters)} clusters, fill_start=0x{fill_start:x} (iso-rel)")
    print(f"next_ref={next_ref}, expected ~{num_base + 1 + num_objs}")

    # ---- Parse fill ----
    print("\n=== Fill section parsing ===")

    # Find the correct String fill position by locating the first known string
    # (the alloc parsing has subtle gaps; use auto-detection)
    test_str = b'useShouldInterceptRequest'
    str_pos = iso_data.find(test_str)
    # The encoded length (ReadUnsigned) for this 25-char string is just before it at str_pos-1
    # Verify: ReadUnsigned at str_pos-1 should give 50
    test_s = Stream(iso_data, str_pos - 1)
    test_enc = test_s.read_unsigned()
    if test_enc == 50:
        fill_start = str_pos - 1
        print(f"Auto-detected fill_start=0x{fill_start:x} (from string pattern)")
    else:
        print(f"WARNING: Could not verify fill_start, using computed 0x{fill_start:x}")

    s_fill = Stream(iso_data, fill_start)

    strings = {}    # ref -> value
    functions = {}  # ref -> (name_ref, code_index, kind_tag)
    codes = {}      # ref -> (owner_ref, payload_info, instr_index)
    instr_idx = 0

    # Helper: read one raw byte (dart_parser Stream doesn't have read_byte)
    def read_byte(st):
        b = st.data[st.pos]
        st.pos += 1
        return b

    for ci, cm in enumerate(clusters):
        cid = cm['cid']
        count = cm['count']
        main_count = cm['main_count']
        ref = cm['start_ref']
        if count <= 0:
            continue

        name = {84: 'Str', 17: 'Code', 7: 'Func', 5: 'Class', 21: 'Pool',
                45: 'TA', 47: 'Type', 48: 'FT', 50: 'TP', 51: 'Clos',
                11: 'Field', 12: 'Script', 13: 'Lib'}.get(cid, f'C{cid}')

        try:
            fill_pos = s_fill.pos

            if cid == CID_STRING:
                for _ in range(count):
                    encoded = s_fill.read_unsigned()
                    length = encoded >> 1
                    is_two_byte = encoded & 1
                    nbytes = length * (2 if is_two_byte else 1)
                    raw = s_fill.read_bytes(nbytes)
                    if is_two_byte:
                        runes = []
                        for j in range(length):
                            lo = raw[j*2]
                            hi = raw[j*2+1]
                            runes.append(chr(lo | (hi << 8)))
                        value = ''.join(runes)
                    else:
                        value = raw.decode('utf-8', errors='replace')
                    strings[ref] = value
                    ref += 1

            elif cid == CID_FUNCTION:
                for _ in range(count):
                    # 4 refs: name(0), owner(1), signature(2), data(3)
                    name_ref = read_ref(s_fill)
                    owner_ref = read_ref(s_fill)
                    sig_ref = read_ref(s_fill)
                    data_ref = read_ref(s_fill)
                    # Scalars: code_index(OpUnsigned) + kind_tag(OpTagged32)
                    code_idx = s_fill.read_unsigned()
                    kind_tag = s_fill.read_tagged64()  # read_tagged32 → same encoding
                    functions[ref] = (name_ref, code_idx, kind_tag)
                    ref += 1

            elif cid == CID_CODE:
                for i in range(count):
                    owner_ref = 0
                    payload_info = 0
                    cluster_idx = -1

                    if i < main_count:
                        # Main code: read payload_info
                        payload_info = s_fill.read_unsigned()
                        cluster_idx = instr_idx
                        instr_idx += 1

                        # Discarded codes read compressed_stackmaps ref
                        if False:  # no discarded codes detected in this snapshot
                            owner_ref = read_ref(s_fill)
                            # Skip this discarded code
                            codes[ref] = (owner_ref, payload_info, cluster_idx)
                            ref += 1
                            continue

                    # Read 6 refs: owner(0), exception_handlers(1), pc_descriptors(2),
                    # catch_entry(3), inlined_id_to_function(4), code_source_map(5)
                    owner_ref = read_ref(s_fill)
                    r1 = read_ref(s_fill)   # exception_handlers
                    r2 = read_ref(s_fill)   # pc_descriptors
                    r3 = read_ref(s_fill)   # catch_entry
                    r4 = read_ref(s_fill)   # inlined_id_to_function
                    r5 = read_ref(s_fill)   # code_source_map

                    codes[ref] = (owner_ref, payload_info, cluster_idx)
                    ref += 1

            elif cid == CID_CLASS:
                for i in range(count):
                    # 13 refs then scalars + conditional bitmap
                    for _ in range(13):
                        read_ref(s_fill)
                    s_fill.read_tagged64()  # class_id (int32)
                    s_fill.read_tagged64()  # instance_size
                    s_fill.read_tagged64()  # next_field_offset
                    s_fill.read_tagged64()  # type_args_offset
                    s_fill.read_tagged64()  # num_type_args (int16)
                    s_fill.read_tagged64()  # num_native_fields (uint16)
                    s_fill.read_tagged64()  # state_bits (uint32)
                    # Conditional bitmap
                    is_predefined = i < main_count
                    class_id = 0  # we didn't save it; assume not top-level
                    if is_predefined or True:  # always read for safety
                        s_fill.read_unsigned()
                    ref += 1

            elif cid == 21:  # ObjectPool
                for _ in range(count):
                    length = s_fill.read_unsigned()
                    for _ in range(length):
                        entry_bits = read_byte(s_fill)
                        type_bits = entry_bits & 0x7F
                        if type_bits == 0:  # kTaggedObject
                            read_ref(s_fill)
                        elif type_bits == 1:  # kImmediate
                            s_fill.read_tagged64()
                        elif type_bits == 4:  # kNativeEntryData
                            read_ref(s_fill)
                        # else: nothing
                ref += count

            elif cid == 45:  # TypeArguments
                for _ in range(count):
                    length = s_fill.read_unsigned()
                    s_fill.read_tagged64()  # hash
                    s_fill.read_unsigned()  # nullability
                    read_ref(s_fill)        # instantiations
                    for _ in range(length):
                        read_ref(s_fill)
                ref += count

            elif cid in _CANONICAL_SET_ALLOC:  # Type(47), TypeParam(50), FuncType(48)
                # FillRefs with scalars — use exact specs from fillspec.go
                fmt = {
                    # TypeParameter v2.17-v2.19: 3 refs + class_id(tagged32) + base(uint8) + index(uint8) + combined(uint8)
                    50: (3, ['tagged32', 'uint8', 'uint8', 'uint8']),
                    # Type v2.17-v2.18: 3 refs + type_class_id(unsigned) + combined(uint8)
                    47: (3, ['unsigned', 'uint8']),
                    # FunctionType v2.17+: 6 refs + combined(uint8) + packed_params(tagged32) + packed_type_params(tagged32)
                    48: (6, ['uint8', 'tagged32', 'tagged32']),
                }
                num_refs, scalars = fmt.get(cid, (3, []))
                for _ in range(count):
                    for _ in range(num_refs):
                        read_ref(s_fill)
                    for sop in scalars:
                        if sop in ('unsigned',):
                            s_fill.read_unsigned()
                        elif sop == 'uint8':
                            read_byte(s_fill)
                        elif sop == 'tagged32':
                            s_fill.read_tagged64()
                ref += count

            elif cid in (51,):  # Closure — 6 refs
                for _ in range(count):
                    for _ in range(6):
                        read_ref(s_fill)
                ref += count

            elif cid == 11:  # Field — 4 refs + scalars
                for _ in range(count):
                    for _ in range(4):
                        read_ref(s_fill)
                    kind_bits = s_fill.read_tagged64()
                    read_ref(s_fill)  # value_or_offset
                    if (kind_bits >> 1) & 1:  # static
                        s_fill.read_unsigned()
                ref += count

            elif cid == 13:  # Library — 10 refs + 4 scalars
                for _ in range(count):
                    for _ in range(10):
                        read_ref(s_fill)
                    s_fill.read_tagged64()
                    s_fill.read_tagged64()
                    read_byte(s_fill)
                    read_byte(s_fill)
                ref += count

            elif cid == 12:  # Script — 1 ref + 1 scalar
                for _ in range(count):
                    read_ref(s_fill)
                    s_fill.read_tagged64()
                ref += count

            elif cid == 55:  # Mint — FillNone (no fill data)
                pass  # no fill bytes to consume

            elif cid == 56:  # Double — FillDouble: ReadTagged64 per object
                for _ in range(count):
                    s_fill.read_tagged64()
                ref += count

            elif cid in (82, 81):  # Array, ImmArray — FillArray
                for _ in range(count):
                    length = s_fill.read_unsigned()
                    read_ref(s_fill)  # type_args
                    for _ in range(length):
                        read_ref(s_fill)  # element
                ref += count

            elif cid == 83:  # GrowableObjectArray — 3 refs
                for _ in range(count):
                    for _ in range(3):
                        read_ref(s_fill)
                ref += count

            elif cid in (77, 78, 79, 80):  # Map, ConstMap, Set, ConstSet — 5 refs
                for _ in range(count):
                    for _ in range(5):
                        read_ref(s_fill)
                ref += count

            elif cid in (22, 23, 24):  # PcDesc, CodeSrcMap, CompStkMaps — FillInlineBytes
                for _ in range(count):
                    length = s_fill.read_unsigned()
                    s_fill.read_bytes(length)
                ref += count

            elif cid == 26:  # ExcHandlers
                for _ in range(count):
                    raw = s_fill.read_unsigned()
                    read_ref(s_fill)  # handled_types_data
                    for _ in range(raw):
                        s_fill.read_tagged64()  # pc_offset
                        s_fill.read_tagged64()  # outer_try_index
                        read_byte(s_fill)      # needs_stacktrace
                        read_byte(s_fill)      # has_catch_all
                        read_byte(s_fill)      # is_generated
                ref += count

            elif cid == 27:  # Context
                for _ in range(count):
                    length = s_fill.read_unsigned()
                    read_ref(s_fill)  # parent
                    for _ in range(length):
                        read_ref(s_fill)  # variable
                ref += count

            elif cid == 28:  # ContextScope
                for _ in range(count):
                    length = s_fill.read_unsigned()
                    read_byte(s_fill)  # is_implicit
                    for _ in range(length * 7):  # ~7 pointer fields per var
                        read_ref(s_fill)
                ref += count

            elif cid >= CID_INSTANCE:
                # FillInstance — read bitmap once, then per-object fields
                if count <= 0:
                    continue
                bitmap = s_fill.read_unsigned()
                # We need next_field_offset. Try to read it from the bitmap
                # For safety, read no fields (bitmap only)
                # This is a simplified skip; might leave unconsumed bytes
                ref += count

            else:
                # Generic FillRefs skip — assume fixed ref count
                # This is a fallback; most types should be handled above
                pass  # Warning: this may leave unconsumed fill data

            delta = s_fill.pos - fill_pos

        except Exception as e:
            print(f"  ERROR fill[{ci}] CID={cid} {name} at 0x{fill_pos:x}: {e}")
            import traceback
            traceback.print_exc()
            break

        if delta > 0 and (ci < 10 or cid in (CID_STRING, CID_CODE, CID_FUNCTION, CID_CLASS, 21)):
            print(f"  fill[{ci:3d}] {name:6s} count={count:6d} delta={delta}")

    print(f"\nFill done: strings={len(strings)} functions={len(functions)} codes={len(codes)}")
    print(f"Final fill pos: 0x{s_fill.pos:x} / {len(iso_data):x}")

    # ---- Cross-reference ----
    print("\n=== Cross-referencing Functions and Codes ===")

    # Function: (name_ref, code_index, kind_tag) -> resolve name
    func_info = {}  # function_ref -> (name_str, code_index)
    for fref, (name_ref, code_idx, kind_tag) in functions.items():
        name = strings.get(name_ref, f"<unnamed ref={name_ref}>")
        func_info[fref] = (name, code_idx)

    # Code: (owner_ref, payload_info, instr_index)
    # Build instructions_index -> code_ref map
    instr_to_code = {}
    for cref, (owner_ref, payload_info, ci) in codes.items():
        if ci >= 0:
            instr_to_code[ci] = (cref, owner_ref, payload_info)

    # Match functions to codes via code_index
    matched = []
    for fref, (name, code_idx) in func_info.items():
        if code_idx in instr_to_code:
            cref, owner_ref, payload_info = instr_to_code[code_idx]
            matched.append((name, fref, code_idx, cref, owner_ref, payload_info))
    matched.sort(key=lambda x: x[0].lower())

    print(f"Matched {len(matched)} functions to Code objects")

    # Find checkAppMetaData
    print("\n=== checkAppMetaData analysis ===")
    for name, fref, ci, cref, owner_ref, payload_info in matched:
        if 'checkAppMetaData' in name:
            print(f"  Name:          {name}")
            print(f"  Function ref:  {fref}")
            print(f"  Code index:    {ci}")
            print(f"  Code ref:      {cref}")
            print(f"  Payload info:  {payload_info} (0x{payload_info:x})")
            break
    else:
        # Search in all functions by name
        print("  Not found in matched set. Searching raw function data...")
        for fref, (name_ref, code_idx, kind_tag) in functions.items():
            name = strings.get(name_ref, '')
            if 'checkAppMetaData' in name:
                print(f"  Found in functions: fref={fref} name={name!r} code_idx={code_idx}")
        for sref, sval in strings.items():
            if 'checkAppMetaData' in sval:
                print(f"  Found in strings: sref={sref} value={sval!r}")

    # Output results
    outpath = '/root/ppcat/entry_points.txt'
    with open(outpath, 'w', encoding='utf-8', errors='replace') as f:  # replace surrogates
        f.write(f"# Dart AOT Snapshot: Function name -> Code mappings\n")
        f.write(f"# Total Functions: {len(functions)}, Total Codes: {len(codes)}\n")
        f.write(f"# Matched name->code: {len(matched)}\n")
        f.write(f"#\n")
        f.write(f"# Columns: function_name | fref | code_index | cref | owner_ref | payload_info\n")
        f.write(f"#\n")
        for name, fref, ci, cref, owner_ref, payload_info in matched:
            f.write(f"{name} | fref={fref} | ci={ci} | cref={cref} | "
                    f"owner={owner_ref} | payload={payload_info} | 0x{payload_info:x}\n")
    print(f"\nWrote {len(matched)} entries to {outpath}")

    # Show check* functions
    print("\n=== All 'check*' functions ===")
    for name, fref, ci, cref, owner_ref, payload_info in matched:
        if name.startswith('check'):
            print(f"  ci={ci:5d} fref={fref:6d} cref={cref:6d} payload=0x{payload_info:x} {name}")


if __name__ == '__main__':
    main()
