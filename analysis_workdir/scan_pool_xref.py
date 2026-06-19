#!/usr/bin/env python3
"""
Scan friend's asm.txt and build a map of pool slot offsets accessed at each PC.

Pattern 1 (most common):
  ADD X16, X27, #N, LSL #12     # X16 = X27 + N*4096
  LDR X16, [X16, #M]             # X16 = pool[N*4096 + M]
  
Pattern 2:
  ADD X17, X27, #N, LSL #12
  LDR X17, [X17, #M]

Pattern 3 (direct, less common):
  LDR X16, [X27, #M]             # X16 = pool[M]

Output: list of (pc, pool_offset, instr_text) for every pool access.
"""
import re
import sys

ADD_RE = re.compile(r'^0x([0-9a-f]+)\s+([0-9a-f ]+)\s+ADD\s+(X\d+),\s*(X\d+),\s*#(0x[0-9a-f]+|\d+),\s*LSL\s*#(\d+)')
LDR_RE = re.compile(r'^0x([0-9a-f]+)\s+([0-9a-f ]+)\s+LDR\s+(X\d+),\s*\[(X\d+)(?:,#(\d+))?\]')
LDR_X27_RE = re.compile(r'^0x([0-9a-f]+)\s+([0-9a-f ]+)\s+LDR\s+(X\d+),\s*\[X27(?:,#(\d+))?\]')

def main(asm_path, output_path):
    # Track: reg -> base_offset from X27
    reg_state = {}  # 'X16' -> 0x5000 etc, or 'X27' -> 0
    
    accesses = []  # list of (pc, pool_offset, full_line)
    
    with open(asm_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.rstrip()
            
            # Try ADD Xn, X27, #N, LSL #M
            m = ADD_RE.match(line)
            if m:
                pc = int(m.group(1), 16)
                dst = m.group(3)
                src = m.group(4)
                val_str = m.group(5)
                shift = int(m.group(6))
                if src == 'X27':
                    val = int(val_str, 0)
                    add_val = val << shift
                    reg_state[dst] = add_val
                else:
                    # Not pool-related, invalidate dst
                    reg_state.pop(dst, None)
                continue
            
            # Try LDR Xn, [Xm, #imm]
            m = LDR_RE.match(line)
            if m:
                pc = int(m.group(1), 16)
                dst = m.group(3)
                src = m.group(4)
                imm_str = m.group(5)
                imm = int(imm_str) if imm_str else 0
                
                if src == 'X27':
                    # Direct pool access
                    accesses.append((pc, imm, line))
                    reg_state.pop(dst, None)
                elif src in reg_state:
                    base = reg_state[src]
                    accesses.append((pc, base + imm, line))
                    reg_state.pop(dst, None)
                else:
                    reg_state.pop(dst, None)
                continue
            
            # Any other instruction that writes to a tracked register invalidates it
            # This is simplified - we should detect "destination register"
            # For now, just check if line starts with a known write pattern
            m_write = re.match(r'^0x[0-9a-f]+\s+[0-9a-f ]+\s+([A-Z]+\d?)\s+(X\d+),', line)
            if m_write:
                dst = m_write.group(2)
                # Only invalidate if it's not ADD X.., X27 (handled above) or LDR (handled above)
                mnem = m_write.group(1)
                if mnem != 'ADD' and mnem != 'LDR' and mnem != 'STR':
                    reg_state.pop(dst, None)
            # STR also invalidates since it doesn't write back
    
    print(f'Total pool accesses found: {len(accesses)}')
    
    # Write to output
    with open(output_path, 'w') as out:
        out.write(f'# Pool access map\n')
        out.write(f'# Total: {len(accesses)} accesses\n')
        out.write(f'# Format: pc  pool_offset  full_line\n\n')
        for pc, off, line in accesses:
            out.write(f'0x{pc:08x}  0x{off:06x}  {line}\n')
    
    return accesses

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
