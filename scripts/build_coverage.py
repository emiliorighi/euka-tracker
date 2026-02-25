#!/usr/bin/env python3
"""
Assign coverage states to species and propagate up the tree.
Outputs coverage_nodes.parquet: taxid, coverage_state (0-5).
"""

import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Coverage state encoding (priority: higher = better)
FULL = 5
GENOME_ANNOTATION_ONLY = 4
GENOME_READS_NO_ANNOTATION = 3
GENOME_ONLY = 2
READS_ONLY = 1
NO_DATA = 0

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
TREE_LAYOUT_DIR = REPO_ROOT / "tree_layout"
OUTPUT_DIR = REPO_ROOT / "coverage"


def species_state(has_assembly: bool, has_annotation: bool, has_reads: bool) -> int:
    """Compute coverage state for a species (leaf)."""
    asm = bool(has_assembly)
    ann = bool(has_annotation)
    reads = bool(has_reads)

    if ann and reads:
        return FULL
    if ann and not reads:
        return GENOME_ANNOTATION_ONLY
    if asm and not ann and reads:
        return GENOME_READS_NO_ANNOTATION
    if asm and not ann and not reads:
        return GENOME_ONLY
    if not asm and reads:
        return READS_ONLY
    return NO_DATA


def load_species_matrix(path: Path) -> dict[int, int]:
    """Load species matrix and return taxid -> coverage_state."""
    print(f"Loading species matrix from {path}...")
    df = pd.read_csv(
        path,
        sep="\t",
        dtype={
            "taxid": "int64",
            "has_assembly": "int64",
            "has_annotation": "int64",
            "has_reads": "int64",
        },
        usecols=["taxid", "has_assembly", "has_annotation", "has_reads"],
    )
    result = {}
    for _, row in df.iterrows():
        tid = int(row["taxid"])
        s = species_state(
            has_assembly=bool(row["has_assembly"]),
            has_annotation=bool(row["has_annotation"]),
            has_reads=bool(row["has_reads"]),
        )
        result[tid] = s
    print(f"  {len(result):,} species with states")
    return result


def load_tree_parents(path: Path) -> dict[int, int]:
    """Load nodes.parquet and return child -> parent map."""
    print(f"Loading tree from {path}...")
    df = pd.read_parquet(path, columns=["taxid", "parent_taxid"])
    parents = {}
    for _, row in df.iterrows():
        tid = int(row["taxid"])
        pid = int(row["parent_taxid"])
        if pid >= 0:
            parents[tid] = pid
    print(f"  {len(df):,} nodes")
    return parents


def propagate_states(
    species_states: dict[int, int],
    parents: dict[int, int],
    all_taxids: set[int],
) -> dict[int, int]:
    """
    Propagate best state up the tree. Internal nodes get best state among descendants.
    """
    # Start with species states; internal nodes get NO_DATA initially
    state = {tid: species_states.get(tid, NO_DATA) for tid in all_taxids}

    # Post-order: process children before parents. Use reverse BFS from leaves.
    # Build children map
    children: dict[int, list[int]] = {}
    for c, p in parents.items():
        if p not in children:
            children[p] = []
        children[p].append(c)

    # Topological order: leaves first. Use BFS from root, then reverse.
    roots = all_taxids - set(parents.keys())
    order = []
    stack = list(roots)
    seen = set()
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        order.append(n)
        for c in children.get(n, []):
            if c not in seen:
                stack.append(c)

    # Reverse so we process leaves first
    for n in reversed(order):
        kids = children.get(n, [])
        if kids:
            best = max(state.get(c, NO_DATA) for c in kids)
            state[n] = max(state.get(n, NO_DATA), best)

    return state


def main() -> int:
    matrix_path = DATA_DIR / "eukaryotic_species_matrix.tsv"
    nodes_path = TREE_LAYOUT_DIR / "nodes.parquet"

    if not matrix_path.exists():
        print(f"Error: {matrix_path} not found", file=sys.stderr)
        return 1
    if not nodes_path.exists():
        print(f"Error: {nodes_path} not found. Run build_tree_layout.py first.", file=sys.stderr)
        return 1

    species_states = load_species_matrix(matrix_path)
    parents = load_tree_parents(nodes_path)
    all_taxids = set(parents.keys()) | {c for c, p in parents.items()} | set(species_states.keys())
    # Include all nodes from parquet
    df_nodes = pd.read_parquet(nodes_path, columns=["taxid"])
    all_taxids = set(int(x) for x in df_nodes["taxid"])

    print("Propagating states up tree...")
    state = propagate_states(species_states, parents, all_taxids)

    rows = [{"taxid": tid, "coverage_state": s} for tid, s in state.items()]
    out_df = pd.DataFrame(rows)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "coverage_nodes.parquet"
    pq.write_table(pa.Table.from_pandas(out_df, preserve_index=False), out_path, compression="zstd")
    print(f"Wrote {out_path} ({len(out_df):,} nodes)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
