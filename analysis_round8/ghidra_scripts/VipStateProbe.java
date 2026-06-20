import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileOptions;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.decompiler.component.DecompilerUtils;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceManager;
import ghidra.program.model.symbol.ReferenceIterator;

public class VipStateProbe extends GhidraScript {
    private static final long[] TARGETS = {
        0x911788L, 0xb9fc84L, 0xa54178L, 0x8a0fd4L, 0x8ba3d0L, 0x67994cL
    };

    private DecompInterface setupDecompiler() {
        DecompileOptions options = DecompilerUtils.getDecompileOptions(state.getTool(), currentProgram);
        DecompInterface decomp = new DecompInterface();
        decomp.setOptions(options);
        decomp.toggleCCode(true);
        decomp.toggleSyntaxTree(true);
        decomp.setSimplificationStyle("decompile");
        if (!decomp.openProgram(currentProgram)) {
            println("decompiler open failed: " + decomp.getLastMessage());
        }
        return decomp;
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
        Function fn = getFunctionAt(addr);
        println(String.format("== target 0x%x fn=%s ==", value, fn == null ? "null" : fn.getEntryPoint()));
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

    private void createKnownFunction(long value) throws Exception {
        Address addr = toAddr(value);
        println(String.format("== create function 0x%x ==", value));
        boolean dis = disassemble(addr);
        println("  disassemble=" + dis);
        Function fn = createFunction(addr, null);
        println("  createFunction=" + (fn == null ? "null" : fn.getEntryPoint()));
    }

    private void decompileKnownFunction(DecompInterface decomp, long value) {
        Address addr = toAddr(value);
        Function fn = getFunctionAt(addr);
        if (fn == null) {
            println(String.format("== decompile 0x%x skipped (no function) ==", value));
            return;
        }
        DecompileResults res = decomp.decompileFunction(fn, 60, monitor);
        println(String.format("== decompile 0x%x completed=%s message=%s ==", value,
            res.decompileCompleted(), decomp.getLastMessage()));
        if (res.decompileCompleted() && res.getDecompiledFunction() != null) {
            String c = res.getDecompiledFunction().getC();
            if (c != null) {
                String[] lines = c.split("\\R");
                for (int i = 0; i < Math.min(lines.length, 20); i++) {
                    println("  " + lines[i]);
                }
            }
        }
    }

    @Override
    protected void run() throws Exception {
        println("program=" + currentProgram.getName());
        for (long target : TARGETS) {
            createKnownFunction(target);
        }
        DecompInterface decomp = setupDecompiler();
        for (long target : TARGETS) {
            dumpRefsTo(target);
            dumpWindow(target);
            decompileKnownFunction(decomp, target);
        }
        if (decomp != null) {
            decomp.dispose();
        }
    }
}
