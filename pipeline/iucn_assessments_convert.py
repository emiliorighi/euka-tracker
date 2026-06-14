#!/usr/bin/env python3
"""Stream IUCN Red List assessments.csv → slim TSV with NCBI taxid.

IUCN ``internalTaxonId`` is an IUCN-only identifier — never used as NCBI taxid.
NCBI taxids are resolved from scientific names (plus IUCN synonyms) via ete3.
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import sys
from pathlib import Path
from typing import Any, Iterator

IUCN_STRUCTURED_FIELDS = [
    "redlist_category",
    "population_trend",
    "systems",
    "realm",
    "possibly_extinct",
    "possibly_extinct_ew",
]

IUCN_OUTPUT_FIELDS = [
    "internal_taxon_id",
    "taxid",
    "scientific_name",
    *IUCN_STRUCTURED_FIELDS,
    "habitat",
    "threats",
    "population",
    "conservation_actions",
]

NCBI_BATCH_SIZE = 5000
_TAG_RE = re.compile(r"<[^>]+>")


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = html.unescape(value).replace("\xa0", " ")
    text = _TAG_RE.sub(" ", text)
    return " ".join(text.split())


def _normalize_scientific_name(name: str | None) -> str:
    if not name:
        return ""
    return " ".join(html.unescape(name).split()).strip()


def _escape_tsv(value: Any) -> str:
    if value is None or value == "":
        return ""
    s = str(value).replace("\t", " ").replace("\n", " ").replace("\r", " ")
    return s


def _bool_flag(value: str | None) -> str:
    if not value:
        return "0"
    v = value.strip().lower()
    if v in ("1", "true", "yes", "y"):
        return "1"
    return "0"


def _load_ncbi_taxa(*, update: bool = False):
    try:
        from ete3 import NCBITaxa
    except ImportError as exc:
        raise SystemExit(
            "ete3 is required for NCBI taxid mapping. Install with: pip install ete3"
        ) from exc
    ncbi = NCBITaxa(update=False)
    if update:
        print("Downloading latest NCBI taxdump and rebuilding ete3 database…", file=sys.stderr)
        ncbi.update_taxonomy_database()
        species_count = ncbi.db.execute("SELECT COUNT(*) FROM species").fetchone()[0]
        print(f"ete3 database rebuilt ({species_count:,} species)", file=sys.stderr)
    return ncbi


def _pick_taxid(ncbi: Any, taxids: list[int], internal_taxon_id: str, matched_name: str) -> int | None:
    """Choose one NCBI taxid; reject accidental internalTaxonId numeric collisions."""
    if not taxids:
        return None

    ranks = ncbi.get_rank(taxids)
    species_ids = [tid for tid in taxids if ranks.get(tid) == "species"]
    chosen = species_ids[0] if species_ids else taxids[0]

    try:
        if int(internal_taxon_id) == chosen:
            ncbi_name = ncbi.get_taxid_translator([chosen]).get(chosen, "")
            if _normalize_scientific_name(ncbi_name).lower() != _normalize_scientific_name(
                matched_name
            ).lower():
                return None
    except (TypeError, ValueError):
        pass

    return int(chosen)


def _lookup_names_sqlite(ncbi: Any, names: list[str]) -> dict[str, list[int]]:
    """Case-insensitive name → taxid lookup using parameterized SQL (quote-safe)."""
    if not names:
        return {}

    lower_to_original: dict[str, str] = {}
    for name in names:
        norm = _normalize_scientific_name(name)
        if norm:
            lower_to_original.setdefault(norm.lower(), norm)

    found: dict[str, list[int]] = {}
    lowers = list(lower_to_original.keys())

    for i in range(0, len(lowers), NCBI_BATCH_SIZE):
        chunk = lowers[i : i + NCBI_BATCH_SIZE]
        placeholders = ",".join("?" * len(chunk))

        for table in ("species", "synonym"):
            still_missing = [key for key in chunk if key not in found]
            if not still_missing:
                break
            ph = ",".join("?" * len(still_missing))
            query = (
                f"SELECT spname, taxid FROM {table} "
                f"WHERE lower(spname) IN ({ph})"
            )
            for spname, taxid in ncbi.db.execute(query, still_missing):
                original = lower_to_original[spname.lower()]
                found.setdefault(original, []).append(int(taxid))

    return found


def _resolve_names_batch(
    ncbi: Any,
    names: list[str],
    cache: dict[str, int | None],
    internal_by_name: dict[str, str],
) -> None:
    pending = [name for name in names if name not in cache]
    for i in range(0, len(pending), NCBI_BATCH_SIZE):
        chunk = pending[i : i + NCBI_BATCH_SIZE]
        translated = _lookup_names_sqlite(ncbi, chunk)
        for name in chunk:
            taxids = translated.get(name, [])
            if not taxids:
                cache[name] = None
                continue
            internal_taxon_id = internal_by_name.get(name, "")
            cache[name] = _pick_taxid(ncbi, taxids, internal_taxon_id, name)


def load_iucn_name_candidates(
    assessments_path: Path,
    redlist_dir: Path,
) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Map internalTaxonId → ordered scientific-name candidates; name → internalTaxonId."""
    accepted: dict[str, str] = {}
    with open(assessments_path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            iid = row["internalTaxonId"]
            accepted[iid] = _normalize_scientific_name(row.get("scientificName"))

    candidates: dict[str, list[str]] = {iid: [accepted[iid]] for iid in accepted if accepted[iid]}

    synonyms_path = redlist_dir / "synonyms.csv"
    if synonyms_path.is_file():
        with open(synonyms_path, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                iid = row.get("internalTaxonId", "")
                if iid not in candidates:
                    continue
                genus = _normalize_scientific_name(row.get("genusName"))
                species = _normalize_scientific_name(row.get("speciesName"))
                if genus and species:
                    binom = f"{genus} {species}"
                    if binom not in candidates[iid]:
                        candidates[iid].append(binom)

    taxonomy_path = redlist_dir / "taxonomy.csv"
    if taxonomy_path.is_file():
        with open(taxonomy_path, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                iid = row.get("internalTaxonId", "")
                if iid not in candidates:
                    continue
                genus = _normalize_scientific_name(row.get("genusName"))
                species = _normalize_scientific_name(row.get("speciesName"))
                infra_type = _normalize_scientific_name(row.get("infraType"))
                infra_name = _normalize_scientific_name(row.get("infraName"))
                if genus and species:
                    binom = f"{genus} {species}"
                    if binom not in candidates[iid]:
                        candidates[iid].append(binom)
                    if infra_type and infra_name:
                        infra = f"{genus} {species} {infra_type} {infra_name}"
                        if infra not in candidates[iid]:
                            candidates[iid].append(infra)

    name_to_internal: dict[str, str] = {}
    for iid, names in candidates.items():
        for name in names:
            name_to_internal.setdefault(name, iid)

    return candidates, name_to_internal


def build_taxid_cache(
    candidates: dict[str, list[str]],
    name_to_internal: dict[str, str],
    *,
    update_ncbi: bool = False,
) -> dict[str, int | None]:
    ncbi = _load_ncbi_taxa(update=update_ncbi)
    cache: dict[str, int | None] = {}

    accepted_names = sorted({names[0] for names in candidates.values() if names})
    print(f"Resolving {len(accepted_names)} accepted scientific names…", file=sys.stderr)
    _resolve_names_batch(ncbi, accepted_names, cache, name_to_internal)

    supplemental: list[str] = []
    for iid, names in candidates.items():
        if any(cache.get(name) for name in names[:1]):
            continue
        supplemental.extend(names[1:])

    supplemental = sorted({name for name in supplemental if name not in cache})
    if supplemental:
        print(
            f"Trying {len(supplemental)} synonym/infra name variants for unmapped taxa…",
            file=sys.stderr,
        )
        _resolve_names_batch(ncbi, supplemental, cache, name_to_internal)

    taxid_by_iid: dict[str, int | None] = {}
    for iid, names in candidates.items():
        taxid_by_iid[iid] = None
        for name in names:
            resolved = cache.get(name)
            if resolved is not None:
                taxid_by_iid[iid] = resolved
                break
    return taxid_by_iid


def iter_assessment_rows(
    assessments_path: Path,
    taxid_by_iid: dict[str, int | None] | None,
) -> Iterator[dict[str, str]]:
    with open(assessments_path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            internal_taxon_id = row.get("internalTaxonId", "")
            taxid = ""
            if taxid_by_iid is not None and internal_taxon_id:
                resolved = taxid_by_iid.get(internal_taxon_id)
                if resolved is not None:
                    taxid = str(resolved)

            yield {
                "internal_taxon_id": internal_taxon_id,
                "taxid": taxid,
                "scientific_name": _clean_text(row.get("scientificName")),
                "redlist_category": _clean_text(row.get("redlistCategory")),
                "population_trend": _clean_text(row.get("populationTrend")),
                "systems": _clean_text(row.get("systems")),
                "realm": _clean_text(row.get("realm")),
                "possibly_extinct": _bool_flag(row.get("possiblyExtinct")),
                "possibly_extinct_ew": _bool_flag(row.get("possiblyExtinctInTheWild")),
                "habitat": _clean_text(row.get("habitat")),
                "threats": _clean_text(row.get("threats")),
                "population": _clean_text(row.get("population")),
                "conservation_actions": _clean_text(row.get("conservationActions")),
            }


def write_iucn_assessments_tsv(
    assessments_path: Path,
    out_path: Path,
    *,
    resolve_ncbi: bool = True,
    update_ncbi: bool = False,
) -> tuple[int, int]:
    """Stream convert assessments.csv to TSV. Returns (rows_written, taxid_mapped)."""
    taxid_by_iid: dict[str, int | None] | None = None
    if resolve_ncbi:
        redlist_dir = assessments_path.parent
        candidates, name_to_internal = load_iucn_name_candidates(assessments_path, redlist_dir)
        print(f"Loaded name candidates for {len(candidates)} IUCN taxa", file=sys.stderr)
        taxid_by_iid = build_taxid_cache(
            candidates, name_to_internal, update_ncbi=update_ncbi
        )
        mapped_taxa = sum(1 for v in taxid_by_iid.values() if v is not None)
        print(f"Mapped {mapped_taxa}/{len(candidates)} IUCN taxa to NCBI taxids", file=sys.stderr)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows_written = 0
    taxid_mapped = 0

    with open(out_path, "w", encoding="utf-8", newline="") as out_f:
        writer = csv.DictWriter(
            out_f,
            fieldnames=IUCN_OUTPUT_FIELDS,
            delimiter="\t",
            extrasaction="ignore",
        )
        writer.writeheader()

        for row in iter_assessment_rows(assessments_path, taxid_by_iid):
            if row["taxid"]:
                taxid_mapped += 1
            writer.writerow({k: _escape_tsv(row[k]) for k in IUCN_OUTPUT_FIELDS})
            rows_written += 1

    return rows_written, taxid_mapped


IUCN_TEXT_FIELDS = ("habitat", "threats", "population", "conservation_actions")


def load_iucn_text_by_taxid(iucn_tsv: Path) -> dict[int, dict[str, str]]:
    """Stream iucn_assessments.tsv → taxid → IUCN assessment text fields."""
    records: dict[int, dict[str, str]] = {}
    with open(iucn_tsv, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            taxid_raw = row.get("taxid") or ""
            if not taxid_raw:
                continue
            try:
                taxid = int(taxid_raw)
            except ValueError:
                continue
            rec = {field: (row.get(field) or "").strip() for field in IUCN_TEXT_FIELDS}
            if any(rec.values()):
                records[taxid] = rec
    return records


def load_iucn_by_taxid(iucn_tsv: Path) -> dict[int, dict[str, str]]:
    """Stream iucn_assessments.tsv → taxid → structured IUCN fields (last row wins)."""
    records: dict[int, dict[str, str]] = {}
    with open(iucn_tsv, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            taxid_raw = row.get("taxid") or ""
            if not taxid_raw:
                continue
            try:
                taxid = int(taxid_raw)
            except ValueError:
                continue
            rec = {field: (row.get(field) or "").strip() for field in IUCN_STRUCTURED_FIELDS}
            if row.get("scientific_name"):
                rec["scientific_name"] = (row.get("scientific_name") or "").strip()
            if any(rec.get(f) for f in IUCN_STRUCTURED_FIELDS):
                records[taxid] = rec
    return records


def load_redlist_by_taxid(iucn_tsv: Path) -> dict[int, str]:
    """Stream iucn_assessments.tsv → taxid → redlist_category (last row wins on duplicates)."""
    return {
        taxid: rec["redlist_category"]
        for taxid, rec in load_iucn_by_taxid(iucn_tsv).items()
        if rec.get("redlist_category")
    }


def default_assessments_path(repo_root: Path) -> Path | None:
    matches = sorted(repo_root.glob("redlist_species_data_*/assessments.csv"))
    return matches[-1] if matches else None


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    default_in = default_assessments_path(repo_root)
    default_out = repo_root / "data" / "iucn_assessments.tsv"

    parser = argparse.ArgumentParser(
        description="Convert IUCN assessments.csv to a slim TSV with NCBI taxid"
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=default_in,
        help="Path to IUCN assessments.csv (default: latest redlist_species_data_*/assessments.csv)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=default_out,
        help=f"Output TSV (default: {default_out})",
    )
    parser.add_argument(
        "--no-ncbi",
        action="store_true",
        help="Skip NCBI taxid resolution (taxid column will be empty)",
    )
    parser.add_argument(
        "--update-ncbi",
        action="store_true",
        help="Download latest NCBI taxdump and rebuild the ete3 sqlite database before mapping",
    )
    args = parser.parse_args()

    if args.input is None or not args.input.is_file():
        print("Error: assessments.csv not found. Pass input path explicitly.", file=sys.stderr)
        sys.exit(1)

    print(f"Input: {args.input}", file=sys.stderr)
    print(f"Output: {args.output}", file=sys.stderr)
    rows, mapped = write_iucn_assessments_tsv(
        args.input,
        args.output,
        resolve_ncbi=not args.no_ncbi,
        update_ncbi=args.update_ncbi,
    )
    unmapped = rows - mapped
    print(
        f"Wrote {rows} rows ({mapped} with NCBI taxid, {unmapped} without) to {args.output}",
        file=sys.stderr,
    )
    if unmapped:
        print(
            "Note: remaining unmapped taxa are absent from NCBI Taxonomy under the IUCN "
            "accepted name and binomial synonyms — internalTaxonId is never used as taxid.",
            file=sys.stderr,
        )
