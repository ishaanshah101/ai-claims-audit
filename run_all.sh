#!/usr/bin/env bash
# Reproduce every result in the paper from scratch.
#
# Steps 1 to 4 hit the SEC's servers and take about twenty minutes; step 3
# downloads roughly 229 MB of filings into data/filings/, which is gitignored.
# Steps 5 and 6 require the six rating passes, which are model calls and are not
# scripted here; the published rater output is in data/rating/rater_*.jsonl, so
# skip to step 7 to reproduce the analysis from what is committed.
set -euo pipefail
cd "$(dirname "$0")/src"

python3 stats.py                 # self-checks first: if these fail, stop

if [ "${REBUILD_CORPUS:-0}" = "1" ]; then
  python3 frame.py               # 1. enumerate the EDGAR frame
  python3 sample_filings.py      # 2. stratified draw, seed 20260926
  python3 fetch_and_extract.py   # 3. download and extract sentences
  python3 build_rating_sets.py   # 4. blind, shuffle, assign to six passes
  echo "Now run the six rating passes; see docs/RATER_PROTOCOL.md" && exit 0
fi

python3 validate_ratings.py      # 5. schema-check the rater output
python3 agreement.py             # 6. inter-pass agreement, agreed/disputed split
python3 build_calibration.py     # 7. build the blinded calibration materials
python3 term_audit.py            # 8. term-list false-positive screen
python3 calibrate.py             # 9. unblind, measure the bias
python3 analyze.py               # 10. every number in the paper
python3 supplement.py            # 11. filing-level summaries, blinding audit
python3 figures.py               # 12. figures
python3 verify_paper.py          # 13. recompute every quoted number, fail loudly

echo
echo "Building the PDF."
cd ../paper && pandoc paper.md -o ai-claims-audit.pdf --pdf-engine=xelatex \
  -V mainfont="DejaVu Serif" -V monofont="DejaVu Sans Mono"
echo "paper/ai-claims-audit.pdf"
