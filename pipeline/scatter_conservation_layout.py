#!/usr/bin/env python3
"""Conservation similarity UMAP layout (IUCN block + threats PCA)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

from pipeline.iucn_text_embeddings import DEFAULT_MODEL, load_threat_features_by_taxid
from pipeline.landscape_features import IUCN_BLOCK_DIM, build_iucn_block, standardize_features
from pipeline.scatter_coords import (
    fit_umap_coords,
    load_matrix_rows_by_taxid,
    warn_iucn_axis_correlation,
    write_xy_to_parquet,
)
from pipeline.scatter_landscape import _corr

THREAT_PCA_DIM = 32
FEATURE_DIM = IUCN_BLOCK_DIM + THREAT_PCA_DIM


def build_conservation_features(
    taxid_order: list[int],
    matrix_rows: dict[int, dict[str, str]],
    threat_by_taxid: dict[int, np.ndarray],
) -> np.ndarray:
    zero_threat = np.zeros(THREAT_PCA_DIM, dtype=np.float32)
    rows: list[list[float]] = []
    for taxid in taxid_order:
        row = matrix_rows.get(taxid, {})
        iucn = build_iucn_block(row)
        threat = threat_by_taxid.get(taxid, zero_threat)
        rows.append([*iucn, *threat.astype(np.float64).tolist()])
    features = np.asarray(rows, dtype=np.float64)
    return standardize_features(features)


def apply_conservation_coords(
    parquet_path: Path,
    *,
    matrix_path: Path,
    threat_cache_dir: Path,
) -> dict[str, float | dict[str, list[float]]]:
    table = pq.read_table(parquet_path)
    rows = table.to_pydict()
    n = table.num_rows
    if n == 0:
        return {"row_count": 0, "view_extent": {"x": [-250.0, 250.0], "y": [-250.0, 250.0]}}

    taxid_order = [int(rows["taxid"][i]) for i in range(n)]
    matrix_rows = load_matrix_rows_by_taxid(matrix_path)
    threat_by_taxid = load_threat_features_by_taxid(threat_cache_dir, model_name=DEFAULT_MODEL)

    features = build_conservation_features(taxid_order, matrix_rows, threat_by_taxid)
    coords = fit_umap_coords(features)
    lx = coords[:, 0]
    ly = coords[:, 1]
    write_xy_to_parquet(parquet_path, lx, ly)

    iucn_codes = np.asarray(rows["iucn_code"], dtype=np.float64)
    corr_x_iucn = warn_iucn_axis_correlation(lx, iucn_codes, layout="conservation")

    return {
        "row_count": float(n),
        "feature_dim": float(FEATURE_DIM),
        "x_min": float(lx.min()),
        "x_max": float(lx.max()),
        "y_min": float(ly.min()),
        "y_max": float(ly.max()),
        "corr_xy": _corr(lx, ly),
        "corr_x_iucn": corr_x_iucn,
        "view_extent": {"x": [-250.0, 250.0], "y": [-250.0, 250.0]},
    }
