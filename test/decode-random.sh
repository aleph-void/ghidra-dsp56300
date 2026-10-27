#!/usr/bin/env bash
# Random-word decode differential: <count> random 24-bit words with random extension words,
# decoded by the module and by MAME unidasm -arch dsp563xx, compared by compare.py.
#   test/decode-random.sh <workdir> [count] [seed]
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
W=$1 N=${2:-200000} SEED=${3:-563}
mkdir -p "$W"
p=$W/r$SEED
python3 "$HERE/gen_corpus.py" random "$p" "$N" "$SEED"
python3 "$HERE/mame_dis.py" "$p.mame" "$p.mame.txt" "${UNIDASM:-unidasm}"
"$HERE/ghidra-script.sh" raw DSP56300:LE:24:default "$p.gh" DumpSlots.java "$p.gh.txt" 6
rm -f "$p.mame"
python3 "$HERE/compare.py" "$p" --show 4 > "$p.cmp"
grep -E '^ {0,9}[0-9]+  [a-z]' "$p.cmp" | grep -v '^ *[0-9]*    explained'
