#!/usr/bin/env bash
# Decode every 24-bit instruction word (16 chunks of 2^20) with the module and with MAME unidasm.
#   test/decode-enum.sh <workdir> [jobs]
# Leaves <workdir>/eNN.gh.txt (module) and eNN.mame.txt (MAME) per chunk.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
W=$1 J=${2:-4}
mkdir -p "$W"
one() {
	local c=$1 p=$W/e$1
	python3 "$HERE/gen_corpus.py" enum "$p" "$(printf %x $((10#$c << 20)))" 1048576
	python3 "$HERE/mame_dis.py" "$p.mame" "$p.mame.txt" "${UNIDASM:-unidasm}"
	"$HERE/ghidra-script.sh" raw DSP56300:LE:24:default "$p.gh" DumpSlots.java "$p.gh.txt" 6
	rm -f "$p.mame"
}
export -f one; export W HERE
printf '%02d\n' $(seq 0 15) | xargs -P "$J" -I{} bash -c 'one {}'
