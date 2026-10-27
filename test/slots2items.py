#!/usr/bin/env python3
"""slots2items.py <corpus.gh> <dump.txt> <out.txt> [step]: turn a DumpSlots run over a two-word-slot
corpus into asl_roundtrip items (only the slots the module decodes; every <step>-th one)."""
import sys

d = open(sys.argv[1], "rb").read()
step = int(sys.argv[4]) if len(sys.argv) > 4 else 1
with open(sys.argv[3], "w") as out:
    n = 0
    for l in open(sys.argv[2]):
        p = l.rstrip("\n").split(" ", 2)
        i, ln = int(p[0]), int(p[1])
        if ln == 0:
            continue
        n += 1
        if n % step:
            continue
        ws = [int.from_bytes(d[6 * i + 3 * k:6 * i + 3 * k + 3], "little") for k in range(ln // 3)]
        out.write("%x %s | %s\n" % (2 * i, " ".join("%06x" % w for w in ws), p[2]))
