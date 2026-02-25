#!/usr/bin/env python3
"""
Fetch eukaryotic taxonomy from NCBI Taxonomy database using ete3.

Builds the full eukaryotic tree of life and writes:

  ncbi_taxonomy_tree.tsv: All taxa (internal nodes + leaves), columns: parent_id, id, name, rank
"""

import sys
from pathlib import Path

try:
    from ete3 import NCBITaxa
except ImportError:
    print("Error: ete3 is required. Install with: pip install ete3", file=sys.stderr)
    sys.exit(1)

EUKARYOTA_TAXID = 2759


def _escape_tsv(val: str) -> str:
    """Escape tabs and newlines in TSV values."""
    if val is None:
        return ""
    s = str(val).replace("\t", " ").replace("\n", " ").replace("\r", " ")
    return s


def fetch_ncbi_taxonomy():
    """Fetch eukaryotic taxonomy and write tree TSV (all taxa including leaves)."""
    repo_root = Path(__file__).parent.parent
    data_dir = repo_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    tree_tsv = data_dir / "ncbi_taxonomy_tree.tsv"

    print("Loading NCBI taxonomy database (downloads on first run)...")
    ncbi = NCBITaxa()

    print("Building eukaryotic subtree (this may take a few minutes)...")
    tree = ncbi.get_descendant_taxa(EUKARYOTA_TAXID, return_tree=True)

    # Resolve names for all taxids in the tree (batch for efficiency)
    all_taxids = [int(n.name) for n in tree.traverse() if n.name]
    all_taxids.append(EUKARYOTA_TAXID)  # ensure root is included
    all_taxids = list(set(all_taxids))
    print(f"  Total taxa: {len(all_taxids)}")

    taxid2name = ncbi.get_taxid_translator(all_taxids)
    taxid2rank = ncbi.get_rank(all_taxids)

    # Parent of Eukaryota from full NCBI tree (tree root has no .up in the subtree)
    euk_lineage = ncbi.get_lineage(EUKARYOTA_TAXID)
    euk_parent = euk_lineage[-2] if len(euk_lineage) > 1 else ""

    # Write tree TSV: parent_id, id, name, rank
    print(f"Writing {tree_tsv}...")
    with open(tree_tsv, "w") as f:
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

    print("Done.")
    return True


if __name__ == "__main__":
    try:
        success = fetch_ncbi_taxonomy()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
