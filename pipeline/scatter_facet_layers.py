#!/usr/bin/env python3
"""Precompute facet layer Y columns per DEEPSCATTER_FACETS.md."""

from __future__ import annotations

import math
from typing import Any


def log10p1(value: float | int) -> float:
    return math.log10(float(value) + 1.0)


def compute_major_clade_sizes(rows: list[dict[str, Any]]) -> dict[int, int]:
    """Count matrix species per major_clade_code."""
    sizes: dict[int, int] = {}
    for row in rows:
        code = int(row.get("major_clade_code") or 0)
        sizes[code] = sizes.get(code, 0) + 1
    return sizes


def compute_facet_layers(
    *,
    iucn_code: int,
    log10_catalog_signal: float,
    log10_text_length: float,
    major_clade_size: int,
) -> dict[str, float]:
    """Return layer_a_y … layer_e_y and default display y (layer_c_y)."""
    layer_a = float(iucn_code)
    layer_b = log10_catalog_signal
    layer_c = float(iucn_code) - log10_catalog_signal
    layer_d = log10_catalog_signal + log10_text_length
    layer_e = 1.0 / log10p1(major_clade_size)

    return {
        "layer_a_y": layer_a,
        "layer_b_y": layer_b,
        "layer_c_y": layer_c,
        "layer_d_y": layer_d,
        "layer_e_y": layer_e,
    }
