#!/usr/bin/env python3
"""reach.py <languages-dir> <reach.txt>...: report SLEIGH constructors (by <file>:<line>) that no
decoded instruction reached; exit 1 if any."""
import re
import sys
from pathlib import Path

seen = set()
for f in sys.argv[2:]:
    seen |= set(open(f).read().split())
tot, miss = 0, []
for fn in ("dsp56300.sinc", "dsp56300.slaspec"):
    for i, l in enumerate((Path(sys.argv[1]) / fn).read_text().split("\n")):
        if re.match(r"^(:|[A-Za-z_]\w*:)", l):
            tot += 1
            if f"{fn}:{i + 1}" not in seen:
                miss.append(f"{fn}:{i + 1} {l[:110]}")
print(f"   constructors reached {tot - len(miss)}/{tot}")
for m in miss[:40]:
    print("   not reached:", m)
sys.exit(1 if miss else 0)
