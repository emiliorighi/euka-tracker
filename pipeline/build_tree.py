#!/usr/bin/env python3
"""
Build tree from hierarchy TSV (parent_id, id, name, rank).

Reads ncbi_taxonomy_tree.tsv format:
  parent_id, id, name, rank

Root: node whose parent_id is not in the set of all ids.
"""

from collections import defaultdict
from pathlib import Path
from typing import Any


EUKARYOTA_TAXID = "2759"


def build_tree(tsv_path: Path, root_id: str | None = None) -> dict[str, Any]:
    """
    Load hierarchy TSV and return tree structure.

    Args:
        tsv_path: path to hierarchy TSV
        root_id: optional root node id (e.g. "2759" for Eukaryota). If given,
                 only the subtree rooted at this node is included.

    Returns:
        tree: recursive dict {"id", "name", "rank", "children": [...]}
        nodes: flat dict id -> {name, rank} for lookup
    """
    edges: list[tuple[str, str]] = []
    node_info: dict[str, dict] = {}

    with open(tsv_path) as f:
        header = next(f).strip().split("\t")
        col_map = {h.lower(): i for i, h in enumerate(header)}
        pi = col_map.get("parent_id", 0)
        ii = col_map.get("id", 1)
        ni = col_map.get("name", col_map.get("name", 2)) if "name" in col_map else 2
        ri = col_map.get("rank", 3) if "rank" in col_map else 3

        for line in f:
            row = line.strip().split("\t")
            if len(row) <= max(pi, ii):
                continue
            parent = row[pi].strip()
            child = row[ii].strip()
            name = row[ni] if len(row) > ni else child
            rank = row[ri] if len(row) > ri else "no rank"
            edges.append((parent, child))
            node_info[child] = {"name": name, "rank": rank}

    all_ids = {child for _, child in edges} | {p for p, _ in edges if p}
    # Root: node whose parent is not in all_ids (external parent) or is 0/empty
    roots = set()
    children: dict[str, list[str]] = defaultdict(list)

    for parent, child in edges:
        if parent in ("0", "") or parent not in all_ids:
            roots.add(child)
        else:
            children[parent].append(child)

    if not roots:
        # Fallback: node that is never a child
        children_set = {c for kids in children.values() for c in kids}
        roots = all_ids - children_set

    if root_id is not None:
        root_id = str(root_id)
        if root_id not in all_ids:
            raise ValueError(f"root_id {root_id} not found in hierarchy")
    else:
        root_id = next(iter(roots)) if len(roots) == 1 else sorted(roots)[0]

    def make_node(nid: str) -> dict:
        info = node_info.get(nid, {})
        return {
            "id": nid,
            "name": info.get("name", nid),
            "rank": info.get("rank", "no rank"),
            "children": [make_node(c) for c in sorted(children.get(nid, []))],
        }

    tree = make_node(root_id)
    return {"tree": tree, "nodes": node_info, "root_id": root_id}
