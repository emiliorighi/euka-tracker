"""Build cross_universe.db indexes (GBIF, iNat, OTL) for IUCN matrix resolution."""

from __future__ import annotations

import csv
import re
import sqlite3
import sys
import zipfile
from pathlib import Path

from pipeline.match_keys import binom_key, norm_key

# GBIF Taxon.tsv can have very wide fields
try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:
    csv.field_size_limit(2**31 - 1)

BATCH_SIZE = 50_000
DEFAULT_CACHE_SIZE = -262144

NCBI_SOURCE_RE = re.compile(r"\bncbi:(\d+)\b")
GBIF_SOURCE_RE = re.compile(r"\bgbif:(\d+)\b")
NCBI_TAXID_PATTERNS = (
    re.compile(r"ncbi\.nlm\.nih\.gov:taxon:(\d+)", re.I),
    re.compile(r"ncbi:txid(\d+)", re.I),
    re.compile(r"\bncbi:(\d+)\b", re.I),
)

EUK_KINGDOMS = frozenset(
    {
        "animalia",
        "plantae",
        "fungi",
        "chromista",
        "protozoa",
        "viridiplantae",
        "metazoa",
        "chromalveolata",
        "rhodophyta",
        "stramenopiles",
        "alveolata",
        "amoebozoa",
        "excavata",
        "apusozoa",
        "opisthokonta",
    }
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS gbif_accepted (
    gbif_id INTEGER PRIMARY KEY,
    canonical TEXT NOT NULL,
    genus TEXT NOT NULL,
    family TEXT NOT NULL,
    taxon_order TEXT NOT NULL,
    phylum TEXT NOT NULL,
    kingdom TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS gbif_name (
    name_norm TEXT NOT NULL,
    gbif_id INTEGER NOT NULL,
    UNIQUE(name_norm, gbif_id)
);
CREATE TABLE IF NOT EXISTS gbif_synonym (
    name_norm TEXT NOT NULL,
    gbif_id INTEGER NOT NULL,
    UNIQUE(name_norm, gbif_id)
);
CREATE TABLE IF NOT EXISTS gbif_binomial (
    binom_key TEXT NOT NULL,
    gbif_id INTEGER NOT NULL,
    UNIQUE(binom_key, gbif_id)
);
CREATE TABLE IF NOT EXISTS gbif_ncbi_taxid (
    taxid INTEGER NOT NULL,
    gbif_id INTEGER NOT NULL,
    UNIQUE(taxid, gbif_id)
);
CREATE TABLE IF NOT EXISTS gbif_to_ott (
    gbif_id INTEGER NOT NULL,
    ott_id INTEGER NOT NULL,
    UNIQUE(gbif_id, ott_id)
);
CREATE TABLE IF NOT EXISTS inat_record (
    inat_id INTEGER PRIMARY KEY,
    genus TEXT NOT NULL,
    family TEXT NOT NULL,
    phylum TEXT NOT NULL,
    kingdom TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS inat_name (
    name_norm TEXT NOT NULL,
    inat_id INTEGER NOT NULL,
    UNIQUE(name_norm, inat_id)
);
CREATE TABLE IF NOT EXISTS inat_binomial (
    binom_key TEXT NOT NULL,
    inat_id INTEGER NOT NULL,
    UNIQUE(binom_key, inat_id)
);
CREATE TABLE IF NOT EXISTS ott_synonym (
    name_norm TEXT NOT NULL,
    ott_id INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS iucn_synonym (
    internal_id TEXT NOT NULL,
    name_norm TEXT NOT NULL,
    source TEXT NOT NULL,
    UNIQUE(internal_id, name_norm)
);
CREATE TABLE IF NOT EXISTS iucn_record (
    internal_id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    sci_name TEXT NOT NULL,
    genus TEXT NOT NULL,
    family TEXT NOT NULL,
    phylum TEXT NOT NULL,
    kingdom TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS iucn_name (
    name_norm TEXT NOT NULL,
    internal_id TEXT NOT NULL,
    UNIQUE(name_norm, internal_id)
);
CREATE TABLE IF NOT EXISTS iucn_binomial (
    binom_key TEXT NOT NULL,
    internal_id TEXT NOT NULL,
    UNIQUE(binom_key, internal_id)
);
CREATE TABLE IF NOT EXISTS ncbi_to_ott (
    taxid INTEGER NOT NULL,
    ott_id INTEGER NOT NULL,
    UNIQUE(taxid, ott_id)
);
CREATE TABLE IF NOT EXISTS ott_to_gbif (
    ott_id INTEGER NOT NULL,
    gbif_id INTEGER NOT NULL,
    UNIQUE(ott_id, gbif_id)
);
CREATE INDEX IF NOT EXISTS idx_gbif_name ON gbif_name(name_norm);
CREATE INDEX IF NOT EXISTS idx_gbif_synonym ON gbif_synonym(name_norm);
CREATE INDEX IF NOT EXISTS idx_gbif_binomial ON gbif_binomial(binom_key);
CREATE INDEX IF NOT EXISTS idx_inat_name ON inat_name(name_norm);
CREATE INDEX IF NOT EXISTS idx_inat_binomial ON inat_binomial(binom_key);
CREATE INDEX IF NOT EXISTS idx_iucn_name ON iucn_name(name_norm);
CREATE INDEX IF NOT EXISTS idx_iucn_binomial ON iucn_binomial(binom_key);
CREATE INDEX IF NOT EXISTS idx_ott_synonym ON ott_synonym(ott_id);
CREATE INDEX IF NOT EXISTS idx_ott_synonym_name ON ott_synonym(name_norm);
CREATE INDEX IF NOT EXISTS idx_ott_to_gbif_ott_id ON ott_to_gbif(ott_id);
CREATE INDEX IF NOT EXISTS idx_ncbi_to_ott_taxid ON ncbi_to_ott(taxid);
"""


def _norm_key(name: str | None) -> str:
    return norm_key(name)


def _parse_ncbi_taxid_from_text(value: str | None) -> int | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    for pattern in NCBI_TAXID_PATTERNS:
        match = pattern.search(text)
        if match:
            return int(match.group(1))
    return None


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _build_pragmas(conn: sqlite3.Connection, *, building: bool) -> None:
    if building:
        conn.execute("PRAGMA journal_mode=OFF")
        conn.execute("PRAGMA synchronous=OFF")
        conn.execute("PRAGMA temp_store=FILE")
    else:
        conn.execute(f"PRAGMA cache_size={DEFAULT_CACHE_SIZE}")


def _parse_ott_row(line: str) -> list[str]:
    if "\t|\t" in line:
        return [part.strip() for part in line.rstrip("\n").split("\t|\t")]
    return line.rstrip("\n").split("\t")


def find_otl_taxonomy_tsv(repo_root: Path) -> Path | None:
    otl_root = repo_root / "cache" / "otl"
    if not otl_root.is_dir():
        return None
    candidates = sorted(otl_root.glob("ott*/ott*/taxonomy.tsv"))
    if not candidates:
        candidates = sorted(otl_root.glob("**/taxonomy.tsv"))
    return candidates[0] if candidates else None


def find_otl_forwards_tsv(repo_root: Path, taxonomy_path: Path) -> Path | None:
    forwards = taxonomy_path.parent / "forwards.tsv"
    return forwards if forwards.is_file() else None


def _load_ott_forwards(path: Path | None) -> dict[int, int]:
    forwards: dict[int, int] = {}
    if path is None or not path.is_file():
        return forwards
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = _parse_ott_row(line) if "\t" in line else line.strip().split("\t")
            if len(parts) < 2:
                continue
            try:
                forwards[int(parts[0])] = int(parts[1])
            except ValueError:
                continue
    return forwards


def _resolve_ott_forward(ott_id: int, forwards: dict[int, int]) -> int:
    seen: set[int] = set()
    current = ott_id
    while current in forwards and current not in seen:
        seen.add(current)
        current = forwards[current]
    return current


def find_otl_synonyms_tsv(repo_root: Path, taxonomy_path: Path) -> Path | None:
    synonyms = taxonomy_path.parent / "synonyms.tsv"
    return synonyms if synonyms.is_file() else None


def _load_otl_synonyms(
    conn: sqlite3.Connection,
    taxonomy_path: Path,
    synonyms_path: Path | None,
    forwards: dict[int, int],
) -> None:
    syn_batch: list[tuple[str, int]] = []
    with open(taxonomy_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            parts = _parse_ott_row(line)
            if len(parts) < 3:
                continue
            try:
                ott_id = _resolve_ott_forward(int(parts[0]), forwards)
            except ValueError:
                continue
            name = _norm_key(parts[2])
            if name:
                syn_batch.append((name, ott_id))
            if len(syn_batch) >= BATCH_SIZE:
                conn.executemany(
                    "INSERT OR IGNORE INTO ott_synonym (name_norm, ott_id) VALUES (?, ?)",
                    syn_batch,
                )
                syn_batch.clear()
    if synonyms_path is not None and synonyms_path.is_file():
        with open(synonyms_path, encoding="utf-8") as f:
            for line in f:
                if not line.strip() or line.startswith("name"):
                    continue
                parts = _parse_ott_row(line)
                if len(parts) < 2:
                    continue
                name = _norm_key(parts[0])
                if not name:
                    continue
                try:
                    ott_id = _resolve_ott_forward(int(parts[1]), forwards)
                except ValueError:
                    continue
                syn_batch.append((name, ott_id))
                if len(syn_batch) >= BATCH_SIZE:
                    conn.executemany(
                        "INSERT OR IGNORE INTO ott_synonym (name_norm, ott_id) VALUES (?, ?)",
                        syn_batch,
                    )
                    syn_batch.clear()
    if syn_batch:
        conn.executemany(
            "INSERT OR IGNORE INTO ott_synonym (name_norm, ott_id) VALUES (?, ?)",
            syn_batch,
        )


def _load_otl_mappings(
    conn: sqlite3.Connection,
    taxonomy_path: Path,
    forwards: dict[int, int],
) -> None:
    ncbi_batch: list[tuple[int, int]] = []
    gbif_batch: list[tuple[int, int]] = []
    gbif_to_ott_batch: list[tuple[int, int]] = []
    with open(taxonomy_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            parts = _parse_ott_row(line)
            if len(parts) < 5:
                continue
            try:
                ott_id = int(parts[0])
            except ValueError:
                continue
            ott_id = _resolve_ott_forward(ott_id, forwards)
            for match in NCBI_SOURCE_RE.finditer(parts[4]):
                taxid = int(match.group(1))
                ncbi_batch.append((taxid, ott_id))
            for match in GBIF_SOURCE_RE.finditer(parts[4]):
                gbif_id = int(match.group(1))
                gbif_batch.append((ott_id, gbif_id))
                if gbif_id > 0:
                    gbif_to_ott_batch.append((gbif_id, ott_id))
    conn.executemany(
        "INSERT OR IGNORE INTO ncbi_to_ott (taxid, ott_id) VALUES (?, ?)",
        ncbi_batch,
    )
    conn.executemany(
        "INSERT OR IGNORE INTO ott_to_gbif (ott_id, gbif_id) VALUES (?, ?)",
        gbif_batch,
    )
    conn.executemany(
        "INSERT OR IGNORE INTO gbif_to_ott (gbif_id, ott_id) VALUES (?, ?)",
        gbif_to_ott_batch,
    )


def _load_gbif(conn: sqlite3.Connection, backbone_zip: Path) -> int:
    if not backbone_zip.is_file():
        return 0
    accepted_batch: list[tuple] = []
    name_batch: list[tuple[str, int]] = []
    synonym_batch: list[tuple[str, int]] = []
    binom_batch: list[tuple[str, int]] = []
    ncbi_taxid_batch: list[tuple[int, int]] = []
    pending_synonyms: list[tuple[str, int]] = []
    accepted_ids: set[int] = set()

    with zipfile.ZipFile(backbone_zip) as zf:
        taxon_name = next((n for n in zf.namelist() if n.endswith("Taxon.tsv")), None)
        if taxon_name is None:
            return 0
        with zf.open(taxon_name) as raw:
            reader = csv.DictReader((line.decode("utf-8") for line in raw), delimiter="\t")
            for row in reader:
                if (row.get("taxonRank") or "").lower() != "species":
                    continue
                kingdom = (row.get("kingdom") or "").strip().lower()
                if kingdom not in EUK_KINGDOMS:
                    continue
                try:
                    taxon_id = int(row["taxonID"])
                except (KeyError, ValueError):
                    continue
                name = _norm_key(row.get("canonicalName") or row.get("scientificName"))
                status = (row.get("taxonomicStatus") or "ACCEPTED").strip().upper()
                genus = (row.get("genus") or "").strip()
                epithet = (row.get("specificEpithet") or "").strip()
                bkey = f"{genus} {epithet}".strip().lower() if genus and epithet else binom_key(
                    row.get("canonicalName") or row.get("scientificName")
                )
                remark_blob = " ".join(
                    filter(
                        None,
                        [
                            row.get("taxonRemarks"),
                            row.get("taxonConceptID"),
                            row.get("identifier"),
                            row.get("source"),
                            row.get("nameAccordingTo"),
                        ],
                    )
                )
                ncbi_tid = _parse_ncbi_taxid_from_text(remark_blob)
                if ncbi_tid is not None:
                    ncbi_taxid_batch.append((ncbi_tid, taxon_id))
                if status in ("", "ACCEPTED"):
                    canonical = (row.get("canonicalName") or row.get("scientificName") or "").strip()
                    accepted_ids.add(taxon_id)
                    accepted_batch.append(
                        (
                            taxon_id,
                            canonical,
                            genus,
                            (row.get("family") or "").strip(),
                            (row.get("order") or "").strip(),
                            (row.get("phylum") or "").strip(),
                            (row.get("kingdom") or "").strip(),
                        )
                    )
                    if name:
                        name_batch.append((name, taxon_id))
                    if bkey:
                        binom_batch.append((bkey, taxon_id))
                    if len(accepted_batch) >= BATCH_SIZE:
                        conn.executemany(
                            """INSERT OR REPLACE INTO gbif_accepted
                               (gbif_id, canonical, genus, family, taxon_order, phylum, kingdom)
                               VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            accepted_batch,
                        )
                        conn.executemany(
                            "INSERT OR IGNORE INTO gbif_name (name_norm, gbif_id) VALUES (?, ?)",
                            name_batch,
                        )
                        conn.executemany(
                            "INSERT OR IGNORE INTO gbif_binomial (binom_key, gbif_id) VALUES (?, ?)",
                            binom_batch,
                        )
                        accepted_batch.clear()
                        name_batch.clear()
                        binom_batch.clear()
                elif "SYNONYM" in status:
                    acc = row.get("acceptedNameUsageID")
                    if acc and name:
                        try:
                            pending_synonyms.append((name, int(acc)))
                        except ValueError:
                            pass

    if accepted_batch:
        conn.executemany(
            """INSERT OR REPLACE INTO gbif_accepted
               (gbif_id, canonical, genus, family, taxon_order, phylum, kingdom)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            accepted_batch,
        )
        conn.executemany(
            "INSERT OR IGNORE INTO gbif_name (name_norm, gbif_id) VALUES (?, ?)",
            name_batch,
        )
        conn.executemany(
            "INSERT OR IGNORE INTO gbif_binomial (binom_key, gbif_id) VALUES (?, ?)",
            binom_batch,
        )

    syn_batch = [(n, g) for n, g in pending_synonyms if g in accepted_ids]
    if syn_batch:
        conn.executemany(
            "INSERT OR IGNORE INTO gbif_name (name_norm, gbif_id) VALUES (?, ?)",
            syn_batch,
        )
        conn.executemany(
            "INSERT OR IGNORE INTO gbif_synonym (name_norm, gbif_id) VALUES (?, ?)",
            syn_batch,
        )

    if ncbi_taxid_batch:
        conn.executemany(
            "INSERT OR IGNORE INTO gbif_ncbi_taxid (taxid, gbif_id) VALUES (?, ?)",
            ncbi_taxid_batch,
        )

    return conn.execute("SELECT COUNT(*) FROM gbif_accepted").fetchone()[0]


def _find_inat_taxa_member(zf: zipfile.ZipFile) -> str | None:
    for name in ("taxa.csv", "taxa.txt"):
        if name in zf.namelist():
            return name
    return next((n for n in zf.namelist() if n.endswith(("taxa.csv", "taxa.txt"))), None)


def _load_inat(conn: sqlite3.Connection, dwca_zip: Path) -> int:
    if not dwca_zip.is_file():
        return 0
    batch: list[tuple[str, int]] = []
    binom_batch: list[tuple[str, int]] = []
    record_batch: list[tuple] = []
    with zipfile.ZipFile(dwca_zip) as zf:
        taxa_name = _find_inat_taxa_member(zf)
        if taxa_name is None:
            return 0
        with zf.open(taxa_name) as raw:
            reader = csv.DictReader((line.decode("utf-8") for line in raw))
            for row in reader:
                if (row.get("taxonRank") or "").lower() != "species":
                    continue
                try:
                    tid = int(row["id"])
                except (KeyError, ValueError, TypeError):
                    continue
                name = _norm_key(row.get("scientificName"))
                genus = (row.get("genus") or "").strip()
                epithet = (row.get("specificEpithet") or "").strip()
                family = (row.get("family") or "").strip()
                phylum = (row.get("phylum") or row.get("class") or "").strip()
                kingdom = (row.get("kingdom") or "").strip()
                bkey = f"{genus} {epithet}".strip().lower() if genus and epithet else binom_key(
                    row.get("scientificName")
                )
                record_batch.append((tid, genus, family, phylum, kingdom))
                if name:
                    batch.append((name, tid))
                if bkey:
                    binom_batch.append((bkey, tid))
                if len(record_batch) >= BATCH_SIZE:
                    conn.executemany(
                        """INSERT OR REPLACE INTO inat_record
                           (inat_id, genus, family, phylum, kingdom)
                           VALUES (?, ?, ?, ?, ?)""",
                        record_batch,
                    )
                    conn.executemany(
                        "INSERT OR IGNORE INTO inat_name (name_norm, inat_id) VALUES (?, ?)",
                        batch,
                    )
                    conn.executemany(
                        "INSERT OR IGNORE INTO inat_binomial (binom_key, inat_id) VALUES (?, ?)",
                        binom_batch,
                    )
                    record_batch.clear()
                    batch.clear()
                    binom_batch.clear()
    if record_batch:
        conn.executemany(
            """INSERT OR REPLACE INTO inat_record
               (inat_id, genus, family, phylum, kingdom)
               VALUES (?, ?, ?, ?, ?)""",
            record_batch,
        )
    if batch:
        conn.executemany(
            "INSERT OR IGNORE INTO inat_name (name_norm, inat_id) VALUES (?, ?)",
            batch,
        )
    if binom_batch:
        conn.executemany(
            "INSERT OR IGNORE INTO inat_binomial (binom_key, inat_id) VALUES (?, ?)",
            binom_batch,
        )
    return conn.execute("SELECT COUNT(*) FROM inat_record").fetchone()[0]


def _cross_universe_input_paths(repo_root: Path) -> list[Path]:
    from pipeline.schema import CACHE_FILES

    paths = [
        repo_root / CACHE_FILES["gbif_backbone"],
        repo_root / CACHE_FILES["inat_taxonomy"],
    ]
    otl_tax = find_otl_taxonomy_tsv(repo_root)
    if otl_tax is not None:
        paths.append(otl_tax)
    return paths


def _cross_universe_stale(db_path: Path, repo_root: Path) -> bool:
    if not db_path.is_file():
        return True
    db_mtime = db_path.stat().st_mtime
    for path in _cross_universe_input_paths(repo_root):
        if path.is_file() and path.stat().st_mtime > db_mtime:
            return True
    return False


def build_cross_universe_db(
    db_path: Path,
    repo_root: Path,
    *,
    force: bool = False,
) -> Path:
    if db_path.is_file() and not force and not _cross_universe_stale(db_path, repo_root):
        print(f"Using cached {db_path}", file=sys.stderr)
        return db_path

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.is_file():
        db_path.unlink()

    print(f"Building {db_path}...", file=sys.stderr)
    conn = sqlite3.connect(db_path)
    _build_pragmas(conn, building=True)
    conn.executescript(SCHEMA)

    otl_tax = find_otl_taxonomy_tsv(repo_root)
    if otl_tax is not None:
        forwards = _load_ott_forwards(find_otl_forwards_tsv(repo_root, otl_tax))
        synonyms_path = find_otl_synonyms_tsv(repo_root, otl_tax)
        _load_otl_mappings(conn, otl_tax, forwards)
        _load_otl_synonyms(conn, otl_tax, synonyms_path, forwards)
        n_otl = conn.execute("SELECT COUNT(*) FROM ncbi_to_ott").fetchone()[0]
        n_og = conn.execute("SELECT COUNT(*) FROM ott_to_gbif").fetchone()[0]
        n_os = conn.execute("SELECT COUNT(*) FROM ott_synonym").fetchone()[0]
        print(f"  OTL: {n_otl:,} NCBI→OTT, {n_og:,} OTT→GBIF, {n_os:,} ott_synonym", file=sys.stderr)
    else:
        print("  OTL taxonomy not found; skipping OTL", file=sys.stderr)

    from pipeline.schema import CACHE_FILES

    gbif_n = _load_gbif(conn, repo_root / CACHE_FILES["gbif_backbone"])
    print(f"  GBIF: {gbif_n:,} accepted species", file=sys.stderr)

    inat_n = _load_inat(conn, repo_root / CACHE_FILES["inat_taxonomy"])
    print(f"  iNat: {inat_n:,} species names", file=sys.stderr)


    conn.commit()
    conn.close()
    print(f"Wrote cross_universe.db", file=sys.stderr)
    return db_path


def main() -> None:
    import argparse

    repo = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Build cross_universe.db for IUCN resolution")
    parser.add_argument(
        "--output",
        type=Path,
        default=repo / "datasets" / "cross_universe.db",
        help="Output SQLite path",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    build_cross_universe_db(args.output, repo, force=args.force)


if __name__ == "__main__":
    main()
