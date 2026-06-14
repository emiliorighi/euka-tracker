#!/usr/bin/env python3
"""Hierarchical circle-pack disc layout for scatter x/y coordinates."""

from __future__ import annotations

import math
import sqlite3
from pathlib import Path

from pipeline.ncbi_taxonomy_fetch import EUKARYOTA_TAXID
from pipeline.scatter_phylo_order import (
    COORD_SCALE,
    _load_children,
    _mark_matrix_branches,
    _subtree_matrix_counts,
)

GOLDEN_ANGLE = math.pi * (3.0 - math.sqrt(5.0))
DISC_PAD = 0.92
FALLBACK_CENTER = (220.0, 220.0)
FALLBACK_RADIUS = 28.0


def _child_disc_radii(
    parent_r: float,
    child_nodes: list[int],
    subtree_counts: dict[int, int],
) -> list[float]:
    weights = [math.log1p(subtree_counts.get(c, 1)) for c in child_nodes]
    total = sum(weights) or 1.0
    return [parent_r * math.sqrt(w / total) * DISC_PAD for w in weights]


def _spiral_offsets(n: int, parent_r: float, child_radii: list[float]) -> list[tuple[float, float]]:
    """Golden-angle spiral offsets for child disc centers inside parent."""
    if n == 0:
        return []
    if n == 1:
        return [(0.0, 0.0)]

    offsets: list[tuple[float, float]] = []
    for i, r_i in enumerate(child_radii):
        theta = i * GOLDEN_ANGLE
        dist = max(r_i * 0.55, parent_r * 0.04)
        step = max(parent_r / max(n, 1), r_i * 0.35)
        for _ in range(128):
            ox = dist * math.cos(theta)
            oy = dist * math.sin(theta)
            if math.hypot(ox, oy) + r_i <= parent_r * 0.98:
                offsets.append((ox, oy))
                break
            dist += step
        else:
            scale = (parent_r * 0.85 - r_i) / max(math.hypot(dist * math.cos(theta), dist * math.sin(theta)), 1e-9)
            offsets.append((dist * math.cos(theta) * scale, dist * math.sin(theta) * scale))
    return offsets


def _subtree_matrix_leaves(
    node: int,
    *,
    children: dict[int, list[int]],
    keep: set[int],
    matrix_taxids: set[int],
) -> list[int]:
    kept = [c for c in children.get(node, []) if c in keep]
    if not kept:
        return [node] if node in matrix_taxids else []
    leaves: list[int] = []
    for child in kept:
        leaves.extend(
            _subtree_matrix_leaves(
                child,
                children=children,
                keep=keep,
                matrix_taxids=matrix_taxids,
            )
        )
    return leaves


def _subtree_is_uniform_leaves(
    node: int,
    *,
    children: dict[int, list[int]],
    keep: set[int],
    matrix_taxids: set[int],
) -> bool:
    """True when every kept descendant is a matrix species (spread as siblings)."""
    if node not in keep:
        return False
    kept = [c for c in children.get(node, []) if c in keep]
    if not kept:
        return node in matrix_taxids
    return all(child in matrix_taxids for child in kept)


def _vogel_in_disc(
    cx: float,
    cy: float,
    radius: float,
    taxids: list[int],
    layout: dict[int, tuple[float, float, float]],
    index_by_taxid: dict[int, int],
    next_index: list[int],
) -> None:
    n = len(taxids)
    if n == 0:
        return
    if n == 1:
        tid = taxids[0]
        layout[tid] = (cx, cy, radius)
        index_by_taxid[tid] = next_index[0]
        next_index[0] += 1
        return

    for i, tid in enumerate(taxids):
        r = radius * math.sqrt((i + 0.5) / n) * 0.95
        theta = i * GOLDEN_ANGLE
        layout[tid] = (cx + r * math.cos(theta), cy + r * math.sin(theta), radius / n)
        index_by_taxid[tid] = next_index[0]
        next_index[0] += 1


def _all_matrix_leaf_siblings(
    child_nodes: list[int],
    children: dict[int, list[int]],
    keep: set[int],
    matrix_taxids: set[int],
) -> bool:
    if not child_nodes:
        return False
    for node in child_nodes:
        if node not in matrix_taxids:
            return False
        grand = [g for g in children.get(node, []) if g in keep]
        if grand:
            return False
    return True


def _layout_disc(
    node: int,
    cx: float,
    cy: float,
    radius: float,
    *,
    children: dict[int, list[int]],
    keep: set[int],
    matrix_taxids: set[int],
    subtree_counts: dict[int, int],
    layout: dict[int, tuple[float, float, float]],
    index_by_taxid: dict[int, int],
    next_index: list[int],
) -> None:
    if node not in keep:
        return

    kept_children = [c for c in children.get(node, []) if c in keep]

    if not kept_children:
        if node in matrix_taxids:
            layout[node] = (cx, cy, radius)
            index_by_taxid[node] = next_index[0]
            next_index[0] += 1
        return

    if _subtree_is_uniform_leaves(
        node,
        children=children,
        keep=keep,
        matrix_taxids=matrix_taxids,
    ):
        species = _subtree_matrix_leaves(
            node,
            children=children,
            keep=keep,
            matrix_taxids=matrix_taxids,
        )
        _vogel_in_disc(cx, cy, radius, species, layout, index_by_taxid, next_index)
        return

    if _all_matrix_leaf_siblings(kept_children, children, keep, matrix_taxids):
        _vogel_in_disc(cx, cy, radius, kept_children, layout, index_by_taxid, next_index)
        return

    child_radii = _child_disc_radii(radius, kept_children, subtree_counts)
    offsets = _spiral_offsets(len(kept_children), radius, child_radii)

    for child, r_i, (ox, oy) in zip(kept_children, child_radii, offsets):
        _layout_disc(
            child,
            cx + ox,
            cy + oy,
            r_i,
            children=children,
            keep=keep,
            matrix_taxids=matrix_taxids,
            subtree_counts=subtree_counts,
            layout=layout,
            index_by_taxid=index_by_taxid,
            next_index=next_index,
        )


def _scale_layout_to_bounds(
    layout: dict[int, tuple[float, float, float]],
    *,
    target: float = COORD_SCALE,
) -> None:
    if not layout:
        return

    xs = [v[0] for v in layout.values()]
    ys = [v[1] for v in layout.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(max_x - min_x, 1e-9)
    span_y = max(max_y - min_y, 1e-9)
    span = max(span_x, span_y)
    scale = (2.0 * target) / span
    mid_x = (min_x + max_x) / 2.0
    mid_y = (min_y + max_y) / 2.0

    for taxid, (x, y, r) in list(layout.items()):
        layout[taxid] = (
            (x - mid_x) * scale,
            (y - mid_y) * scale,
            r * scale,
        )


def compute_phylo_pack_layout(
    matrix_taxids: set[int],
    db_path: Path,
    *,
    root: int = EUKARYOTA_TAXID,
) -> tuple[dict[int, tuple[float, float, float]], dict[int, int]]:
    """
    Pack-disc layout for matrix species under Eukaryota.

    Returns:
        layout: taxid → (layout_x, layout_y, pack_disc_r)
        leaf_index: taxid → DFS order index
    """
    if not matrix_taxids:
        return {}, {}

    conn = sqlite3.connect(db_path)
    try:
        children = _load_children(conn, root)
        keep = _mark_matrix_branches(children, matrix_taxids, root)
        subtree_counts = _subtree_matrix_counts(children, keep, matrix_taxids, root)

        layout: dict[int, tuple[float, float, float]] = {}
        index_by_taxid: dict[int, int] = {}
        next_index = [0]

        _layout_disc(
            root,
            0.0,
            0.0,
            COORD_SCALE,
            children=children,
            keep=keep,
            matrix_taxids=matrix_taxids,
            subtree_counts=subtree_counts,
            layout=layout,
            index_by_taxid=index_by_taxid,
            next_index=next_index,
        )

        _scale_layout_to_bounds(layout)
        return layout, index_by_taxid
    finally:
        conn.close()


def assign_lineage_fallback_pack(
    missing: set[int],
    lineage_by_taxid: dict[int, list[int]],
    start_index: int,
) -> tuple[dict[int, tuple[float, float, float]], dict[int, int]]:
    """Place taxids missing from SQLite tree in a trailing cluster disc."""
    if not missing:
        return {}, {}

    ordered = sorted(
        missing,
        key=lambda tid: tuple(lineage_by_taxid.get(tid, [tid])),
    )
    layout: dict[int, tuple[float, float, float]] = {}
    index_by_taxid: dict[int, int] = {}
    cx, cy = FALLBACK_CENTER
    radius = FALLBACK_RADIUS
    n = len(ordered)

    for i, tid in enumerate(ordered):
        if n == 1:
            x, y = cx, cy
        else:
            r = radius * math.sqrt((i + 0.5) / n) * 0.95
            theta = i * GOLDEN_ANGLE
            x = cx + r * math.cos(theta)
            y = cy + r * math.sin(theta)
        layout[tid] = (x, y, radius / max(n, 1))
        index_by_taxid[tid] = start_index + i

    return layout, index_by_taxid
