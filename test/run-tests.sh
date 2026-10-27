#!/usr/bin/env bash
# DSP56300 test suite (see GHIDRA-RARE.md).  Needs GHIDRA_INSTALL_DIR pointing at a Ghidra whose
# Ghidra/Processors/DSP56300 is this module (symlink, with lib/DSP56300.jar built), JDK 21+ for
# Ghidra, Python 3, MAME's unidasm (UNIDASM, default unidasm) and asl (ASL_BIN = directory of
# asl, default PATH).
#   test/run-tests.sh [--work <dir>] [--jobs N] [--real <workdir>]
# Steps: generator reproduces dsp56300.sinc; specs compile; emulator cases (default and modulo
# languages, each with a deliberately wrong expectation that must be reported); loop-end analyzer;
# decode differential vs MAME over all 2^24 words and 200,000 random words; every constructor
# reached; asl round trip over every 10th decoded word; with --real, the real-code checks.
# Exits non-zero on any failure.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)
WORK=$ROOT/scratch/tests J=6 REAL=
while [[ $# -gt 0 ]]; do
	case $1 in
	--work) WORK=$2; shift 2 ;;
	--jobs) J=$2; shift 2 ;;
	--real) REAL=$2; shift 2 ;;
	*) echo "unknown option $1" >&2; exit 2 ;;
	esac
done
: "${GHIDRA_INSTALL_DIR:?set GHIDRA_INSTALL_DIR}"
export PROJ_DIR=${PROJ_DIR:-${TMPDIR:-/tmp}}
mkdir -p "$WORK"
fail=0
step() { echo "== $*"; }
bad() { echo "   FAIL: $*"; fail=1; }

step "1. generator reproduces data/languages/dsp56300.sinc"
python3 "$ROOT/tools/gen_sinc.py" "$ROOT/data/languages/dsp56300.sinc.in" "$ROOT/data/languages/dsp56300_np.sinc.in" \
	"$ROOT/data/languages/dsp56300_root.sinc.in" "$WORK/gen.sinc"
cmp -s "$WORK/gen.sinc" "$ROOT/data/languages/dsp56300.sinc" && echo "   ok" || bad "dsp56300.sinc is stale (run tools/regen.sh)"

step "2. specs compile"
for s in "$ROOT"/data/languages/*.slaspec; do
	if "$GHIDRA_INSTALL_DIR/support/sleigh" "$s" > "$WORK/sleigh.log" 2>&1; then
		sz=$(stat -c %s "${s%.slaspec}.sla")
		echo "   $(basename "$s"): ok, $sz bytes"
		[[ $sz -lt 16000000 ]] || bad "$(basename "$s").sla over 16 MB"
	else
		bad "$(basename "$s")"; tail -5 "$WORK/sleigh.log"
	fi
done

step "3. emulator cases"
python3 "$HERE/emu_build.py" --image "$HERE/emu/words.txt" "$WORK/emu.bin"
for lang in default modulo; do
	"$HERE/ghidra-script.sh" raw "DSP56300:LE:24:$lang" "$WORK/emu.bin" EmuCheck.java "$HERE/emu/tests-$lang.txt" "$WORK/emu-$lang.txt"
	grep -v '^PASS' "$WORK/emu-$lang.txt" | sed 's/^/   /'
	grep -q ' 0 failed, 1 broken expectations detected' "$WORK/emu-$lang.txt" || bad "emulator ($lang)"
done
if command -v "${ASL_BIN:+$ASL_BIN/}asl" >/dev/null; then
	python3 "$HERE/emu_build.py" "$HERE/emu/cases.txt" "$WORK/emu-regen" >/dev/null
	cmp -s "$WORK/emu-regen/words.txt" "$HERE/emu/words.txt" && cmp -s "$WORK/emu-regen/tests-default.txt" "$HERE/emu/tests-default.txt" \
		&& cmp -s "$WORK/emu-regen/tests-modulo.txt" "$HERE/emu/tests-modulo.txt" \
		&& echo "   emu/ is up to date with cases.txt" || bad "test/emu is stale (python3 test/emu_build.py test/emu/cases.txt test/emu)"
fi

step "4. loop-end analyzer"
python3 "$HERE/emu_build.py" --image "$HERE/emu/loopend.words" "$WORK/loopend.bin"
"$HERE/ghidra-script.sh" raw DSP56300:LE:24:default "$WORK/loopend.bin" LoopEndCheck.java "$WORK/loopend.txt" 100 110 120
tail -1 "$WORK/loopend.txt" | sed 's/^/   /'
grep -q '3 passed, 0 failed' "$WORK/loopend.txt" || bad "loop-end analyzer"

step "5. decode differential vs MAME dsp563xx: all 2^24 words"
"$HERE/decode-enum.sh" "$WORK/enum" "$J"
python3 "$HERE/compare.py" $(ls "$WORK"/enum/e??.gh | sed 's/\.gh$//') --show 4 > "$WORK/enum.cmp"
grep -E '^ {0,9}[0-9]+  [a-z]' "$WORK/enum.cmp" | grep -v '^ *[0-9]*    explained' | sed 's/^/   /'
grep -qE '^ +[0-9]+  differ$' "$WORK/enum.cmp" && bad "unexplained decode differences (see $WORK/enum.cmp)"
python3 "$HERE/manual_table.py" "$WORK/enum/e00.gh.txt" | tee "$WORK/manual.txt"
grep -q ', 0 match no manual format' "$WORK/manual.txt" || bad "decoded words outside the manual's formats"
step "   200,000 random words"
"$HERE/decode-random.sh" "$WORK/random" 200000 563 | sed 's/^/   /'
grep -qE '^ +[0-9]+  differ$' "$WORK/random/r563.cmp" && bad "unexplained random-word differences"

step "6. every constructor reached"
"$HERE/reach-enum.sh" "$WORK/enum" "$J" || bad "constructors not reached"

step "7. asl round trip (every 10th decoded word)"
if command -v "${ASL_BIN:+$ASL_BIN/}asl" >/dev/null; then
	"$HERE/decode-roundtrip.sh" "$WORK/enum" 10 | sed 's/^/   /'
	R=$WORK/enum/rt
	grep -qE '^ +[0-9]+  asl-rejects$' "$R/all.summary" && bad "asl rejects module text (see $R/all.rejects)"
	[[ -s $R/all.differ ]] && bad "asl encodes module text differently (see $R/all.differ)"
else
	bad "asl not found (set ASL_BIN)"
fi

if [[ -n $REAL ]]; then
	step "8. real code (sambanks/octabam DSP modules, MIT)"
	"$HERE/real/run-real.sh" "$REAL" | sed 's/^/   /'
	O=$REAL/out
	grep -q '0 bad-instruction bookmarks, 0 error bookmarks; decompile [0-9]* ok, 0 failed, 0 timed out' \
		<(python3 - "$O/summary.txt" <<'PY'
import re, sys
tot = [0] * 7
for l in open(sys.argv[1]):
    n = [int(x) for x in re.findall(r"(?:instructions|functions|bookmarks|decompile:) (\d+)|(\d+) (?:ok|failed|timed)", l) for x in x if x]
    if len(n) == 7:
        tot = [a + b for a, b in zip(tot, n)]
print("%d instructions, %d functions, %d bad-instruction bookmarks, %d error bookmarks; decompile %d ok, %d failed, %d timed out" % tuple(tot))
PY
) || bad "real code: bad instructions, error bookmarks or decompile failures"
	grep -q BAD "$O/all.items" && bad "real code: listed instructions that do not decode"
	grep -qE '^ +[0-9]+  (other words|asl-rejects)$' "$O/rt.summary" && [[ -s $O/rt.differ || $(grep -cE '^ +[0-9]+  asl-rejects$' "$O/rt.summary") -gt 0 ]] \
		&& bad "real code: asl round trip differences"
fi

if [[ $fail -ne 0 ]]; then
	echo "FAILED"
	exit 1
fi
echo "all tests passed"
