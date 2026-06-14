#!/usr/bin/env python3
"""Append IUCN-assessed species not in the catalog matrix (iucn_only rows)."""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from pipeline.build_species_matrix import (  # noqa: E402
    ENRICH_FIELDS,
    MATRIX_FIELDS,
    _empty_bucket_fields,
    load_matrix_taxids,
)
from pipeline.iucn_assessments_convert import load_iucn_by_taxid  # noqa: E402
from pipeline.ncbi_taxonomy_fetch import EUKARYOTA_TAXID  # noqa: E402

DEFAULT_MATRIX = _REPO / "data" / "staged" / "05_eukaryotic_species_matrix.tsv"
DEFAULT_IUCN = _REPO / "data" / "iucn_assessments.tsv"
DEFAULT_DB = _REPO / "data" / "staged" / "taxonomy.sqlite"


def _load_taxonomy_names(conn: sqlite3.Connection, taxids: set[int]) -> dict[int, str]:
    names: dict[int, str] = {}
    taxids_list = sorted(taxids)
    for i in range(0, len(taxids_list), 500):
        chunk = taxids_list[i : i + 500]
        placeholders = ",".join("?" * len(chunk))
        for taxid, name in conn.execute(
            f"SELECT taxid, name FROM taxa WHERE taxid IN ({placeholders})",
            chunk,
        ):
            names[int(taxid)] = name or ""
    return names


def _is_eukaryote_descendant(conn: sqlite3.Connection, taxid: int) -> bool:
    """Walk parents until Eukaryota or root."""
    current = taxid
    for _ in range(128):
        row = conn.execute(
            "SELECT parent_taxid FROM taxa WHERE taxid = ?",
            (current,),
        ).fetchone()
        if row is None:
            return False
        parent = int(row[0])
        if parent == current:
            return False
        if parent == EUKARYOTA_TAXID or current == EUKARYOTA_TAXID:
            return True
        current = parent
    return False


def _empty_iucn_row(
    taxid: int,
    scientific_name: str,
    iucn_rec: dict[str, str],
) -> dict[str, str]:
    row = {f: "" for f in MATRIX_FIELDS}
    row["taxid"] = str(taxid)
    row["scientific_name"] = scientific_name
    row["catalog_source"] = "iucn_only"
    row["assembly_count"] = "0"
    row["annotation_count"] = "0"
    row.update({f"{b}_count": "0" for b in ("wgs_long", "wgs_short", "rnaseq_long", "rnaseq_short")})
    row.update(_empty_bucket_fields())
    for field in ENRICH_FIELDS:
        if iucn_rec.get(field):
            row[field] = iucn_rec[field]
    return row


def merge_iucn_only_species(
    matrix_path: Path,
    iucn_path: Path,
    db_path: Path,
    *,
    copy_to: Path | None = None,
) -> dict[str, int]:
    """
    Append IUCN taxids missing from matrix as sparse iucn_only rows.
    Returns stats dict.
    """
    if not matrix_path.is_file():
        raise FileNotFoundError(f"Matrix not found: {matrix_path}")
    if not iucn_path.is_file():
        raise FileNotFoundError(f"IUCN TSV not found: {iucn_path}")
    if not db_path.is_file():
        raise FileNotFoundError(f"Taxonomy db not found: {db_path}")

    existing = load_matrix_taxids(matrix_path)
    iucn = load_iucn_by_taxid(iucn_path)

    candidates: dict[int, dict[str, str]] = {}
    for taxid, rec in iucn.items():
        if taxid in existing:
            continue
        if rec.get("redlist_category"):
            candidates[taxid] = rec

    conn = sqlite3.connect(db_path)
    try:
        eukaryote_candidates = {
            tid: rec
            for tid, rec in candidates.items()
            if _is_eukaryote_descendant(conn, tid)
        }
        names = _load_taxonomy_names(conn, set(eukaryote_candidates))
    finally:
        conn.close()

    skipped_not_in_taxonomy = len(candidates) - len(
        [t for t in eukaryote_candidates if t in names]
    )
    append_rows: list[dict[str, str]] = []
    for taxid in sorted(eukaryote_candidates):
        rec = eukaryote_candidates[taxid]
        name = names.get(taxid, "") or rec.get("scientific_name", "")
        if not name:
            skipped_not_in_taxonomy += 1
            continue
        append_rows.append(_empty_iucn_row(taxid, name, rec))

    matrix_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_name = tempfile.mkstemp(suffix=".tsv", dir=matrix_path.parent, text=True)
    import os

    os.close(tmp_fd)
    tmp_path = Path(tmp_name)

    catalog_rows = 0
    with matrix_path.open(encoding="utf-8", newline="") as in_f, tmp_path.open(
        "w", encoding="utf-8", newline=""
    ) as out_f:
        reader = csv.DictReader(in_f, delimiter="\t")
        fieldnames = list(reader.fieldnames or MATRIX_FIELDS)
        if "catalog_source" not in fieldnames:
            idx = fieldnames.index("scientific_name") + 1 if "scientific_name" in fieldnames else 1
            fieldnames.insert(idx, "catalog_source")

        writer = csv.DictWriter(out_f, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore")
        writer.writeheader()

        for row in reader:
            if not row.get("taxid"):
                continue
            out_row = {f: row.get(f) or "" for f in fieldnames}
            if not out_row.get("catalog_source"):
                out_row["catalog_source"] = "catalog"
            writer.writerow(out_row)
            catalog_rows += 1

        for row in append_rows:
            writer.writerow(row)

    tmp_path.replace(matrix_path)

    if copy_to:
        copy_to.parent.mkdir(parents=True, exist_ok=True)
        import shutil

        shutil.copy2(matrix_path, copy_to)

    stats = {
        "catalog_rows": catalog_rows,
        "appended_iucn_only": len(append_rows),
        "skipped_existing": len(existing & set(iucn)),
        "skipped_not_eukaryote": len(candidates) - len(eukaryote_candidates),
        "skipped_not_in_taxonomy": skipped_not_in_taxonomy,
    }
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Append IUCN-only species rows to the eukaryotic species matrix"
    )
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--iucn-tsv", type=Path, default=DEFAULT_IUCN)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument(
        "--copy-to",
        type=Path,
        default=_REPO / "data" / "eukaryotic_species_matrix.tsv",
        help="Mirror output to data/eukaryotic_species_matrix.tsv",
    )
    args = parser.parse_args()

    stats = merge_iucn_only_species(
        args.matrix,
        args.iucn_tsv,
        args.db,
        copy_to=args.copy_to,
    )
    print(
        f"Union complete: {stats['catalog_rows']:,} catalog + "
        f"{stats['appended_iucn_only']:,} iucn_only → {args.matrix}",
        file=sys.stderr,
    )
    print(
        f"Skipped: {stats['skipped_not_eukaryote']:,} non-eukaryote, "
        f"{stats['skipped_not_in_taxonomy']:,} missing from taxonomy db",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
