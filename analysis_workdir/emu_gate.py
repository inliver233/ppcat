#!/usr/bin/env python3
"""Unicorn emulation of Dart AOT gate 0x911788 — ARM-native empirical analysis.
Map real libapp.so .text, hook Dart-runtime BL calls (return controlled x0),
mock Thread/Pool/null-sentinel, observe the CSEL return path empirically.

Honest scope: Dart AOT funcs are heap-dependent (pool reads return live object ptrs).
We HOOK all BL (skip Dart runtime stubs) and mock X22/X26/X27/X28. We cannot get a
"true" business-logic result, but we CAN observe CONTROL FLOW: which branch the real
code takes through 0x911788 for given mocked inputs — empirically confirming the
canonical-bool return convention (add x,x22,#0x20 vs #0x30) that static analysis inferred.
"""
import sys
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED
from unicorn.arm64_const import UC_ARM64_REG_X0,UC_ARM64_REG_X15,UC_ARM64_REG_X16,UC_ARM64_REG_X17,UC_ARM64_REG_X21,UC_ARM64_REG_X22,UC_ARM64_REG_X26,UC_ARM64_REG_X27,UC_ARM64_REG_X28,UC_ARM64_REG_X29,UC_ARM64_REG_PC,UC_ARM64_REG_SP,UC_ARM64_REG_X30

d=open('libapp.so','rb').read()
TEXT=0x460000; TEXTLEN=0xf98398-TEXT   # .text-ish region

BASE_MEM=0x10000000
STACK=BASE_MEM+0x100000
STACK_SIZE=0x40000
MOCK_THREAD=BASE_MEM+0x200000
MOCK_POOL =BASE_MEM+0x300000
NULL_SENTINEL=BASE_MEM+0x400000   # X22 base; True=NULL+0x30, False=NULL+0x20

uc=Uc(UC_ARCH_ARM64, UC_MODE_ARM)
# map .text at its real vaddr (file offset==vaddr). libapp .text starts 0x460000.
uc.mem_map(0x400000, 0x1000000)   # covers 0x400000..0x1400000 (incl .text 0x460000+)
uc.mem_write(TEXT, d[TEXT:TEXT+min(TEXTLEN,0x1000000-(TEXT-0x400000))])
# stack / mock regions
for base,sz in [(BASE_MEM,0x100000),(STACK,sz) if False else (STACK,STACK_SIZE),(MOCK_THREAD,0x1000),(MOCK_POOL,0x1000)]:
    pass
uc.mem_map(BASE_MEM, 0x600000)   # one big chunk for stack+thread+pool+null
uc.mem_write(BASE_MEM, b'\x00'*0x600000)

GATE=0x911788
# Track BL hooks: skip Dart runtime calls, set x0 to controlled value
bl_count=[0]
ret_log=[]
def hook_code(uc, addr, size, ud):
    inst=int.from_bytes(uc.mem_read(addr,4),'little')
    # BL: 0x94000000 | imm26
    if (inst & 0xFC000000)==0x94000000:
        bl_count[0]+=1
        # skip the BL: emulate as x0 = NULL_SENTINEL+0x30 (mock "true"/valid) and continue past it
        uc.reg_write(UC_ARM64_REG_X0, NULL_SENTINEL+0x30)
        uc.reg_write(UC_ARM64_REG_PC, addr+4)
        return
    # RET: stop
    if inst==0xd65f03c0:
        x0=uc.reg_read(UC_ARM64_REG_X0)
        ret_log.append((addr,'RET x0=0x%x'%x0))
        uc.emu_stop()
    # B (unconditional): let unicorn handle (it does)
def hook_unmapped(uc, access, addr, size, value, ud):
    # any unmapped read/write in mocked regions: return 0 (already zeroed). For thread/pool reads just allow.
    print('  UNMAPPED access @0x%x size %d (pc=0x%x)'%(addr,size,uc.reg_read(UC_ARM64_REG_PC)))
    return False  # stop on truly unmapped

uc.hook_add(UC_HOOK_CODE, hook_code)
uc.hook_add(UC_HOOK_MEM_UNMAPPED, hook_unmapped)

# setup registers
uc.reg_write(UC_ARM64_REG_X15, STACK+STACK_SIZE-0x100)   # shadow stack
uc.reg_write(UC_ARM64_REG_X29, STACK+STACK_SIZE-0x200)   # frame
uc.reg_write(UC_ARM64_REG_X22, NULL_SENTINEL)            # null sentinel; True=+0x30 False=+0x20
uc.reg_write(UC_ARM64_REG_X26, MOCK_THREAD)              # Thread
uc.reg_write(UC_ARM64_REG_X27, MOCK_POOL)                # Pool/PP
uc.reg_write(UC_ARM64_REG_X28, 0)                        # heap base
uc.reg_write(UC_ARM64_REG_X21, MOCK_POOL)                # object store (used by BLR x30 dispatch)
# mock thread store: [X26+0x80] -> a sub-object
uc.mem_write(MOCK_THREAD+0x80, (MOCK_THREAD+0x800).to_bytes(8,'little'))
# args (x0..x4): the gate takes (param1..param5). give null-ish.
for r in (UC_ARM64_REG_X0,):
    uc.reg_write(r, NULL_SENTINEL+0x20)

print('Emulating gate 0x%x with BL-hooked (mock runtime)...'%GATE)
try:
    uc.emu_start(GATE, GATE+0x400, count=2000)
except Exception as e:
    print('  emu exception:', e)
pc=uc.reg_read(UC_ARM64_REG_PC)
x0=uc.reg_read(UC_ARM64_REG_X0)
print('  stopped at PC=0x%x  X0=0x%x'%(pc,x0))
print('  BL calls hooked:', bl_count[0])
print('  return log:', ret_log)
print('  X0 relative to NULL_SENTINEL: +0x%x  (0x20=False, 0x30=True)'%(x0-NULL_SENTINEL if x0>=NULL_SENTINEL else -1))
print('  (note: with mocked/null inputs + BL->true, this shows control-flow reachability,')
print('   not a real business result — Dart heap not present)')
