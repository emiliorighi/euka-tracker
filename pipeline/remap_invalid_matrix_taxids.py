#!/usr/bin/env python3
"""Remap matrix rows with invalid NCBI taxids via scientific name; drop unresolved."""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from pipeline.iucn_assessments_convert import (  # noqa: E402
    _load_ncbi_taxa,
    _lookup_names_sqlite,
    _normalize_scientific_name,
    _pick_taxid,
)
from pipeline.ncbi_taxonomy_fetch import EUKARYOTA_TAXID  # noqa: E402
from pipeline.patch_species_tax_lineage import (  # noqa: E402
    LINEAGE_COL,
    format_lineage,
    lineage_has_eukaryota,
    resolve_species_lineage,
)

DEFAULT_MATRIX = _REPO / "data" / "staged" / "05_eukaryotic_species_matrix.tsv"
DEFAULT_DB = _REPO / "data" / "staged" / "taxonomy.sqlite"


def _taxid_valid_in_ncbi(ncbi, taxid: int) -> bool:
    try:
        ncbi.get_lineage(taxid)
        return True
    except Exception:
        return False


def _is_eukaryote_species(ncbi, taxid: int) -> bool:
    if not _taxid_valid_in_ncbi(ncbi, taxid):
        return False
    try:
        lineage = ncbi.get_lineage(taxid)
    except Exception:
        return False
    if EUKARYOTA_TAXID not in lineage:
        return False
    rank = ncbi.get_rank([taxid]).get(taxid)
    return rank == "species"


def resolve_taxid_by_scientific_name(ncbi, name: str) -> int | None:
    """Map a scientific name to one NCBI species taxid under Eukaryota."""
    norm = _normalize_scientific_name(name)
    if not norm:
        return None

    hits = _lookup_names_sqlite(ncbi, [norm]).get(norm, [])
    if not hits:
        return None

    chosen = _pick_taxid(ncbi, hits, "", norm)
    if chosen is None:
        return None

    if not _is_eukaryote_species(ncbi, chosen):
        ranks = ncbi.get_rank(hits)
        species_ids = [tid for tid in hits if ranks.get(tid) == "species"]
        for tid in species_ids:
            if _is_eukaryote_species(ncbi, tid):
                return int(tid)
        return None

    return int(chosen)


def _assembly_accession(row: dict[str, str]) -> str:
    return (row.get("ref_assembly_accession") or "").strip()


def fetch_organism_names_by_assembly(accessions: list[str]) -> dict[str, str]:
    """
    accession → organism_name via NCBI datasets CLI (when installed).
    Missing or failed accessions are omitted.
    """
    accessions = sorted({acc for acc in accessions if acc})
    if not accessions:
        return {}

    try:
        proc = subprocess.run(
            ["datasets", "summary", "genome", "accession", *accessions, "--as-json-lines"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return {}

    if proc.returncode != 0:
        return {}

    out: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        accession = rec.get("accession")
        organism = rec.get("organism") or {}
        name = _normalize_scientific_name(organism.get("organism_name"))
        if accession and name:
            out[str(accession)] = name
    return out


def _needs_remap(
    ncbi,
    conn: sqlite3.Connection,
    taxid: int,
    ete3_cache: dict[int, list[int]],
) -> bool:
    if not _taxid_valid_in_ncbi(ncbi, taxid):
        return True
    lineage, _ = resolve_species_lineage(conn, taxid, ete3_cache)
    return not lineage_has_eukaryota(lineage)


def _name_candidates(
    row: dict[str, str],
    assembly_names: dict[str, str],
) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()

    def add(name: str) -> None:
        norm = _normalize_scientific_name(name)
        if not norm:
            return
        key = norm.lower()
        if key in seen:
            return
        seen.add(key)
        names.append(norm)

    add(row.get("scientific_name") or "")
    acc = _assembly_accession(row)
    if acc:
        add(assembly_names.get(acc, ""))
    return names


def remap_invalid_matrix_taxids(
    conn: sqlite3.Connection,
    matrix_in: Path,
    matrix_out: Path,
    *,
    in_place: bool = False,
) -> dict[str, int]:
    """
    Remap rows whose taxid is missing from NCBI or lacks Eukaryota lineage.
    Drops rows that cannot be resolved to a eukaryote species taxid by name.
    """
    if in_place and matrix_out.resolve() != matrix_in.resolve():
        raise ValueError("in_place requires matrix_out == matrix_in")

    ncbi = _load_ncbi_taxa()

    pending_rows: list[dict[str, str]] = []
    with matrix_in.open(newline="", encoding="utf-8") as fin:
        reader = csv.DictReader(fin, delimiter="\t")
        fieldnames = list(reader.fieldnames or [])
        for row in reader:
            pending_rows.append(row)

    assembly_names = fetch_organism_names_by_assembly(
        [_assembly_accession(row) for row in pending_rows]
    )

    ete3_cache: dict[int, list[int]] = {}
    existing_taxids: set[int] = set()
    for row in pending_rows:
        try:
            existing_taxids.add(int(row["taxid"]))
        except (KeyError, ValueError):
            continue

    dest = matrix_out
    tmp: Path | None = None
    if in_place:
        tmp = matrix_in.with_suffix(".remap_taxid.tmp")
        dest = tmp

    stats = {
        "rows_in": len(pending_rows),
        "kept_unchanged": 0,
        "remapped": 0,
        "dropped_unresolved": 0,
        "dropped_duplicate_taxid": 0,
        "rows_out": 0,
    }

    with dest.open("w", newline="", encoding="utf-8") as fout:
        writer = csv.DictWriter(
            fout,
            fieldnames=fieldnames,
            delimiter="\t",
            extrasaction="ignore",
        )
        writer.writeheader()

        for row in pending_rows:
            try:
                old_taxid = int(row["taxid"])
            except (KeyError, ValueError):
                stats["dropped_unresolved"] += 1
                continue

            if not _needs_remap(ncbi, conn, old_taxid, ete3_cache):
                stats["kept_unchanged"] += 1
                writer.writerow(row)
                stats["rows_out"] += 1
                continue

            new_taxid: int | None = None
            resolved_name = ""
            for candidate in _name_candidates(row, assembly_names):
                new_taxid = resolve_taxid_by_scientific_name(ncbi, candidate)
                if new_taxid is not None:
                    resolved_name = candidate
                    break

            if new_taxid is None:
                stats["dropped_unresolved"] += 1
                continue

            if new_taxid in existing_taxids and new_taxid != old_taxid:
                stats["dropped_duplicate_taxid"] += 1
                continue

            if new_taxid != old_taxid:
                existing_taxids.discard(old_taxid)
                existing_taxids.add(new_taxid)
                row["taxid"] = str(new_taxid)
                stats["remapped"] += 1

            if resolved_name:
                row["scientific_name"] = resolved_name
            elif not (row.get("scientific_name") or "").strip():
                row["scientific_name"] = ncbi.get_taxid_translator([new_taxid]).get(new_taxid, "")

            lineage, _ = resolve_species_lineage(conn, new_taxid, ete3_cache)
            if lineage_has_eukaryota(lineage):
                row[LINEAGE_COL] = format_lineage(lineage)
            else:
                row[LINEAGE_COL] = ""

            writer.writerow(row)
            stats["rows_out"] += 1

    if tmp is not None:
        tmp.replace(matrix_in)

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Remap invalid matrix taxids by scientific name; drop unresolved rows"
    )
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--in-place", action="store_true")
    parser.add_argument(
        "--copy-to",
        type=Path,
        default=_REPO / "data" / "eukaryotic_species_matrix.tsv",
        help="Mirror output matrix (default: data/eukaryotic_species_matrix.tsv)",
    )
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
        stats = remap_invalid_matrix_taxids(
            conn, args.matrix, out, in_place=args.in_place or out == args.matrix
        )
    finally:
        conn.close()

    print(
        f"Remap complete: {stats['rows_in']:,} in → {stats['rows_out']:,} out "
        f"({stats['remapped']:,} remapped, {stats['dropped_unresolved']:,} dropped unresolved, "
        f"{stats['dropped_duplicate_taxid']:,} dropped duplicate) → {out}",
        file=sys.stderr,
    )

    if args.copy_to and out.resolve() == args.matrix.resolve():
        import shutil

        args.copy_to.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.matrix, args.copy_to)

    return 0


if __name__ == "__main__":
    sys.exit(main())
