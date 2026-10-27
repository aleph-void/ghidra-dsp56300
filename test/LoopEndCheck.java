// Checks the module's DSP56300 Loop End analyzer: for each "<do-addr>" (hex word address) of the
// image, disassembles the DO/DOR there, runs the analyzer, and checks that the instruction holding
// the loop's last word (LA) branches back to the loop top in its p-code.
// Script args: <outfile> <do-addr>...    Output: PASS/FAIL lines and a count.
//@category Testing

import java.io.PrintStream;

import ghidra.app.plugin.core.analysis.DSP56300LoopEndAnalyzer;
import ghidra.app.script.GhidraScript;
import ghidra.app.util.importer.MessageLog;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.address.AddressSpace;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.pcode.PcodeOp;

public class LoopEndCheck extends GhidraScript {

	@Override
	protected void run() throws Exception {
		String[] args = getScriptArgs();
		AddressSpace p = currentProgram.getAddressFactory().getDefaultAddressSpace();
		int pass = 0, fail = 0;
		try (PrintStream out = new PrintStream(args[0])) {
			for (int k = 1; k < args.length; k++) {
				Address a = p.getTruncatedAddress(Long.parseLong(args[k], 16), true);
				disassemble(a);
				new DSP56300LoopEndAnalyzer().added(currentProgram,
					new AddressSet(currentProgram.getMemory()), monitor, new MessageLog());
				Instruction d = getInstructionAt(a);
				// LA = the DO's extension word (DO) or DO address + displacement (DOR)
				byte[] b = new byte[3];
				currentProgram.getMemory().getBytes(a.add(3), b);
				long v = (b[0] & 0xffL) | (b[1] & 0xffL) << 8 | (b[2] & 0xffL) << 16;
				long la = d.getMnemonicString().equals("dor") ? (args[k].isEmpty() ? 0
						: (Long.parseLong(args[k], 16) + ((v << 40) >> 40)) & 0xffffff) : v;
				Instruction last = currentProgram.getListing()
						.getInstructionContaining(p.getTruncatedAddress(la, true));
				long top = Long.parseLong(args[k], 16) + 2;
				boolean ok = false;
				if (last != null) {
					for (PcodeOp op : last.getPcode()) {
						if ((op.getOpcode() == PcodeOp.BRANCH || op.getOpcode() == PcodeOp.CBRANCH) &&
							op.getInput(0).getAddress().getAddressSpace() == p &&
							op.getInput(0).getAddress().getAddressableWordOffset() == top) {
							ok = true;
						}
					}
				}
				out.printf("%s loop at %s: last instruction %s %s%n", ok ? "PASS" : "FAIL", a,
					last == null ? "none" : last.getAddress(), last == null ? "" : last.toString());
				if (ok) {
					pass++;
				}
				else {
					fail++;
				}
			}
			out.printf("loop-end analyzer: %d passed, %d failed%n", pass, fail);
		}
	}
}
