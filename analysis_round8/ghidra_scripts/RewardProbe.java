import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileOptions;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.decompiler.component.DecompilerUtils;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.symbol.SourceType;

public class RewardProbe extends GhidraScript {
    private static final long[] TARGETS = {
        0x8758bcL, // ad dispatcher
        0x8920d0L, // reward config / cheat string hit inside
        0x88aaccL, // onReward entry
        0x8cf36cL, // reward privilege status machine
        0xaa5848L  // hidden test panel
    };

    private static final long[] NEXT_PROLOGUES = {
        0x876154L,
        0x8927c0L,
        0x88aeccL,
        0x8cf8f0L,
        0xaa65f8L
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

    private void createWithBody(long startOff, long nextOff) throws Exception {
        Address start = toAddr(startOff);
        Address end = toAddr(nextOff).subtract(4);
        AddressSet body = new AddressSet(start, end);
        disassemble(start);
        Function fn = currentProgram.getListing().createFunction(null, start, body, SourceType.USER_DEFINED);
        println(String.format("create 0x%x..0x%x -> %s", startOff, end.getOffset(), fn == null ? "null" : fn.getEntryPoint()));
    }

    private void dumpWindow(long startOff) {
        Address start = toAddr(startOff);
        Address begin = start.subtract(0x20);
        Address end = start.add(0x80);
        println(String.format("window target=0x%x", startOff));
        Instruction inst = getInstructionAt(begin);
        if (inst == null) {
            inst = getInstructionAfter(begin);
        }
        while (inst != null && inst.getAddress().compareTo(end) <= 0) {
            println(String.format("  %s: %s %s", inst.getAddress(), inst.getMnemonicString(), inst));
            inst = inst.getNext();
        }
    }

    private void decompile(DecompInterface decomp, long startOff) {
        Address start = toAddr(startOff);
        Function fn = getFunctionAt(start);
        println(String.format("decompile target 0x%x fn=%s", startOff, fn == null ? "null" : fn.getEntryPoint()));
        if (fn == null) {
            return;
        }
        DecompileResults res = decomp.decompileFunction(fn, 60, monitor);
        println("completed=" + res.decompileCompleted() + " message=" + decomp.getLastMessage());
        if (res.decompileCompleted() && res.getDecompiledFunction() != null) {
            String[] lines = res.getDecompiledFunction().getC().split("\\R");
            for (int i = 0; i < Math.min(lines.length, 80); i++) {
                println(lines[i]);
            }
        }
    }

    @Override
    protected void run() throws Exception {
        println("program=" + currentProgram.getName());
        for (int i = 0; i < TARGETS.length; i++) {
            createWithBody(TARGETS[i], NEXT_PROLOGUES[i]);
        }
        DecompInterface decomp = setupDecompiler();
        for (long target : TARGETS) {
            println("====");
            dumpWindow(target);
            decompile(decomp, target);
        }
        decomp.dispose();
    }
}
