#!/bin/sh
# Rebuilds every result and chart from the raw BLS files in data/raw/ (see data/README.md).
set -e
cd "$(dirname "$0")"
PY=${PYTHON:-.venv/bin/python}
$PY src/build.py
$PY src/reconcile_team.py
(cd src && ../$PY analysis.py > /dev/null)
$PY src/charts.py
echo "done: see results/ and charts/"
