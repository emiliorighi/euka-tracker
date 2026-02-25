#!/bin/bash
# Run full Tree of Life pipeline: layout -> coverage -> tiles
set -e
cd "$(dirname "$0")/.."
echo "1/3 build_tree_layout.py"
pipenv run python scripts/build_tree_layout.py
echo "2/3 build_coverage.py"
pipenv run python scripts/build_coverage.py
echo "3/3 build_tree_tiles.py (parquet + json)"
pipenv run python scripts/build_tree_tiles.py --json
echo "Done. Serve with: python -m http.server 8000"
echo "Open: http://localhost:8000/frontend/"
