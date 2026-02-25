#!/usr/bin/env python3
"""
Build tree layout for the eukaryotic taxonomy.
Computes rectangular dendrogram layout: x=depth, y=leaf_order (DFS).
Outputs nodes.parquet with taxid, parent_taxid, x, y, depth.
"""

import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

EUKARYOTA_ROOT = 2759
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
OUTPUT_DIR = REPO_ROOT / "tree_layout"


def load_taxonomy_tree(path: Path) -> pd.DataFrame:
    """Load taxonomy TSV. Columns: parent_id, id, name, rank."""
    print(f"Loading taxonomy from {path}...")
    df = pd.read_csv(
        path,
        sep="\t",
        dtype={"parent_id": "int64", "id": "int64", "name": "str", "rank": "str"},
        usecols=["parent_id", "id"],
        low_memory=False,
    )
    df = df.rename(columns={"parent_id": "parent_taxid", "id": "taxid"})
    print(f"  Loaded {len(df):,} rows")
    return df


def extract_subtree(df: pd.DataFrame, root: int) -> tuple[dict, set]:
    """
    Build parent->children map and set of nodes for subtree rooted at root.
    Returns (children_map, all_taxids).
    """
    children: dict[int, list[int]] = {}
    for _, row in df.iterrows():
        p = int(row["parent_taxid"])
        c = int(row["taxid"])
        if p not in children:
            children[p] = []
        children[p].append(c)

    # BFS/DFS to collect subtree under root
    subtree = set()
    stack = [root]
    while stack:
        n = stack.pop()
        if n in subtree:
            continue
        subtree.add(n)
        for child in children.get(n, []):
            if child not in subtree:
                stack.append(child)

    sub_children = {n: [c for c in children.get(n, []) if c in subtree] for n in subtree}

    print(f"  Subtree under {root}: {len(subtree):,} nodes")
    return sub_children, subtree


def compute_layout(children: dict[int, list[int]], root: int) -> pd.DataFrame:
    """
    DFS traversal to compute depth, leaf_index, x, y.
    x = depth (normalized), y = leaf order (normalized).
    """
    # First pass: assign depth and leaf order via iterative DFS
    depth_map: dict[int, int] = {}
    leaf_index_map: dict[int, int] = {}
    next_leaf = [0]

    stack: list[tuple[int, int, bool]] = [(root, 0, False)]
    post_order: list[int] = []

    while stack:
        n, d, visited = stack.pop()
        if visited:
            kids = children.get(n, [])
            if not kids:
                leaf_index_map[n] = next_leaf[0]
                next_leaf[0] += 1
            else:
                # internal: y = midpoint of children's y range
                child_indices = [leaf_index_map[c] for c in kids]
                leaf_index_map[n] = (min(child_indices) + max(child_indices)) / 2.0
            continue

        depth_map[n] = d
        stack.append((n, d, True))
        for c in sorted(children.get(n, [])):
            stack.append((c, d + 1, False))

    n_leaves = next_leaf[0]
    max_depth = max(depth_map.values()) if depth_map else 0

    parent_map = {c: p for p, kids in children.items() for c in kids}

    rows = []
    for n in depth_map:
        d = depth_map[n]
        y_raw = leaf_index_map.get(n, 0)
        x_norm = d / max_depth if max_depth > 0 else 0
        y_norm = y_raw / (n_leaves - 1) if n_leaves > 1 else 0.5
        parent = parent_map.get(n) if n != root else None
        rows.append({
            "taxid": n,
            "parent_taxid": (parent if parent is not None else -1),
            "x": x_norm,
            "y": y_norm,
            "depth": d,
        })

    return pd.DataFrame(rows)


def main() -> int:
    tree_path = DATA_DIR / "ncbi_taxonomy_tree.tsv"
    if not tree_path.exists():
        print(f"Error: {tree_path} not found", file=sys.stderr)
        return 1

    df = load_taxonomy_tree(tree_path)
    children, subtree = extract_subtree(df, EUKARYOTA_ROOT)

    if EUKARYOTA_ROOT not in subtree:
        print("Error: Eukaryota root not in taxonomy", file=sys.stderr)
        return 1

    print("Computing layout...")
    layout_df = compute_layout(children, EUKARYOTA_ROOT)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "nodes.parquet"
    table = pa.Table.from_pandas(layout_df, preserve_index=False)
    pq.write_table(table, out_path, compression="zstd")
    print(f"Wrote {out_path} ({len(layout_df):,} nodes)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
