#!/usr/bin/env python3
"""Threat landscape UMAP layout (threats PCA + systems + realm)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

from pipeline.iucn_text_embeddings import DEFAULT_MODEL, load_threat_features_by_taxid
from pipeline.landscape_features import realm_code, standardize_features, systems_flags
from pipeline.scatter_coords import (
    fit_umap_coords,
    load_matrix_rows_by_taxid,
    write_xy_to_parquet,
)
from pipeline.scatter_landscape import _corr

THREAT_PCA_DIM = 32
REALM_ONE_HOT_DIM = 8
SYSTEMS_DIM = 3
FEATURE_DIM = THREAT_PCA_DIM + SYSTEMS_DIM + REALM_ONE_HOT_DIM


def _realm_one_hot(value: str | None) -> list[float]:
    code = realm_code(value)
    out = [0.0] * REALM_ONE_HOT_DIM
    if 0 <= code < REALM_ONE_HOT_DIM:
        out[code] = 1.0
    return out


def build_threat_features(
    taxid_order: list[int],
    matrix_rows: dict[int, dict[str, str]],
    threat_by_taxid: dict[int, np.ndarray],
) -> np.ndarray:
    zero_threat = np.zeros(THREAT_PCA_DIM, dtype=np.float32)
    rows: list[list[float]] = []
    for taxid in taxid_order:
        row = matrix_rows.get(taxid, {})
        threat = threat_by_taxid.get(taxid, zero_threat)
        terrestrial, freshwater, marine = systems_flags(row.get("systems"))
        realm = _realm_one_hot(row.get("realm"))
        rows.append(
            [
                *threat.astype(np.float64).tolist(),
                float(terrestrial),
                float(freshwater),
                float(marine),
                *realm,
            ]
        )
    features = np.asarray(rows, dtype=np.float64)
    return standardize_features(features)


def apply_threat_coords(
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

    features = build_threat_features(taxid_order, matrix_rows, threat_by_taxid)
    coords = fit_umap_coords(features)
    lx = coords[:, 0]
    ly = coords[:, 1]
    write_xy_to_parquet(parquet_path, lx, ly)

    return {
        "row_count": float(n),
        "feature_dim": float(FEATURE_DIM),
        "x_min": float(lx.min()),
        "x_max": float(lx.max()),
        "y_min": float(ly.min()),
        "y_max": float(ly.max()),
        "corr_xy": _corr(lx, ly),
        "view_extent": {"x": [-250.0, 250.0], "y": [-250.0, 250.0]},
    }
