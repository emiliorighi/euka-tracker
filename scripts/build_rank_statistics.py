#!/usr/bin/env python3
"""
Build JSON statistics of taxonomic ranks (phylum, class, order, family, genus)
from the eukaryotic species matrix and NCBI taxonomy tree.

Output: counts per state, percentages, and average gc_content and genome_size.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path


# States ordered by "best" first (for assigning a taxon its best state)
STATE_ORDER = [
    "fully_covered",           # assembly + annotation + reads
    "genome_annotation_only",  # assembly + annotation, no reads
    "genome_reads_no_annotation",  # assembly + reads, no annotation
    "genome_only",             # assembly only
    "reads_only",              # reads only (no assembly)
    "no_data",                 # no assembly, annotation, or reads
]


def _classify_species(has_assembly: int, has_annotation: int, has_reads: int) -> str:
    """Classify a species into one of the six states."""
    a, b, c = bool(has_assembly), bool(has_annotation), bool(has_reads)
    if a and b and c:
        return "fully_covered"
    if a and b and not c:
        return "genome_annotation_only"
    if a and not b and c:
        return "genome_reads_no_annotation"
    if a and not b and not c:
        return "genome_only"
    if not a and c:
        return "reads_only"
    return "no_data"


def load_taxonomy_tree(path: Path) -> dict:
    """
    Load NCBI taxonomy tree. Returns:
    - nodes: taxid -> {parent_id, rank, name}
    - ranks_at: {rank_name: set of taxids at that rank}
    """
    nodes = {}
    ranks_at = defaultdict(set)
    with open(path) as f:
        next(f)  # header
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 4:
                continue
            parent_id, taxid, name, rank = parts[0], parts[1], parts[2], parts[3]
            try:
                taxid = int(taxid)
                parent_id = int(parent_id)
            except ValueError:
                continue
            nodes[taxid] = {"parent_id": parent_id, "rank": rank, "name": name}
            if rank in ("phylum", "class", "order", "family", "genus"):
                ranks_at[rank].add(taxid)
    return {"nodes": nodes, "ranks_at": dict(ranks_at)}


def get_lineage(taxid: int, nodes: dict) -> dict:
    """
    Get phylum, class, order, family, genus for a taxid by traversing up.
    Returns dict: rank_name -> taxid (closest ancestor at that rank).
    """
    lineage = {}
    current = taxid
    seen = set()
    while current and current not in seen:
        seen.add(current)
        if current not in nodes:
            break
        node = nodes[current]
        rank = node["rank"]
        if rank in ("phylum", "class", "order", "family", "genus"):
            lineage[rank] = current
        current = node["parent_id"]
    return lineage


def load_matrix(path: Path) -> list[dict]:
    """Load eukaryotic species matrix. Returns list of row dicts."""
    rows = []
    with open(path) as f:
        header = next(f).strip().split("\t")
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 4:
                continue
            row = dict(zip(header, parts))
            try:
                row["taxid"] = int(row["taxid"])
                row["has_assembly"] = int(row.get("has_assembly", 0) or 0)
                row["has_annotation"] = int(row.get("has_annotation", 0) or 0)
                row["has_reads"] = int(row.get("has_reads", 0) or 0)
                gs = row.get("genome_size", "") or ""
                row["genome_size"] = int(gs) if gs and str(gs).isdigit() else None
                gc = row.get("gc_content", "") or ""
                try:
                    row["gc_content"] = float(gc) if gc else None
                except ValueError:
                    row["gc_content"] = None
            except (ValueError, KeyError):
                continue
            rows.append(row)
    return rows


def build_rank_stats(matrix_rows: list[dict], tax_tree: dict) -> dict:
    """
    Build per-rank statistics. Returns structure:
    ranks -> rank_name -> total, states, percentages, avg_gc_content, avg_genome_size
    """
    nodes = tax_tree["nodes"]
    ranks_at = tax_tree["ranks_at"]
    target_ranks = ["phylum", "class", "order", "family", "genus"]

    # taxon_id at rank -> best state index (0=best) among its species
    taxon_state = defaultdict(lambda: defaultdict(lambda: len(STATE_ORDER)))
    # rank -> taxon_id -> {gc: [], gs: []} for computing averages
    taxon_gc_gs = defaultdict(lambda: defaultdict(lambda: {"gc": [], "gs": []}))

    for row in matrix_rows:
        taxid = row["taxid"]
        state = _classify_species(
            row["has_assembly"], row["has_annotation"], row["has_reads"]
        )
        lineage = get_lineage(taxid, nodes)
        for rank_name in target_ranks:
            if rank_name not in lineage:
                continue
            taxon_id = lineage[rank_name]
            idx = STATE_ORDER.index(state)
            taxon_state[rank_name][taxon_id] = min(
                taxon_state[rank_name][taxon_id],
                idx,
            )
            if row.get("gc_content") is not None:
                taxon_gc_gs[rank_name][taxon_id]["gc"].append(row["gc_content"])
            if row.get("genome_size") is not None:
                taxon_gc_gs[rank_name][taxon_id]["gs"].append(row["genome_size"])

    result = {"ranks": {}}

    for rank_name in target_ranks:
        all_taxa = ranks_at.get(rank_name, set())
        taxa_with_data = set(taxon_state[rank_name].keys())
        taxa_no_data = all_taxa - taxa_with_data

        state_counts = {s: 0 for s in STATE_ORDER}
        for taxon_id in taxa_with_data:
            state_idx = taxon_state[rank_name][taxon_id]
            state_counts[STATE_ORDER[state_idx]] += 1
        state_counts["no_data"] = len(taxa_no_data)

        total = len(all_taxa)
        if total == 0:
            total = len(taxa_with_data)
            state_counts["no_data"] = 0

        percentages = {
            s: round(state_counts[s] / total, 3) if total else 0
            for s in STATE_ORDER
        }

        # Average gc_content and genome_size over species with values
        all_gc = []
        all_gs = []
        for taxon_id in taxa_with_data:
            all_gc.extend(taxon_gc_gs[rank_name][taxon_id]["gc"])
            all_gs.extend(taxon_gc_gs[rank_name][taxon_id]["gs"])
        avg_gc = round(sum(all_gc) / len(all_gc), 2) if all_gc else None
        avg_gs = round(sum(all_gs) / len(all_gs), 0) if all_gs else None

        result["ranks"][rank_name] = {
            "total": total,
            "states": state_counts,
            "percentages": percentages,
            "avg_gc_content": avg_gc,
            "avg_genome_size": int(avg_gs) if avg_gs is not None else None,
        }

    return result


def main():
    repo_root = Path(__file__).resolve().parent.parent
    data_dir = repo_root / "data"
    tree_path = data_dir / "ncbi_taxonomy_tree.tsv"
    matrix_path = data_dir / "eukaryotic_species_matrix.tsv"
    out_path = data_dir / "rank_statistics.json"

    if not tree_path.exists():
        print(f"Error: {tree_path} not found", file=sys.stderr)
        sys.exit(1)
    if not matrix_path.exists():
        print(f"Error: {matrix_path} not found", file=sys.stderr)
        sys.exit(1)

    print("Loading taxonomy tree...")
    tax_tree = load_taxonomy_tree(tree_path)
    print(f"  Loaded {len(tax_tree['nodes'])} nodes")

    print("Loading species matrix...")
    matrix_rows = load_matrix(matrix_path)
    print(f"  Loaded {len(matrix_rows)} species")

    print("Building rank statistics...")
    stats = build_rank_stats(matrix_rows, tax_tree)

    print(f"Writing {out_path}...")
    with open(out_path, "w") as f:
        json.dump(stats, f, indent=2)

    print("Done.")
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
