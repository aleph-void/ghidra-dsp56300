#!/usr/bin/env bash
# Real-code check on freely licensed DSP56300 sources (sources.txt: sambanks/octabam, MIT, pinned
# commit + SHA-256).  Each file is fetched, adapted to asl's spelling (prep.py), assembled with asl,
# imported raw into Ghidra (RealCheck.java: disassembly from every listed instruction, functions,
# decompilation), and the module's text at every instruction is re-assembled with asl and
# compared with the listing's words (asl_roundtrip.py).  Nothing fetched is committed.
#   test/real/run-real.sh <workdir>
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
T=$HERE/..
W=$1
mkdir -p "$W/src" "$W/out"
COMMIT=ae69a3be36a64bbcd65eb89c82e3f5426fcd2510
ASL=${ASL_BIN:+$ASL_BIN/}asl
: > "$W/out/all.items"
: > "$W/out/summary.txt"
grep -v '^#' "$HERE/sources.txt" | while read -r sha path; do
	n=$(echo "${path#modules/}" | tr / _ | sed 's/\.asm$//')
	f=$W/src/$n.orig.asm
	if [[ ! -f $f ]] || ! echo "$sha  $f" | sha256sum -c --quiet - 2>/dev/null; then
		curl -sSL -o "$f" "https://raw.githubusercontent.com/sambanks/octabam/$COMMIT/$path"
		echo "$sha  $f" | sha256sum -c --quiet -
	fi
	python3 "$HERE/prep.py" "$f" "$W/src/$n.asm"
	(cd "$W/src" && "$ASL" -L -q -U "$n.asm" >/dev/null)
	python3 "$HERE/lst2img.py" "$W/src/$n.lst" "$W/out/$n"
	"$T/ghidra-script.sh" raw DSP56300:LE:24:default "$W/out/$n.bin" RealCheck.java "$W/out/$n" "$W/out/$n.addrs"
	echo "$n: $(head -2 "$W/out/$n/summary.txt" | tr '\n' ' ')" >> "$W/out/summary.txt"
	cat "$W/out/$n/guided.txt" >> "$W/out/all.items"
done
cat "$W/out/summary.txt"
python3 - "$W/out/summary.txt" <<'PY'
import re, sys
tot = [0] * 7
for l in open(sys.argv[1]):
    n = [int(x) for x in re.findall(r"(?:instructions|functions|bookmarks|decompile:) (\d+)|(\d+) (?:ok|failed|timed)", l) for x in x if x]
    if len(n) == 7:
        tot = [a + b for a, b in zip(tot, n)]
print("real code total: %d instructions, %d functions, %d bad-instruction bookmarks, %d error bookmarks; "
      "decompile %d ok, %d failed, %d timed out" % tuple(tot))
PY
echo "real code: $(grep -c BAD "$W/out/all.items" || true) listed instruction addresses with no decode"
TMPDIR=$W/out python3 "$T/asl_roundtrip.py" "$W/out/all.items" "$W/out/rt"
if [[ -s $W/out/rt.altimg ]]; then
	"$T/ghidra-script.sh" raw DSP56300:LE:24:default "$W/out/rt.altimg" DumpSlots.java "$W/out/rt.altdump" 6
	python3 "$T/asl_roundtrip.py" --classify "$W/out/rt" "$W/out/rt.altdump"
fi
