#!/usr/bin/env python3
"""Map NCBI taxids to iNaturalist photos via taxonomy DwCA + batched API."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
import time
import zipfile
from pathlib import Path
from typing import Any, Iterator
from urllib.request import Request, urlopen

try:
    import requests
    from requests.exceptions import ConnectionError as RequestsConnectionError
    from requests.exceptions import Timeout
    from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
except ImportError:
    requests = None  # type: ignore
    RequestsConnectionError = Timeout = Exception  # type: ignore
    retry = retry_if_exception_type = stop_after_attempt = wait_exponential = None  # type: ignore

TAXONOMY_DWCA_URL = "https://www.inaturalist.org/taxa/inaturalist-taxonomy.dwca.zip"
INAT_API_BASE = "https://api.inaturalist.org/v1"
DEFAULT_USER_AGENT = "euka-tracker/1.0 (biodiversity genomics tracker; pipeline/inaturalist_photos_fetch.py)"

SPECIES_PHOTO_FIELDS = [
    "taxid",
    "scientific_name",
    "inat_taxon_id",
    "photo_url",
    "photo_license",
    "photo_attribution",
]

API_BATCH_SIZE = 200
API_PAUSE_SEC = 1.0


def _escape_tsv(value: Any) -> str:
    if value is None or value == "":
        return ""
    return str(value).replace("\t", " ").replace("\n", " ").replace("\r", " ")


def _normalize_name(name: str | None) -> str:
    if not name:
        return ""
    return " ".join(name.split()).strip()


def download_file(url: str, dest: Path, *, force: bool = False) -> None:
    if dest.is_file() and not force:
        print(f"Using cached {dest}", file=sys.stderr)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} → {dest}", file=sys.stderr)
    req = Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    with urlopen(req, timeout=600) as resp, open(dest, "wb") as out:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = downloaded * 100 // total
                print(f"  … {pct}% ({downloaded // (1024 * 1024)} MiB)", file=sys.stderr, end="\r")
    print(file=sys.stderr)


def ensure_taxonomy_dwca(cache_dir: Path, *, force: bool = False) -> Path:
    zip_path = cache_dir / "inaturalist-taxonomy.dwca.zip"
    download_file(TAXONOMY_DWCA_URL, zip_path, force=force)
    return zip_path


def iter_inat_species_taxa(dwca_zip: Path) -> Iterator[tuple[int, str]]:
    """Yield (inat_taxon_id, scientific_name) for species rank from DwCA taxa.csv."""
    with zipfile.ZipFile(dwca_zip) as zf:
        with zf.open("taxa.csv") as raw:
            text = (line.decode("utf-8") for line in raw)
            reader = csv.DictReader(text)
            for row in reader:
                if (row.get("taxonRank") or "").lower() != "species":
                    continue
                name = _normalize_name(row.get("scientificName"))
                if not name:
                    continue
                try:
                    taxon_id = int(row["id"])
                except (KeyError, TypeError, ValueError):
                    continue
                yield taxon_id, name


def build_inat_name_index(dwca_zip: Path, cache_dir: Path, *, force: bool = False) -> dict[str, int]:
    """Map lowercase scientific name → iNat taxon_id (last species wins on duplicates)."""
    cache_path = cache_dir / "inat_species_name_index.json"
    if cache_path.is_file() and not force:
        print(f"Loading cached iNat name index from {cache_path}", file=sys.stderr)
        with open(cache_path, encoding="utf-8") as f:
            raw = json.load(f)
        return {k: int(v) for k, v in raw.items()}

    index: dict[str, int] = {}
    for taxon_id, name in iter_inat_species_taxa(dwca_zip):
        index[name.lower()] = taxon_id

    cache_dir.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(index, f)
    print(f"Cached iNat name index ({len(index):,} names) → {cache_path}", file=sys.stderr)
    return index


def load_taxid_filter(path: Path) -> set[int]:
    """Load taxids from a text file (one per line) or TSV with a taxid column."""
    taxids: set[int] = set()
    with open(path, encoding="utf-8") as f:
        first = f.readline()
        f.seek(0)
        if "\t" in first and "taxid" in first.lower():
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                val = row.get("taxid") or row.get("id")
                if val:
                    try:
                        taxids.add(int(val))
                    except ValueError:
                        pass
        else:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    try:
                        taxids.add(int(line.split()[0]))
                    except ValueError:
                        pass
    return taxids


def load_ncbi_taxa(
    taxonomy_path: Path,
    *,
    ranks: set[str] | None = None,
    taxid_filter: set[int] | None = None,
) -> list[tuple[int, str, str]]:
    """Load (taxid, name, rank) from NCBI taxonomy tree TSV or TSV.GZ."""
    open_fn = gzip.open if taxonomy_path.suffix == ".gz" else open
    mode = "rt" if taxonomy_path.suffix == ".gz" else "r"
    rows: list[tuple[int, str, str]] = []
    with open_fn(taxonomy_path, mode, encoding="utf-8") as f:
        header = f.readline()
        if not header.startswith("parent_id"):
            f.seek(0)
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 4:
                continue
            try:
                taxid = int(parts[1])
            except ValueError:
                continue
            if taxid_filter is not None and taxid not in taxid_filter:
                continue
            name = _normalize_name(parts[2])
            rank = parts[3].strip().lower()
            if ranks and rank not in ranks:
                continue
            if name:
                rows.append((taxid, name, rank))
    return rows


def match_ncbi_to_inat(
    ncbi_taxa: list[tuple[int, str, str]],
    inat_index: dict[str, int],
) -> list[dict[str, Any]]:
    matched: list[dict[str, Any]] = []
    for taxid, name, rank in ncbi_taxa:
        inat_id = inat_index.get(name.lower())
        if inat_id is None:
            continue
        matched.append(
            {
                "taxid": taxid,
                "scientific_name": name,
                "inat_taxon_id": inat_id,
                "rank": rank,
            }
        )
    return matched


def _fetch_taxa_batch(
    session: Any,
    params: dict[str, Any],
) -> dict[str, Any]:
    if retry is None:
        resp = session.get(f"{INAT_API_BASE}/taxa", params=params, timeout=120)
        resp.raise_for_status()
        return resp.json()

    @retry(
        retry=retry_if_exception_type((RequestsConnectionError, Timeout)),
        stop=stop_after_attempt(6),
        wait=wait_exponential(multiplier=2, min=4, max=120),
        reraise=True,
    )
    def _get() -> dict[str, Any]:
        resp = session.get(f"{INAT_API_BASE}/taxa", params=params, timeout=120)
        resp.raise_for_status()
        return resp.json()

    return _get()


def fetch_taxa_photos_api(
    inat_taxon_ids: list[int],
    *,
    batch_size: int = API_BATCH_SIZE,
    pause_sec: float = API_PAUSE_SEC,
    allowed_licenses: set[str] | None = None,
) -> dict[int, dict[str, str]]:
    if requests is None:
        raise SystemExit("requests is required. Install with: pip install requests")

    photos: dict[int, dict[str, str]] = {}
    unique_ids = sorted(set(inat_taxon_ids))
    session = requests.Session()
    session.headers["User-Agent"] = DEFAULT_USER_AGENT

    for i in range(0, len(unique_ids), batch_size):
        chunk = unique_ids[i : i + batch_size]
        params = {"id": ",".join(str(tid) for tid in chunk), "per_page": batch_size}
        data = _fetch_taxa_batch(session, params)
        for taxon in data.get("results", []):
            tid = taxon.get("id")
            if tid is None:
                continue
            default_photo = taxon.get("default_photo") or {}
            license_code = (default_photo.get("license_code") or "").lower()
            if allowed_licenses and license_code and license_code not in allowed_licenses:
                continue
            if not default_photo:
                continue
            url = (
                default_photo.get("medium_url")
                or default_photo.get("url")
                or default_photo.get("square_url")
                or ""
            )
            if not url:
                continue
            photos[int(tid)] = {
                "photo_url": url,
                "photo_license": license_code,
                "photo_attribution": default_photo.get("attribution") or "",
            }
        done = min(i + batch_size, len(unique_ids))
        print(f"Fetched photos for {done}/{len(unique_ids)} iNat taxa…", file=sys.stderr)
        if i + batch_size < len(unique_ids):
            time.sleep(pause_sec)

    return photos


PHOTO_MATRIX_FIELDS = ("inat_taxon_id", "photo_url", "photo_license", "photo_attribution")


def load_species_photos_by_taxid(path: Path) -> dict[int, dict[str, str]]:
    """Stream species_photos.tsv → taxid → {inat_taxon_id, photo_url, ...}."""
    photos: dict[int, dict[str, str]] = {}
    if not path.is_file():
        return photos
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            taxid_raw = row.get("taxid") or ""
            if not taxid_raw:
                continue
            try:
                taxid = int(taxid_raw)
            except ValueError:
                continue
            photos[taxid] = {
                field: row.get(field) or "" for field in PHOTO_MATRIX_FIELDS
            }
    return photos


def write_species_photos_tsv(
    rows: list[dict[str, Any]],
    out_path: Path,
) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=SPECIES_PHOTO_FIELDS,
            delimiter="\t",
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _escape_tsv(row.get(k)) for k in SPECIES_PHOTO_FIELDS})
    return len(rows)


def build_species_photos(
    taxonomy_path: Path,
    out_path: Path,
    *,
    cache_dir: Path,
    ranks: set[str] | None = None,
    taxid_filter: set[int] | None = None,
    refresh_taxonomy: bool = False,
    skip_photos: bool = False,
    batch_size: int = API_BATCH_SIZE,
    allowed_licenses: set[str] | None = None,
    limit: int | None = None,
) -> tuple[int, int, int]:
    """Returns (ncbi_taxa, name_matched, rows_with_photo)."""
    dwca_zip = ensure_taxonomy_dwca(cache_dir, force=refresh_taxonomy)
    print("Indexing iNaturalist species names from DwCA…", file=sys.stderr)
    inat_index = build_inat_name_index(dwca_zip, cache_dir, force=refresh_taxonomy)
    print(f"  {len(inat_index):,} iNat species names indexed", file=sys.stderr)

    print(f"Loading NCBI taxonomy from {taxonomy_path}…", file=sys.stderr)
    ncbi_taxa = load_ncbi_taxa(taxonomy_path, ranks=ranks, taxid_filter=taxid_filter)
    if limit is not None:
        ncbi_taxa = ncbi_taxa[:limit]
    print(f"  {len(ncbi_taxa):,} NCBI taxa loaded", file=sys.stderr)

    matched = match_ncbi_to_inat(ncbi_taxa, inat_index)
    print(f"Matched {len(matched):,}/{len(ncbi_taxa):,} NCBI taxa to iNat taxon IDs", file=sys.stderr)

    photo_by_inat: dict[int, dict[str, str]] = {}
    if not skip_photos and matched:
        inat_ids = [row["inat_taxon_id"] for row in matched]
        photo_by_inat = fetch_taxa_photos_api(
            inat_ids,
            batch_size=batch_size,
            allowed_licenses=allowed_licenses,
        )

    output_rows: list[dict[str, Any]] = []
    with_photo = 0
    for row in matched:
        photo = photo_by_inat.get(row["inat_taxon_id"], {})
        out = {
            "taxid": row["taxid"],
            "scientific_name": row["scientific_name"],
            "inat_taxon_id": row["inat_taxon_id"],
            "photo_url": photo.get("photo_url", ""),
            "photo_license": photo.get("photo_license", ""),
            "photo_attribution": photo.get("photo_attribution", ""),
        }
        if out["photo_url"]:
            with_photo += 1
        output_rows.append(out)

    write_species_photos_tsv(output_rows, out_path)
    return len(ncbi_taxa), len(matched), with_photo


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    default_taxonomy = repo_root / "data" / "ncbi_taxonomy_tree.tsv.gz"
    if not default_taxonomy.is_file():
        default_taxonomy = repo_root / "data" / "ncbi_taxonomy_tree.tsv"
    default_out = repo_root / "data" / "species_photos.tsv"
    default_cache = repo_root / "data" / "inaturalist_cache"

    parser = argparse.ArgumentParser(
        description="Map NCBI taxids to iNaturalist photos (DwCA name match + batched API)"
    )
    parser.add_argument(
        "--ncbi-taxonomy",
        type=Path,
        default=default_taxonomy,
        help="NCBI taxonomy tree TSV (.gz), columns: parent_id, id, name, rank",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=default_out,
        help=f"Output TSV (default: {default_out})",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=default_cache,
        help=f"Cache directory for DwCA download (default: {default_cache})",
    )
    parser.add_argument(
        "--rank",
        action="append",
        dest="ranks",
        help="Only include NCBI taxa at this rank (repeatable, default: species)",
    )
    parser.add_argument(
        "--refresh-taxonomy",
        action="store_true",
        help="Re-download iNaturalist taxonomy DwCA zip",
    )
    parser.add_argument(
        "--skip-photos",
        action="store_true",
        help="Only write taxid → inat_taxon_id mapping (no API photo fetch)",
    )
    parser.add_argument(
        "--photo-license",
        action="append",
        dest="photo_licenses",
        help="Only keep photos with these licenses (e.g. cc0, cc-by). Default: any",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=API_BATCH_SIZE,
        help=f"iNat API taxa batch size (default: {API_BATCH_SIZE})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Process only the first N NCBI taxa (for testing)",
    )
    parser.add_argument(
        "--taxids-file",
        type=Path,
        help="Only process taxids listed in this file (one per line, or TSV with taxid column)",
    )
    args = parser.parse_args()

    if not args.ncbi_taxonomy.is_file():
        print(f"Error: NCBI taxonomy not found: {args.ncbi_taxonomy}", file=sys.stderr)
        sys.exit(1)

    ranks = {r.lower() for r in args.ranks} if args.ranks else {"species"}
    licenses = {lic.lower() for lic in args.photo_licenses} if args.photo_licenses else None
    taxid_filter: set[int] | None = None
    if args.taxids_file:
        if not args.taxids_file.is_file():
            print(f"Error: taxids file not found: {args.taxids_file}", file=sys.stderr)
            sys.exit(1)
        taxid_filter = load_taxid_filter(args.taxids_file)
        print(f"Filtering to {len(taxid_filter):,} taxids from {args.taxids_file}", file=sys.stderr)

    print(f"NCBI taxonomy: {args.ncbi_taxonomy}", file=sys.stderr)
    print(f"Output: {args.output}", file=sys.stderr)
    print(f"Cache: {args.cache_dir}", file=sys.stderr)
    print(f"NCBI ranks: {', '.join(sorted(ranks))}", file=sys.stderr)

    ncbi_n, matched_n, photo_n = build_species_photos(
        args.ncbi_taxonomy,
        args.output,
        cache_dir=args.cache_dir,
        ranks=ranks,
        taxid_filter=taxid_filter,
        refresh_taxonomy=args.refresh_taxonomy,
        skip_photos=args.skip_photos,
        batch_size=args.batch_size,
        allowed_licenses=licenses,
        limit=args.limit,
    )
    print(
        f"Wrote {matched_n} rows ({photo_n} with photos) from {ncbi_n} NCBI taxa to {args.output}",
        file=sys.stderr,
    )
