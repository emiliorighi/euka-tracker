"""Fit UMAP layout on IUCN lineage features and write scatter parquet."""

from __future__ import annotations

import argparse
import sys
import time
import zlib
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.ipc as ipc
import pyarrow.parquet as pq

from pipeline.scatter_derived import append_derived_scatter_columns
from pipeline.scatter_features import (
    FEATURE_DIM,
    LINEAGE_COLUMNS,
    build_feature_matrix_columnar,
)
from pipeline.schema import IUCN_MATRIX_FIELDS

PIPELINE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = PIPELINE_DIR / "output" / "iucn_species_matrix.tsv"
DEFAULT_PARQUET = PIPELINE_DIR / "output" / "iucn_species_scatter.parquet"
DEFAULT_ARROW = PIPELINE_DIR / "output" / "iucn_species_scatter.arrow"

UMAP_KWARGS = {
    "n_neighbors": 30,
    "min_dist": 0.5,
    "spread": 1.5,
    "metric": "cosine",
    "n_components": 2,
    "n_jobs": -1,
    "init": "pca",
}

COORD_SCALE = 250.0
JITTER_SCALE = COORD_SCALE * 0.003


def _scale_coords(coords: np.ndarray) -> np.ndarray:
    if coords.size == 0:
        return coords
    lo = coords.min(axis=0)
    hi = coords.max(axis=0)
    span = np.maximum(hi - lo, 1e-9)
    centered = (coords - lo) / span
    return (centered * 2.0 - 1.0) * COORD_SCALE


def _scatter_is_up_to_date(*, matrix_path: Path, output_path: Path) -> bool:
    if not output_path.is_file() or not matrix_path.is_file():
        return False
    return output_path.stat().st_mtime >= matrix_path.stat().st_mtime


def _read_matrix_table(matrix_path: Path) -> pa.Table:
    parse_opts = pacsv.ParseOptions(delimiter="\t")
    read_opts = pacsv.ReadOptions(use_threads=True)
    convert_opts = pacsv.ConvertOptions(include_columns=list(IUCN_MATRIX_FIELDS))
    return pacsv.read_csv(matrix_path, parse_options=parse_opts, read_options=read_opts, convert_options=convert_opts)


def _lineage_columns(table: pa.Table) -> dict[str, list[str]]:
    n = table.num_rows
    out: dict[str, list[str]] = {}
    for col in LINEAGE_COLUMNS:
        if col in table.column_names:
            out[col] = [str(v or "") for v in table.column(col).to_pylist()]
        else:
            out[col] = [""] * n
    return out


def _dedupe_features(features: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return unique feature rows and inverse index mapping each row -> unique row."""
    structured = np.ascontiguousarray(features).view(
        np.dtype((np.void, features.dtype.itemsize * features.shape[1]))
    )
    _, unique_idx, inverse = np.unique(structured, return_index=True, return_inverse=True)
    return features[unique_idx], inverse.ravel()


def _apply_jitter(coords: np.ndarray, taxon_ids: list[str]) -> np.ndarray:
    """Spread co-lineage species with deterministic jitter keyed by internalTaxonId."""
    out = coords.copy()
    for i, taxon_id in enumerate(taxon_ids):
        seed = zlib.crc32(str(taxon_id).encode("utf-8")) & 0xFFFFFFFF
        rng = np.random.default_rng(seed)
        out[i] += rng.uniform(-JITTER_SCALE, JITTER_SCALE, size=2)
    return out


def _run_umap(features: np.ndarray) -> np.ndarray:
    try:
        import umap
    except ImportError as exc:
        raise ImportError(
            "umap-learn is required for scatter layout. Install with: pip install umap-learn"
        ) from exc

    unique_features, inverse = _dedupe_features(features)
    n_total = len(features)
    n_unique = len(unique_features)
    print(
        f"Running UMAP on {n_unique:,} unique lineage vectors "
        f"({n_total:,} species, {100.0 * (1 - n_unique / max(n_total, 1)):.1f}% deduped)...",
        file=sys.stderr,
    )

    t0 = time.perf_counter()
    reducer = umap.UMAP(**UMAP_KWARGS)
    unique_coords = reducer.fit_transform(unique_features)
    elapsed = time.perf_counter() - t0
    print(f"UMAP finished in {elapsed:.1f}s", file=sys.stderr)
    return unique_coords[inverse]


def _write_scatter_arrow(table: pa.Table, arrow_path: Path) -> None:
    arrow_path.parent.mkdir(parents=True, exist_ok=True)
    with arrow_path.open("wb") as handle:
        with ipc.new_file(handle, table.schema) as writer:
            writer.write_table(table)


def build_scatter_parquet(
    *,
    matrix_path: Path = DEFAULT_MATRIX,
    output_path: Path = DEFAULT_PARQUET,
    arrow_path: Path = DEFAULT_ARROW,
    force: bool = False,
) -> tuple[Path, dict[str, float]]:
    if not matrix_path.is_file():
        raise FileNotFoundError(f"Matrix not found: {matrix_path}")

    if not force and _scatter_is_up_to_date(matrix_path=matrix_path, output_path=output_path):
        row_count = pq.read_metadata(output_path).num_rows
        print(
            f"Using cached {output_path} ({row_count:,} rows; "
            f"newer than {matrix_path.name})",
            file=sys.stderr,
        )
        cached = pq.read_table(output_path)
        scatter_table = append_derived_scatter_columns(cached)
        if scatter_table.schema != cached.schema:
            pq.write_table(scatter_table, output_path, compression="zstd")
            _write_scatter_arrow(scatter_table, arrow_path)
            print(f"Updated derived columns on cached scatter parquet", file=sys.stderr)
        elif not arrow_path.is_file():
            _write_scatter_arrow(scatter_table, arrow_path)
            print(f"Wrote missing {arrow_path}", file=sys.stderr)
        return output_path, {"row_count": float(row_count), "feature_dim": float(FEATURE_DIM)}

    table = _read_matrix_table(matrix_path)
    n_rows = table.num_rows
    if n_rows == 0:
        raise ValueError(f"Matrix is empty: {matrix_path}")

    print(f"Building UMAP features ({FEATURE_DIM} dims) for {n_rows:,} species...", file=sys.stderr)
    features = build_feature_matrix_columnar(_lineage_columns(table))
    coords = _run_umap(features)
    coords = _scale_coords(np.asarray(coords, dtype=np.float64))

    taxon_ids = [str(v or "") for v in table.column("internalTaxonId").to_pylist()]
    coords = _apply_jitter(coords, taxon_ids)

    scatter_table = table.append_column("x", pa.array(coords[:, 0], type=pa.float64()))
    scatter_table = scatter_table.append_column("y", pa.array(coords[:, 1], type=pa.float64()))
    scatter_table = append_derived_scatter_columns(scatter_table)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(scatter_table, output_path, compression="zstd")
    _write_scatter_arrow(scatter_table, arrow_path)

    lx = coords[:, 0]
    ly = coords[:, 1]
    stats: dict[str, float] = {
        "row_count": float(n_rows),
        "feature_dim": float(FEATURE_DIM),
        "x_min": float(lx.min()),
        "x_max": float(lx.max()),
        "y_min": float(ly.min()),
        "y_max": float(ly.max()),
    }
    print(
        f"Wrote {output_path} ({n_rows:,} rows)\n"
        f"Wrote {arrow_path}\n"
        f"  x [{stats['x_min']:.1f}, {stats['x_max']:.1f}], "
        f"y [{stats['y_min']:.1f}, {stats['y_max']:.1f}]",
        file=sys.stderr,
    )
    return output_path, stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Build IUCN scatter parquet with UMAP coordinates")
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--output", type=Path, default=DEFAULT_PARQUET)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild scatter parquet even when output is newer than matrix",
    )
    args = parser.parse_args()
    build_scatter_parquet(matrix_path=args.matrix, output_path=args.output, force=args.force)


if __name__ == "__main__":
    main()
