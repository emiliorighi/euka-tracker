#!/usr/bin/env python3
"""Annotrieve annotation export for eukaryotes → TSV (paginated, 1k per request)."""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path
from typing import Any, Iterator

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

ANNOTRIEVE_API = "https://genome.crg.es/annotrieve/api/v0"
ANNOTRIEVE_ANNOTATIONS_URL = f"{ANNOTRIEVE_API}/annotations"

EUKARYOTA_TAXID = 2759
PAGE_LIMIT = 1000  # API maximum per request

ANNOTRIEVE_ANNOTATION_FIELDS = [
    "annotation_id",
    "assembly_accession",
    "taxid",
    "tax_lineage",
    "db_source",
    "release_date",
    "source_url",
    "busco_complete",
    "busco_single_copy",
    "busco_lineage",
    "lncrna_gene_count",
    "mrna_gene_count",
    "mrna_avg_length_full",
    "mrna_avg_length_exon_concat",
    "mrna_avg_length_cds_concat",
    "mrna_transcript_count",
    "lncrna_avg_length_full",
    "lncrna_avg_length_exon_concat",
    "lncrna_transcript_count",
    "total_genes_count",
    "total_transcripts_count",
]


def annotrieve_annotation_params(offset: int = 0, limit: int = PAGE_LIMIT) -> dict[str, str | int]:
    """Query parameters for GET /annotations."""
    return {
        "taxids": EUKARYOTA_TAXID,
        "offset": offset,
        "limit": min(limit, PAGE_LIMIT),
    }


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _mean(stats: dict[str, Any] | None, *path: str) -> float | None:
    if not stats:
        return None
    node: Any = stats
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    if isinstance(node, dict):
        return _as_float(node.get("mean"))
    return _as_float(node)


def parse_annotation_record(rec: dict[str, Any]) -> dict[str, Any] | None:
    """Map Annotrieve JSON record to TSV row (TODO.txt ANNOTATION fields)."""
    assembly_accession = rec.get("assembly_accession")
    taxid = rec.get("taxid")
    if not assembly_accession or taxid is None:
        return None

    lineage = rec.get("taxon_lineage") or []
    if str(EUKARYOTA_TAXID) not in {str(t) for t in lineage}:
        return None

    source = rec.get("source_file_info") or {}
    stats = rec.get("features_statistics") or {}
    gene_cats = stats.get("gene_category_stats") or {}
    tx_types = stats.get("transcript_type_stats") or {}

    mrna = tx_types.get("mRNA") or {}
    lncrna = tx_types.get("lnc_RNA") or {}
    mrna_genes = (mrna.get("associated_genes") or {}).get("total_count")
    lncrna_genes = (lncrna.get("associated_genes") or {}).get("total_count")

    total_genes = sum(
        _as_int((gene_cats.get(cat) or {}).get("total_count")) or 0
        for cat in ("coding", "non_coding", "pseudogene")
    )
    total_transcripts = sum(
        _as_int((tx_types.get(t) or {}).get("total_count")) or 0 for t in tx_types
    )
    busco = rec.get("busco") or {}

    return {
        "annotation_id": rec.get("annotation_id") or "",
        "assembly_accession": assembly_accession,
        "taxid": int(taxid),
        "tax_lineage": ",".join(str(t) for t in lineage),
        "db_source": source.get("database") or "",
        "release_date": source.get("release_date") or "",
        "source_url": source.get("url_path") or "",
        "busco_complete": _as_float(busco.get("complete")),
        "busco_single_copy": _as_float(busco.get("single_copy")),
        "busco_lineage": busco.get("busco_lineage") or "",
        "lncrna_gene_count": _as_int(lncrna_genes),
        "mrna_gene_count": _as_int(mrna_genes),
        "mrna_avg_length_full": _mean(mrna, "length_stats"),
        "mrna_avg_length_exon_concat": _mean(
            mrna.get("exon_stats") if mrna else None, "concatenated_length"
        ),
        "mrna_avg_length_cds_concat": _mean(
            mrna.get("cds_stats") if mrna else None, "concatenated_length"
        ),
        "mrna_transcript_count": _as_int(mrna.get("total_count")),
        "lncrna_avg_length_full": _mean(lncrna, "length_stats"),
        "lncrna_avg_length_exon_concat": _mean(
            lncrna.get("exon_stats") if lncrna else None, "concatenated_length"
        ),
        "lncrna_transcript_count": _as_int(lncrna.get("total_count")),
        "total_genes_count": total_genes or None,
        "total_transcripts_count": total_transcripts or None,
    }


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=60))
def _fetch_page(offset: int, limit: int = PAGE_LIMIT) -> dict[str, Any]:
    response = requests.get(
        ANNOTRIEVE_ANNOTATIONS_URL,
        params=annotrieve_annotation_params(offset=offset, limit=limit),
        headers={"Accept": "application/json"},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def iter_annotrieve_annotations(
    *,
    page_limit: int = PAGE_LIMIT,
    sleep_seconds: float = 0.2,
) -> Iterator[dict[str, Any]]:
    """Paginate Annotrieve /annotations (max 1k records per request)."""
    offset = 0
    total: int | None = None

    while total is None or offset < total:
        payload = _fetch_page(offset, page_limit)
        total = int(payload.get("total") or 0)
        results = payload.get("results") or []

        if not results:
            break

        for rec in results:
            row = parse_annotation_record(rec)
            if row is not None:
                yield row

        offset += len(results)
        if sleep_seconds:
            time.sleep(sleep_seconds)


def iter_annotrieve_annotations_tsv(path: Path) -> Iterator[dict[str, Any]]:
    """Stream annotations from a staged TSV file."""
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row.get("taxid"):
                try:
                    row["taxid"] = int(row["taxid"])
                except ValueError:
                    continue
                yield row


def write_annotrieve_annotations_tsv(out_path: Path) -> int:
    """Fetch eukaryotic annotations and write TSV. Returns row count."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=ANNOTRIEVE_ANNOTATION_FIELDS,
            delimiter="\t",
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in iter_annotrieve_annotations():
            writer.writerow(
                {k: "" if row.get(k) is None else row[k] for k in ANNOTRIEVE_ANNOTATION_FIELDS}
            )
            count += 1
    return count


if __name__ == "__main__":
    import argparse

    repo_root = Path(__file__).resolve().parent.parent
    default_out = repo_root / "data" / "staged" / "03_annotrieve_annotations.tsv"

    parser = argparse.ArgumentParser(
        description="Export eukaryotic genome annotations from Annotrieve to TSV"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=default_out,
        help=f"Output TSV path (default: {default_out})",
    )
    args = parser.parse_args()

    print(f"URL: {ANNOTRIEVE_ANNOTATIONS_URL}", file=sys.stderr)
    print(f"Params: taxids={EUKARYOTA_TAXID}, limit={PAGE_LIMIT} per page", file=sys.stderr)
    print(f"Fields: {','.join(ANNOTRIEVE_ANNOTATION_FIELDS)}", file=sys.stderr)
    n = write_annotrieve_annotations_tsv(args.output)
    print(f"Wrote {n} annotations to {args.output}", file=sys.stderr)
