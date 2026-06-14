#!/usr/bin/env python3
"""Attention gap layout — literal catalog attention vs conservation need axes."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

from pipeline.scatter_coords import compute_percentile_extent, write_xy_to_parquet
from pipeline.scatter_landscape import _corr


def apply_gap_coords(parquet_path: Path) -> dict[str, float | dict[str, list[float]]]:
    table = pq.read_table(
        parquet_path,
        columns=["attention_score", "conservation_need"],
    )
    rows = table.to_pydict()
    n = table.num_rows
    if n == 0:
        extent = {"x": [0.0, 1.0], "y": [0.0, 1.0]}
        return {"row_count": 0, "view_extent": extent}

    attention = np.asarray(rows["attention_score"], dtype=np.float64)
    need = np.asarray(rows["conservation_need"], dtype=np.float64)
    write_xy_to_parquet(parquet_path, attention, need)
    view_extent = compute_percentile_extent(attention, need)

    return {
        "row_count": float(n),
        "x_min": float(attention.min()),
        "x_max": float(attention.max()),
        "y_min": float(need.min()),
        "y_max": float(need.max()),
        "corr_xy": _corr(attention, need),
        "view_extent": view_extent,
    }
