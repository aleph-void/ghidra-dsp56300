#!/usr/bin/env python3
"""mame_dis.py <image.mame> <out.txt> [unidasm]: run MAME unidasm -arch dsp563xx on a two-word-slot
image and write one line per slot: "<slot> <words> <text>" (words = 1 or 2, as MAME decoded)."""
import re
import subprocess
import sys

exe = sys.argv[3] if len(sys.argv) > 3 else "unidasm"
p = subprocess.run([exe, sys.argv[1], "-arch", "dsp563xx"], capture_output=True, text=True, check=True)
with open(sys.argv[2], "w") as out:
    for line in p.stdout.splitlines():
        m = re.match(r"\s*([0-9a-f]+): ((?:[0-9a-f]{8} )+)\s*(.*)$", line + " ")
        if not m:
            continue
        a = int(m.group(1), 16)
        if a % 2:
            if len(m.group(2).split()) != 1:
                sys.exit("filler at %x decoded as two words: resync lost" % a)
            continue
        out.write("%d %d %s\n" % (a // 2, len(m.group(2).split()), m.group(3).strip()))
