#!/usr/bin/env python3
"""Assemble the emulator cases (test/emu/cases.txt) with asl and write the test image and lists.

    emu_build.py <cases.txt> <outdir>          needs asl (Macro Assembler AS) on PATH or $ASL_BIN
    emu_build.py --image <words.txt> <out.bin>  words.txt -> raw image (3-byte little-endian words)

cases.txt:
    case <name> [modulo]       start of a case; 'modulo' runs it in DSP56300:LE:24:modulo
    init <item,item,...>       register/memory state before (reg=hex, x:addr=hex, y:..., p:..., ss:...)
    expect <item,...>          state at the stop address, worked out by hand from the Family Manual
    <tab> asm line             code; '@name' is a label local to the case; the case stops at its
                               end, or at '@done' if the code defines it

asl is used only to encode the code (a black box); the expected values are hand-computed.
Writes <outdir>/words.txt ("<addr> <word>" in hex, the assembled image) and
<outdir>/tests-default.txt, tests-modulo.txt (EmuCheck.java input).
"""
import os
import re
import subprocess
import sys
import tempfile


def image(words_txt, out_bin):
    mem = {}
    for line in open(words_txt):
        if line.strip():
            a, w = line.split()
            mem[int(a, 16)] = int(w, 16)
    top = max(mem) + 1
    with open(out_bin, "wb") as f:
        for a in range(top):
            f.write(mem.get(a, 0).to_bytes(3, "little"))


def main():
    if sys.argv[1] == "--image":
        image(sys.argv[2], sys.argv[3])
        return
    src, outdir = sys.argv[1], sys.argv[2]
    cases = []
    cur = None
    for line in open(src):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0] in " \t@":
            cur["code"].append(line.strip())
            continue
        kw, _, rest = line.strip().partition(" ")
        if kw == "case":
            p = rest.split()
            cur = {"name": p[0], "lang": "modulo" if "modulo" in p[1:] else "default",
                   "init": "-", "expect": "-", "code": []}
            cases.append(cur)
        elif kw in ("init", "expect"):
            cur[kw] = rest.replace(" ", "")
        else:
            sys.exit("bad line: " + line)
    asm = ["\tcpu\t56300"]
    for k, c in enumerate(cases):
        pre = "c%d_" % k
        asm.append("\torg\t$%x" % (0x100 * (k + 1)))
        asm.append("%sstart_:" % pre)
        for l in c["code"]:
            l = re.sub(r"@(\w+)", lambda m: pre + m.group(1), l)
            if re.match(r"^\w+:$", l):
                asm.append(l)
            else:
                asm.append("\t" + l)
        asm.append("%send_:" % pre)
    asl = os.environ.get("ASL_BIN", "")
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "e.asm"), "w").write("\n".join(asm) + "\n")
        r = subprocess.run([os.path.join(asl, "asl") if asl else "asl", "-L", "-q", "-U", "e.asm"],
                           cwd=d, capture_output=True, text=True)
        lst = open(os.path.join(d, "e.lst"), errors="replace").read() if os.path.exists(
            os.path.join(d, "e.lst")) else ""
        if r.returncode:
            sys.exit("asl failed:\n" + r.stdout + r.stderr + "\n".join(
                l for l in lst.splitlines() if "rror" in l))
    words = {}
    syms = {}
    for l in lst.splitlines():
        # asl lists a negative extension word with 8 digits (FFFFF000): keep the 24-bit word
        m = re.match(r"^\s*\d+/\s*([0-9A-F]+) : ((?:[0-9A-F]{6,8} ?)+)\s", l + " ")
        if m:
            a = int(m.group(1), 16)
            for i, w in enumerate(m.group(2).split()):
                words[a + i] = int(w, 16) & 0xffffff
        m = re.match(r"^\s*\d+/\s*([0-9A-F]+) : \s*(c\d+_\w+):", l)
        if m:
            syms[m.group(2).upper()] = int(m.group(1), 16)
    # the symbol table is the reliable source for label addresses
    for m in re.finditer(r"\b(C\d+_\w+) :\s+([0-9A-F]+) C", lst.upper()):
        syms[m.group(1)] = int(m.group(2), 16)
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "words.txt"), "w") as f:
        for a in sorted(words):
            f.write("%x %06x\n" % (a, words[a]))
    for lang in ("default", "modulo"):
        with open(os.path.join(outdir, "tests-%s.txt" % lang), "w") as f:
            for k, c in enumerate(cases):
                if c["lang"] != lang:
                    continue
                pre = "C%d_" % k
                stop = syms.get(pre + "DONE", syms[pre + "END_"])
                f.write("%s %x %x %s %s\n" % (c["name"], syms[pre + "START_"], stop, c["init"], c["expect"]))
    print("emu_build: %d cases, %d words" % (len(cases), len(words)))


if __name__ == "__main__":
    main()
