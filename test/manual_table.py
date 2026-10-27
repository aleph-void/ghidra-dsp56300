#!/usr/bin/env python3
"""Fixed-bit check of the non-parallel opcode space against the DSP56300 Family Manual.

    manual_table.py <e00.gh.txt>

The table below is the "Instruction Formats and Opcodes" bit strings of the DSP56300 Family Manual
(Rev. 5, chapter 13), transcribed from the manual independently of the module's templates (letters
are operand fields, 0/1 fixed bits).  Every word with bits 23..20 = 0 (the non-parallel
instructions and the class II moves) that the module decodes must match the fixed bits of at least
one entry; the script lists the words that match none (reserved bits the module ignores).  It does
not check operand field values (register codes, conditions): the MAME differential does that.
"""
import sys

TABLE = """
ADD #xx,D            0000000101iiiiii1000d000
ADD #xxxx,D          00000001010000001100d000
AND #xx,D            0000000101iiiiii1000d110
AND #xxxx,D          00000001010000001100d110
ANDI #xx,D           00000000iiiiiiii101110EE
ASL #ii,S2,D         0000110000011101SiiiiiiD
ASL S1,S2,D          0000110000011110010SsssD
ASR #ii,S2,D         0000110000011100SiiiiiiD
ASR S1,S2,D          0000110000011110011SsssD
Bcc xxxx             00001101000100000100CCCC
Bcc xxx              00000101CCCC01aaaa0aaaaa
Bcc Rn               0000110100011RRR0100CCCC
BCHG ea              0000101101MMMRRR0S0bbbbb
BCHG aa              0000101100aaaaaa0S0bbbbb
BCHG pp              0000101110pppppp0S0bbbbb
BCHG qq              0000000101qqqqqq0S0bbbbb
BCHG D               0000101111DDDDDD010bbbbb
BCLR ea              0000101001MMMRRR0S0bbbbb
BCLR aa              0000101000aaaaaa0S0bbbbb
BCLR pp              0000101010pppppp0S0bbbbb
BCLR qq              0000000100qqqqqq0S0bbbbb
BCLR D               0000101011DDDDDD010bbbbb
BRA xxxx             000011010001000011000000
BRA xxx              00000101000011aaaa0aaaaa
BRA Rn               0000110100011RRR11000000
BRCLR ea             0000110010MMMRRR0S0bbbbb
BRCLR aa             0000110010aaaaaa1S0bbbbb
BRCLR pp             0000110011pppppp0S0bbbbb
BRCLR qq             0000010010qqqqqq0S0bbbbb
BRCLR S              0000110011DDDDDD100bbbbb
BRKcc                00000000000000100001CCCC
BRSET ea             0000110010MMMRRR0S1bbbbb
BRSET aa             0000110010aaaaaa1S1bbbbb
BRSET pp             0000110011pppppp0S1bbbbb
BRSET qq             0000010010qqqqqq0S1bbbbb
BRSET S              0000110011DDDDDD101bbbbb
BScc xxxx            00001101000100000000CCCC
BScc xxx             00000101CCCC00aaaa0aaaaa
BScc Rn              0000110100011RRR0000CCCC
BSCLR ea             0000110110MMMRRR0S0bbbbb
BSCLR aa             0000110110aaaaaa1S0bbbbb
BSCLR qq             0000010010qqqqqq1S0bbbbb
BSCLR pp             0000110111pppppp0S0bbbbb
BSCLR S              0000110111DDDDDD100bbbbb
BSET ea              0000101001MMMRRR0S1bbbbb
BSET aa              0000101000aaaaaa0S1bbbbb
BSET pp              0000101010pppppp0S1bbbbb
BSET qq              0000000100qqqqqq0S1bbbbb
BSET D               0000101011DDDDDD011bbbbb
BSR xxxx             000011010001000010000000
BSR xxx              00000101000010aaaa0aaaaa
BSR Rn               0000110100011RRR10000000
BSSET ea             0000110110MMMRRR0S1bbbbb
BSSET aa             0000110110aaaaaa1S1bbbbb
BSSET pp             0000110111pppppp0S1bbbbb
BSSET qq             0000010010qqqqqq1S1bbbbb
BSSET S              0000110111DDDDDD101bbbbb
BTST ea              0000101101MMMRRR0S1bbbbb
BTST aa              0000101100aaaaaa0S1bbbbb
BTST pp              0000101110pppppp0S1bbbbb
BTST qq              0000000101qqqqqq0S1bbbbb
BTST D               0000101111DDDDDD011bbbbb
CLB S,D              0000110000011110000000SD
CMP #xx,S2           0000000101iiiiii1000d101
CMP #xxxx,S2         00000001010000001100d101
CMPU S1,S2           00001100000111111111gggd
DEBUG                000000000000001000000000
DEBUGcc              00000000000000110000CCCC
DEC D                00000000000000000000101d
DIV S,D              000000011000000001JJd000
DMAC                 000000010010010s1sdkQQQQ
DO ea                0000011001MMMRRR0S000000
DO aa                0000011000aaaaaa0S000000
DO #xxx              00000110iiiiiiii1000hhhh
DO S                 0000011011DDDDDD00000000
DO FOREVER           000000000000001000000011
DOR ea               0000011001MMMRRR0S010000
DOR aa               0000011000aaaaaa0S010000
DOR #xxx             00000110iiiiiiii1001hhhh
DOR S                0000011011DDDDDD00010000
DOR FOREVER          000000000000001000000010
ENDDO                000000000000000010001100
EOR #xx,D            0000000101iiiiii1000d011
EOR #xxxx,D          00000001010000001100d011
EXTRACT S1,S2,D      0000110000011010000sSSSD
EXTRACT #CO,S2,D     0000110000011000000s000D
EXTRACTU S1,S2,D     0000110000011010100sSSSD
EXTRACTU #CO,S2,D    0000110000011000100s000D
ILLEGAL              000000000000000000000101
INC D                00000000000000000000100d
INSERT S1,S2,D       00001100000110110qqqSSSD
INSERT #CO,S2,D      00001100000110010qqq000D
Jcc xxx              00001110CCCCaaaaaaaaaaaa
Jcc ea               0000101011MMMRRR1010CCCC
JCLR ea              0000101001MMMRRR1S0bbbbb
JCLR aa              0000101000aaaaaa1S0bbbbb
JCLR pp              0000101010pppppp1S0bbbbb
JCLR qq              0000000110qqqqqq1S0bbbbb
JCLR S               0000101011DDDDDD000bbbbb
JMP ea               0000101011MMMRRR10000000
JMP xxx              000011000000aaaaaaaaaaaa
JScc xxx             00001111CCCCaaaaaaaaaaaa
JScc ea              0000101111MMMRRR1010CCCC
JSCLR ea             0000101101MMMRRR1S0bbbbb
JSCLR aa             0000101100aaaaaa1S0bbbbb
JSCLR pp             0000101110pppppp1S0bbbbb
JSCLR qq             0000000111qqqqqq1S0bbbbb
JSCLR S              0000101111DDDDDD000bbbbb
JSET ea              0000101001MMMRRR1S1bbbbb
JSET aa              0000101000aaaaaa1S1bbbbb
JSET pp              0000101010pppppp1S1bbbbb
JSET qq              0000000110qqqqqq1S1bbbbb
JSET S               0000101011DDDDDD001bbbbb
JSR ea               0000101111MMMRRR10000000
JSR xxx              000011010000aaaaaaaaaaaa
JSSET ea             0000101101MMMRRR1S1bbbbb
JSSET aa             0000101100aaaaaa1S1bbbbb
JSSET pp             0000101110pppppp1S1bbbbb
JSSET qq             0000000111qqqqqq1S1bbbbb
JSSET S              0000101111DDDDDD001bbbbb
LRA Rn,D             0000010011000RRR000ddddd
LRA xxxx,D           0000010001000000010ddddd
LSL #ii,D            000011000001111010iiiiiD
LSL S,D              00001100000111100001sssD
LSR #ii,D            000011000001111011iiiiiD
LSR S,D              00001100000111100011sssD
LUA ea,D             00000100010MMRRR000ddddd
LUA (Rn+aa),D        0000010000aaaRRRaaaadddd
MAC S,#n,D           00000001000sssss11QQdk10
MACR S,#n,D          00000001000sssss11QQdk11
MPY S,#n,D           00000001000sssss11QQdk00
MPYR S,#n,D          00000001000sssss11QQdk01
MACI #xxxx,S,D       000000010100000111qqdk10
MACRI #xxxx,S,D      000000010100000111qqdk11
MPYI #xxxx,S,D       000000010100000111qqdk00
MPYRI #xxxx,S,D      000000010100000111qqdk01
MACsu/uu             00000001001001101sdkQQQQ
MPYsu/uu             00000001001001111sdkQQQQ
MERGE S,D            00001100000110111000SSSD
MOVE X:(Rn+xxxx)     0000101001110RRR1WDDDDDD
MOVE X:(Rn+xxx)      0000001aaaaaaRRR1a0WDDDD
MOVE Y:(Rn+xxxx)     0000101101110RRR1WDDDDDD
MOVE Y:(Rn+xxx)      0000001aaaaaaRRR1a1WDDDD
MOVEC ea             00000101W1MMMRRR0S1ddddd
MOVEC aa             00000101W0aaaaaa0S1ddddd
MOVEC S2,D1          00000100W1eeeeee101ddddd
MOVEC #xx,D1         00000101iiiiiiii101ddddd
MOVEM ea             00000111W1MMMRRR10dddddd
MOVEM aa             00000111W0aaaaaa00dddddd
MOVEP pp,ea          0000100sW1MMMRRR1Spppppp
MOVEP X:qq,ea        00000111W1MMMRRR0Sqqqqqq
MOVEP Y:qq,ea        00000111W0MMMRRR1Sqqqqqq
MOVEP pp,P:ea        0000100sW1MMMRRR01pppppp
MOVEP qq,P:ea        000000001WMMMRRR0Sqqqqqq
MOVEP pp,D           0000100sW1dddddd00pppppp
MOVEP X:qq,D         00000100W1dddddd1q0qqqqq
MOVEP Y:qq,D         00000100W1dddddd0q1qqqqq
NOP                  000000000000000000000000
NORM Rn,D            0000000111011RRR0001d101
NORMF S,D            00001100000111100010sssD
OR #xx,D             0000000101iiiiii1000d010
OR #xxxx,D           00000001010000001100d010
ORI #xx,D            00000000iiiiiiii111110EE
PFLUSH               000000000000000000000011
PFLUSHUN             000000000000000000000001
PFREE                000000000000000000000010
PLOCK ea             0000101111MMMRRR10000001
PLOCKR xxxx          000000000000000000001111
PUNLOCK ea           0000101011MMMRRR10000001
PUNLOCKR xxxx        000000000000000000001110
REP ea               0000011001MMMRRR0S100000
REP aa               0000011000aaaaaa0S100000
REP #xxx             00000110iiiiiiii1010hhhh
REP S                0000011011dddddd00100000
RESET                000000000000000010000100
RTI                  000000000000000000000100
RTS                  000000000000000000001100
STOP                 000000000000000010000111
SUB #xx,D            0000000101iiiiii1000d100
SUB #xxxx,D          00000001010000001100d100
Tcc S1,D1            00000010CCCC00000JJJd000
Tcc S1,D1 S2,D2      00000011CCCC0ttt0JJJdTTT
Tcc S2,D2            00000010CCCC1ttt00000TTT
TRAP                 000000000000000000000110
TRAPcc               00000000000000000001CCCC
VSL S,i,L:ea         0000101S11MMMRRR110i0000
WAIT                 000000000000000010000110
X:R class II         0000100d00MMMRRRaaaaaaaa
R:Y class II         0000100d10MMMRRRaaaaaaaa
"""


def entries():
    out = []
    for line in TABLE.strip().split("\n"):
        name, bits = line[:21].strip(), line[21:].strip()
        assert len(bits) == 24, line
        mask = int("".join("1" if c in "01" else "0" for c in bits), 2)
        val = int("".join(c if c in "01" else "0" for c in bits), 2)
        out.append((name, mask, val))
    return out


def main():
    ents = entries()
    bad = []
    n = 0
    for line in open(sys.argv[1]):
        i, ln, text = (line.rstrip("\n").split(" ", 2) + [""])[:3]
        w = int(i)
        if w >> 20 or ln == "0":
            continue
        n += 1
        if not any(w & m == v for _, m, v in ents):
            bad.append("%06x %s" % (w, text))
    print("   manual fixed-bit table: %d decoded non-parallel words, %d match no manual format" % (n, len(bad)))
    for b in bad[:20]:
        print("   no manual format:", b)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
