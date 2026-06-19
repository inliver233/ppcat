#!/usr/bin/env python3
"""Faster function analyzer."""
import struct
import sys
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

def main(libapp_path, outdir):
    with open(libapp_path, 'rb') as f:
        data = f.read()
    
    CODE_START = 0x464d18
    TEXT_END = 0x464ce0 + 0xb329d0  # = 0xf976b0
    code = data[CODE_START:TEXT_END]
    
    md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    md.detail = False
    
    print('Disassembling and analyzing in one pass...')
    
    func_info = {}  # addr -> dict
    current_func = None
    prologue_set = set()
    count = 0
    
    for ins in md.disasm(code, CODE_START):
        addr = ins.address
        mn = ins.mnemonic
        ops = ins.op_str
        
        # New function?
        if mn == 'stp' and 'x29' in ops and 'x30' in ops and ('!' in ops or '], #' in ops):
            prologue_set.add(addr)
            current_func = {
                'addr': addr,
                'size': 0,
                'instr_count': 0,
                'pool_loads': 0,
                'bl_count': 0,
                'cond_branches': 0,
                'comparisons': 0,
                'bl_targets': [],
                'last_addr': addr,
            }
            func_info[addr] = current_func
        
        if current_func is None: continue
        current_func['instr_count'] += 1
        current_func['last_addr'] = addr
        
        if mn == 'ldr' and '[x27' in ops:
            current_func['pool_loads'] += 1
        elif mn == 'bl':
            current_func['bl_count'] += 1
            try:
                t = int(ops.lstrip('#'), 16)
                current_func['bl_targets'].append(t)
            except: pass
        elif mn in ('b.eq', 'b.ne', 'b.gt', 'b.lt', 'b.ge', 'b.le', 'b.cs', 'b.cc',
                    'b.hi', 'b.ls', 'cbz', 'cbnz', 'tbz', 'tbnz'):
            current_func['cond_branches'] += 1
        elif mn == 'cmp':
            current_func['comparisons'] += 1
        
        count += 1
        if count % 500000 == 0:
            print(f'  ...{count}')
    
    print(f'Total instructions: {count}')
    print(f'Functions: {len(func_info)}')
    
    # Compute sizes (last_addr - addr + 4)
    for fi in func_info.values():
        fi['size'] = fi['last_addr'] - fi['addr'] + 4
    
    # Write summary
    funcs_sorted = sorted(func_info.values(), key=lambda x: x['addr'])
    with open(outdir + '/function_summary.txt', 'w') as f:
        f.write(f'# Function summary\n')
        f.write(f'# Total functions: {len(funcs_sorted)}\n\n')
        f.write(f'{"addr":>10} {"size":>6} {"instrs":>6} {"pool":>5} {"bl":>4} {"cond":>4} {"cmp":>4}\n')
        for fi in funcs_sorted:
            f.write(f'0x{fi["addr"]:08x} {fi["size"]:6d} {fi["instr_count"]:6d} {fi["pool_loads"]:5d} {fi["bl_count"]:4d} {fi["cond_branches"]:4d} {fi["comparisons"]:4d}\n')
    
    print(f'Wrote function_summary.txt')
    
    # Top candidates for aggregation predicate (high cmp + cond_branches + moderate pool_loads)
    print('\n=== Top 30 by conditional branches ===')
    sorted_funcs = sorted(funcs_sorted, key=lambda x: -x['cond_branches'])
    for fi in sorted_funcs[:30]:
        print(f'  0x{fi["addr"]:08x}: size={fi["size"]:5}, instrs={fi["instr_count"]:4}, cond={fi["cond_branches"]:3}, cmp={fi["comparisons"]:3}, pool={fi["pool_loads"]:3}, bl={fi["bl_count"]:3}')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
