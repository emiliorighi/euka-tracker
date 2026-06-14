#!/usr/bin/env python3
"""Stream NCBI taxonomy TSV into an on-disk SQLite index (memory-efficient)."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from pipeline.ncbi_taxonomy_fetch import iter_taxonomy_rows  # noqa: E402

DEFAULT_TAXONOMY = _REPO / "data" / "ncbi_taxonomy_tree.tsv.gz"
DEFAULT_DB = _REPO / "data" / "staged" / "taxonomy.sqlite"
BATCH_SIZE = 10_000

SCHEMA = """
CREATE TABLE IF NOT EXISTS taxa (
  taxid INTEGER PRIMARY KEY,
  parent_taxid INTEGER NOT NULL,
  name TEXT NOT NULL,
  rank TEXT NOT NULL,
  depth INTEGER,
  species_count_ncbi INTEGER
);
CREATE INDEX IF NOT EXISTS idx_taxa_parent ON taxa(parent_taxid);
"""


def build_taxonomy_index(
    taxonomy_path: Path,
    db_path: Path,
    *,
    force: bool = False,
) -> int:
    """Stream taxonomy rows into SQLite. Returns row count."""
    if db_path.is_file() and not force:
        raise FileExistsError(f"{db_path} exists (use force=True to rebuild)")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if force and db_path.is_file():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.execute("DELETE FROM taxa")

        batch: list[tuple[int, int, str, str]] = []
        count = 0

        for parent_id, taxid, name, rank in iter_taxonomy_rows(taxonomy_path):
            batch.append((taxid, parent_id, name, rank))
            if len(batch) >= BATCH_SIZE:
                conn.executemany(
                    "INSERT INTO taxa (taxid, parent_taxid, name, rank) VALUES (?, ?, ?, ?)",
                    batch,
                )
                count += len(batch)
                batch.clear()

        if batch:
            conn.executemany(
                "INSERT INTO taxa (taxid, parent_taxid, name, rank) VALUES (?, ?, ?, ?)",
                batch,
            )
            count += len(batch)

        conn.commit()
        conn.execute("PRAGMA optimize")
        return count
    finally:
        conn.close()


def needs_rebuild(db_path: Path, taxonomy_path: Path) -> bool:
    if not db_path.is_file():
        return True
    if not taxonomy_path.is_file():
        return False
    return taxonomy_path.stat().st_mtime > db_path.stat().st_mtime


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SQLite taxonomy index from NCBI TSV")
    parser.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--force", action="store_true", help="Rebuild even if db exists")
    args = parser.parse_args()

    if not args.taxonomy.is_file():
        print(f"Error: taxonomy not found: {args.taxonomy}", file=sys.stderr)
        return 1

    try:
        n = build_taxonomy_index(args.taxonomy, args.db, force=args.force)
    except FileExistsError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {n:,} taxa to {args.db}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
