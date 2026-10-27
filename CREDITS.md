# Credits

## Upstream

- Repository: [roblg/ghidra-dsp56300](https://github.com/roblg/ghidra-dsp56300)
- Commit: `fec2cab8def2b3ec0585479b76542b835e3fbaf7` (GitHub HEAD on 2026-10-08)
- License: Apache License 2.0 (`LICENSE`, unchanged; sources in `NOTICE.md`)
- Original author: Robert Gay (GitHub @roblg, robertgay@gmail.com), all 8 upstream commits
  (co-authored with Claude Opus 5.5 according to their commit trailers)

Everything here except the changes below is the upstream author's work.

## Ghidra-Rare changes

Branch `ghidra-rare`, one commit per change, on top of `fec2cab`.

Decode (found by the full 2^24-word differential against MAME `unidasm -arch dsp563xx`, each checked
against the DSP56300 Family Manual, Rev. 5):

1. Reserved bits the manual fixes are now checked: RESET/STOP/WAIT/ENDDO bits 6 and 4; REP #xxx
   bits 7..4 = 1010; Tcc S1,D1 / S2,D2 zero fields; LRA xxxx,D bits 13..8; MOVE(C) register forms
   bits 7..5 = 101; ADD/SUB/CMP/AND/OR/EOR #xx and #xxxx zero fields; MPYI/MPYRI/MACI/MACRI
   bits 13..8; the S bit of MOVEP/MOVE(C) with an immediate source.
2. Shift counts and S,#n limited to the defined ranges: ASL/ASR #ii 0..40, LSL #ii 0..16,
   LSR #ii 0..23, MPY/MAC (+/-)S,#n,D n = 1..23.
3. BRCLR/BRSET/BSCLR/BSSET no longer accept the absolute-address ea (the one extension word is the
   displacement; the module read a third word).

Semantics (found by the emulator cases in `test/emu/cases.txt`):

4. Condition codes NN and NR were swapped.
5. System stack: return addresses, DO loop tops, LRA and the Rn-relative branch targets used
   `inst_next`/`inst_start`, which p-code gives as byte offsets (3 per word), so RTS returned to
   three times the right address; JSR-class calls and DO pushed SR without the CCR bits; DO/DOR now
   set LF (and FV), and the loop end restores them.
6. Data ALU: the data limiter (24/48-bit, with scaling, L and S), rounding (convergent / two's
   complement per RM, scaled position), E/U under scaling and the arithmetic saturation mode SM are
   p-code instead of the user ops `sat24`, `sat48`, `rnd56`; MPY/MPYR/MAC/MACR (all forms),
   MPYI-class, MPY/MACsu/uu and DMAC leave C unchanged; CMP/CMPM do not saturate.
7. DIV, NORM, NORMF, CLB are p-code instead of user ops; CMPU compares bits 47..0 and sets N.
8. The modulo variant computes Mn-based address updates (linear, reverse carry, modulo with block
   jumps, multiple wrap-around) in p-code instead of the user op `agu_modulo`.
9. The compiler spec gives SR its reset value at function entry (mode tests fold away in the
   decompiler).

Additions (their own commit): `GHIDRA-RARE.md`, this file, `test/` (suite, harness, emulator cases,
real-code fetch list), Ghidra-Rare's `build.gradle`; `README.md` limitation and pointer updates.

## Sources and tools

- Motorola/Freescale *DSP56300 Family Manual*, DSP56300FM Rev. 5 (encodings, semantics, CCR tables).
- MAME `unidasm` (`dsp563xx`) and asl (Macro Assembler AS, Alfred Arnold, GPL) run as black boxes
  only; no source of either was read.
- `test/RealCheck.java` and the AGU modifier and limiter p-code follow the approach of Ghidra-Rare's
  own DSP56000 module (MIT, `DspRealCheck.java`, `aguAdd`, `busAcc`, `roundAcc`), rewritten for the
  24-bit DSP56300 and its mode bits.
- `test/ghidra-script.sh`, `DumpSlots.java`, `Reach.java`, `EmuCheck.java` are adapted from the
  harness of Ghidra-Rare's community-module verifications.
- Real code: [sambanks/octabam](https://github.com/sambanks/octabam) (MIT, Sam Banks) DSP modules at
  commit `ae69a3be36a64bbcd65eb89c82e3f5426fcd2510`, fetched by `test/real/run-real.sh` by URL and
  SHA-256 (`test/real/sources.txt`); nothing of it is committed.
