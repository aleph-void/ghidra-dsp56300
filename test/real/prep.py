#!/usr/bin/env python3
"""prep.py <in.asm> <out.asm>: adapt an octabam DSP module (written for the dsp56300 project's
assembler, Motorola syntax) to asl (Macro Assembler AS).  Only spelling changes, no code changes:
  - 'cpu 56300' header
  - MOVE to/from program memory (P:) is MOVEM
  - MOVE to/from a control register (Mn, SR, OMR, LA, LC, SP, SSH, SSL, VBA, SC, SZ, EP) is MOVEC
    (Motorola's assembler accepts the MOVE spelling; asl does not)
  - '#>' (forced long) on ADD/SUB/CMP/AND/OR/EOR immediates and DO/DOR/REP counts, '>' on
    DO/DOR targets, which asl
    rejects; asl chooses the long form itself when the value needs it
"""
import re
import sys

CTL = r"(?:m[0-7]|sr|omr|la|lc|sp|ssh|ssl|vba|sc|sz|ep|mr|ccr)"
out = ["\tcpu\t56300"]
for line in open(sys.argv[1], errors="replace"):
    line = line.rstrip("\n")
    code, sep, comment = line.partition(";")
    m = re.match(r"^(\s*(?:\w+:?)?\s+)move(\s+)([^\s,]+),(\S+)\s*$", code, re.I)
    disp = m and re.search(r"\(r[0-7][+-][$0-9]", m.group(3) + m.group(4), re.I)
    if m and not disp and (re.fullmatch(CTL, m.group(4), re.I) or re.fullmatch(CTL, m.group(3), re.I)):
        code = "%smovec%s%s,%s" % (m.group(1), m.group(2), m.group(3), m.group(4))
    elif m and (m.group(3).lower().startswith("p:") or m.group(4).lower().startswith("p:")):
        code = "%smovem%s%s,%s" % (m.group(1), m.group(2), m.group(3), m.group(4))
    code = re.sub(r"^(\s*(?:\w+:?)?\s+(?:add|sub|cmp|and|or|eor)\s+)#>", r"\1#", code, flags=re.I)
    code = re.sub(r"^(\s*(?:\w+:?)?\s+(?:do|dor)\s+[^,]+,)>", r"\1", code, flags=re.I)
    code = re.sub(r"^(\s*(?:\w+:?)?\s+(?:do|dor|rep)\s+)#[<>]", r"\1#", code, flags=re.I)
    out.append(code + sep + comment)
open(sys.argv[2], "w").write("\n".join(out) + "\n")
