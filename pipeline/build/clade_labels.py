"""Build phylum clade label GeoJSON from scatter parquet centroids."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq

PIPELINE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PARQUET = PIPELINE_DIR / "output" / "iucn_species_scatter.parquet"
DEFAULT_OUTPUT = PIPELINE_DIR / "output" / "iucn_clade_labels.geojson"


def _label_size(species_count: int) -> float:
    """Font size in pt for deepscatter (height field); keep in ~14–22."""
    return round(14.0 + math.log10(max(species_count, 1)), 1)


def _phylum_features(
    sums: dict[str, dict[str, float | str | int]],
) -> list[dict]:
    features: list[dict] = []
    for key in sorted(sums.keys()):
        entry = sums[key]
        n = int(entry["n"])
        if n <= 0:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(entry["x"]) / n, float(entry["y"]) / n],
                },
                "properties": {
                    "label": str(entry["label"]),
                    "rank": "phylum",
                    "taxonName": str(entry["label"]),
                    "speciesCount": n,
                    "labelSize": _label_size(n),
                    "groupKey": key,
                },
            }
        )
    return features


def build_clade_labels_geojson(
    parquet_path: Path,
    *,
    output_path: Path = DEFAULT_OUTPUT,
) -> Path:
    if not parquet_path.is_file():
        raise FileNotFoundError(f"Scatter parquet not found: {parquet_path}")

    table = pq.read_table(parquet_path, columns=["x", "y", "kingdomName", "phylumName"])
    rows = table.to_pydict()

    phylum_sums: dict[str, dict[str, float | str | int]] = defaultdict(
        lambda: {"x": 0.0, "y": 0.0, "n": 0, "label": ""}
    )

    for x, y, kingdom, phylum in zip(
        rows["x"],
        rows["y"],
        rows["kingdomName"],
        rows["phylumName"],
        strict=True,
    ):
        if kingdom and phylum:
            pk = f"{str(kingdom).strip()}|{str(phylum).strip()}"
            pname = str(phylum).strip()
            if pk and pname:
                entry = phylum_sums[pk]
                entry["x"] = float(entry["x"]) + float(x)
                entry["y"] = float(entry["y"]) + float(y)
                entry["n"] = int(entry["n"]) + 1
                entry["label"] = pname

    features = _phylum_features(phylum_sums)

    geojson = {"type": "FeatureCollection", "features": features}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(geojson, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {output_path} ({len(features)} phylum labels)", file=sys.stderr)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build IUCN phylum label GeoJSON")
    parser.add_argument("--parquet", type=Path, default=DEFAULT_PARQUET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build_clade_labels_geojson(args.parquet, output_path=args.output)


if __name__ == "__main__":
    main()
