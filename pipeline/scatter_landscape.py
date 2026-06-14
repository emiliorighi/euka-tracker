#!/usr/bin/env python3
"""Fit UMAP landscape coordinates and write x/y to scatter parquet."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from pipeline.landscape_features import (  # noqa: E402
    FEATURE_DIM,
    build_feature_matrix_from_sources,
)

DEFAULT_PARQUET = _REPO / "data" / "scatter" / "species_scatter.parquet"
DEFAULT_MATRIX = _REPO / "data" / "staged" / "05_eukaryotic_species_matrix.tsv"
DEFAULT_IUCN = _REPO / "data" / "iucn_assessments.tsv"

UMAP_KWARGS = {
    "n_neighbors": 30,
    "min_dist": 0.5,
    "spread": 1.5,
    "metric": "cosine",
    "random_state": 42,
    "n_components": 2,
}

COORD_SCALE = 250.0
KNOWLEDGE_CORR_WARN = 0.65


def _scale_coords(coords: np.ndarray) -> np.ndarray:
    if coords.size == 0:
        return coords
    lo = coords.min(axis=0)
    hi = coords.max(axis=0)
    span = np.maximum(hi - lo, 1e-9)
    centered = (coords - lo) / span
    return (centered * 2.0 - 1.0) * COORD_SCALE


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 2:
        return 0.0
    a = a - a.mean()
    b = b - b.mean()
    denom = float(np.sqrt((a * a).sum() * (b * b).sum()))
    if denom < 1e-12:
        return 0.0
    return float((a * b).sum() / denom)


def apply_landscape_coords(
    parquet_path: Path,
    *,
    matrix_path: Path,
    iucn_tsv: Path,
) -> dict[str, float]:
    """Read parquet taxids, UMAP embedding from matrix+IUCN features, overwrite x/y."""
    table = pq.read_table(parquet_path)
    rows = table.to_pydict()
    n = table.num_rows
    if n == 0:
        return {"row_count": 0}

    taxid_order = [int(rows["taxid"][i]) for i in range(n)]

    features, _, knowledge_scores = build_feature_matrix_from_sources(
        matrix_path,
        iucn_tsv,
        taxid_order=taxid_order,
    )

    try:
        import umap
    except ImportError as exc:
        raise ImportError(
            "umap-learn is required for landscape embedding. "
            "Install with: pip install umap-learn"
        ) from exc

    reducer = umap.UMAP(**UMAP_KWARGS)
    coords = reducer.fit_transform(features)
    coords = _scale_coords(np.asarray(coords, dtype=np.float64))

    lx = coords[:, 0].astype(np.float64)
    ly = coords[:, 1].astype(np.float64)

    corr_xy = _corr(lx, ly)
    corr_xk = _corr(lx, knowledge_scores)
    corr_yk = _corr(ly, knowledge_scores)

    columns = {name: rows[name] for name in table.column_names if name not in ("landscape_x", "landscape_y")}
    columns["x"] = lx
    columns["y"] = ly

    out = pa.table(columns)
    pq.write_table(out, parquet_path, compression="zstd")

    stats: dict[str, float] = {
        "row_count": float(n),
        "feature_dim": float(FEATURE_DIM),
        "x_min": float(lx.min()),
        "x_max": float(lx.max()),
        "y_min": float(ly.min()),
        "y_max": float(ly.max()),
        "corr_xy": corr_xy,
        "corr_x_knowledge": corr_xk,
        "corr_y_knowledge": corr_yk,
        "knowledge_p50": float(np.percentile(knowledge_scores, 50)),
        "knowledge_p90": float(np.percentile(knowledge_scores, 90)),
    }

    if abs(corr_xk) > KNOWLEDGE_CORR_WARN or abs(corr_yk) > KNOWLEDGE_CORR_WARN:
        print(
            f"Warning: knowledge_score correlation with layout exceeds {KNOWLEDGE_CORR_WARN}: "
            f"corr(x,k)={corr_xk:.3f}, corr(y,k)={corr_yk:.3f}",
            file=sys.stderr,
        )

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply UMAP landscape coordinates to scatter parquet")
    parser.add_argument("--parquet", type=Path, default=DEFAULT_PARQUET)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--iucn", type=Path, default=DEFAULT_IUCN)
    args = parser.parse_args()

    if not args.parquet.is_file():
        print(f"Error: parquet not found: {args.parquet}", file=sys.stderr)
        return 1
    if not args.matrix.is_file():
        print(f"Error: matrix not found: {args.matrix}", file=sys.stderr)
        return 1

    stats = apply_landscape_coords(
        args.parquet,
        matrix_path=args.matrix,
        iucn_tsv=args.iucn,
    )
    print(
        f"Landscape coords for {int(stats['row_count']):,} species "
        f"({int(stats.get('feature_dim', 0))} features) → {args.parquet}\n"
        f"  x [{stats.get('x_min', 0):.1f}, {stats.get('x_max', 0):.1f}], "
        f"y [{stats.get('y_min', 0):.1f}, {stats.get('y_max', 0):.1f}]\n"
        f"  corr(x,y)={stats.get('corr_xy', 0):.3f}, "
        f"corr(x,knowledge)={stats.get('corr_x_knowledge', 0):.3f}, "
        f"corr(y,knowledge)={stats.get('corr_y_knowledge', 0):.3f}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
