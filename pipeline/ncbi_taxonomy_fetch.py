#!/usr/bin/env python3
"""
Fetch eukaryotic taxonomy from NCBI Taxonomy database using ete3.

Writes staged gzip TSV: parent_id, id, name, rank
"""

from __future__ import annotations

import csv
import gzip
import sys
from pathlib import Path
from typing import Iterator

EUKARYOTA_TAXID = 2759


def _escape_tsv(val: str) -> str:
    if val is None:
        return ""
    s = str(val).replace("\t", " ").replace("\n", " ").replace("\r", " ")
    return s


def iter_taxonomy_rows(path: Path) -> Iterator[tuple[int, int, str, str]]:
    """Stream taxonomy rows: (parent_id, taxid, name, rank). Supports .gz."""
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            try:
                parent_id = int(row["parent_id"])
                taxid = int(row["id"])
            except (KeyError, ValueError):
                continue
            name = row.get("name") or ""
            rank = row.get("rank") or ""
            yield parent_id, taxid, name, rank


def iter_species_names(path: Path) -> Iterator[tuple[int, str]]:
    """Stream (taxid, scientific_name) for rank=species rows."""
    for _parent, taxid, name, rank in iter_taxonomy_rows(path):
        if rank == "species":
            yield taxid, name


def _fill_names(taxids: set[int], taxonomy_path: Path) -> dict[int, str]:
    """Lookup scientific names for taxids from taxonomy file (streaming)."""
    names: dict[int, str] = {}
    if not taxids:
        return names
    remaining = set(taxids)
    for _parent, taxid, name, _rank in iter_taxonomy_rows(taxonomy_path):
        if taxid in remaining:
            names[taxid] = name
            remaining.discard(taxid)
            if not remaining:
                break
    return names


def write_ncbi_taxonomy_tsv(out_path: Path) -> int:
    """Fetch eukaryotic taxonomy and write staged TSV (gzip if path ends with .gz)."""
    try:
        from ete3 import NCBITaxa
    except ImportError as exc:
        raise ImportError("ete3 is required. Install with: pip install ete3") from exc

    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("Loading NCBI taxonomy database (downloads on first run)...", file=sys.stderr)
    ncbi = NCBITaxa()

    print("Building eukaryotic subtree (this may take a few minutes)...", file=sys.stderr)
    tree = ncbi.get_descendant_taxa(EUKARYOTA_TAXID, return_tree=True)

    all_taxids = [int(n.name) for n in tree.traverse() if n.name]
    all_taxids.append(EUKARYOTA_TAXID)
    all_taxids = list(set(all_taxids))
    print(f"  Total taxa: {len(all_taxids)}", file=sys.stderr)

    taxid2name = ncbi.get_taxid_translator(all_taxids)
    taxid2rank = ncbi.get_rank(all_taxids)

    euk_lineage = ncbi.get_lineage(EUKARYOTA_TAXID)
    euk_parent = euk_lineage[-2] if len(euk_lineage) > 1 else ""

    opener = gzip.open if str(out_path).endswith(".gz") else open
    count = 0
    print(f"Writing {out_path}...", file=sys.stderr)
    with opener(out_path, "wt", encoding="utf-8", newline="") as f:
        f.write("parent_id\tid\tname\trank\n")
        for node in tree.traverse():
            taxid = int(node.name) if node.name else None
            if taxid is None:
                continue
            parent = node.up
            parent_id = int(parent.name) if parent and parent.name else euk_parent
            name = taxid2name.get(taxid, "")
            rank = taxid2rank.get(taxid, "")
            f.write(f"{parent_id}\t{taxid}\t{_escape_tsv(name)}\t{_escape_tsv(rank)}\n")
            count += 1

    print(f"Wrote {count} taxa to {out_path}", file=sys.stderr)
    return count


def fetch_ncbi_taxonomy(out_path: Path | None = None) -> bool:
    """Backward-compatible entry point."""
    repo_root = Path(__file__).parent.parent
    path = out_path or repo_root / "data" / "staged" / "01_ncbi_taxonomy_tree.tsv.gz"
    write_ncbi_taxonomy_tsv(path)
    return True


if __name__ == "__main__":
    import argparse

    repo_root = Path(__file__).resolve().parent.parent
    default_out = repo_root / "data" / "staged" / "01_ncbi_taxonomy_tree.tsv.gz"

    parser = argparse.ArgumentParser(description="Export eukaryotic NCBI taxonomy tree to TSV")
    parser.add_argument("-o", "--output", type=Path, default=default_out)
    args = parser.parse_args()

    try:
        write_ncbi_taxonomy_tsv(args.output)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
