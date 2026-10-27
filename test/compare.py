#!/usr/bin/env python3
"""Compare the module's decode (DumpSlots.java) with MAME unidasm -arch dsp563xx (mame_dis.py).

    compare.py <ghidra.txt> <mame.txt> <corpus.gh> [--show N]
    compare.py --summary <compare-output>...

Counts agree / both invalid / explained (MAME bugs and display conventions confirmed against the
Family Manual, each with its reason) and lists every remaining difference by signature ("differ").
"""
import re
import sys
from collections import Counter, defaultdict
import difflib

NUM = re.compile(r"(?<![a-z0-9_])(\$[0-9a-f]+|0x[0-9a-f]+|\d+)(?![a-z0-9_])")


def num(m):
    t = m.group(1)
    if t.startswith("$"):
        return str(int(t[1:], 16))
    if t.startswith("0x"):
        return str(int(t[2:], 16))
    return str(int(t))


def norm(t):
    t = t.lower().strip()
    t = t.replace("<", "").replace(">", "")
    t = NUM.sub(num, t)
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\s*,\s*", ",", t)
    return t


XYMODE_MAME = {0: "(r)+n", 1: "(r)-", 2: "(r)+", 3: "(r)"}
XYMODE_TRUE = {0: "(r)", 1: "(r)+n", 2: "(r)-", 3: "(r)+"}


def ea_text(mode, r):
    return mode.replace("(r)", "(r%d)" % r).replace("+n", "+n%d" % r)


MAME_QQQQ = ["x0,x0", "y0,y0", "x1,x0", "y1,y0", "x1,x1", "y1,y1", "x0,x1", "y0,y1",
             "x0,y1", "y0,x0", "x1,y0", "y1,x1", "y1,x0", "x0,y0", "y0,x1", "x1,y1"]
TRUE_QQQQ = ["x0,x0", "y0,y0", "x1,x0", "y1,y0", "x0,y1", "y0,x0", "x1,y0", "y1,x1",
             "x1,x1", "y1,y1", "x0,x1", "y0,y1", "y1,x0", "x0,y0", "y0,x1", "x1,y1"]


def mame_fix(t, w):
    """Rewrite MAME's text for its confirmed bugs and display conventions.  Returns (text, reasons)."""
    why = []

    def sub(reason, pat, rep, s, flags=0):
        r = re.sub(pat, rep, s, flags=flags)
        if r != s:
            why.append(reason)
        return r

    t = sub("MAME spells MACR as maccr", r"\bmaccr\b", "macr", t)
    t = sub("MAME prints an explicit + sign", r"^(\S+\s+)\+", r"\1", t)
    if w & 0x800000:
        xr, xm = (w >> 8) & 7, (w >> 11) & 3
        yr = ((w >> 13) & 3) + (0 if xr >= 4 else 4)
        ym = (w >> 20) & 3
        if xm != 0 or ym != 0 or True:
            t0 = t
            t = t.replace("x:" + ea_text(XYMODE_MAME[xm], xr), "x:" + ea_text(XYMODE_TRUE[xm], xr))
            t = t.replace("y:" + ea_text(XYMODE_MAME[ym], yr), "y:" + ea_text(XYMODE_TRUE[ym], yr))
            if t != t0:
                why.append("MAME bug: X:Y move MM/mm address modes shifted by one")
    if (w >> 20) == 1 and (w >> 14) & 1:
        # R:Y class I: MAME decodes the fields with the X:R layout (ff=19..18, d=17, e=16)
        md, me, mff = "ab"[(w >> 17) & 1], "x%d" % ((w >> 16) & 1), ["y0", "y1", "a", "b"][(w >> 18) & 3]
        td, te, tff = "ab"[(w >> 19) & 1], "x%d" % ((w >> 18) & 1), ["y0", "y1", "a", "b"][(w >> 16) & 3]
        m = re.match(r"^(.*\s)%s,%s (.*)$" % (md, me), t)
        if m:
            rest = m.group(2)
            if rest.endswith("," + mff):
                rest = rest[:-len(mff)] + tff
            elif rest.startswith(mff + ","):
                rest = tff + rest[len(mff):]
            t2 = "%s%s,%s %s" % (m.group(1), td, te, rest)
            if t2 != t:
                why.append("MAME bug: R:Y class I fields decoded with the X:R layout")
            t = t2
    if (w >> 17) == 4 and (w >> 15) & 1 == 1 and (w >> 14) & 1 == 0:
        # R:Y class II: MAME prints the two transfers in the opposite order
        t = sub("R:Y class II operand order (display)", r"([ab]),(y:\S+) (y0),([ab])$", r"\3,\4 \1,\2", t)
    # DO/DOR: MAME prints LA, the assembler syntax (and the module) the address after the loop
    m = re.match(r"^(do|dor)\s+(.*),\$([0-9a-f]+)$", t)
    if m:
        t = "%s %s,$%x" % (m.group(1), m.group(2), (int(m.group(3), 16) + 1) & 0xffffff)
        why.append("DO/DOR target: MAME prints LA, the module LA+1 (assembler syntax)")
    # (+/-)S,#n,D: MAME prints the constant 2^-n, the module n (manual syntax)
    m = re.match(r"^(mpy|mpyr|mac|macr)(\s+-?[xy][01]),#\$([0-9a-f]+),([ab])$", t)
    if m and w >> 16 == 1:
        c = int(m.group(3), 16)
        if c and c & (c - 1) == 0:
            t = "%s%s,#%d,%s" % (m.group(1), m.group(2), 23 - (c.bit_length() - 1), m.group(4))
            why.append("S,#n,D: MAME prints 2^-n as a constant")
    # MPYI/MACI/...: MAME takes qq (bits 5..4) from the QQ table of MPY S,#n
    m = re.match(r"^(mpyi|mpyri|maci|macri)(\s+-?#\$[0-9a-f]+),([xy][01]),([ab])$", t)
    if m:
        r = ["x0", "y0", "x1", "y1"][(w >> 4) & 3]
        if r != m.group(3):
            why.append("MAME bug: MPYI-class qq decoded with the QQ table")
        t = "%s%s,%s,%s" % (m.group(1), m.group(2), r, m.group(4))
    # QQQQ (MPYsu/uu, MACsu/uu, DMAC): MAME's table swaps 0100-0111 with 1000-1011
    m = re.match(r"^(mpysu|mpyuu|macsu|macuu|dmacss|dmacsu|dmacuu)(\s+-?)([xy][01],[xy][01]),([ab])$", t)
    if m:
        q = MAME_QQQQ.index(m.group(3))
        if TRUE_QQQQ[w & 15] != m.group(3):
            why.append("MAME bug: QQQQ operand table")
        t = "%s%s%s,%s" % (m.group(1), m.group(2), TRUE_QQQQ[w & 15], m.group(4))
    # INSERT/EXTRACT(U): MAME prints the destination as a literal 'd'
    if re.match(r"^(insert|extract|extractu)\s", t) and t.endswith(",d"):
        t = t[:-1] + "ab"[w & 1]
        why.append("MAME bug: INSERT/EXTRACT destination printed as 'd'")
    return t, why


def explain(w, gt, mt, gbad, mbad):
    """Whole-instruction difference classes, each confirmed against the manual (and asl)."""
    if gbad and not mbad:
        if (w >> 14) in (0x032, 0x036) and (w >> 8) & 0x3f == 0x30:
            return ("MAME accepts an absolute-address ea in BRCLR/BRSET/BSCLR/BSSET: the format's one "
                    "extension word holds the displacement (asl rejects it as well)")
        if w >> 8 == 0x0100 and (w >> 6) & 3 == 3:
            return "MAME accepts (+/-)S,#n,D with n=0, which the manual's table (n=1..22) does not define"
        if w >> 2 == 0x00c3c0 >> 2:
            return "MAME bug: CLB decoded at 00C3Cx (the manual and asl put CLB at 0C1E0x)"
    if mbad and not gbad:
        if (w >> 7) in (0x0c1b << 1 | 0, 0x0c1a << 1 | 0, 0x0c1a << 1 | 1) and w & 1:
            return "MAME bug: INSERT/EXTRACT/EXTRACTU with destination B rejected (asl encodes it)"
        if w >> 6 == 0x307b and 17 <= (w >> 1) & 0x1f <= 23:
            return "MAME bug: LSR #ii rejected for ii=17..23 (manual: 0-23; asl encodes it)"
        if w >> 2 == 0x0c1e00 >> 2:
            return "MAME bug: CLB not decoded at its encoding 0C1E0x"
        if w == 0x200000:
            return "MAME rejects MOVE with no parallel move (200000), which asl assembles for 'move'"
    if not gbad and not mbad and gt.startswith("lra ") and mt.startswith("lra #$"):
        if norm(gt) == norm(mt.replace("#$", "$")):
            return "LRA xxxx,D: MAME prints the target with '#'"
    return None


def words(path):
    d = open(path, "rb").read()
    return [(int.from_bytes(d[i:i + 3], "little"), int.from_bytes(d[i + 3:i + 6], "little"))
            for i in range(0, len(d), 6)]


def load(path):
    r = {}
    for l in open(path):
        p = l.rstrip("\n").split(" ", 2)
        r[int(p[0])] = (int(p[1]), p[2] if len(p) > 2 else "")
    return r


def shape(toks):
    return " ".join(re.sub(r"\b\d+\b", "#", t) for t in toks)


def signature(g, m):
    a, b = re.findall(r"[\w#.]+|[^\w\s]", g), re.findall(r"[\w#.]+|[^\w\s]", m)
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op != "equal":
            out.append("[%s|%s]" % (shape(a[i1:i2]), shape(b[j1:j2])))
    return " ".join(out)


def main():
    args = sys.argv[1:]
    show = 3
    if "--show" in args:
        k = args.index("--show")
        show = int(args[k + 1])
        del args[k:k + 2]
    cnt = Counter()
    sig = defaultdict(list)
    import multiprocessing
    with multiprocessing.Pool(min(8, len(args))) as pool:
        for c, sg in pool.map(compare_one, args):
            cnt.update(c)
            for k, v in sg.items():
                sig[k].extend(v[:1000] if len(sig[k]) > 1000 else v)
    for k in sorted(cnt):
        print("%9d  %s" % (cnt[k], k))
    for k, v in sorted(sig.items(), key=lambda kv: -len(kv[1])):
        ones, zeros = 0xffffff, 0xffffff
        for x in v:
            w = int(x[:6], 16)
            ones &= w
            zeros &= ~w
        pat = "".join("1" if ones >> b & 1 else "0" if zeros >> b & 1 else "." for b in range(23, -1, -1))
        print("%7d  %s    {%s}" % (len(v), k, pat))
        for x in v[:show]:
            print("           " + x)


def compare_one(prefix):
    cnt, sig = Counter(), defaultdict(list)
    compare(prefix, cnt, sig)
    return cnt, sig


def compare(prefix, cnt, sig):
    gh, mame, ws = load(prefix + ".gh.txt"), load(prefix + ".mame.txt"), words(prefix + ".gh")
    for i, (w, e) in enumerate(ws):
        glen, gt = gh[i]
        mlen, mt = mame[i]
        gbad = glen == 0
        mbad = mt in ("unknown", "") or "unknown" in mt
        if gbad and mbad:
            cnt["both invalid"] += 1
            continue
        why = explain(w, gt, mt, gbad, mbad)
        if why:
            cnt["explained"] += 1
            cnt["  explained: " + why] += 1
            continue
        if gbad:
            key = "ghidra-invalid " + mt.split()[0]
        elif mbad:
            key = "mame-invalid " + gt.split()[0]
        else:
            ng = norm(gt)
            fixed, why = mame_fix(mt, w)
            nm = norm(fixed)
            if ng == nm and glen == 3 * mlen:
                if why:
                    cnt["explained"] += 1
                    for r in why:
                        cnt["  explained: " + r] += 1
                else:
                    cnt["agree"] += 1
                continue
            key = (gt.split()[0] + " " + signature(ng, nm)) if ng != nm else "length %d/%d" % (glen // 3, mlen)
        cnt["differ"] += 1
        sig[key].append("%06x %06x | %s | %s" % (w, e, gt, mt))
        if len(sig[key]) > 200000:
            sig[key].pop()


if __name__ == "__main__":
    main()
