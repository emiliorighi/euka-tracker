#!/usr/bin/env python3
"""Build phylum cluster labels GeoJSON and view extent for deepscatter."""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

from pipeline.scatter_coords import compute_data_extent
from pipeline.scatter_export import (
    ANCESTOR_MAX_DEPTH,
    ANCESTOR_MIN_DEPTH,
    EUKARYOTA_TAXID,
)
from pipeline.taxon_rollup import LANDSCAPE_SCATTER_FIELDS


def build_phylum_labels_geojson(
    parquet_path: Path,
    *,
    label_field: str = "labels",
) -> dict:
    """Centroid label per phylum from exported scatter parquet."""
    table = pq.read_table(parquet_path, columns=["x", "y", "phylum_taxid", "phylum_name"])
    rows = table.to_pydict()
    xs = rows["x"]
    ys = rows["y"]
    phylum_taxids = rows["phylum_taxid"]
    phylum_names = rows["phylum_name"]

    sums: dict[int, dict[str, float | str | int]] = defaultdict(
        lambda: {"x": 0.0, "y": 0.0, "n": 0, "name": ""}
    )
    for x, y, ptid, pname in zip(xs, ys, phylum_taxids, phylum_names, strict=True):
        if ptid is None:
            continue
        tid = int(ptid)
        entry = sums[tid]
        entry["x"] = float(entry["x"]) + float(x)
        entry["y"] = float(entry["y"]) + float(y)
        entry["n"] = int(entry["n"]) + 1
        if pname and not entry["name"]:
            entry["name"] = str(pname)

    features = []
    for phylum_taxid, entry in sorted(sums.items(), key=lambda kv: kv[0]):
        n = int(entry["n"])
        if n <= 0:
            continue
        name = str(entry["name"] or f"Phylum {phylum_taxid}")
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(entry["x"]) / n, float(entry["y"]) / n],
                },
                "properties": {
                    label_field: name,
                    "phylum_taxid": phylum_taxid,
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}


def _load_rollup_meta(rollups_path: Path) -> dict[int, dict[str, int]]:
    meta: dict[int, dict[str, int]] = {}
    with rollups_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            try:
                taxid = int(row["taxid"])
            except (KeyError, TypeError, ValueError):
                continue
            try:
                depth = int(row.get("depth_from_eukaryota") or 0)
            except ValueError:
                depth = 0
            try:
                with_data = int(row.get("species_count_with_data") or 0)
            except ValueError:
                with_data = 0
            meta[taxid] = {
                "depth": depth,
                "species_count_with_data": with_data,
            }
    return meta


def build_taxon_centroids(
    parquet_path: Path,
    rollups_path: Path,
) -> dict[str, dict[str, object]]:
    """Mean (x,y) and zoom bbox per internal taxon from scatter parquet."""
    rollups = _load_rollup_meta(rollups_path)
    ancestor_cols = [
        f"ancestor_d{d}" for d in range(ANCESTOR_MIN_DEPTH, ANCESTOR_MAX_DEPTH + 1)
    ]
    table = pq.read_table(parquet_path, columns=["x", "y", *ancestor_cols])
    rows = table.to_pydict()
    xs = np.asarray(rows["x"], dtype=np.float64)
    ys = np.asarray(rows["y"], dtype=np.float64)
    row_count = len(xs)

    accum: dict[int, dict[str, list[float]]] = defaultdict(
        lambda: {"xs": [], "ys": []},
    )

    for depth in range(ANCESTOR_MIN_DEPTH, ANCESTOR_MAX_DEPTH + 1):
        col = rows[f"ancestor_d{depth}"]
        for i in range(row_count):
            raw = col[i]
            if raw is None:
                continue
            taxid = int(raw)
            if taxid <= 0:
                continue
            accum[taxid]["xs"].append(float(xs[i]))
            accum[taxid]["ys"].append(float(ys[i]))

    accum[EUKARYOTA_TAXID] = {"xs": xs.tolist(), "ys": ys.tolist()}

    centroids: dict[str, dict[str, object]] = {}
    skipped_empty = 0
    missing_with_data: list[int] = []

    for taxid, rollup in rollups.items():
        bucket = accum.get(taxid)
        if not bucket or not bucket["xs"]:
            skipped_empty += 1
            if rollup["species_count_with_data"] > 0:
                missing_with_data.append(taxid)
            continue

        tx = np.asarray(bucket["xs"], dtype=np.float64)
        ty = np.asarray(bucket["ys"], dtype=np.float64)
        bbox = compute_data_extent(tx, ty)
        centroids[str(taxid)] = {
            "x": float(tx.mean()),
            "y": float(ty.mean()),
            "bbox": bbox,
            "n": int(len(tx)),
        }

    print(
        f"Built {len(centroids):,} taxon centroids "
        f"(skipped {skipped_empty:,} empty rollups entries)",
        file=sys.stderr,
    )
    if missing_with_data:
        sample = missing_with_data[:10]
        print(
            f"Warning: {len(missing_with_data):,} rollups taxa have "
            f"species_count_with_data>0 but no scatter points "
            f"(sample taxids: {sample})",
            file=sys.stderr,
        )

    return centroids


def _centroid_row_fields(entry: dict[str, object]) -> dict[str, float]:
    bbox = entry["bbox"]
    if not isinstance(bbox, dict):
        raise TypeError("centroid entry missing bbox dict")
    x_bounds = bbox.get("x")
    y_bounds = bbox.get("y")
    if not isinstance(x_bounds, list) or not isinstance(y_bounds, list):
        raise TypeError("centroid bbox must include x/y ranges")
    return {
        "landscape_cx": float(entry["x"]),
        "landscape_cy": float(entry["y"]),
        "landscape_bbox_x0": float(x_bounds[0]),
        "landscape_bbox_x1": float(x_bounds[1]),
        "landscape_bbox_y0": float(y_bounds[0]),
        "landscape_bbox_y1": float(y_bounds[1]),
    }


def merge_landscape_centroids_into_rollups(
    rollups_path: Path,
    centroids: dict[str, dict[str, object]],
) -> int:
    """Patch landscape scatter columns onto 06_taxon_rollups.tsv rows."""
    with rollups_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"Rollups file has no header: {rollups_path}")

        fieldnames = list(reader.fieldnames)
        for field in LANDSCAPE_SCATTER_FIELDS:
            if field not in fieldnames:
                fieldnames.append(field)
        rows = list(reader)

    updated = 0
    for row in rows:
        taxid = row.get("taxid", "")
        entry = centroids.get(str(taxid))
        if entry is None:
            for field in LANDSCAPE_SCATTER_FIELDS:
                row[field] = row.get(field, "") or ""
            continue
        row.update(_centroid_row_fields(entry))
        updated += 1

    with rollups_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            delimiter="\t",
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    print(
        f"Patched landscape scatter columns on {updated:,} rows → {rollups_path}",
        file=sys.stderr,
    )
    return updated


def write_scatter_sidecars(
    parquet_path: Path,
    tile_dir: Path,
    view_extent: dict[str, list[float]],
    *,
    rollups_path: Path | None = None,
    layout: str | None = None,
) -> tuple[Path, Path]:
    """Write labels.geojson and view_extent.json beside quadfeather tiles."""
    tile_dir.mkdir(parents=True, exist_ok=True)
    labels_path = tile_dir / "labels.geojson"
    extent_path = tile_dir / "view_extent.json"

    geojson = build_phylum_labels_geojson(parquet_path)
    labels_path.write_text(json.dumps(geojson, indent=2), encoding="utf-8")
    extent_path.write_text(json.dumps(view_extent, indent=2), encoding="utf-8")

    if (
        layout == "landscape"
        and rollups_path is not None
        and rollups_path.is_file()
    ):
        centroids = build_taxon_centroids(parquet_path, rollups_path)
        merge_landscape_centroids_into_rollups(rollups_path, centroids)

    return labels_path, extent_path
