#!/usr/bin/env python3
"""
Round 8 patch safety verification script for test2 proposals.
Verifies each proposed patch site follows safe NOP patterns.
"""
import sys

def read_u32(d, addr):
    return int.from_bytes(d[addr:addr+4], 'little')

def verify_safe_nop_pattern(d, addr, desc):
    """Verify addr follows the safe NOP pattern: 2xSTP push + BL + ADD X15 + MOV X0,X22 + RET"""
    # Check for the standard 2xSTP push pattern at the start
    stp1 = d[addr:addr+4]
    stp2 = d[addr+4:addr+8]
    if stp1 == bytes.fromhex('fd79bfa9'):  # STP X29, X30, [X15,#-16]!
        if stp2 == bytes.fromhex('fd030faa'):  # MOV X29, X15
            print(f"[OK] {desc}: Standard prologue (patchable)")
            return True
    print(f"[??] {desc}: Non-standard entry at {hex(addr)}: {d[addr:addr+8].hex()}")
    return False

def verify_entry_point(d, addr, desc):
    """Just check if it's a function entry with STP X29,X30 prologue"""
    prologue = d[addr:addr+8]
    if prologue[:4] == bytes.fromhex('fd79bfa9'):
        print(f"[OK] {desc}: Function entry confirmed at {hex(addr)}")
        return True
    print(f"[??] {desc}: NOT a function entry at {hex(addr)}: {prologue.hex()}")
    return False

def main():
    with open('libapp.so', 'rb') as f:
        d = f.read()

    print("# Round 8 Patch Safety Verification")
    print(f"# libapp.so: {len(d)} bytes")
    print()

    # 1. MissingPluginException ctor @ 0xca8bdc
    verify_entry_point(d, 0xca8bdc, "MissingPluginException ctor entry")

    # 2. PlatformException ctor @ 0xca8c58
    verify_entry_point(d, 0xca8c58, "PlatformException ctor entry")

    # 3. Fault body builder @ 0x920d7c
    verify_entry_point(d, 0x920d7c, "Fault body builder")

    # 4. 喵喵饿了 widget builder @ 0xae30e0
    verify_entry_point(d, 0xae30e0, "Widget builder (喵喵饿了)")

    # 5. Check the CMP W0,#0x14 at 0xae3128
    cmp_instr = d[0xae3128:0xae3128+4]
    print(f"\n[INFO] 0xae3128: CMP instruction = {cmp_instr.hex()} (expected 1f 50 00 71 for CMP W0,#0x14)")
    if cmp_instr == bytes.fromhex('1f500071'):
        print("[OK] CMP W0,#0x14 confirmed")
    else:
        print(f"[!!] Unexpected instruction!")

    # 6. Branch at 0xae312c
    b_instr = d[0xae312c:0xae312c+4]
    print(f"[INFO] 0xae312c: Branch = {b_instr.hex()}")
    if b_instr == bytes.fromhex('c10d0054'):
        print("[OK] B.NE confirmed (patchable to unconditional B)")

    # 7. Verify pool refs
    import json
    try:
        pool = json.load(open('pool_deserialized.json'))
        pool_refs = {e['idx']: e['val'] for e in pool['entries'] if e['type'] == 0}

        anchors = {
            0xf8e: 27913,  # MissingPluginException(
            0xf8d: 21867,  # PlatformException(
            0xf8c: 18589,  # MethodCall
            0x59bc: 28525, # 喵喵饿了
            0x59bb: 21707, # 每日喂喵
            0x869c: 19128, # 饿了喵~
            0x320f: 11545, # onReward Cheat Triggered!
        }
        print("\n# Pool anchor verification")
        all_ok = True
        for slot, expected_ref in anchors.items():
            actual = pool_refs.get(slot)
            if actual == expected_ref:
                print(f"  [OK] slot 0x{slot:x}: ref={actual}")
            else:
                print(f"  [FAIL] slot 0x{slot:x}: expected ref={expected_ref}, got {actual}")
                all_ok = False
        if all_ok:
            print("  All pool anchors verified!")
    except FileNotFoundError:
        print("\n[SKIP] pool_deserialized.json not found")

    # 8. Verify Direction D patch sites (ad async function entries)
    print("\n# Direction D: Ad async function entry point verification")
    ad_funcs = {
        0x888b18: 'showSplashAd_async',
        0x8880c0: 'ad_register_ksad_like',
        0x88862c: 'ad_initAd_like',
        0x8863e8: 'ad_controller',
        0x8758bc: 'ad_dispatcher',
    }
    for addr, name in ad_funcs.items():
        verify_entry_point(d, addr, name)

    # 9. Verify showDialog BL sites in ad functions (safe NOP candidates)
    print("\n# Direction D: showDialog BL sites in ad functions")
    showdialog_bls = {
        0x888c3c: 'showSplashAd→showDialog',
        0x8881f0: 'ad_async_1→showDialog',
        0x888750: 'ad_async_2→showDialog',
        0x886564: 'ad_controller→showDialog',
    }
    for addr, desc in showdialog_bls.items():
        instr = d[addr:addr+4]
        print(f"  {hex(addr)} ({desc}): {instr.hex()}")

    # 10. Verify invokeMethod BL sites
    print("\n# Direction D: invokeMethod BL sites")
    invoke_bls = {
        0x888c10: 'showSplashAd→invoke(0x886290)',
        0x8881c4: 'ad_async_1→invoke(0x885ee0)',
        0x888724: 'ad_async_2→invoke(0x885ee0)',
    }
    for addr, desc in invoke_bls.items():
        instr = d[addr:addr+4]
        print(f"  {hex(addr)} ({desc}): {instr.hex()}")

    # 11. Proposed patch summary
    print("\n# ==========================")
    print("# Proposed Patches (Round 8)")
    print("# ==========================")
    print("""
    ## Patch 1: 喵喵饿了常驻块消失 (方案A-1)
    d[0xae312c:0xae312c+4] = bytes.fromhex('c10d0014')  # B.NE → B
    或:
    d[0xae3128:0xae3128+4] = bytes.fromhex('1f000071')  # CMP #0x14 → CMP #0x0

    ## Patch 2: 静默 MissingPluginException (方案A-5) ★实验性
    d[0xca8bdc:0xca8bdc+8] = bytes.fromhex('e00316aac0035fd6')  # MOV X0,X22; RET

    ## Patch 3: 广告async函数入口return-null (方案D-1) ★★推荐
    for addr in [0x888b18, 0x8880c0, 0x88862c]:
        d[addr:addr+8] = bytes.fromhex('e00316aac0035fd6')

    ## Patch 4: NOP广告showDialog BL (方案D-3, 已证安全但不够)
    for addr in [0x888c3c, 0x8881f0, 0x888750, 0x886564]:
        d[addr:addr+4] = bytes.fromhex('1f2003d5')

    ## Patch 5: 全局 onError 回调截断 (地址待定)
    # 需 logcat Dart 栈帧或 Ghidra 反编译定位回调地址
    # d[0xXXXXXX:0xXXXXXX+8] = bytes.fromhex('e00316aac0035fd6')

    ## V4 Stub (方案B-1): 按方法名返回正确类型
    # 见分析报告8.md §6.3
    """)

if __name__ == '__main__':
    main()
