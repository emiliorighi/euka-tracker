"""Feature encoding for lineage-only UMAP scatter layout."""

from __future__ import annotations

import zlib
from typing import Any

import numpy as np

from pipeline.iucn_taxonomy import iucn_lineage_tokens

LINEAGE_HASH_DIM = 64
FEATURE_DIM = LINEAGE_HASH_DIM

LINEAGE_COLUMNS = (
    "kingdomName",
    "phylumName",
    "className",
    "orderName",
    "familyName",
    "genusName",
)


def _stable_bucket(token: str) -> int:
    return zlib.crc32(token.encode("utf-8")) % LINEAGE_HASH_DIM


def lineage_hash_bag(tokens: list[str]) -> list[float]:
    """Multi-hot hash bag of lineage tokens (kingdom → genus)."""
    buckets = [0.0] * LINEAGE_HASH_DIM
    for token in tokens:
        if token:
            buckets[_stable_bucket(token)] = 1.0
    return buckets


def row_to_feature_vector(row: dict[str, Any]) -> list[float]:
    vec = lineage_hash_bag(iucn_lineage_tokens(row))
    assert len(vec) == FEATURE_DIM
    return vec


def standardize_features(features: np.ndarray) -> np.ndarray:
    mean = features.mean(axis=0)
    std = features.std(axis=0)
    std = np.where(std < 1e-9, 1.0, std)
    return ((features - mean) / std).astype(np.float32)


def build_feature_matrix(rows: list[dict[str, Any]]) -> np.ndarray:
    raw = np.zeros((len(rows), FEATURE_DIM), dtype=np.float32)
    for i, row in enumerate(rows):
        raw[i] = row_to_feature_vector(row)
    return standardize_features(raw)


def build_feature_matrix_columnar(lineage_by_column: dict[str, list[str]]) -> np.ndarray:
    """Build feature matrix from column lists (same length, IUCN lineage fields)."""
    n = len(next(iter(lineage_by_column.values())))
    raw = np.zeros((n, FEATURE_DIM), dtype=np.float32)
    for i in range(n):
        row = {col: lineage_by_column[col][i] for col in LINEAGE_COLUMNS}
        raw[i] = row_to_feature_vector(row)
    return standardize_features(raw)
