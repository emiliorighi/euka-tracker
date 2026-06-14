#!/usr/bin/env python3
"""Scatter layout registry — parquet paths, tile dirs, metadata."""

from __future__ import annotations

from datetime import date
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
DEFAULT_SCATTER_DIR = _REPO / "data" / "scatter"
DEFAULT_TILES_ROOT = _REPO / "tiles" / "species"

SCATTER_LAYOUTS: dict[str, dict[str, str | bool]] = {
    "landscape": {
        "parquet": "species_landscape.parquet",
        "tile_subdir": "landscape",
        "needs_umap_labels": True,
    },
    "conservation": {
        "parquet": "species_conservation.parquet",
        "tile_subdir": "conservation-similarity",
        "needs_umap_labels": True,
    },
    "threat": {
        "parquet": "species_threat.parquet",
        "tile_subdir": "threat-landscape",
        "needs_umap_labels": True,
    },
    "gap": {
        "parquet": "species_gap.parquet",
        "tile_subdir": "attention-gap",
        "needs_umap_labels": False,
    },
}

DEFAULT_UMAP_VIEW_EXTENT: dict[str, list[float]] = {
    "x": [-250.0, 250.0],
    "y": [-250.0, 250.0],
}

LEGACY_PARQUET = "species_scatter.parquet"


def all_layout_ids() -> list[str]:
    return list(SCATTER_LAYOUTS.keys())


def parquet_path(
    layout: str,
    scatter_dir: Path = DEFAULT_SCATTER_DIR,
) -> Path:
    meta = SCATTER_LAYOUTS.get(layout)
    if meta is None:
        raise ValueError(f"Unknown layout {layout!r}; expected one of {all_layout_ids()}")
    return scatter_dir / str(meta["parquet"])


def tile_dir(
    layout: str,
    version: str | None = None,
    tiles_root: Path = DEFAULT_TILES_ROOT,
) -> Path:
    meta = SCATTER_LAYOUTS.get(layout)
    if meta is None:
        raise ValueError(f"Unknown layout {layout!r}; expected one of {all_layout_ids()}")
    stamp = version or f"v{date.today():%Y%m%d}"
    return tiles_root / str(meta["tile_subdir"]) / stamp


def needs_umap_labels(layout: str) -> bool:
    meta = SCATTER_LAYOUTS.get(layout)
    if meta is None:
        raise ValueError(f"Unknown layout {layout!r}")
    return bool(meta["needs_umap_labels"])
