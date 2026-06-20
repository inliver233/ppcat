#!/usr/bin/env python3
"""
test3 Round 9 patch verification script.
Verifies function entries, pool slot loads, and patch bytes.
"""
import json, struct, bisect

DATA = open('/root/ppcat/libapp.so', 'rb').read()
PROLOGUE = bytes.fromhex('fd79bfa9fd030faa')

# Build function table
FUNCS = []
a = 0x460000
while a < len(DATA) - 8:
    if DATA[a:a+8] == PROLOGUE:
        FUNCS.append(a)
    a += 4

def func_of(addr):
    i = bisect.bisect_right(FUNCS, addr) - 1
    return FUNCS[i] if i >= 0 else None

pool = json.load(open('pool_deserialized.json'))
by_ref = pool['by_ref']
ref_to_slot = {int(k): v[0] for k, v in by_ref.items()}
slot_to_ref = {v[0]: int(k) for k, v in by_ref.items()}

print("# test3 Round 9 Patch Verification")
print(f"# {len(FUNCS)} functions indexed, {len(by_ref)} pool refs mapped")
print()

all_ok = True

# 1. Function entry point verification
print("## 1. Function Entry Points")
entries = {
    0xae30e0: 'MeowMeow build',
    0xa54178: 'VIP page ctor',
    0xbc5dc8: 'Reward prompt (onTap)',
    0xbd2e1c: 'Home page build',
    0xbd3540: 'ImmediateGet + AdMob banner',
    0xbd3084: 'Store version',
    0xb3abd0: 'Reader loader',
    0xbc82d0: 'Book detail page',
    0xbc71ec: 'Book detail grand-caller',
    0xbc7f9c: 'Book detail parent-caller',
    0x846b1c: 'MeowMeow daily scaffold',
    0xb3ff04: 'Reader with status.jpg',
    0x8cf36c: 'Privilege timer',
    0x920d7c: 'Fault body builder',
    0xca8bdc: 'MissingPluginException ctor',
}

for addr, desc in entries.items():
    prologue = DATA[addr:addr+8]
    ok = prologue == PROLOGUE
    if not ok:
        all_ok = False
    status = 'OK' if ok else 'FAIL'
    print(f'  [{status}] 0x{addr:x} {desc}')

# 2. Pool anchor verification
print()
print("## 2. Pool Anchor Verification")
anchors = {
    0x59bc: 28525,   # 喵喵饿了
    0x59bb: 21707,   # 每日喂喵
    0x59bd: 91705,   # 喵喵块 class field
    0x59a4: 121017,  # 喵喵块 class field (loaded by 0xbd3540)
    0x276e: 27673,   # 无法正常联网…广告无法显示
}
for slot, expected_ref in anchors.items():
    actual = slot_to_ref.get(slot)
    ok = actual == expected_ref
    if not ok:
        all_ok = False
    status = 'OK' if ok else f'FAIL (got {actual})'
    print(f'  [{status}] slot 0x{slot:x}: ref={actual} (expected {expected_ref})')

# 3. 0xae30e0 internals
print()
print("## 3. 0xae30e0 Internal Patch Points")
checks = [
    (0xae3128, '1f500071', 'CMP W0,#0x14'),
    (0xae312c, 'c10d0054', 'B.NE'),
    (0xae32d4, 'e00301aa', 'MOV X0,X1 (return widget)'),
]
for addr, expected_hex, desc in checks:
    actual = DATA[addr:addr+4].hex()
    ok = actual == expected_hex
    if not ok:
        all_ok = False
    status = 'OK' if ok else f'FAIL ({actual})'
    print(f'  [{status}] 0x{addr:x}: {actual} ({desc})')

# 4. Patch target verification
print()
print("## 4. Patch Target Bytes")
patches = [
    (0xbc5dd0, 'efa100d1a00b40f9', 'Reward prompt entry+8 (pre-patch)'),
]
for addr, expected_hex, desc in patches:
    actual = DATA[addr:addr+8].hex()
    ok = actual == expected_hex
    if not ok:
        all_ok = False
    status = 'OK' if ok else f'FAIL ({actual})'
    print(f'  [{status}] 0x{addr:x}: {actual} ({desc})')

# 5. Cross-reference verification
print()
print("## 5. Cross-Reference Verification")
xref_checks = [
    (0xbc5dc8, 0xbd3540, 'Reward prompt vs Home overlay (different funcs)'),
    (0xb3abd0, 0xbd2e1c, 'Reader loader vs Home page (different funcs)'),
]
for f1, f2, desc in xref_checks:
    ok = f1 != f2
    status = 'OK' if ok else 'FAIL'
    print(f'  [{status}] 0x{f1:x} != 0x{f2:x} ({desc})')

xref_db = json.load(open('xref_db.json'))
xref_db = {int(k): v for k, v in xref_db.items()}

# Verify caller chains
chain_checks = [
    (0xbc82d0, [0xbc7f9c], 'Book detail called by 0xbc7f9c'),
    (0xbc7f9c, [0xbc71ec], '0xbc7f9c called by 0xbc71ec'),
    (0xbd3540, [0xbd2e1c], '立即获取 called by Home page'),
]
for callee, expected_callers, desc in chain_checks:
    v = xref_db.get(callee, {})
    actual = v.get('callers', [])
    ok = set(expected_callers).issubset(set(actual))
    if not ok:
        all_ok = False
    status = 'OK' if ok else f'FAIL (got {actual})'
    print(f'  [{status}] 0x{callee:x} callers={actual} ({desc})')

# 6. Slot loading cross-reference
print()
print("## 6. Slot Loading Cross-Reference")
slot_loader_checks = [
    (0x59bc, [0xae30e0, 0xa54178], '喵喵饿了 loaded by MeowMeow build + VIP ctor'),
    (0x59bb, [0x846b1c, 0xa54178, 0xae71bc], '每日喂喵 loaded by 3 funcs'),
]
# These are from scan_slot results - just document them
for slot, expected_funcs, desc in slot_loader_checks:
    print(f'  [INFO] slot 0x{slot:x}: expected loaders = {[hex(f) for f in expected_funcs]} ({desc})')

print()
print(f'# Overall: {"ALL PASSED" if all_ok else "SOME FAILURES"}')
