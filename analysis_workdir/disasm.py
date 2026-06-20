#!/usr/bin/env python3
"""Annotated ARM64 disassembler for ppcat libapp.so (Dart AOT, bare-instructions).
vaddr == file offset. Recognizes: prologue, BL/B/BLR, PP(X27)-relative pool loads,
canonical bool returns, Thread(X26)/shadow-stack(X15) idioms.
Usage: disasm.py <hex_offset> [count]   or   disasm.py func <hex_offset>
"""
import sys, json
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

PATH = '/root/ppcat_repo/libapp.so'
with open(PATH,'rb') as f: DATA=f.read()
POOL = json.load(open('/root/ppcat_repo/analysis_workdir/pool_deserialized.json'))
ENTRIES = POOL['entries']           # list of {idx,type,val,eb,off}
# slot index -> entry
BY_IDX = {e['idx']:e for e in ENTRIES}
BY_REF = {int(k):v for k,v in POOL['by_ref'].items()}  # ref -> [idx, off]
XREF = json.load(open('/root/ppcat_repo/analysis_workdir/xref_db.json'))  # dec str -> info
# reverse: dec addr -> function info
PROLOGUE = bytes.fromhex('fd79bfa9fd030faa')

md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
md.detail = True

REGN = {0:'x0',27:'x27(PP)',26:'x26(Th)',22:'x22(null)',28:'x28(heap)',15:'x15(sstk)',29:'x29',30:'x30(lr)'}
def rn(r):
    if r in REGN: return REGN[r]
    return ('x%d'%r) if r<31 else 'sp'

def pool_at_off(off):
    # off is byte offset into pool (slot_index*8). return slot entry if present
    for e in ENTRIES:
        if e['idx']*8 == off:
            return e
    return None

def annot(insn):
    m=insn.mnemonic; op=insn.op_str; a=[]
    # BL / B
    if m in ('bl','b','cbz','cbnz','tbz','tbnz') and insn.operands:
        # last operand often imm
        for o in insn.operands:
            if o.type==2:  # imm
                tgt=o.imm & 0xffffffff
                info=XREF.get(str(tgt))
                tag=''
                if info:
                    cs=info.get('callers',[])
                    ss=info.get('strs',[])
                    tag=f'  -> f@0x{tgt:x} callers={len(cs)} strs={[s[:24] for s in ss[:2]]}'
                    if info.get('bool_ret'): tag+=' [bool]'
                else:
                    # check prologue at tgt
                    if DATA[tgt:tgt+8]==PROLOGUE: tag=f'  -> f@0x{tgt:x} (prologue)'
                    else: tag=f'  -> 0x{tgt:x}'
                a.append(tag)
                break
    # PP-relative load: ldr/ldr xN,[x27,#imm]
    if m.startswith('ldr') and 'x27' in op:
        for o in insn.operands:
            if o.type==3 and o.mem.base==27 and o.mem.disp is not None:  # mem
                sloto=o.mem.disp
                if sloto%8==0:
                    e=pool_at_off(sloto)
                    if e:
                        a.append(f'  POOL[slot0x{sloto//8:x}=ref{e["val"]} t{e["type"]}]')
                break
    # add xN, x27, #imm  (PP offset arithmetic)
    if m=='add' and 'x27' in op:
        for o in insn.operands:
            if o.type==2 and o.imm is not None:
                # check if it's a pool slot offset
                if 0 < o.imm < len(ENTRIES)*8 and o.imm%8==0:
                    e=pool_at_off(o.imm)
                    if e: a.append(f'  PP+0x{o.imm:x}=POOL[slot0x{o.imm//8:x}=ref{e["val"]} t{e["type"]}]')
                break
    # canonical bool
    if m=='add' and 'x22, #' in op and (', #0x30' in op or ', #0x20' in op or '#48' in op or '#32' in op):
        a.append('  CANON-BOOL '+('TRUE' if ('0x30' in op or '48' in op) else 'FALSE'))
    return ''.join(a)

def dump(start, count=120):
    start=int(start,16) if isinstance(start,str) else start
    for insn in md.disasm(DATA[start:start+count*4], start):
        extra=annot(insn)
        pl = '* ' if DATA[insn.address:insn.address+8]==PROLOGUE and insn.address!=start else '  '
        print(f'{pl}0x{insn.address:x}: {insn.bytes.hex():<10} {insn.mnemonic:<7} {insn.op_str}{extra}')
        if insn.mnemonic=='ret':
            # peek: stop a bit after ret
            pass

def func(start):
    start=int(start,16) if isinstance(start,str) else start
    print(f'=== FUNCTION @ 0x{start:x} ===')
    n=0
    for insn in md.disasm(DATA[start:start+2000], start):
        extra=annot(insn)
        pl = '*P' if (DATA[insn.address:insn.address+8]==PROLOGUE and insn.address!=start) else '  '
        print(f'{pl}0x{insn.address:x}: {insn.bytes.hex():<10} {insn.mnemonic:<7} {insn.op_str}{extra}')
        n+=1
        if insn.mnemonic=='ret' and n>3:
            # one ret usually ends dart func; but confirm next isn't same func tail. stop after ret+peek
            break
        if n>400: print('...truncated'); break

if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='func':
        func(sys.argv[2])
    else:
        dump(sys.argv[1], int(sys.argv[2]) if len(sys.argv)>2 else 120)
