#!/usr/bin/env python3
"""lst2img.py <file.lst> <out-prefix>: from an asl listing write <prefix>.bin (raw image from
address 0, 3-byte little-endian words), <prefix>.addrs (hex word address of every instruction:
listing lines with code whose source is not a data directive) and <prefix>.items
("<addr> <words> | <source>")."""
import re
import sys

DATA = re.compile(r"^\s*(?:\w+:?\s+)?(dc|ds|dsm|dcb|bsc|org)\b", re.I)
mem, ins = {}, []
for l in open(sys.argv[1], errors="replace"):
    m = re.match(r"^\s*\d+/\s*([0-9A-F]+) : ((?:[0-9A-F]{6,8} ?)+)\s*(.*)$", l.rstrip("\n"))
    if not m:
        continue
    a = int(m.group(1), 16)
    ws = [int(w, 16) & 0xffffff for w in m.group(2).split()]
    for i, w in enumerate(ws):
        mem[a + i] = w
    src = m.group(3).split(";")[0].strip()
    if not DATA.match(src) and src:
        ins.append((a, ws, src))
top = max(mem) + 1 if mem else 0
with open(sys.argv[2] + ".bin", "wb") as f:
    for a in range(top):
        f.write(mem.get(a, 0).to_bytes(3, "little"))
with open(sys.argv[2] + ".addrs", "w") as f:
    f.write("".join("%x\n" % a for a, ws, s in ins))
with open(sys.argv[2] + ".items", "w") as f:
    f.write("".join("%x %s | %s\n" % (a, " ".join("%06x" % w for w in ws), s) for a, ws, s in ins))
