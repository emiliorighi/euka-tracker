#!/usr/bin/env python3
"""Patch tax_lineage onto species matrix using SQLite parent walks."""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from pipeline.ncbi_taxonomy_fetch import EUKARYOTA_TAXID  # noqa: E402

DEFAULT_MATRIX = _REPO / "data" / "staged" / "05_eukaryotic_species_matrix.tsv"
DEFAULT_DB = _REPO / "data" / "staged" / "taxonomy.sqlite"

LINEAGE_COL = "tax_lineage"

_ncbi_taxa: object | None = None


def _get_parent(conn: sqlite3.Connection, taxid: int) -> int | None:
    row = conn.execute(
        "SELECT parent_taxid FROM taxa WHERE taxid = ?",
        (taxid,),
    ).fetchone()
    if row is None:
        return None
    return int(row[0])


def lineage_to_root(
    conn: sqlite3.Connection,
    taxid: int,
    *,
    stop_at: int = EUKARYOTA_TAXID,
    max_hops: int = 128,
) -> list[int]:
    """Walk tip → root; return root → tip (ENA / Annotrieve convention)."""
    path: list[int] = []
    seen: set[int] = set()
    current = taxid
    hops = 0
    while current and current not in seen and hops < max_hops:
        seen.add(current)
        path.append(current)
        if current == stop_at:
            break
        parent = _get_parent(conn, current)
        if parent is None or parent == current:
            break
        current = parent
        hops += 1
    path.reverse()
    return path


def format_lineage(taxids: list[int]) -> str:
    return ",".join(str(t) for t in taxids)


def lineage_has_eukaryota(path: list[int]) -> bool:
    """True when path is root→tip and starts at Eukaryota."""
    return bool(path) and path[0] == EUKARYOTA_TAXID


def _get_ncbi_taxa():
    global _ncbi_taxa
    if _ncbi_taxa is not None:
        return _ncbi_taxa
    try:
        from ete3 import NCBITaxa
    except ImportError as exc:
        raise ImportError(
            "ete3 is required for NCBI lineage fallback. Install with: pip install ete3"
        ) from exc
    _ncbi_taxa = NCBITaxa()
    return _ncbi_taxa


def lineage_via_ete3(
    taxid: int,
    cache: dict[int, list[int]],
) -> list[int]:
    """
    Fetch Eukaryota→tip lineage from NCBI when taxid is absent from taxonomy.sqlite.
    ete3 get_lineage returns root→tip; slice from Eukaryota to match matrix convention.
    """
    if taxid in cache:
        return cache[taxid]

    ncbi = _get_ncbi_taxa()
    try:
        full = [int(t) for t in ncbi.get_lineage(taxid)]
    except Exception:
        cache[taxid] = []
        return []

    if EUKARYOTA_TAXID not in full:
        cache[taxid] = []
        return []

    path = full[full.index(EUKARYOTA_TAXID) :]
    cache[taxid] = path
    return path


def resolve_species_lineage(
    conn: sqlite3.Connection,
    taxid: int,
    ete3_cache: dict[int, list[int]],
) -> tuple[list[int], str]:
    """
    Resolve root→tip lineage from Eukaryota to species.
    Returns (path, source) where source is sqlite, ete3, or none.
    """
    path = lineage_to_root(conn, taxid)
    if lineage_has_eukaryota(path):
        return path, "sqlite"

    path = lineage_via_ete3(taxid, ete3_cache)
    if lineage_has_eukaryota(path):
        return path, "ete3"

    return [], "none"


def matrix_has_lineage(matrix_path: Path) -> bool:
    with matrix_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        if not reader.fieldnames:
            return False
        return LINEAGE_COL in reader.fieldnames


def patch_matrix_lineage(
    conn: sqlite3.Connection,
    matrix_in: Path,
    matrix_out: Path,
    *,
    in_place: bool = False,
) -> tuple[int, int, int, int]:
    """
    Stream matrix TSV, append tax_lineage column.
    Returns (rows_written, lineage_ok, missing_taxid, ete3_fallback).
    """
    matrix_out.parent.mkdir(parents=True, exist_ok=True)

    if in_place and matrix_out.resolve() != matrix_in.resolve():
        raise ValueError("in_place requires matrix_out == matrix_in")

    dest = matrix_out
    tmp: Path | None = None
    if in_place:
        tmp = matrix_in.with_suffix(".tax_lineage.tmp")
        dest = tmp

    rows_written = 0
    lineage_ok = 0
    missing_taxid = 0
    ete3_fallback = 0
    ete3_cache: dict[int, list[int]] = {}

    with matrix_in.open(newline="", encoding="utf-8") as fin, dest.open(
        "w", newline="", encoding="utf-8"
    ) as fout:
        reader = csv.DictReader(fin, delimiter="\t")
        if not reader.fieldnames:
            raise ValueError(f"Empty matrix: {matrix_in}")

        fieldnames = list(reader.fieldnames)
        if LINEAGE_COL not in fieldnames:
            fieldnames.append(LINEAGE_COL)

        writer = csv.DictWriter(fout, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore")
        writer.writeheader()

        for row in reader:
            try:
                taxid = int(row["taxid"])
            except (KeyError, ValueError):
                row[LINEAGE_COL] = ""
                missing_taxid += 1
                writer.writerow(row)
                rows_written += 1
                continue

            lineage, source = resolve_species_lineage(conn, taxid, ete3_cache)
            if lineage_has_eukaryota(lineage):
                row[LINEAGE_COL] = format_lineage(lineage)
                lineage_ok += 1
                if source == "ete3":
                    ete3_fallback += 1
            else:
                row[LINEAGE_COL] = ""
                missing_taxid += 1

            writer.writerow(row)
            rows_written += 1

    if tmp is not None:
        tmp.replace(matrix_in)

    return rows_written, lineage_ok, missing_taxid, ete3_fallback


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch tax_lineage onto species matrix")
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--output", type=Path, default=None, help="Default: overwrite --matrix")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--in-place", action="store_true", help="Replace matrix file atomically")
    args = parser.parse_args()

    if not args.matrix.is_file():
        print(f"Error: matrix not found: {args.matrix}", file=sys.stderr)
        return 1
    if not args.db.is_file():
        print(f"Error: taxonomy db not found: {args.db}", file=sys.stderr)
        return 1

    out = args.output or args.matrix
    conn = sqlite3.connect(args.db)
    try:
        rows, ok, missing, ete3 = patch_matrix_lineage(
            conn, args.matrix, out, in_place=args.in_place or out == args.matrix
        )
    finally:
        conn.close()

    print(
        f"Patched {rows:,} rows ({ok:,} with lineage, {ete3:,} via ete3, "
        f"{missing:,} missing) → {out}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
