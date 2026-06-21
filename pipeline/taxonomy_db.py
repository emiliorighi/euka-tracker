"""On-disk NCBI taxonomy index (low RAM) built from ete3 taxa.sqlite."""

from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path
from typing import Iterator

from pipeline.schema import EUKARYOTA_TAXID

BATCH_SIZE = 50_000
DEFAULT_CACHE_SIZE = -262144  # 256 MiB page cache

SCHEMA = """
CREATE TABLE IF NOT EXISTS node (
    taxid INTEGER PRIMARY KEY,
    parent_id INTEGER NOT NULL,
    rank TEXT NOT NULL,
    name TEXT NOT NULL,
    track TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS synonym (
    taxid INTEGER NOT NULL,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS species_ancestor (
    taxid INTEGER PRIMARY KEY,
    species_taxid INTEGER
);
CREATE INDEX IF NOT EXISTS idx_synonym_taxid ON synonym(taxid);
CREATE INDEX IF NOT EXISTS idx_species_ancestor_species ON species_ancestor(species_taxid);
"""


def _ete3_db_path() -> Path:
    return Path.home() / ".etetoolkit" / "taxa.sqlite"


def _escape_tsv(value: object) -> str:
    if value is None or value == "":
        return ""
    return str(value).replace("\t", " ").replace("\n", " ").replace("\r", " ")


def _track_to_lineage(track: str, *, stop_at: int = EUKARYOTA_TAXID) -> str:
    parts = [int(x) for x in track.split(",") if x]
    try:
        idx = parts.index(stop_at)
    except ValueError:
        return ""
    lineage = parts[idx::-1]
    return ",".join(str(t) for t in lineage)


def _species_from_track(track: str, species_taxids: set[int]) -> int | None:
    for tid in (int(x) for x in track.split(",") if x):
        if tid in species_taxids:
            return tid
    return None


def _build_pragmas(conn: sqlite3.Connection, *, building: bool) -> None:
    if building:
        conn.execute("PRAGMA journal_mode=OFF")
        conn.execute("PRAGMA synchronous=OFF")
        conn.execute("PRAGMA temp_store=FILE")
    else:
        conn.execute(f"PRAGMA cache_size={DEFAULT_CACHE_SIZE}")


def build_taxonomy_db(db_path: Path, *, force: bool = False) -> Path:
    """Build taxonomy.db from ete3 taxa.sqlite. Peak RAM: species set + one batch."""
    ete_path = _ete3_db_path()
    if not ete_path.is_file():
        raise FileNotFoundError(
            f"ete3 taxonomy database not found at {ete_path}. "
            "Run once: python -c 'from ete3 import NCBITaxa; NCBITaxa()'"
        )

    if db_path.is_file() and not force:
        return db_path

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if force and db_path.is_file():
        db_path.unlink()

    print(f"Building {db_path} from ete3 {ete_path}...", file=sys.stderr)
    conn = sqlite3.connect(db_path)
    _build_pragmas(conn, building=True)
    conn.executescript(SCHEMA)

    conn.execute("ATTACH DATABASE ? AS ete", (str(ete_path),))

    print("  inserting eukaryote nodes...", file=sys.stderr)
    conn.execute(
        """
        INSERT INTO node (taxid, parent_id, rank, name, track)
        SELECT taxid, parent, COALESCE(rank, ''), COALESCE(spname, ''), COALESCE(track, '')
        FROM ete.species
        WHERE track IS NOT NULL AND track != ''
          AND (
            taxid = ?
            OR track LIKE ?
            OR track LIKE ?
            OR track LIKE ?
          )
        """,
        (EUKARYOTA_TAXID, f"%,{EUKARYOTA_TAXID},%", f"%,{EUKARYOTA_TAXID}", f"{EUKARYOTA_TAXID},%"),
    )
    node_count = conn.execute("SELECT COUNT(*) FROM node").fetchone()[0]
    print(f"  {node_count:,} nodes", file=sys.stderr)

    print("  inserting synonyms...", file=sys.stderr)
    conn.execute(
        """
        INSERT INTO synonym (taxid, name)
        SELECT s.taxid, s.spname
        FROM ete.synonym s
        INNER JOIN node n ON n.taxid = s.taxid
        WHERE s.spname IS NOT NULL AND s.spname != ''
        """
    )
    conn.commit()
    conn.execute("DETACH DATABASE ete")

    print("  building species_ancestor map...", file=sys.stderr)
    species_taxids: set[int] = {
        row[0] for row in conn.execute("SELECT taxid FROM node WHERE rank = 'species'")
    }
    print(f"  {len(species_taxids):,} species taxids", file=sys.stderr)

    ancestor_batch: list[tuple[int, int | None]] = []
    written = 0
    for taxid, track in conn.execute("SELECT taxid, track FROM node"):
        ancestor = _species_from_track(track, species_taxids)
        ancestor_batch.append((taxid, ancestor))
        if len(ancestor_batch) >= BATCH_SIZE:
            conn.executemany(
                "INSERT OR REPLACE INTO species_ancestor (taxid, species_taxid) VALUES (?, ?)",
                ancestor_batch,
            )
            written += len(ancestor_batch)
            ancestor_batch.clear()
            if written % 500_000 == 0:
                print(f"    … {written:,} ancestors", file=sys.stderr)

    if ancestor_batch:
        conn.executemany(
            "INSERT OR REPLACE INTO species_ancestor (taxid, species_taxid) VALUES (?, ?)",
            ancestor_batch,
        )
        written += len(ancestor_batch)

    conn.commit()
    conn.close()
    print(f"Wrote taxonomy.db ({node_count:,} nodes, {written:,} ancestors)", file=sys.stderr)
    return db_path


class TaxonomyDb:
    """Query interface for taxonomy.db."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        _build_pragmas(self._conn, building=False)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> TaxonomyDb:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def species_ancestor(self, taxid: int) -> int | None:
        row = self._conn.execute(
            "SELECT species_taxid FROM species_ancestor WHERE taxid = ?",
            (taxid,),
        ).fetchone()
        if row is None or row[0] is None:
            return None
        return int(row[0])

    def synonyms_pipe(self, taxid: int) -> str:
        rows = self._conn.execute(
            "SELECT name FROM synonym WHERE taxid = ? ORDER BY name",
            (taxid,),
        ).fetchall()
        return "|".join(sorted({r[0] for r in rows if r[0]}))

    def iter_species_taxids(self) -> Iterator[int]:
        for (taxid,) in self._conn.execute("SELECT taxid FROM node WHERE rank = 'species'"):
            yield int(taxid)

    def build_species_lineage_context(self) -> dict[int, tuple[str, str, str, str, str]]:
        """Map species taxid -> (genus, family, order, phylum, kingdom) lowercased names."""
        rank_by_taxid: dict[int, tuple[str, str]] = {}
        for taxid, rank, name in self._conn.execute("SELECT taxid, rank, name FROM node"):
            rank_by_taxid[int(taxid)] = (str(rank or ""), str(name or ""))

        context: dict[int, tuple[str, str, str, str, str]] = {}
        for taxid, track in self._conn.execute(
            "SELECT taxid, track FROM node WHERE rank = 'species'"
        ):
            tid = int(taxid)
            parts = [int(x) for x in str(track).split(",") if x]
            by_rank: dict[str, str] = {}
            for pt in parts:
                if pt in rank_by_taxid:
                    r, n = rank_by_taxid[pt]
                    if r and n:
                        by_rank[r] = n.lower()
            sp_name = rank_by_taxid.get(tid, ("", ""))[1]
            genus = sp_name.split()[0].lower() if sp_name else by_rank.get("genus", "")
            context[tid] = (
                genus,
                by_rank.get("family", ""),
                by_rank.get("order", ""),
                by_rank.get("phylum", ""),
                by_rank.get("kingdom", ""),
            )
        return context

    def iter_names_for_taxids(self, taxids: set[int]) -> Iterator[tuple[int, str]]:
        if not taxids:
            return
        batch: list[int] = []
        for taxid in sorted(taxids):
            batch.append(taxid)
            if len(batch) >= BATCH_SIZE:
                yield from self._iter_names_batch(batch)
                batch.clear()
        if batch:
            yield from self._iter_names_batch(batch)

    def _iter_names_batch(self, taxids: list[int]) -> Iterator[tuple[int, str]]:
        placeholders = ",".join("?" for _ in taxids)
        for taxid, name in self._conn.execute(
            f"SELECT taxid, name FROM node WHERE taxid IN ({placeholders})",
            taxids,
        ):
            if name:
                yield int(taxid), str(name)
        for taxid, name in self._conn.execute(
            f"SELECT taxid, name FROM synonym WHERE taxid IN ({placeholders})",
            taxids,
        ):
            if name:
                yield int(taxid), str(name)

    def iter_species(self, *, limit: int | None = None) -> Iterator[dict[str, str]]:
        sql = """
            SELECT n.taxid, n.name, n.track,
                   COALESCE(
                       (SELECT GROUP_CONCAT(s.name, '|')
                        FROM synonym s WHERE s.taxid = n.taxid),
                       ''
                   ) AS syns
            FROM node n
            WHERE n.rank = 'species'
            ORDER BY n.taxid
        """
        count = 0
        for taxid, name, track, syns in self._conn.execute(sql):
            if limit is not None and count >= limit:
                return
            yield {
                "taxid": str(taxid),
                "name": name or "",
                "synonyms": syns or "",
                "rank": "species",
                "tax_lineage": _track_to_lineage(track),
            }
            count += 1

    def write_species_backbone_tsv(self, out_path: Path) -> int:
        fields = ["taxid", "name", "synonyms", "rank", "tax_lineage"]
        out_path.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", extrasaction="ignore")
            writer.writeheader()
            for row in self.iter_species():
                writer.writerow({k: _escape_tsv(row.get(k)) for k in fields})
                count += 1
                if count % 500_000 == 0:
                    print(f"  … {count:,} species backbone rows", file=sys.stderr)
        return count


def open_taxonomy_db(db_path: Path, *, build: bool = True, force_build: bool = False) -> TaxonomyDb:
    if build and (force_build or not db_path.is_file()):
        build_taxonomy_db(db_path, force=force_build)
    if not db_path.is_file():
        raise FileNotFoundError(f"taxonomy.db not found: {db_path}")
    return TaxonomyDb(db_path)
