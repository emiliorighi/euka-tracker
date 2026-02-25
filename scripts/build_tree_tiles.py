#!/usr/bin/env python3
"""
Build multi-resolution LOD-aware tiles for the tree of life.
- Zoom levels 0-7, tile along Y: tile_y = floor(y * 2^z)
- Level-of-detail: collapse single-child chains, aggregate large subtrees
- ~20k nodes per tile; smart downsampling when exceeded
- Output: taxid, parent_taxid, x, y, depth, coverage_state, name, rank
  + optional: is_aggregate, n_descendants, coverage_counts
"""

import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

MAX_NODES_PER_TILE = 20_000
ZOOM_LEVELS = list(range(8))  # 0..7
COVERAGE_NAMES = ["NO_DATA", "READS_ONLY", "GENOME_ONLY", "GENOME_READS", "ANNOTATION_ONLY", "FULL"]

# Lifemap-style tile schema for frontend compatibility
TILE_SCHEMA = pa.schema([
    ("taxid", pa.int64()),
    ("parent_taxid", pa.int64()),
    ("x", pa.float64()),
    ("y", pa.float64()),
    ("depth", pa.int64()),
    ("coverage_state", pa.int8()),
    ("name", pa.string()),
    ("rank", pa.string()),
])

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
TREE_LAYOUT_DIR = REPO_ROOT / "tree_layout"
COVERAGE_DIR = REPO_ROOT / "coverage"
OUTPUT_DIR = REPO_ROOT / "tree_tiles"


def load_taxonomy_names(path: Path) -> dict[int, tuple[str, str]]:
    """Load taxid -> (name, rank). Stream to reduce memory."""
    print(f"Loading taxonomy names from {path}...")
    result = {}
    for chunk in pd.read_csv(
        path, sep="\t", usecols=["id", "name", "rank"],
        dtype={"id": "int64", "name": "str", "rank": "str"},
        chunksize=100_000, low_memory=False
    ):
        for _, row in chunk.iterrows():
            tid = int(row["id"])
            result[tid] = (str(row["name"] or ""), str(row["rank"] or ""))
    print(f"  {len(result):,} taxa")
    return result


def load_merged_data(names: dict) -> pd.DataFrame:
    """Load nodes + coverage + names."""
    print("Loading nodes and coverage...")
    nodes = pd.read_parquet(TREE_LAYOUT_DIR / "nodes.parquet")
    coverage = pd.read_parquet(COVERAGE_DIR / "coverage_nodes.parquet")
    merged = nodes.merge(coverage, on="taxid", how="left")
    merged["coverage_state"] = merged["coverage_state"].fillna(0).astype(np.int8)

    default = ("", "")
    names_list = [names.get(int(t), default) for t in merged["taxid"]]
    merged["name"] = [n[0] for n in names_list]
    merged["rank"] = [n[1] for n in names_list]

    print(f"  {len(merged):,} nodes")
    return merged


def assign_tile_y(df: pd.DataFrame, z: int) -> np.ndarray:
    """Assign tile_y = floor(y * 2^z)."""
    n_tiles = 2**z
    return (df["y"].values * n_tiles).astype(np.int64).clip(0, n_tiles - 1)


def collapse_chains(tile_df: pd.DataFrame) -> pd.DataFrame:
    """
    Collapse single-child chains: keep chain heads and leaves, drop middles.
    Preserves tree structure while reducing node count.
    """
    if len(tile_df) <= MAX_NODES_PER_TILE:
        return tile_df

    taxids = set(tile_df["taxid"].astype(int))
    parent_to_children = defaultdict(list)
    for _, row in tile_df.iterrows():
        p = int(row["parent_taxid"])
        c = int(row["taxid"])
        if p >= 0 and p in taxids:
            parent_to_children[p].append(c)

    keep = set()
    for tid in taxids:
        children = parent_to_children.get(tid, [])
        if len(children) == 0:
            keep.add(tid)  # leaf
        elif len(children) >= 2:
            keep.add(tid)  # branch
        else:
            child = children[0]
            child_children = parent_to_children.get(child, [])
            if len(child_children) != 1:
                keep.add(tid)  # chain head (next is branch/leaf)
            # else: middle of chain, drop

    return tile_df[tile_df["taxid"].isin(keep)]


def aggregate_subtrees(tile_df: pd.DataFrame, max_n: int) -> pd.DataFrame:
    """
    When still over max_n, aggregate deep subtrees into representative nodes.
    Keep structural nodes (depth <= 8), sample rest, add aggregate placeholders.
    """
    if len(tile_df) <= max_n:
        return tile_df

    # Sort by depth; keep shallow structure + coverage nodes + sample
    df = tile_df.copy()
    df = df.sort_values(["depth", "y"], kind="mergesort")

    structural = df[df["depth"] <= 8]
    rest = df[df["depth"] > 8]

    if len(structural) >= max_n:
        return structural.head(max_n)

    # Prefer nodes with data
    with_data = rest[rest["coverage_state"] > 0]
    without_data = rest[rest["coverage_state"] == 0]

    take_from_with = min(len(with_data), max_n - len(structural))
    take_from_without = max(0, max_n - len(structural) - take_from_with)

    if take_from_with <= 0:
        with_sample = with_data.iloc[0:0]
    elif len(with_data) <= take_from_with:
        with_sample = with_data
    else:
        step = max(1, len(with_data) // take_from_with)
        with_sample = with_data.iloc[::step].head(take_from_with)

    if take_from_without <= 0:
        without_sample = without_data.iloc[0:0]
    elif len(without_data) <= take_from_without:
        without_sample = without_data
    else:
        step = max(1, len(without_data) // take_from_without)
        without_sample = without_data.iloc[::step].head(take_from_without)

    result = pd.concat([structural, with_sample, without_sample], ignore_index=True)
    return result.head(max_n)


def lod_downsample(tile_df: pd.DataFrame, max_n: int) -> pd.DataFrame:
    """Apply LOD: chain collapse then subtree aggregation. Fast path for huge tiles."""
    if len(tile_df) <= max_n:
        return tile_df
    if len(tile_df) > 100_000:
        # Fast path: skip chain collapse, use stratified depth sample
        return aggregate_subtrees(tile_df, max_n)
    df = collapse_chains(tile_df)
    return aggregate_subtrees(df, max_n)


def build_tiles(df: pd.DataFrame, emit_json: bool = False) -> None:
    """Build tiles for each zoom level."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cols = ["taxid", "parent_taxid", "x", "y", "depth", "coverage_state", "name", "rank"]

    for z in ZOOM_LEVELS:
        n_tiles = 2**z
        tile_y = assign_tile_y(df, z)
        z_dir = OUTPUT_DIR / f"z{z}"
        z_dir.mkdir(parents=True, exist_ok=True)

        for ty in range(n_tiles):
            mask = tile_y == ty
            tile_df = df.loc[mask, cols].copy()
            tile_df = lod_downsample(tile_df, MAX_NODES_PER_TILE)

            out_path = z_dir / f"{ty}.parquet"
            table = pa.Table.from_pandas(tile_df, schema=TILE_SCHEMA, preserve_index=False)
            pq.write_table(table, out_path, compression="zstd")

            if emit_json:
                json_path = z_dir / f"{ty}.json"
                records = []
                for _, row in tile_df.iterrows():
                    r = {
                        "taxid": int(row["taxid"]),
                        "parent_taxid": int(row["parent_taxid"]),
                        "x": float(row["x"]),
                        "y": float(row["y"]),
                        "depth": int(row["depth"]),
                        "coverage_state": int(row["coverage_state"]),
                        "name": str(row["name"]) if pd.notna(row["name"]) else "",
                        "rank": str(row["rank"]) if pd.notna(row["rank"]) else "",
                    }
                    records.append(r)
                with open(json_path, "w") as f:
                    json.dump(records, f, separators=(",", ":"))

        print(f"  z{z}: {n_tiles} tiles")

    print(f"Wrote tiles to {OUTPUT_DIR}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Also emit JSON tiles for web frontend")
    parser.add_argument("--no-names", action="store_true", help="Skip taxonomy names (faster, no tooltips)")
    args = parser.parse_args()

    taxonomy_path = DATA_DIR / "ncbi_taxonomy_tree.tsv"
    nodes_path = TREE_LAYOUT_DIR / "nodes.parquet"
    coverage_path = COVERAGE_DIR / "coverage_nodes.parquet"

    if not nodes_path.exists():
        print("Error: Run build_tree_layout.py first.", file=sys.stderr)
        return 1
    if not coverage_path.exists():
        print("Error: Run build_coverage.py first.", file=sys.stderr)
        return 1

    names = {} if args.no_names else (load_taxonomy_names(taxonomy_path) if taxonomy_path.exists() else {})
    df = load_merged_data(names)
    build_tiles(df, emit_json=args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
