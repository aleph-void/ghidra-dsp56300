#!/usr/bin/env bash
# Every-constructor check: Reach.java over the 16 enumeration chunks (decode-enum.sh images) in the
# default context, plus a small random corpus decoded as a DO-loop end (lbot, lbot+lfor) and as a
# REP target (rpt), which reach the loop constructors of the root table.
#   test/reach-enum.sh <enum-workdir> [jobs]
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
W=$1 J=${2:-6}
R=$W/reach
mkdir -p "$R"
export HERE
ls "$W"/e??.gh | xargs -P "$J" -I{} bash -c '"$HERE/ghidra-script.sh" raw DSP56300:LE:24:default {} Reach.java {}.reach 6'
python3 "$HERE/gen_corpus.py" random "$R/ctx" 2000 7
rm -f "$R/ctx.mame"
"$HERE/ghidra-script.sh" raw DSP56300:LE:24:default "$R/ctx.gh" Reach.java ctx:lbot=1 "$R/c1.reach" 6
"$HERE/ghidra-script.sh" raw DSP56300:LE:24:default "$R/ctx.gh" Reach.java ctx:lbot=1 ctx:lfor=1 "$R/c2.reach" 6
"$HERE/ghidra-script.sh" raw DSP56300:LE:24:default "$R/ctx.gh" Reach.java ctx:rpt=1 "$R/c3.reach" 6
python3 "$HERE/reach.py" "$HERE/../data/languages" "$W"/e??.gh.reach "$R"/c?.reach
