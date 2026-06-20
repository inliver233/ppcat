import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceManager;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.program.flatapi.FlatProgramAPI;

public class VipStateProbe extends GhidraScript {
    private static final long[] TARGETS = {
        0x911788L, 0xb9fc84L, 0xa54178L, 0x8a0fd4L, 0x8ba3d0L, 0x67994cL
    };

    private Address findPrologue(Address around) {
        Address start;
        try {
            start = around.subtractNoWrap(0x8000);
        }
        catch (Exception e) {
            start = currentProgram.getMinAddress();
        }
        for (Address cur = around; cur.compareTo(start) >= 0; cur = cur.subtract(4)) {
            Instruction i1 = getInstructionAt(cur);
            Instruction i2 = getInstructionAt(cur.add(4));
            if (i1 == null || i2 == null) {
                continue;
            }
            if ("stp".equals(i1.getMnemonicString()) &&
                i1.toString().contains("x29,x30") &&
                "mov".equals(i2.getMnemonicString()) &&
                i2.toString().contains("x29,x15")) {
                return cur;
            }
        }
        return null;
    }

    private void dumpRefsTo(long value) {
        Address addr = toAddr(value);
        ReferenceManager rm = currentProgram.getReferenceManager();
        ReferenceIterator refs = rm.getReferencesTo(addr);
        int count = 0;
        while (refs.hasNext()) {
            refs.next();
            count++;
        }
        refs = rm.getReferencesTo(addr);
        println(String.format("== refs to 0x%x (%d) ==", value, count));
        while (refs.hasNext()) {
            Reference ref = refs.next();
            println("  " + ref.getFromAddress());
        }
    }

    private void dumpWindow(long value) {
        Address addr = toAddr(value);
        Address fn = findPrologue(addr);
        println(String.format("== target 0x%x fnStart=%s ==", value, fn));
        Address begin = addr.subtract(0x20);
        Address end = addr.add(0x40);
        Instruction inst = getInstructionAt(begin);
        if (inst == null) {
            inst = getInstructionAfter(begin);
        }
        while (inst != null && inst.getAddress().compareTo(end) <= 0) {
            println(String.format("  %s: %s %s", inst.getAddress(), inst.getMnemonicString(), inst));
            inst = inst.getNext();
        }
    }

    @Override
    protected void run() throws Exception {
        println("program=" + currentProgram.getName());
        for (long target : TARGETS) {
            dumpRefsTo(target);
            dumpWindow(target);
        }
    }
}
