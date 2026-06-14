#!/usr/bin/env python3
"""Inject per-tile extent/children metadata required by deepscatter 2.x."""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow.feather as feather


def _child_keys(key: str, keys: set[str]) -> list[str]:
    z, x, y = (int(part) for part in key.split("/"))
    out: list[str] = []
    for i in (0, 1):
        for j in (0, 1):
            child = f"{z + 1}/{x * 2 + i}/{y * 2 + j}"
            if child in keys:
                out.append(child)
    return out


def patch_tile_metadata(tile_dir: Path) -> int:
    """
    quadfeather 2.x stores extents in manifest.feather only; deepscatter 2.x
    expects extent + children on each tile's schema metadata.
    """
    manifest_path = tile_dir / "manifest.feather"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"manifest not found: {manifest_path}")

    manifest = feather.read_table(manifest_path)
    rows = {row["key"]: row for row in manifest.to_pylist()}
    keys = set(rows)

    patched = 0
    for key in sorted(keys):
        z, x, y = (int(part) for part in key.split("/"))
        tile_path = tile_dir / str(z) / str(x) / f"{y}.feather"
        if not tile_path.is_file():
            continue

        table = feather.read_table(tile_path)
        existing = dict(table.schema.metadata or {})
        meta = dict(existing)
        meta[b"extent"] = rows[key]["extent"].encode("utf-8")
        meta[b"children"] = json.dumps(_child_keys(key, keys)).encode("utf-8")
        # deepscatter bundles apache-arrow 13, which cannot decode zstd feather bodies.
        feather.write_feather(
            table.replace_schema_metadata(meta),
            tile_path,
            compression="uncompressed",
        )
        patched += 1

    return patched
