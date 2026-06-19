#!/usr/bin/env python3
"""
For each function, compute characteristics that may indicate its purpose:
- Number of pool loads (LDR from x27)
- Number of BL calls
- Number of conditional branches
- Function size
- Specific patterns: string compare, showDialog calls, etc.
"""
import struct
import sys
import re
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

def main(libapp_path, outdir):
    with open(libapp_path, 'rb') as f:
        data = f.read()
    
    CODE_START = 0x464d18
    TEXT_END = 0x464ce0 + 0xb329d0  # = 0xf976b0
    code = data[CODE_START:TEXT_END]
    
    md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    md.detail = True
    
    # First pass: find all prologues
    print('Finding prologues...')
    prologue_set = set()
    instructions = []  # list of (addr, mnem, ops)
    for ins in md.disasm(code, CODE_START):
        instructions.append((ins.address, ins.mnemonic, ins.op_str))
        if ins.mnemonic == 'stp' and 'x29' in ins.op_str and 'x30' in ins.op_str:
            if '!' in ins.op_str or '], #' in ins.op_str:
                prologue_set.add(ins.address)
    print(f'Instructions: {len(instructions)}, Prologues: {len(prologue_set)}')
    
    # Build function table: addr -> instruction index
    func_starts = sorted(prologue_set)
    func_starts.append(TEXT_END)  # sentinel
    
    # For each function, analyze
    print('Analyzing functions...')
    func_info = []  # list of dicts
    for i, start_addr in enumerate(func_starts[:-1]):
        end_addr = func_starts[i+1]
        size = end_addr - start_addr
        
        # Find instruction range
        start_idx = next((j for j, (a, _, _) in enumerate(instructions) if a == start_addr), None)
        if start_idx is None: continue
        end_idx = next((j for j in range(start_idx, len(instructions)) if instructions[j][0] >= end_addr), len(instructions))
        
        func_instrs = instructions[start_idx:end_idx]
        
        # Count patterns
        pool_loads = 0  # LDR xN, [x27, #imm]
        bl_count = 0
        cond_branches = 0  # B.cond, CBZ, CBNZ, TBZ, TBNZ
        str_cmps = 0  # patterns suggesting string compare (CMP with 0, conditional)
        comparisons = 0  # CMP instructions
        bl_targets = []
        
        for addr, mn, ops in func_instrs:
            if mn == 'ldr' and 'x27' in ops and '[' in ops:
                pool_loads += 1
            elif mn == 'bl':
                bl_count += 1
                try:
                    bl_targets.append(int(ops.lstrip('#'), 16))
                except: pass
            elif mn in ('b.eq', 'b.ne', 'b.gt', 'b.lt', 'b.ge', 'b.le', 'b.cs', 'b.cc', 'cbz', 'cbnz', 'tbz', 'tbnz'):
                cond_branches += 1
            elif mn == 'cmp':
                comparisons += 1
        
        func_info.append({
            'addr': start_addr,
            'size': size,
            'instr_count': len(func_instrs),
            'pool_loads': pool_loads,
            'bl_count': bl_count,
            'cond_branches': cond_branches,
            'comparisons': comparisons,
            'bl_targets': bl_targets,
        })
    
    print(f'Total functions analyzed: {len(func_info)}')
    
    # Output summary
    with open(outdir + '/function_summary.txt', 'w') as f:
        f.write(f'# Function summary\n')
        f.write(f'# Total functions: {len(func_info)}\n\n')
        f.write(f'{"addr":>10} {"size":>6} {"instrs":>6} {"pool":>5} {"bl":>4} {"cond":>4} {"cmp":>4}\n')
        for fi in func_info:
            f.write(f'0x{fi["addr"]:08x} {fi["size"]:6d} {fi["instr_count"]:6d} {fi["pool_loads"]:5d} {fi["bl_count"]:4d} {fi["cond_branches"]:4d} {fi["comparisons"]:4d}\n')
    
    print(f'Wrote function_summary.txt')
    
    # Find candidates for aggregation predicate (high cmp count + high cond_branches)
    print('\n=== Top 20 functions by conditional branches (aggregation predicate candidates) ===')
    sorted_by_cond = sorted(func_info, key=lambda x: (-x['cond_branches'], -x['comparisons']))
    for fi in sorted_by_cond[:20]:
        print(f'  0x{fi["addr"]:08x}: size={fi["size"]}, cond={fi["cond_branches"]}, cmp={fi["comparisons"]}, pool={fi["pool_loads"]}, bl={fi["bl_count"]}')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
