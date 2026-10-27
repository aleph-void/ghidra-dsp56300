#!/usr/bin/env bash
# asl round trip over the enumeration chunks left by decode-enum.sh: every <step>-th decoded
# instruction is re-assembled from the module's text by asl and compared with its words; asl's
# other encodings are decoded back with the module and classified (asl_roundtrip.py).
#   test/decode-roundtrip.sh <enum-workdir> [step]
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
W=$1 STEP=${2:-10}
R=$W/rt
mkdir -p "$R"
: > "$R/all.items"
for g in "$W"/e??.gh; do
	python3 "$HERE/slots2items.py" "$g" "${g%.gh}.gh.txt" "$R/tmp.items" "$STEP"
	cat "$R/tmp.items" >> "$R/all.items"
done
rm -f "$R/tmp.items"
TMPDIR=$R python3 "$HERE/asl_roundtrip.py" "$R/all.items" "$R/all"
"$HERE/ghidra-script.sh" raw DSP56300:LE:24:default "$R/all.altimg" DumpSlots.java "$R/all.altdump" 6
python3 "$HERE/asl_roundtrip.py" --classify "$R/all" "$R/all.altdump"
