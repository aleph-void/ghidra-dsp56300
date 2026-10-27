#!/usr/bin/env python3
"""Decode corpora for the DSP56300 differential.

    gen_corpus.py enum <out-prefix> <first-word-hex> <count>   every word in [first, first+count)
    gen_corpus.py random <out-prefix> <count> <seed>           random 24-bit words
    gen_corpus.py words <out-prefix> <file-of-hex-words>       given words (one per line)

Each test instruction gets a two-word slot: the instruction word and an extension word (used by
the two-word forms as absolute address, immediate or displacement). The extension word is picked
from FILLERS by a hash of the instruction word; every filler is a one-word instruction for MAME's
dsp563xx disassembler, so MAME, which disassembles the image linearly, re-synchronises at every
slot whether the test instruction is one or two words long.

Writes <prefix>.gh (3-byte little-endian words: the Ghidra raw image) and <prefix>.mame (4-byte
little-endian words: what unidasm -arch dsp563xx reads).
"""
import struct
import sys
import random

# One-word for MAME (checked by gen_corpus.py check-fillers); a mix of small, large, negative,
# peripheral-range and sign-boundary values.
FILLERS = [0x000000, 0x000001, 0x000010, 0x000123, 0x00abcd, 0x7fffff, 0x800000, 0xffffff,
           0xfffff0, 0xff0000, 0x123456, 0x654321, 0x00ffc0, 0xffffc5, 0x000107, 0x3fffff,
           0xc00000, 0x555555, 0xaaaaaa, 0x000040, 0x00003f, 0xffff80, 0x000fff, 0x001000]


def ext_for(w):
    return FILLERS[((w * 2654435761) >> 8) % len(FILLERS)]


def write(prefix, words, exts=None):
    gh = bytearray()
    mame = bytearray()
    for k, w in enumerate(words):
        e = exts[k] if exts else ext_for(w)
        for x in (w, e):
            gh += struct.pack("<I", x)[:3]
            mame += struct.pack("<I", x)
    open(prefix + ".gh", "wb").write(gh)
    open(prefix + ".mame", "wb").write(mame)


def main():
    mode = sys.argv[1]
    if mode == "enum":
        first, count = int(sys.argv[3], 16), int(sys.argv[4])
        write(sys.argv[2], range(first, first + count))
    elif mode == "random":
        # random words, each with a randomly chosen extension word (other pairs than enum's)
        rnd = random.Random(int(sys.argv[4]))
        n = int(sys.argv[3])
        ws = [rnd.randrange(1 << 24) for _ in range(n)]
        write(sys.argv[2], ws, [rnd.choice(FILLERS) for _ in range(n)])
    elif mode == "words":
        write(sys.argv[2], [int(l.split()[0], 16) for l in open(sys.argv[3]) if l.strip()])
    elif mode == "check-fillers":
        # emit the fillers each followed by a nop; mame_dis.py on it must show one word for each
        open(sys.argv[2], "wb").write(b"".join(struct.pack("<II", f, 0) for f in FILLERS))
    else:
        sys.exit("unknown mode " + mode)


if __name__ == "__main__":
    main()
