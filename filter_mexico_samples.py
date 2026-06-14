#!/usr/bin/env python3
"""
Filter mapped_locations.jsonl to keep only samples whose coordinates fall
within Mexican boundaries (from mexico.geojson). Writes results to
mapped_locations_mexico.jsonl.
"""

import json
import sys
from pathlib import Path

from shapely.geometry import shape, Point


def load_mexico_boundary(geojson_path: Path):
    """Load Mexico polygon from GeoJSON. Returns a Shapely geometry."""
    with open(geojson_path) as f:
        feature = json.load(f)
    return shape(feature["geometry"])


def main():
    base = Path(__file__).resolve().parent
    input_path = base / "mapped_locations.jsonl"
    output_path = base / "mapped_locations_mexico.jsonl"
    mexico_geojson = base / "mexico.geojson"

    if not mexico_geojson.exists():
        print(f"Error: {mexico_geojson} not found.", file=sys.stderr)
        sys.exit(1)
    if not input_path.exists():
        print(f"Error: {input_path} not found.", file=sys.stderr)
        sys.exit(1)

    mexico = load_mexico_boundary(mexico_geojson)
    total = 0
    kept = 0

    with open(input_path) as fin, open(output_path, "w") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            total += 1
            record = json.loads(line)
            lat = record.get("latitude")
            lon = record.get("longitude")
            if lat is None or lon is None:
                continue
            point = Point(lon, lat)
            if mexico.contains(point):
                fout.write(line + "\n")
                kept += 1

    print(f"Read {total} samples, kept {kept} within Mexico -> {output_path}")


if __name__ == "__main__":
    main()
