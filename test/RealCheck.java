// Real-code check: run on a raw import (no analysis) of an assembled program.  Disassembles from
// every instruction address of the assembler listing (args[1], one hex word address per line),
// creates functions at the first listed address and at every call target, decompiles them all.
// Writes into <outdir>:
//   summary.txt  instructions, functions, bad-instruction and error bookmarks, decompile results
//   guided.txt   "<addr> <words> | <text>" for each listed address (asl_roundtrip.py items),
//                "<addr> BAD" where nothing decodes
// Script args: <outdir> <addrfile>
// Adapted from Ghidra-Rare's DSP56000 DspRealCheck.java (MIT).
//@category Testing

import java.io.File;
import java.io.PrintStream;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSpace;
import ghidra.program.model.listing.Bookmark;
import ghidra.program.model.listing.BookmarkType;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;

public class RealCheck extends GhidraScript {

	@Override
	protected void run() throws Exception {
		String[] args = getScriptArgs();
		File dir = new File(args[0]);
		dir.mkdirs();
		AddressSpace p = currentProgram.getAddressFactory().getDefaultAddressSpace();
		List<Address> addrs = new ArrayList<>();
		for (String line : Files.readAllLines(new File(args[1]).toPath())) {
			if (!line.isBlank()) {
				addrs.add(p.getTruncatedAddress(Long.parseLong(line.trim(), 16), true));
			}
		}
		for (Address a : addrs) {
			if (currentProgram.getListing().getInstructionAt(a) == null) {
				disassemble(a);
			}
		}
		List<Address> entries = new ArrayList<>();
		entries.add(addrs.get(0));
		for (Instruction ins : currentProgram.getListing().getInstructions(true)) {
			if (ins.getFlowType().isCall()) {
				for (Address t : ins.getFlows()) {
					entries.add(t);
				}
			}
		}
		for (Address e : entries) {
			if (getFunctionAt(e) == null && currentProgram.getListing().getInstructionAt(e) != null) {
				createFunction(e, null);
			}
		}
		int nins = 0;
		for (Instruction ins : currentProgram.getListing().getInstructions(true)) {
			nins++;
		}
		int bad = 0, err = 0;
		List<String> errs = new ArrayList<>();
		Iterator<Bookmark> it = currentProgram.getBookmarkManager().getBookmarksIterator();
		while (it.hasNext()) {
			Bookmark b = it.next();
			if (b.getTypeString().equals(BookmarkType.ERROR)) {
				err++;
				if (b.getCategory().contains("Bad Instruction")) {
					bad++;
				}
				errs.add(b.getAddress() + " " + b.getCategory() + ": " + b.getComment());
			}
		}
		int nf = 0, ok = 0, fail = 0, timeout = 0;
		List<String> failed = new ArrayList<>();
		DecompInterface dec = new DecompInterface();
		dec.openProgram(currentProgram);
		for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
			nf++;
			DecompileResults r = dec.decompileFunction(f, 60, monitor);
			if (r.decompileCompleted() && r.getDecompiledFunction() != null) {
				ok++;
			}
			else if (r.isTimedOut()) {
				timeout++;
				failed.add(f.getName() + " (timeout)");
			}
			else {
				fail++;
				failed.add(f.getName() + ": " + r.getErrorMessage());
			}
		}
		dec.dispose();
		try (PrintStream out = new PrintStream(new File(dir, "summary.txt"))) {
			out.printf("instructions %d, functions %d, bad-instruction bookmarks %d, error bookmarks %d%n",
				nins, nf, bad, err);
			out.printf("decompile: %d ok, %d failed, %d timed out%n", ok, fail, timeout);
			for (String s : failed) {
				out.println("  decompile " + s);
			}
			for (String s : errs) {
				out.println("  bookmark " + s);
			}
		}
		try (PrintStream out = new PrintStream(new File(dir, "guided.txt"))) {
			for (Address a : addrs) {
				Instruction ins = currentProgram.getListing().getInstructionAt(a);
				if (ins == null) {
					out.printf("%x BAD%n", a.getAddressableWordOffset());
					continue;
				}
				StringBuilder w = new StringBuilder();
				byte[] b = ins.getBytes();
				for (int i = 0; i < b.length; i += 3) {
					w.append(String.format(" %06x",
						(b[i] & 0xff) | (b[i + 1] & 0xff) << 8 | (b[i + 2] & 0xff) << 16));
				}
				out.printf("%x%s | %s%n", a.getAddressableWordOffset(), w, ins);
			}
		}
	}
}
