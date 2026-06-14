#!/usr/bin/env python3
"""
Build taxon hierarchy rollups (memory-efficient).

Stages:
  1. Stream taxonomy TSV → SQLite index
  2. Patch tax_lineage onto species matrix
  3. Aggregate matrix metrics over lineages (~156k induced taxa in RAM)
  4. Compute NCBI species_count_ncbi via depth-ordered SQL
  4b. Sync matrix species counts + per-rank node counters in SQLite
  5. Emit slim data/staged/06_taxon_rollups.tsv (internal nodes only, 13 columns)
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from pipeline.ncbi_taxonomy_fetch import EUKARYOTA_TAXID  # noqa: E402
from pipeline.patch_species_tax_lineage import (  # noqa: E402
    matrix_has_lineage,
    patch_matrix_lineage,
)
from pipeline.remap_invalid_matrix_taxids import remap_invalid_matrix_taxids  # noqa: E402
from pipeline.taxonomy_index import build_taxonomy_index, needs_rebuild  # noqa: E402
from pipeline.taxon_rollup import (  # noqa: E402
    accumulate_rollups_from_matrix,
    assign_depths,
    compute_rank_node_counts,
    compute_species_counts_ncbi,
    emit_rollup_tsv,
    ensure_rollup_schema,
    iter_spot_check,
    sync_matrix_species_counts,
)

DEFAULT_TAXONOMY = _REPO / "data" / "ncbi_taxonomy_tree.tsv.gz"
DEFAULT_MATRIX = _REPO / "data" / "staged" / "05_eukaryotic_species_matrix.tsv"
DEFAULT_DB = _REPO / "data" / "staged" / "taxonomy.sqlite"
DEFAULT_OUTPUT = _REPO / "data" / "staged" / "06_taxon_rollups.tsv"

MAMMALIA_TAXID = 40674


def run_pipeline(
    *,
    taxonomy_path: Path,
    matrix_path: Path,
    db_path: Path,
    output_path: Path,
    skip_index_build: bool = False,
    skip_lineage_patch: bool = False,
    force_rebuild_index: bool = False,
    verbose: bool = True,
) -> dict[str, int | float]:
    stats: dict[str, int | float] = {}

    # Stage 1: taxonomy SQLite index
    rebuild = force_rebuild_index or needs_rebuild(db_path, taxonomy_path)
    if not skip_index_build and rebuild:
        if verbose:
            print(f"Building taxonomy index → {db_path}…", file=sys.stderr)
        stats["taxonomy_rows"] = build_taxonomy_index(
            taxonomy_path, db_path, force=force_rebuild_index or not db_path.is_file()
        )
    elif not db_path.is_file():
        raise FileNotFoundError(f"Taxonomy db missing: {db_path} (run without --skip-index-build)")
    elif verbose:
        print(f"Using existing taxonomy index: {db_path}", file=sys.stderr)

    conn = sqlite3.connect(db_path)

    try:
        ensure_rollup_schema(conn)

        # Stage 2: patch tax_lineage (always refresh so new iucn_only rows get lineage)
        if skip_lineage_patch:
            has_lineage = matrix_has_lineage(matrix_path)
            if not has_lineage:
                raise ValueError(
                    f"Matrix lacks tax_lineage and --skip-lineage-patch was set: {matrix_path}"
                )
            if verbose:
                print(f"Matrix already has tax_lineage: {matrix_path}", file=sys.stderr)
        else:
            if verbose:
                print(f"Remapping invalid matrix taxids on {matrix_path}…", file=sys.stderr)
            remap_stats = remap_invalid_matrix_taxids(
                conn, matrix_path, matrix_path, in_place=True
            )
            stats["matrix_rows_before_remap"] = remap_stats["rows_in"]
            stats["matrix_rows_after_remap"] = remap_stats["rows_out"]
            stats["taxid_remapped"] = remap_stats["remapped"]
            stats["taxid_dropped_unresolved"] = remap_stats["dropped_unresolved"]
            stats["taxid_dropped_duplicate"] = remap_stats["dropped_duplicate_taxid"]

            if verbose:
                print(f"Patching tax_lineage onto {matrix_path}…", file=sys.stderr)
            rows, ok, missing, ete3 = patch_matrix_lineage(
                conn, matrix_path, matrix_path, in_place=True
            )
            stats["matrix_rows"] = rows
            stats["lineage_ok"] = ok
            stats["lineage_missing"] = missing
            stats["lineage_ete3"] = ete3

        # Stage 4 (before emit): NCBI species counts in SQLite
        if verbose:
            print("Assigning taxonomy depths…", file=sys.stderr)
        max_depth = assign_depths(conn, EUKARYOTA_TAXID)
        stats["max_depth"] = max_depth

        if verbose:
            print("Computing species_count_ncbi…", file=sys.stderr)
        compute_species_counts_ncbi(conn)

        root = iter_spot_check(conn, EUKARYOTA_TAXID)
        if root:
            stats["eukaryota_species_count_ncbi"] = root.get("species_count_ncbi") or 0

        # Stage 3: matrix rollups in RAM
        if verbose:
            print(f"Aggregating matrix rollups from {matrix_path}…", file=sys.stderr)
        rollups, matrix_rows, skipped = accumulate_rollups_from_matrix(matrix_path)
        stats["matrix_rows_read"] = matrix_rows
        stats["skipped_no_lineage"] = skipped
        stats["induced_taxa"] = len(rollups)

        euk_agg = rollups.get(EUKARYOTA_TAXID)
        if euk_agg:
            stats["eukaryota_species_count_matrix"] = euk_agg.species_count_matrix

        mammalia = rollups.get(MAMMALIA_TAXID)
        if mammalia:
            stats["mammalia_species_count_matrix"] = mammalia.species_count_matrix

        mammalia_meta = iter_spot_check(conn, MAMMALIA_TAXID)
        if mammalia_meta:
            stats["mammalia_species_count_ncbi"] = mammalia_meta.get("species_count_ncbi") or 0

        if verbose:
            print("Syncing matrix species counts to SQLite…", file=sys.stderr)
        sync_matrix_species_counts(conn, rollups)

        if verbose:
            print("Computing per-rank node counters…", file=sys.stderr)
        compute_rank_node_counts(conn)

        mammalia_meta = iter_spot_check(conn, MAMMALIA_TAXID)
        if mammalia_meta:
            stats["mammalia_order_nodes_total"] = mammalia_meta.get("order_nodes_total") or 0
            stats["mammalia_order_nodes_with_data"] = (
                mammalia_meta.get("order_nodes_with_data") or 0
            )
            stats["mammalia_family_nodes_total"] = mammalia_meta.get("family_nodes_total") or 0
            stats["mammalia_family_nodes_with_data"] = (
                mammalia_meta.get("family_nodes_with_data") or 0
            )
            stats["mammalia_genus_nodes_total"] = mammalia_meta.get("genus_nodes_total") or 0
            stats["mammalia_genus_nodes_with_data"] = (
                mammalia_meta.get("genus_nodes_with_data") or 0
            )

        # Stage 5: emit
        if verbose:
            print(f"Writing {output_path}…", file=sys.stderr)
        stats["output_rows"] = emit_rollup_tsv(conn, rollups, output_path)

    finally:
        conn.close()

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Build taxon hierarchy rollup TSV")
    parser.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-index-build", action="store_true")
    parser.add_argument("--skip-lineage-patch", action="store_true")
    parser.add_argument("--force-rebuild-index", action="store_true")
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args()

    if not args.taxonomy.is_file():
        print(f"Error: taxonomy not found: {args.taxonomy}", file=sys.stderr)
        return 1
    if not args.matrix.is_file():
        print(f"Error: matrix not found: {args.matrix}", file=sys.stderr)
        return 1

    try:
        stats = run_pipeline(
            taxonomy_path=args.taxonomy,
            matrix_path=args.matrix,
            db_path=args.db,
            output_path=args.output,
            skip_index_build=args.skip_index_build,
            skip_lineage_patch=args.skip_lineage_patch,
            force_rebuild_index=args.force_rebuild_index,
            verbose=not args.quiet,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not args.quiet:
        print("\nSummary:", file=sys.stderr)
        for key, val in stats.items():
            if isinstance(val, float):
                print(f"  {key}: {val:,.0f}", file=sys.stderr)
            else:
                print(f"  {key}: {val:,}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
