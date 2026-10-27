#!/usr/bin/env python3
"""Second, independent encoder check: re-assemble the module's disassembly with asl.

    asl_roundtrip.py <items.txt> <outprefix> [--summary]

items.txt: "<word-addr-hex> <word-hex> [<ext-hex>] | <module text>" per instruction (from
DumpSlots output via slots2items, or from RealCheck guided output).  Each instruction is assembled
at its own address ("org") with asl (Macro Assembler AS, run as a black box: $ASL_BIN or PATH) and
the words asl produces are compared with the original words.  Classes:
  same          asl encodes the module's text to the original word(s)
  alt-encoding  asl encodes it to other words that the module decodes to the same text (written
                to <outprefix>.alt for the caller to check by decoding them back)
  differ        asl encodes it to other words; the text means something else (a decode bug or an asl
                bug: listed in <outprefix>.differ)
  asl-rejects   asl does not accept the text (listed in <outprefix>.rejects with asl's message)
"""
import collections
import os
import re
import subprocess
import sys
import tempfile


def to_asl(t):
    """The module's text in asl's spelling (asl's syntax, not a change of meaning):
    asl writes no '<<' for I/O short addresses, no '#<'/'#>' except on MOVE, and the
    (+/-)S,#n,D multiplies with the constant 2^-n instead of n (as MAME prints them)."""
    m = re.match(r"^(mpy|mpyr|mac|macr)(\s+-?[xy][01]),#0x([0-9a-f]+),([ab])$", t)
    if m:
        t = "%s%s,#$%x,%s" % (m.group(1), m.group(2), 1 << (23 - int(m.group(3), 16)), m.group(4))
    t = re.sub(r"0x([0-9a-fA-F]+)", r"$\1", t)
    t = t.replace(":<<", ":")
    if not t.startswith("move "):
        t = t.replace("#<", "#").replace("#>", "#")
    else:
        t = t.replace("#<", "#")
    return t


def norm(t):
    return re.sub(r"[<>]", "", t)


def run_asl(lines):
    asl = os.environ.get("ASL_BIN", "")
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
        open(os.path.join(d, "r.asm"), "w").write("\n".join(lines) + "\n")
        subprocess.run([os.path.join(asl, "asl") if asl else "asl", "-L", "-q", "-U", "r.asm"],
                       cwd=d, capture_output=True, text=True)
        return open(os.path.join(d, "r.lst"), errors="replace").read()


def main():
    items = []
    for l in open(sys.argv[1]):
        if "|" not in l:
            continue
        head, text = l.rstrip("\n").split("|", 1)
        h = head.split()
        items.append((int(h[0], 16), [int(x, 16) for x in h[1:]], text.strip()))
    out = sys.argv[2]
    # one org + one instruction per item; source line numbers 2 + 2*i + 1 (1-based)
    lines = ["\tcpu\t56300"]
    for a, ws, t in items:
        lines.append("\torg\t$%x" % a)
        lines.append("\t" + to_asl(t))
    cnt = collections.Counter()
    bykind = collections.defaultdict(list)
    alt = []
    CH = 20000
    for c0 in range(0, len(items), CH):
        chunk = items[c0:c0 + CH]
        lst = run_asl(["\tcpu\t56300"] + [x for a, ws, t in chunk for x in ("\torg\t$%x" % a, "\t" + to_asl(t))])
        got, err = {}, {}
        last = None
        for l in lst.splitlines():
            m = re.match(r"^\s*(\d+)/\s*[0-9A-F]+ : ((?:[0-9A-F]{6,8} ?)*)", l)
            if m:
                last = int(m.group(1))
                if m.group(2).strip():
                    got[last] = [int(w, 16) & 0xffffff for w in m.group(2).split()]
                continue
            m = re.match(r"^> > >.*\((\d+)\)(?::\d+)?: error: (.*)$", l)
            if m:
                err[int(m.group(1))] = m.group(2)
        for i, (a, ws, t) in enumerate(chunk):
            ln = 2 + 2 * i + 1
            rec = "%06x %s | %s" % (a, " ".join("%06x" % w for w in ws), t)
            mn = t.split()[0] if t else "?"
            if ln in err or ln not in got:
                if re.match(r"^move .*\(r[0-7][+-]0x[0-9a-f]+\)", t) and len(ws) == 2:
                    cnt["asl-rejects: MOVE X/Y:(Rn+xxxx) with a register outside the data ALU "
                        "(asl limitation; manual: DDDDDD = all on-chip registers)"] += 1
                    continue
                if t.startswith("vsl "):
                    cnt["asl-rejects: VSL (asl does not implement it)"] += 1
                    continue
                cnt["asl-rejects"] += 1
                bykind["rejects"].append("%s || %s" % (rec, err.get(ln, "no output")))
                continue
            g = got[ln]
            if g == ws:
                cnt["same"] += 1
                continue
            cnt["other words"] += 1
            bykind["alt"].append("%s || %s" % (rec, " ".join("%06x" % w for w in g)))
            alt.append((a, g, t))
    for k in ("rejects", "alt"):
        with open(out + "." + k, "w") as f:
            f.write("\n".join(bykind[k]) + ("\n" if bykind[k] else ""))
    # the other-word encodings as a two-word-slot corpus for DumpSlots (classify step)
    with open(out + ".altimg", "wb") as f:
        for a, g, t in alt:
            for w in (g + [0])[:2]:
                f.write(w.to_bytes(3, "little"))
    with open(out + ".altlist", "w") as f:
        for a, g, t in alt:
            f.write("%x %s | %s\n" % (a, " ".join("%06x" % w for w in g), t))
    with open(out + ".summary", "w") as f:
        for k in sorted(cnt):
            f.write("%9d  %s\n" % (cnt[k], k))
    sys.stdout.write(open(out + ".summary").read())


def asl_bug(t, a, g):
    """Confirmed asl encoding bugs (checked against the Family Manual, see GHIDRA-RARE.md)."""
    m = re.match(r"^dor\s.*,0x([0-9a-f]+)$", t)
    if m and len(g) == 2 and g[1] == (int(m.group(1), 16) - 1) & 0xffffff:
        return "DOR extension word is the absolute LA (manual: PC + xxxx -> LA)"
    if re.match(r"^cmp (a,b|b,a)\b", t) and g[0] & 0xf7 == 0x15:
        return "CMP B/A,D encoded with JJJ = 001 (MAX/MAXM); manual Table 12-16: JJJ = 000"
    if re.match(r"^asl [abxy][01]?,[ab],[ab]$", t) and g[0] >> 5 == 0x0c1e << 3 | 1:
        return "ASL S1,S2,D encoded as NORMF (bits 7..5 = 001; manual: 010)"
    return None


def same_rel(t1, a1, t2, a2):
    """t1 decoded at a1 and t2 decoded at a2 differ only in PC-relative targets that keep their
    distance from the instruction (the classify image holds the words at other addresses)."""
    n1 = re.split(r"(0x[0-9a-f]+)", t1)
    n2 = re.split(r"(0x[0-9a-f]+)", t2)
    if len(n1) != len(n2):
        return False
    for x, y in zip(n1, n2):
        if x == y:
            continue
        if not (x.startswith("0x") and y.startswith("0x")):
            return False
        if (int(x, 16) - a1) & 0xffffff != (int(y, 16) - a2) & 0xffffff:
            return False
    return True


def classify(out, dump):
    """asl_roundtrip.py --classify <outprefix> <altimg DumpSlots output>: decode asl's other
    encodings with the module; the same instruction text (ignoring </> size forcing) means an
    alternative encoding of the same instruction, anything else is a real difference."""
    alt = [l.rstrip("\n") for l in open(out + ".altlist")]
    dec = {}
    for l in open(dump):
        p = l.rstrip("\n").split(" ", 2)
        dec[int(p[0])] = (int(p[1]), p[2] if len(p) > 2 else "")
    cnt = collections.Counter()
    bad = []
    for i, l in enumerate(alt):
        head, t = l.split(" | ", 1)
        g = head.split()[1:]
        ln, dt = dec.get(i, (0, ""))
        a0 = int(head.split()[0], 16)
        why = asl_bug(t, a0, [int(x, 16) for x in g])
        if ln == 3 * len(g) and (norm(dt) == norm(t) or same_rel(norm(t), a0, norm(dt), 2 * i)):
            cnt["same instruction, other encoding"] += 1
        elif why:
            cnt["asl bug: " + why] += 1
        else:
            cnt["differ"] += 1
            bad.append("%s || asl %s -> module %s" % (l, " ".join(g), dt or "invalid"))
    with open(out + ".differ", "w") as f:
        f.write("\n".join(bad) + ("\n" if bad else ""))
    for k in sorted(cnt):
        print("%9d  other words: %s" % (cnt[k], k))


if __name__ == "__main__":
    if sys.argv[1] == "--classify":
        classify(sys.argv[2], sys.argv[3])
    else:
        main()
