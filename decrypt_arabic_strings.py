#!/usr/bin/env python3
"""
Offline Arabic string decryptor for ppcat ad plugin classes.

Based on reverse-engineering the sparse-switch + xor hash dispatch algorithm
used in Lสۦ۠ۦۨ/สۥ۟۟ۡ;.ۥ้้۟۟ۡ() (code_off=0x549c84, classes2.dex).

Principle:
1. Each Arabic-encrypted string's Java hashCode() is computed
2. The hash maps to a key in the central decryption function's sparse-switch table
3. Each sparse-switch handler corresponds to a specific plaintext value
4. This script extracts the hash→key mapping and provides lookup

Usage:
  python3 decrypt_arabic_strings.py

Output:
  - Prints decryption dispatch table
  - Maps known plaintext SDK identifiers to their encrypted Arabic forms
  - Computes hash for any given Arabic string
"""

import sys
import struct
import os

sys.path.insert(0, os.path.dirname(__file__))
from parse_dex_class import DexParser

# ─── Java String.hashCode() implementation ──────────────────────────────
def java_hashcode(s):
    """Compute Java-compatible String.hashCode() for a Python string."""
    h = 0
    for c in s:
        h = (31 * h + ord(c)) & 0xFFFFFFFF
        if h > 0x7FFFFFFF:
            h -= 0x100000000
    return h

# ─── Known plaintext SDK identifiers ────────────────────────────────────
KNOWN_PLAINTEXTS = {
    # AdMob
    'com.google.android.gms.ads.MobileAds': 'AdMob 初始化类',
    'com.google.android.gms.ads.initialization.OnInitializationCompleteListener': 'AdMob 初始化回调',
    'ca-app-pub-5440663071705011~9273252967': 'AdMob APP_ID',

    # GDT (腾讯优量汇)
    'com.qq.e.ads.InterstitialAd': 'GDT 插页广告',
    'com.qq.e.ads.banner.ADSize': 'GDT Banner',
    'com.qq.e.ads.splash.SplashAD': 'GDT 开屏广告',
    'com.qq.e.comm.managers.GDTADManager': 'GDT 广告管理器',
    'com.qq.e.comm.managers.GDTAdSdk': 'GDT SDK 主类',

    # Pangle/CSJ (穿山甲)
    'com.bytedance.sdk.openadsdk.TTAdSdk': 'Pangle SDK 主类',
    'com.bytedance.sdk.openadsdk.TTAdConfig': 'Pangle 配置类',
    'com.bytedance.sdk.openadsdk.TTAdManager': 'Pangle 广告管理器',

    # Kwad (快手)
    'com.kwad.sdk.SdkConfig': 'Kwad SDK 配置',
    'com.kwad.sdk.api.KsAdSDK': 'Kwad SDK 主类',
    'com.kwad.sdk.api.KsSplashScreenAd': 'Kwad 开屏广告',
    'com.kwad.components.ad.splash.SplashAd': 'Kwad 开屏实现',

    # Umeng
    '5cecdbb14ca3575f39000861': 'UMENG_APPKEY',

    # MethodChannel names (推测)
    'ppcat/admob': 'AdMob channel',
    'ppcat/gdt': 'GDT channel',
    'ppcat/pangle': 'Pangle channel',
    'ppcat/kwad': 'Kwad channel',
}

# ─── DEX Decryption Class Analysis ──────────────────────────────────────

def extract_sparse_switch_tables(dp, code_off, insns_size):
    """
    Extract all sparse-switch tables from the decryption method.
    Returns list of {hash_keys: [k1,k2,k3,k4], handler_offsets: [o1,o2,o3,o4]}
    """
    d = dp.data
    insns = d[code_off+16:code_off+16+insns_size*2]

    tables = []
    i = 0
    while i < len(insns):
        cu = insns[i] | (insns[i+1] << 8)
        op = cu & 0xFF

        if op == 0x2C:  # sparse-switch
            va = cu >> 8
            soff = insns[i+2] | (insns[i+3] << 8) | (insns[i+4] << 16) | (insns[i+5] << 24)
            if soff >= 0x80000000:
                soff -= 0x100000000
            target_cu = (i // 2) + soff

            table_offset = target_cu * 2
            if table_offset < 0 or table_offset + 4 > len(insns):
                i += 6
                continue
            if 0 <= table_offset and table_offset + 4 <= len(insns):
                ident = insns[table_offset] | (insns[table_offset+1] << 8)
                size = insns[table_offset+2] | (insns[table_offset+3] << 8)

                if ident == 0x0200 and size > 0:
                    keys = []
                    targets = []
                    keys_start = table_offset + 4
                    targets_start = table_offset + 4 + size * 4

                    for ki in range(size):
                        key = insns[keys_start + ki*4] | (insns[keys_start + ki*4 + 1] << 8) | \
                              (insns[keys_start + ki*4 + 2] << 16) | (insns[keys_start + ki*4 + 3] << 24)
                        if key >= 0x80000000:
                            key -= 0x100000000
                        tgt = insns[targets_start + ki*4] | (insns[targets_start + ki*4 + 1] << 8) | \
                              (insns[targets_start + ki*4 + 2] << 16) | (insns[targets_start + ki*4 + 3] << 24)
                        if tgt >= 0x80000000:
                            tgt -= 0x100000000
                        keys.append(key)
                        targets.append(tgt)

                    tables.append({
                        'inst_offset': i // 2,
                        'target_cu': target_cu,
                        'keys': keys,
                        'targets': targets,
                    })

            i += 6
        else:
            i += 2

    return tables


def extract_encrypted_strings_from_class(dp, class_type_name):
    """
    Extract all Arabic-encrypted const-string references from a plugin class.
    Returns list of (method_name, string_idx, string_value, hash_value).
    """
    # Find class_def
    class_def = None
    for cidx, cd in enumerate(dp.class_defs):
        if dp.get_type_name(cd[0]) == class_type_name:
            class_def = cd
            break

    if not class_def:
        return []

    class_data_off = class_def[6]
    if not class_data_off:
        return []

    cdata = dp.parse_class_data(class_data_off)
    if not cdata:
        return []

    results = []
    d = dp.data

    for category, method_list in [('direct', cdata['direct_methods']),
                                   ('virtual', cdata['virtual_methods'])]:
        for mi, af, co in method_list:
            if co == 0:
                continue

            try:
                insns_size = struct.unpack_from('<I', d, co + 12)[0]
            except:
                continue

            mname = dp.get_method_name(mi)
            insns = d[co+16:co+16+insns_size*2]

            i = 0
            while i < len(insns) - 4:
                cu = insns[i] | (insns[i+1] << 8)
                op = cu & 0xFF

                if op == 0x1A:  # const-string
                    sidx = insns[i+2] | (insns[i+3] << 8)
                    if sidx < len(dp.strings):
                        s = dp.strings[sidx][1]
                        if any(0x06D6 <= ord(c) <= 0x06EC for c in s):
                            h = java_hashcode(s)
                            results.append((mname, sidx, s, h))
                    i += 4
                elif op == 0x1B:  # const-string/jumbo
                    sidx = insns[i+2] | (insns[i+3] << 8) | (insns[i+4] << 16) | (insns[i+5] << 24)
                    if sidx < len(dp.strings):
                        s = dp.strings[sidx][1]
                        if any(0x06D6 <= ord(c) <= 0x06EC for c in s):
                            h = java_hashcode(s)
                            results.append((mname, sidx, s, h))
                    i += 6
                else:
                    i += 2

    return results


def main():
    dex_path = 'main_dex/classes2.dex'

    print("=" * 80)
    print("PPCAT Ad Plugin Arabic String Decryptor")
    print("=" * 80)

    dp = DexParser(dex_path)

    # ─── Part 1: Decryption dispatch table analysis ─────────────────────
    print("\n" + "=" * 80)
    print("PART 1: Decryption Function Sparse-Switch Dispatch Table")
    print("=" * 80)

    # The decryption class
    decrypt_class = 'Lสۦ۠ۦۨ/สۥ۟۟ۡ;'
    decrypt_method_off = 0x549c84

    # Verify
    for cidx, cd in enumerate(dp.class_defs):
        if dp.get_type_name(cd[0]) == decrypt_class:
            cdata = dp.parse_class_data(cd[6])
            if cdata:
                for mi, af, co in cdata['direct_methods'] + cdata['virtual_methods']:
                    if co == decrypt_method_off:
                        mname = dp.get_method_name(mi)
                        print(f"Decryption method: {cdata} class -> [{mi}] {mname}")
                        break
            break

    d = dp.data
    regs, ins, outs, tries, dbg, insns_size = struct.unpack_from('<HHHHII', d, decrypt_method_off)
    print(f"Method stats: {insns_size} code units, {tries} try blocks")

    tables = extract_sparse_switch_tables(dp, decrypt_method_off, insns_size)
    print(f"Found {len(tables)} sparse-switch tables")

    # Build a hash→(table_idx, key_idx) mapping
    hash_to_table = {}
    for ti, table in enumerate(tables):
        for ki, key in enumerate(table['keys']):
            hash_to_table[key] = (ti, ki, table['targets'][ki])

    print(f"Total unique hash keys: {len(hash_to_table)}")

    # ─── Part 2: Compute hashes for known plaintexts ────────────────────
    print("\n" + "=" * 80)
    print("PART 2: Known Plaintext -> Hash Mapping")
    print("=" * 80)

    for plaintext, desc in sorted(KNOWN_PLAINTEXTS.items()):
        h = java_hashcode(plaintext)
        found = h in hash_to_table
        status = "✓ MATCH" if found else "  (no match in dispatch table)"
        print(f"  {status} hash={h:12d} (0x{h:08x}): {desc}")
        print(f"    plaintext: {repr(plaintext[:80])}")

    # ─── Part 3: Extract Arabic strings from ad plugin classes ──────────
    print("\n" + "=" * 80)
    print("PART 3: Arabic Encrypted Strings from Ad Plugin Classes")
    print("=" * 80)

    ad_classes = {
        'AdMob': 'Lสۥ۠ۦ/สۥ۟ۢ;',
        'Pangle/CSJ': 'Lสۥ۠ۦۧ/สۥ۟۟ۡ;',
        'Kwad': 'Lสۥ۠ۤۧ/สۥ۟۠ۢ;',
        'GDT': 'Lสۥۡۨ/สۥ۟۠ۢ;',
        'Kwad小类': 'Lสۦ۟ۡۥ/สۥ۟۠ۢ;',
    }

    all_hashes = set()

    for label, class_name in ad_classes.items():
        strings = extract_encrypted_strings_from_class(dp, class_name)
        print(f"\n{label} ({class_name}):")
        print(f"  Total Arabic strings: {len(strings)}")

        # Show unique hashes
        hashes = set(h for _, _, _, h in strings)
        all_hashes.update(hashes)
        print(f"  Unique hash values: {len(hashes)}")

        # Check which hashes match the dispatch table
        matched = [h for h in hashes if h in hash_to_table]
        unmatched = [h for h in hashes if h not in hash_to_table]
        print(f"  Matched in dispatch table: {len(matched)}")
        print(f"  Unmatched: {len(unmatched)}")

        # Show first 5 example strings
        for mname, sidx, s, h in strings[:5]:
            print(f"    [{mname}] string@{sidx}: len={len(s)} hash={h} (0x{h:08x})")
            print(f"      value: {repr(s[:60])}")

    print(f"\nTotal unique hash values across all ad classes: {len(all_hashes)}")
    matched_all = all_hashes & set(hash_to_table.keys())
    unmatched_all = all_hashes - set(hash_to_table.keys())
    print(f"Matched in dispatch table: {len(matched_all)}")
    print(f"Unmatched: {len(unmatched_all)}")

    # ─── Part 4: Hash value lookup utility ─────────────────────────────
    print("\n" + "=" * 80)
    print("PART 4: Manual Hash Lookup")
    print("=" * 80)
    print("To check an Arabic string, compute its Java hashCode and look up in the table.")
    print("Example: python3 -c \"from decrypt_arabic_strings import *; print(java_hashcode('...'))\"")

    # Save dispatch table
    out_path = '/root/ppcat/analysis_workdir/decryption_dispatch_table.txt'
    with open(out_path, 'w') as f:
        f.write("# Decryption Dispatch Table\n")
        f.write(f"# Total sparse-switch tables: {len(tables)}\n")
        f.write(f"# Total unique hash keys: {len(hash_to_table)}\n\n")
        f.write("# Format: hash_key -> table_idx, key_idx, handler_offset\n")
        for h in sorted(hash_to_table.keys()):
            ti, ki, toff = hash_to_table[h]
            f.write(f"{h:12d} (0x{h:08x}) -> table[{ti}].key[{ki}] -> +{toff}\n")

    print(f"\nDispatch table saved to: {out_path}")
    print("Done.")


if __name__ == '__main__':
    main()
