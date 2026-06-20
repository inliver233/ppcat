import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.address.Address;

public class SmokeRefs extends GhidraScript {
    @Override
    protected void run() throws Exception {
        println("program=" + currentProgram.getName());
        Address addr = toAddr("0xb9fc84");
        Function fn = getFunctionAt(addr);
        println("function@0xb9fc84=" + (fn == null ? "null" : fn.getName()));
        Reference[] refs = getReferencesTo(addr);
        for (Reference ref : refs) {
            println("xref -> " + ref.getFromAddress());
        }
    }
}
