#!/usr/bin/env bash
# Rebuild metrics, charts, and the LaTeX PDF for report/.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 scripts/rebuild_report_metrics.py
python3 scripts/rebuild_report_charts.py

# Prefer latexmk, then pdflatex, then tectonic if present.
cd report
if command -v latexmk >/dev/null 2>&1; then
  latexmk -pdf -interaction=nonstopmode main.tex
elif command -v pdflatex >/dev/null 2>&1; then
  pdflatex -interaction=nonstopmode main.tex
  pdflatex -interaction=nonstopmode main.tex
elif command -v tectonic >/dev/null 2>&1; then
  tectonic main.tex
elif [[ -x /workspace/tectonic ]]; then
  /workspace/tectonic main.tex
else
  echo "No LaTeX engine found (latexmk/pdflatex/tectonic). PDF not rebuilt." >&2
  exit 1
fi
cp -f main.pdf report.pdf
echo "wrote report/report.pdf"
