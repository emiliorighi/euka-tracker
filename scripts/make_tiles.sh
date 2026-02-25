#!/bin/bash
# Generate vector tiles from GeoJSON (requires tippecanoe and tile-join)

set -e
cd "$(dirname "$0")/.."

GEOJSON_DIR="${GEOJSON_DIR:-output/geojson}"
MBTILES="${MBTILES:-output/tiles.mbtiles}"
TILE_DIR="${TILE_DIR:-tiles}"

if ! command -v tippecanoe >/dev/null 2>&1; then
  echo "Error: tippecanoe not found. Install from https://github.com/felt/tippecanoe"
  exit 1
fi

echo "Generating tiles (per-layer, then merge)..."
builddir="output/tile_build"
mkdir -p "$builddir"

for layer in polygons lines points; do
  src="$GEOJSON_DIR/${layer}.geojson"
  [ -f "$src" ] || continue
  echo "  tippecanoe: $layer"
  tippecanoe --force -o "$builddir/${layer}.mbtiles" \
    -z 14 -Z 0 \
    -l "$layer" \
    --no-tile-size-limit \
    --drop-densest-as-needed \
    "$src"
done

echo "  tile-join: merging layers..."
mbtiles_files=()
for layer in polygons lines points; do
  f="$builddir/${layer}.mbtiles"
  [ -f "$f" ] && mbtiles_files+=("$f")
done
tile-join --force -o "$MBTILES" "${mbtiles_files[@]}"

if command -v mb-util >/dev/null 2>&1; then
  echo "Extracting to $TILE_DIR..."
  rm -rf "$TILE_DIR"
  mkdir -p "$TILE_DIR"
  mb-util --image_format=pbf "$MBTILES" "$TILE_DIR"
  echo "Done. Tiles in $TILE_DIR/"
elif python3 -c "import sqlite3" 2>/dev/null; then
  echo "Extracting with Python (mb-util not found)..."
  python3 scripts/extract_tiles.py
else
  echo "mb-util not found. Run: python3 scripts/extract_tiles.py"
fi
