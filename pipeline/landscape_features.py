#!/usr/bin/env python3
"""Landscape UMAP feature encoding per LANDSCAPE_FEATURES.md."""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any

import numpy as np

from pipeline.iucn_assessments_convert import IUCN_TEXT_FIELDS, load_iucn_text_by_taxid
from pipeline.scatter_export import _lineage_taxids

IUCN_BLOCK_DIM = 26
LINEAGE_HASH_DIM = 64
KNOWLEDGE_DIM = 4
FEATURE_DIM = IUCN_BLOCK_DIM + LINEAGE_HASH_DIM + KNOWLEDGE_DIM  # 94

READ_BUCKETS = ("wgs_long", "wgs_short", "rnaseq_long", "rnaseq_short")

KNOWLEDGE_WEIGHTS = {
    "read": 1.0,
    "assembly": 3.0,
    "annotation": 5.0,
    "iucn_text": 0.5,
}

IUCN_CODE = {
    "least concern": 1,
    "near threatened": 2,
    "vulnerable": 3,
    "endangered": 4,
    "critically endangered": 5,
    "data deficient": 6,
    "extinct in the wild": 7,
    "extinct": 7,
    "lower risk/near threatened": 2,
    "lower risk/least concern": 1,
}

POP_TREND_LABELS = ("Decreasing", "Stable", "Increasing", "Unknown")
REALM_LABELS = (
    "Neotropical",
    "Afrotropical",
    "Indomalayan",
    "Palearctic",
    "Australasian",
    "Nearctic",
    "Oceanian",
)


def _int(value: Any) -> int:
    if value is None or value == "":
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _iucn_code(category: str | None) -> int:
    if not category:
        return 0
    key = category.strip().lower()
    for prefix, code in IUCN_CODE.items():
        if key == prefix or key.startswith(prefix):
            return code
    return 0


def pop_trend_code(value: str | None) -> int:
    if not value:
        return 3
    v = value.strip()
    for i, label in enumerate(POP_TREND_LABELS):
        if v == label:
            return i
    return 3


def systems_flags(value: str | None) -> tuple[int, int, int]:
    if not value:
        return 0, 0, 0
    v = value.lower()
    return (
        int("terrestrial" in v),
        int("freshwater" in v or "inland waters" in v),
        int("marine" in v),
    )


def realm_code(value: str | None) -> int:
    """0–6 standard realm, 7 = other/multi."""
    if not value:
        return 7
    primary = value.split("|", 1)[0].strip()
    for i, label in enumerate(REALM_LABELS):
        if primary == label:
            return i
    return 7


def _one_hot(index: int, size: int) -> list[float]:
    out = [0.0] * size
    if 0 <= index < size:
        out[index] = 1.0
    return out


def lineage_hash_bag(lineage: list[int]) -> list[float]:
    """Multi-hot hash bag of taxids on lineage path (skip Eukaryota root)."""
    buckets = [0.0] * LINEAGE_HASH_DIM
    for tid in lineage[1:]:
        buckets[hash(tid) % LINEAGE_HASH_DIM] = 1.0
    return buckets


def read_count(row: dict[str, Any]) -> int:
    return sum(_int(row.get(f"{b}_count")) for b in READ_BUCKETS)


def iucn_text_length(iucn_text: dict[str, str] | None) -> int:
    if not iucn_text:
        return 0
    return sum(len(iucn_text.get(field) or "") for field in IUCN_TEXT_FIELDS)


def compute_knowledge_features(
    row: dict[str, Any],
    iucn_text: dict[str, str] | None = None,
) -> tuple[list[float], float]:
    """Return 4 log1p knowledge dims and weighted scalar for QA."""
    log_read = math.log1p(read_count(row))
    log_asm = math.log1p(_int(row.get("assembly_count")))
    log_ann = math.log1p(_int(row.get("annotation_count")))
    log_text = math.log1p(iucn_text_length(iucn_text))

    features = [log_read, log_asm, log_ann, log_text]
    score = (
        KNOWLEDGE_WEIGHTS["read"] * log_read
        + KNOWLEDGE_WEIGHTS["assembly"] * log_asm
        + KNOWLEDGE_WEIGHTS["annotation"] * log_ann
        + KNOWLEDGE_WEIGHTS["iucn_text"] * log_text
    )
    return features, score


def build_iucn_block(row: dict[str, Any]) -> list[float]:
    """Public IUCN / biogeography block (26 dims) for conservation UMAP."""
    return _iucn_block(row)


def _iucn_block(row: dict[str, Any]) -> list[float]:
    vec: list[float] = []
    vec.extend(_one_hot(_iucn_code(row.get("redlist_category")), 9))
    vec.extend(_one_hot(pop_trend_code(row.get("population_trend")), 4))
    vec.extend(systems_flags(row.get("systems")))
    vec.extend(_one_hot(realm_code(row.get("realm")), 8))
    vec.append(float(_int(row.get("possibly_extinct"))))
    vec.append(float(_int(row.get("possibly_extinct_ew"))))
    assert len(vec) == IUCN_BLOCK_DIM
    return vec


def matrix_row_to_feature_vector(
    row: dict[str, Any],
    *,
    iucn_text: dict[str, str] | None = None,
) -> list[float]:
    """Build 94-dim feature vector for one species matrix row."""
    species_taxid = _int(row.get("taxid"))
    lineage = _lineage_taxids(row.get("tax_lineage") or "", species_taxid)

    vec: list[float] = []
    vec.extend(_iucn_block(row))
    vec.extend(lineage_hash_bag(lineage))
    knowledge, _ = compute_knowledge_features(row, iucn_text)
    vec.extend(knowledge)
    assert len(vec) == FEATURE_DIM, f"expected {FEATURE_DIM}, got {len(vec)}"
    return vec


def standardize_features(features: np.ndarray) -> np.ndarray:
    """Zero mean, unit variance per column (epsilon for constant cols)."""
    mean = features.mean(axis=0)
    std = features.std(axis=0)
    std = np.where(std < 1e-9, 1.0, std)
    return ((features - mean) / std).astype(np.float32)


def iter_matrix_rows(matrix_path: Path) -> list[dict[str, str]]:
    with matrix_path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def build_feature_matrix_from_sources(
    matrix_path: Path,
    iucn_tsv: Path,
    *,
    taxid_order: list[int] | None = None,
) -> tuple[np.ndarray, list[int], np.ndarray]:
    """
    Build standardized (n, FEATURE_DIM) matrix aligned to taxid_order or matrix row order.

    Returns (features, taxids, knowledge_scores).
    """
    matrix_rows = iter_matrix_rows(matrix_path)
    iucn_text_by_taxid = load_iucn_text_by_taxid(iucn_tsv) if iucn_tsv.is_file() else {}

    row_by_taxid: dict[int, dict[str, str]] = {}
    for row in matrix_rows:
        taxid = _int(row.get("taxid"))
        if taxid:
            row_by_taxid[taxid] = row

    if taxid_order is not None:
        ordered_taxids = taxid_order
    else:
        ordered_taxids = [_int(r.get("taxid")) for r in matrix_rows if _int(r.get("taxid"))]

    n = len(ordered_taxids)
    raw = np.zeros((n, FEATURE_DIM), dtype=np.float32)
    knowledge_scores = np.zeros(n, dtype=np.float64)

    for i, taxid in enumerate(ordered_taxids):
        row = row_by_taxid.get(taxid, {})
        raw[i] = matrix_row_to_feature_vector(row, iucn_text=iucn_text_by_taxid.get(taxid))
        _, knowledge_scores[i] = compute_knowledge_features(
            row,
            iucn_text=iucn_text_by_taxid.get(taxid),
        )

    return standardize_features(raw), ordered_taxids, knowledge_scores


def build_feature_matrix(
    rows: list[dict[str, Any]],
    *,
    iucn_text_by_taxid: dict[int, dict[str, str]] | None = None,
) -> np.ndarray:
    """Return standardized (n_species, FEATURE_DIM) float32 matrix from row dicts."""
    iucn_text_by_taxid = iucn_text_by_taxid or {}
    raw = np.zeros((len(rows), FEATURE_DIM), dtype=np.float32)
    for i, row in enumerate(rows):
        taxid = _int(row.get("taxid"))
        raw[i] = matrix_row_to_feature_vector(
            row,
            iucn_text=iucn_text_by_taxid.get(taxid),
        )
    return standardize_features(raw)
