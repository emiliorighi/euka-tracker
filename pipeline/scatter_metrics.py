#!/usr/bin/env python3
"""Catalog and conservation metrics for scatter export and gap layout."""

from __future__ import annotations

import math
from typing import Any

READ_BUCKETS = ("wgs_long", "wgs_short", "rnaseq_long", "rnaseq_short")

ATTENTION_WEIGHTS = {
    "run": 1.0,
    "assembly": 3.0,
    "annotation": 5.0,
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
    key = value.strip().lower()
    if key == "decreasing":
        return 0
    if key == "stable":
        return 1
    if key == "increasing":
        return 2
    return 3


def run_count(row: dict[str, Any]) -> int:
    return sum(_int(row.get(f"{b}_count")) for b in READ_BUCKETS)


def compute_data_tier(row: dict[str, Any]) -> int:
    rc = run_count(row)
    asm = _int(row.get("assembly_count"))
    ann = _int(row.get("annotation_count"))
    if ann > 0:
        return 3
    if asm > 0:
        return 2
    if rc > 0:
        return 1
    return 0


def compute_attention_score(row: dict[str, Any]) -> float:
    rc = run_count(row)
    asm = _int(row.get("assembly_count"))
    ann = _int(row.get("annotation_count"))
    return (
        ATTENTION_WEIGHTS["run"] * math.log10(rc + 1)
        + ATTENTION_WEIGHTS["assembly"] * math.log10(asm + 1)
        + ATTENTION_WEIGHTS["annotation"] * math.log10(ann + 1)
    )


def compute_conservation_need(row: dict[str, Any]) -> float:
    code = float(_iucn_code(row.get("redlist_category")))
    trend = pop_trend_code(row.get("population_trend"))
    decreasing = 1.0 if trend == 0 else 0.0
    possibly_extinct = float(_int(row.get("possibly_extinct")))
    possibly_extinct_ew = float(_int(row.get("possibly_extinct_ew")))
    return (
        code
        + 0.5 * decreasing
        + 2.0 * possibly_extinct
        + 1.0 * possibly_extinct_ew
    )


def scatter_metric_fields(row: dict[str, Any]) -> dict[str, int | float]:
    rc = run_count(row)
    asm = _int(row.get("assembly_count"))
    ann = _int(row.get("annotation_count"))
    return {
        "run_count": rc,
        "assembly_count": asm,
        "annotation_count": ann,
        "log10_run_count": math.log10(rc + 1),
        "attention_score": compute_attention_score(row),
        "data_tier": compute_data_tier(row),
        "conservation_need": compute_conservation_need(row),
    }
