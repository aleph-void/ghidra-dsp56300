# Ghidra-Rare notes: Motorola/Freescale DSP56300

Fork of [roblg/ghidra-dsp56300](https://github.com/roblg/ghidra-dsp56300) (Apache-2.0, see
`CREDITS.md`), verified by Ghidra-Rare. Language IDs `DSP56300:LE:24:default` (linear address
updates) and `DSP56300:LE:24:modulo` (address updates through the Mn modifiers), plus the upstream
**DSP56300 Loop End** analyzer. Prebuilt zips for Ghidra 12.1.3, 12.1.4 and 12.2 are on the fork's
Releases page.

## What it covers

The DSP56300 core instruction set of the Family Manual (Rev. 5): every non-parallel instruction,
every data ALU operation with every parallel move class (immediate short, register, X/Y, long,
X:R, R:Y, class II, X:Y, IFcc/IFcc.U), DO/DOR/REP hardware loops (loop-back attached to the loop's
last word through context; the analyzer handles a two-word last instruction), the system stack as
the `SS` space. P-code models the data limiter with scaling, rounding by RM, the SM saturation mode,
the CCR per instruction, DIV/NORM/NORMF/CLB, and in the modulo variant the AGU modifiers.

## Results

| Area | Result |
|---|---|
| Decode | All 2^24 instruction words (each with an extension word) vs MAME `unidasm -arch dsp563xx`: 5,036,139 agree, 983,726 both invalid, 10,757,351 explained, **0 unexplained**. 200,000 random words with random extension words: 60,158 agree, 11,725 both invalid, 128,117 explained, 0 unexplained. asl round trip over every 10th decoded word (1,579,314): 1,565,743 re-assemble to the same words, 987 to another encoding of the same instruction, 12,502 differ by confirmed asl bugs, 82 asl rejects (asl limitations), 0 unexplained. Every constructor reached: **1023/1023**. A manual fixed-bit check (`test/manual_table.py`) finds no decoded non-parallel word outside the manual's formats. |
| Semantics | 40 hand-computed emulator cases (33 default language, 7 modulo variant) plus one deliberately wrong expectation per language, which is reported (**broken expectation detected**): ADD/SUB flags, limiting with L/S, MPY/MPYuu/MAC with C unchanged, convergent/two's-complement/scaled rounding, scale-up limiting, SM saturation, 24-step DIV, NORM, CLB/NORMF, NN/NR, IFcc, logic and shifts, CMPU, EXTRACTU, parallel-move read order, X:Y moves, every addressing mode, absolute/immediate/displacement/long moves, LUA, bit operations, JCLR, BSR/RTS, DO and REP loops, modulo, reverse carry, multiple wrap-around, block jump. Loop-end analyzer: 3/3 loops (fails 2/3 with the analyzer off). |
| Real code | 23 DSP56300 modules of sambanks/octabam (MIT), assembled with asl: 13,548 instructions, 68 functions, 0 bad-instruction and 0 error bookmarks, 68/68 functions decompile (0 failed, 0 timeouts); the module's text at all 13,548 instructions re-assembles with asl to the listing's words. |
| Doesn't work | See "Known gaps". |
| Unverified | Behaviour on hardware (no DSP56300 board or cycle-accurate reference emulator was used); DSP56300 binaries produced by Motorola's own toolchain (COFF/.cld; no freely licensed ones found); the 16-bit modes. |

## Changes

See `CREDITS.md` for the list. In short: three decode fixes (reserved bits, operand ranges, BRCLR-
class ea), NN/NR swapped, the system stack and PC-relative values (p-code `inst_next` is a byte
offset in a 3-byte-word space), data limiter/rounding/scaling/SM, MAC-class C flag, DIV, NORM,
NORMF, CLB, CMPU, modulo AGU, and the reset SR for the decompiler.

## Known gaps

- **Sixteen-bit modes SA and SC, double-precision multiply mode DM**: not modelled; the p-code
  implements the 24-bit modes (the reset state). They are expressible in p-code (each data move,
  multiply and address update would branch on the SR bit) but have not been written; code that sets
  them decodes correctly and computes as in 24-bit mode.
- **BRKcc** jumps through a computed target, LA+1: LA is a run-time register, and the enclosing loop
  is not known when one instruction is decoded.
- **DO loop counts and the emulator**: DO/REP loops run in Ghidra's emulator through context set at
  disassembly. Context that the Loop End analyzer sets after the fact is seen by the listing and
  the decompiler but not by `EmulatorHelper` (it does not re-read program context); the analyzer is
  therefore checked on the listing's p-code (`test/LoopEndCheck.java`), not by emulation.
- **Halt, reset, cache, debug and interrupt instructions** (STOP, WAIT, RESET, PFLUSH/PFREE/PLOCK,
  DEBUG, TRAP, ILLEGAL) are pcodeops: hardware state outside the program.

## Confirmed reference-tool bugs

MAME `dsp563xx` (each checked against the Family Manual tables; asl agrees with the module where it
supports the form):

- X:Y moves: the MM/mm address modes are shifted by one ((Rn) shown as (Rn)+Nn, ...); Table 12-16:
  00 (Rn), 01 (Rn)+Nn, 10 (Rn)-, 11 (Rn)+.
- R:Y class I moves decoded with the X:R field layout.
- QQQQ operand table (MPY/MAC su/uu, DMAC): rows 0100-0111 and 1000-1011 swapped (Table 12-16).
- MPYI/MPYRI/MACI/MACRI: the qq field decoded with the QQ table of MPY S,#n.
- INSERT/EXTRACT/EXTRACTU: destination printed as `d`; destination B rejected.
- LSR #ii rejected for ii = 17..23 (manual: 0..23).
- CLB decoded at $00C3Cx instead of its encoding $0C1E0x.
- Accepts reserved forms: BRCLR-class with an absolute ea, (+/-)S,#n,D with n = 0.
- Display: `maccr` for MACR, explicit `+` signs, DO/DOR show LA instead of the assembler's LA+1,
  S,#n,D shows the constant 2^-n, MOVE with no parallel move (`200000`) rejected.

asl (Macro Assembler AS 1.42 Bld 315):

- DOR: the extension word holds the absolute LA; the manual's operation is PC + xxxx -> LA (MAME
  and the module agree).
- CMP B,A / CMP A,B encoded with JJJ = 001, which is MAX/MAXM on the DSP56300 (Table 12-16:
  B/A = 000).
- ASL S1,S2,D encoded with bits 7..5 = 001 (NORMF's encoding); the manual has 010.
- Limitations (not encoding bugs): rejects MOVE X/Y:(Rn+xxxx) with registers outside the data ALU
  (manual: DDDDDD, all on-chip registers), lacks VSL, writes (+/-)S,#n,D with the constant 2^-n,
  accepts `#>`/`#<` and `<<` only in some places, lists negative extension words with 8 digits.

## Testing

```
export GHIDRA_INSTALL_DIR=/path/to/ghidra   # with Ghidra/Processors/DSP56300 -> this directory
export ASL_BIN=/path/to/asl/bin             # asl, p2bin; MAME unidasm on PATH (or UNIDASM=)
test/run-tests.sh [--work DIR] [--jobs N] [--real WORKDIR]
```

1. `tools/gen_sinc.py` reproduces `data/languages/dsp56300.sinc`;
2. both specs compile (`.sla` < 16 MB);
3. emulator cases (`test/emu/cases.txt` -> `emu_build.py` -> `EmuCheck.java`), both languages;
4. loop-end analyzer (`LoopEndCheck.java`);
5. decode differential vs MAME over all 2^24 words (`decode-enum.sh`, `compare.py`) and 200,000
   random words (`decode-random.sh`);
6. every constructor reached (`reach-enum.sh`, `Reach.java`, `reach.py`);
7. asl round trip (`decode-roundtrip.sh`, `asl_roundtrip.py`);
8. with `--real`: `test/real/run-real.sh` fetches the octabam sources by pinned URL and SHA-256,
   adapts their spelling to asl (`prep.py`), assembles, imports and checks them (`RealCheck.java`)
   and round-trips the module's text through asl.

Steps 5-7 need about 1.5 GB in the work directory and some minutes with 6 jobs.
