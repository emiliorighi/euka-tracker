#!/usr/bin/env python3
"""Shared UMAP coordinate helpers for scatter layouts."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from pipeline.scatter_landscape import COORD_SCALE, UMAP_KWARGS, _corr, _scale_coords

IUCN_CORR_WARN = 0.8


def fit_umap_coords(features: np.ndarray) -> np.ndarray:
    """Fit 2D UMAP on feature matrix and scale to ±COORD_SCALE."""
    if features.shape[0] == 0:
        return np.zeros((0, 2), dtype=np.float64)
    try:
        import umap
    except ImportError as exc:
        raise ImportError(
            "umap-learn is required for scatter UMAP layouts. "
            "Install with: pip install umap-learn"
        ) from exc

    reducer = umap.UMAP(**UMAP_KWARGS)
    coords = reducer.fit_transform(features)
    return _scale_coords(np.asarray(coords, dtype=np.float64))


def write_xy_to_parquet(parquet_path: Path, x: np.ndarray, y: np.ndarray) -> None:
    table = pq.read_table(parquet_path)
    rows = table.to_pydict()
    columns = {
        name: rows[name]
        for name in table.column_names
        if name not in ("landscape_x", "landscape_y")
    }
    columns["x"] = x.astype(np.float64)
    columns["y"] = y.astype(np.float64)
    pq.write_table(pa.table(columns), parquet_path, compression="zstd")


def compute_percentile_extent(
    xs: np.ndarray,
    ys: np.ndarray,
    *,
    lo: float = 1.0,
    hi: float = 99.0,
    pad: float = 0.05,
) -> dict[str, list[float]]:
    x_lo, x_hi = np.percentile(xs, [lo, hi])
    y_lo, y_hi = np.percentile(ys, [lo, hi])
    x_span = max(float(x_hi - x_lo), 1e-9)
    y_span = max(float(y_hi - y_lo), 1e-9)
    x_pad = x_span * pad
    y_pad = y_span * pad
    return {
        "x": [float(x_lo - x_pad), float(x_hi + x_pad)],
        "y": [float(y_lo - y_pad), float(y_hi + y_pad)],
    }


# Core-density zoom bbox for atlas tree clicks (deepscatter point_size ≈ 4 at edges).
TAXON_ZOOM_PERCENTILE_LO = 5.0
TAXON_ZOOM_PERCENTILE_HI = 95.0
TAXON_ZOOM_EXTENT_PAD = 0.12


def clamp_extent_to_bounds(
    extent: dict[str, list[float]],
    *,
    bound: float = COORD_SCALE,
) -> dict[str, list[float]]:
    """Clamp axis-aligned extent to landscape coordinate limits (±COORD_SCALE)."""
    x0, x1 = extent["x"]
    y0, y1 = extent["y"]
    return {
        "x": [max(-bound, float(x0)), min(bound, float(x1))],
        "y": [max(-bound, float(y0)), min(bound, float(y1))],
    }


def compute_data_extent(
    xs: np.ndarray,
    ys: np.ndarray,
    *,
    lo: float = TAXON_ZOOM_PERCENTILE_LO,
    hi: float = TAXON_ZOOM_PERCENTILE_HI,
    pad: float = TAXON_ZOOM_EXTENT_PAD,
) -> dict[str, list[float]]:
    """Core-density zoom bbox: percentile window + pad, clamped to landscape bounds."""
    extent = compute_percentile_extent(xs, ys, lo=lo, hi=hi, pad=pad)
    return clamp_extent_to_bounds(extent)


def load_matrix_rows_by_taxid(matrix_path: Path) -> dict[int, dict[str, str]]:
    import csv

    out: dict[int, dict[str, str]] = {}
    with matrix_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            raw = row.get("taxid")
            if not raw:
                continue
            try:
                taxid = int(raw)
            except ValueError:
                continue
            out[taxid] = row
    return out


def warn_iucn_axis_correlation(
    x: np.ndarray,
    iucn_codes: np.ndarray,
    *,
    layout: str,
    threshold: float = IUCN_CORR_WARN,
) -> float:
    corr = _corr(x, iucn_codes.astype(np.float64))
    if abs(corr) > threshold:
        print(
            f"Warning: {layout} layout |corr(x, iucn_code)|={abs(corr):.3f} "
            f"exceeds {threshold}",
            file=sys.stderr,
        )
    return corr
