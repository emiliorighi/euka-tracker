#!/usr/bin/env python3
"""
Merge lookup TSV (id, has_genomes, has_annotations, has_reads) into layout nodes.

Reads eukaryotic_species_matrix.tsv:
  taxid, has_assembly, has_annotation, has_reads, genome_size, gc_content

Maps to: has_genomes, has_annotations, has_reads (boolean)
"""

from pathlib import Path
from typing import Any


def load_lookup(tsv_path: Path) -> dict[str, dict]:
    """Load lookup TSV. Returns id -> {has_genomes, has_annotations, has_reads}."""
    lookup: dict[str, dict] = {}
    with open(tsv_path) as f:
        header = next(f).strip().split("\t")
        col_map = {h.lower().replace("-", "_"): i for i, h in enumerate(header)}
        id_col = col_map.get("taxid", col_map.get("id", 0))
        # Map: has_assembly -> has_genomes, has_annotation -> has_annotations
        def _bool(val: str) -> bool:
            return str(val).lower() in ("1", "true", "yes")
        for line in f:
            row = line.strip().split("\t")
            if len(row) <= id_col:
                continue
            nid = str(row[id_col])
            lookup[nid] = {
                "has_genomes": _bool(row[col_map.get("has_assembly", 1)]) if len(row) > 1 else False,
                "has_annotations": _bool(row[col_map.get("has_annotation", 2)]) if len(row) > 2 else False,
                "has_reads": _bool(row[col_map.get("has_reads", 3)]) if len(row) > 3 else False,
            }
    return lookup


def enrich_nodes(nodes: list[dict], lookup: dict[str, dict]) -> None:
    """Mutate nodes in place, adding has_genomes, has_annotations, has_reads."""
    default = {"has_genomes": False, "has_annotations": False, "has_reads": False}
    for node in nodes:
        extra = lookup.get(str(node.get("id", "")), default)
        node["has_genomes"] = extra["has_genomes"]
        node["has_annotations"] = extra["has_annotations"]
        node["has_reads"] = extra["has_reads"]
