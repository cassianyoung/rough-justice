#!/usr/bin/env bash
# build.sh : the PDFs of Rough Justice from the one source (split 2026-11-18).
#
#   paper/build.sh            draft builds
#   paper/build.sh --final    final builds: refused while any \Prov, \Pending, \Check or \DraftBox is left
#
# For each target, two PDFs:
#   build/RoughJustice_T.pdf                 the main paper, title to references
#   build/RoughJustice_T_supplementary.pdf   "Rough Justice: Supplementary Material", the appendices, S-numbered
# Each part reads the other's .aux (xr-hyper), so they are compiled supplement, main, supplement.
# arxiv : the author's name, the abstract as a single full-width column above the two columns, first person.
# review: ACL template, anonymous, line numbers, the author's earlier paper (Young 2026) in the third person.
set -euo pipefail
cd "$(dirname "$0")"
FINAL=no
[ "${1:-}" = "--final" ] && FINAL=yes
PY="${PYTHON:-python3}"
if [ "$FINAL" = yes ]; then
  "$PY" ../tools/check_typed_numbers.py
else
  "$PY" ../tools/check_typed_numbers.py --draft
fi
mkdir -p build
compile() {   # target, part, job name
  local T="$1" P="$2" J="$3"
  # tectonic resolves \input and graphics relative to the working directory, so compile from paper/.
  printf '\\def\\buildtarget{%s}\\def\\buildpart{%s}\\def\\buildfinal{%s}\\input{main}\n' "$T" "$P" "$FINAL" > "${J}.tex"
  cp "${J}.tex" "build/${J}.tex"
  tectonic --keep-intermediates --keep-logs --outdir build "${J}.tex" > "build/${J}.log.tectonic" 2>&1 \
    || { rm -f "${J}.tex"; echo "BUILD FAILED: ${J} (see paper/build/${J}.log)"; tail -20 "build/${J}.log.tectonic"; exit 1; }
  rm -f "${J}.tex"
  # The labels alone, for the other part's xr-hyper: the full .aux carries lineno's line records, and the line labels
  # of \Check marks hold a lineno command; xr-hyper can read neither.
  grep '^\\newlabel' "build/${J}.aux" | grep -v '^\\newlabel{rjcheck' > "build/xr_${J}.aux" || true
}
for T in arxiv review; do
  compile "$T" supp "RoughJustice_${T}_supplementary"
  compile "$T" main "RoughJustice_${T}"
  compile "$T" supp "RoughJustice_${T}_supplementary"
  echo "built paper/build/RoughJustice_${T}.pdf and RoughJustice_${T}_supplementary.pdf"
done
