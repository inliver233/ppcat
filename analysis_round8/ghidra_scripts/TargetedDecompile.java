import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileOptions;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.decompiler.component.DecompilerUtils;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.SourceType;

public class TargetedDecompile extends GhidraScript {
    private static final long[] TARGETS = {
        0x920d7cL, 0xae71bcL, 0xb68234L, 0x913bf8L, 0xbc0f40L, 0xbd5a24L
    };
    private static final long[] NEXT_PROLOGUES = {
        0x921324L, 0xae7e00L, 0xb68308L, 0x914ffcL, 0xbc127cL, 0xbd6354L
    };

    private DecompInterface setupDecompiler() {
        DecompileOptions options = DecompilerUtils.getDecompileOptions(state.getTool(), currentProgram);
        DecompInterface decomp = new DecompInterface();
        decomp.setOptions(options);
        decomp.toggleCCode(true);
        decomp.toggleSyntaxTree(true);
        decomp.setSimplificationStyle("decompile");
        decomp.openProgram(currentProgram);
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

    private void decompile(DecompInterface decomp, long startOff) {
        Address start = toAddr(startOff);
        Function fn = getFunctionAt(start);
        println(String.format("decompile target 0x%x fn=%s", startOff, fn == null ? "null" : fn.getEntryPoint()));
        if (fn == null) {
            return;
        }
        DecompileResults res = decomp.decompileFunction(fn, 60, monitor);
        println("completed=" + res.decompileCompleted());
        if (res.decompileCompleted() && res.getDecompiledFunction() != null) {
            String[] lines = res.getDecompiledFunction().getC().split("\\R");
            for (int i = 0; i < Math.min(lines.length, 40); i++) {
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
            decompile(decomp, target);
        }
        decomp.dispose();
    }
}
