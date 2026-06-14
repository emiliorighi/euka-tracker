#!/usr/bin/env python3
"""Assign taxonomic leaf order (DFS) and log-width X bands for scatter coordinates."""

from __future__ import annotations

import math
import sqlite3
from pathlib import Path

from pipeline.ncbi_taxonomy_fetch import EUKARYOTA_TAXID

COORD_SCALE = 250.0


def _load_children(conn: sqlite3.Connection, root: int) -> dict[int, list[int]]:
    """Build parent→children map for the subtree rooted at root."""
    children: dict[int, list[int]] = {}
    frontier = [root]
    seen: set[int] = {root}
    while frontier:
        chunk = frontier
        frontier = []
        placeholders = ",".join("?" * len(chunk))
        rows = conn.execute(
            f"SELECT taxid, parent_taxid FROM taxa WHERE parent_taxid IN ({placeholders})",
            chunk,
        ).fetchall()
        for taxid, parent in rows:
            tid = int(taxid)
            pid = int(parent)
            if tid in seen:
                continue
            seen.add(tid)
            children.setdefault(pid, []).append(tid)
            frontier.append(tid)
    for kids in children.values():
        kids.sort()
    return children


def _mark_matrix_branches(
    children: dict[int, list[int]],
    matrix_taxids: set[int],
    root: int,
) -> set[int]:
    """Nodes on paths to at least one matrix taxid (including root)."""
    keep: set[int] = set()

    def dfs(node: int) -> bool:
        in_matrix = node in matrix_taxids
        child_hit = False
        for child in children.get(node, []):
            if dfs(child):
                child_hit = True
        if in_matrix or child_hit:
            keep.add(node)
            return True
        return False

    dfs(root)
    return keep


def _subtree_matrix_counts(
    children: dict[int, list[int]],
    keep: set[int],
    matrix_taxids: set[int],
    root: int,
) -> dict[int, int]:
    """Matrix species count in each pruned subtree (memoized bottom-up)."""
    counts: dict[int, int] = {}

    def count(node: int) -> int:
        if node not in keep:
            return 0
        if node in counts:
            return counts[node]
        total = 1 if node in matrix_taxids else 0
        for child in children.get(node, []):
            if child in keep:
                total += count(child)
        counts[node] = total
        return total

    count(root)
    return counts


def _layout_log_width(
    node: int,
    x_left: float,
    x_right: float,
    *,
    children: dict[int, list[int]],
    keep: set[int],
    matrix_taxids: set[int],
    subtree_counts: dict[int, int],
    x_by_taxid: dict[int, float],
    index_by_taxid: dict[int, int],
    next_index: list[int],
) -> None:
    """Recursively assign x = clade_offset + local position within log-width band."""
    if node not in keep:
        return

    kept_children = [c for c in children.get(node, []) if c in keep]

    if not kept_children:
        if node in matrix_taxids:
            x_by_taxid[node] = (x_left + x_right) / 2.0
            index_by_taxid[node] = next_index[0]
            next_index[0] += 1
        return

    weights = [math.log1p(subtree_counts.get(c, 1)) for c in kept_children]
    total_w = sum(weights) or 1.0
    span = x_right - x_left
    x_pos = x_left

    for child, weight in zip(kept_children, weights):
        child_span = span * (weight / total_w)
        _layout_log_width(
            child,
            x_pos,
            x_pos + child_span,
            children=children,
            keep=keep,
            matrix_taxids=matrix_taxids,
            subtree_counts=subtree_counts,
            x_by_taxid=x_by_taxid,
            index_by_taxid=index_by_taxid,
            next_index=next_index,
        )
        x_pos += child_span


def compute_tax_leaf_order(
    matrix_taxids: set[int],
    db_path: Path,
    *,
    root: int = EUKARYOTA_TAXID,
) -> dict[int, tuple[int, float]]:
    """
    Log-width DFS layout for matrix species under Eukaryota.

    width(child) ∝ log1p(matrix_species_in_subtree); x = center of allocated band.

    Returns taxid → (tax_leaf_index, tax_leaf_x) where tax_leaf_x ∈ [-250, 250].
    """
    if not matrix_taxids:
        return {}

    conn = sqlite3.connect(db_path)
    try:
        children = _load_children(conn, root)
        keep = _mark_matrix_branches(children, matrix_taxids, root)
        subtree_counts = _subtree_matrix_counts(children, keep, matrix_taxids, root)

        x_by_taxid: dict[int, float] = {}
        index_by_taxid: dict[int, int] = {}
        next_index = [0]

        _layout_log_width(
            root,
            -COORD_SCALE,
            COORD_SCALE,
            children=children,
            keep=keep,
            matrix_taxids=matrix_taxids,
            subtree_counts=subtree_counts,
            x_by_taxid=x_by_taxid,
            index_by_taxid=index_by_taxid,
            next_index=next_index,
        )

        return {
            taxid: (index_by_taxid[taxid], x_by_taxid[taxid])
            for taxid in x_by_taxid
        }
    finally:
        conn.close()


def assign_lineage_fallback_order(
    missing: set[int],
    lineage_by_taxid: dict[int, list[int]],
    start_index: int,
    *,
    n_mapped: int = 0,
) -> dict[int, tuple[int, float]]:
    """
    Append taxids missing from tree index in a trailing log-width block at +X.

    Uniform spacing inside the block; block width ∝ log1p(n_missing).
    """
    if not missing:
        return {}

    ordered = sorted(
        missing,
        key=lambda tid: tuple(lineage_by_taxid.get(tid, [tid])),
    )
    n_missing = len(ordered)
    total_span = 2.0 * COORD_SCALE
    block_width = total_span * math.log1p(n_missing) / (
        math.log1p(n_missing) + math.log1p(max(n_mapped, 1))
    )
    x_right = COORD_SCALE
    x_left = x_right - block_width

    out: dict[int, tuple[int, float]] = {}
    for i, tid in enumerate(ordered):
        idx = start_index + i
        if n_missing == 1:
            x = (x_left + x_right) / 2.0
        else:
            x = x_left + (i + 0.5) / n_missing * block_width
        out[tid] = (idx, x)
    return out
