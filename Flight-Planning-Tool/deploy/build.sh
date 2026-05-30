#!/usr/bin/env bash
# Package the N9082P planner into a Lambda deployment zip.
# Pure standard library -> just bundle source + the FAA data file. No pip install.
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"          # Flight-Planning-Tool/
PERF_SRC="$HERE/../Performance/src"               # the performance calculator package
BUILD="$HERE/build"
ZIP="$HERE/n9082p-planner.zip"

[ -f "$HERE/data/airports_faa.json" ] || { echo "ERROR: data/airports_faa.json missing. Run tools/build_faa_airports.py first."; exit 1; }
[ -d "$PERF_SRC" ] || { echo "ERROR: $PERF_SRC not found."; exit 1; }

rm -rf "$BUILD" "$ZIP"
mkdir -p "$BUILD/data"

cp "$HERE/app/handler.py" "$BUILD/handler.py"      # Lambda entrypoint: handler.lambda_handler
cp -R "$HERE/planner" "$BUILD/planner"
cp -R "$PERF_SRC" "$BUILD/perf_engine"             # calculator, imported as perf_engine
cp "$HERE/data/airports_faa.json" "$BUILD/data/"

# strip caches
find "$BUILD" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "$BUILD" -name '*.pyc' -delete 2>/dev/null || true
find "$BUILD" -name '.DS_Store' -delete 2>/dev/null || true

( cd "$BUILD" && zip -qr "$ZIP" . )
echo "built $ZIP ($(du -h "$ZIP" | cut -f1))"
