#!/bin/sh
# Rebuilds every result and chart from the raw BLS files in data/raw/ (see data/README.md).
set -e
cd "$(dirname "$0")"
PY=${PYTHON:-.venv/bin/python}
$PY src/build.py                       # raw BLS files -> data/processed/interviews.csv
$PY src/reconcile_team.py > /dev/null  # pandas check of the team reconciliation
(cd src && ../$PY analysis.py)         # pandas check of the estimates + validation and benchmarks
$PY src/run_sql.py                     # SQL pipeline in DuckDB, compared with the pandas results
$PY src/charts.py
echo "done: see results/ and charts/"
