#!/usr/bin/env python3
"""ENA read_run search — POST streaming export to staged TSV."""

from __future__ import annotations

import csv
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Iterator

import requests

ENA_SEARCH_API = "https://www.ebi.ac.uk/ena/portal/api/search"
ENA_BROWSER_URL = "https://www.ebi.ac.uk/ena/browser/advanced-search"

EUKARYOTE_READ_RUN_QUERY = (
    "tax_tree(2759) AND "
    "not_tax_tree(2) AND "
    "not_tax_eq(2157) AND "
    '(library_source="genomic" OR library_source="transcriptomic") AND '
    "base_count>10000000 AND "
    "read_count>100000 AND "
    '(library_strategy="WGS" OR library_strategy="RNA-Seq")'
)

EUKARYOTE_READ_RUN_FIELDS = [
    "run_accession",
    "experiment_title",
    "tax_id",
    "first_public",
    "library_source",
    "instrument_model",
    "instrument_platform",
    "base_count",
    "library_strategy",
    "library_layout",
    "read_count",
    "tax_lineage",
    "study_accession",
]


def eukaryote_read_run_search():
    """Return (query, fields) for the ENA read_run export."""
    return EUKARYOTE_READ_RUN_QUERY, EUKARYOTE_READ_RUN_FIELDS


def eukaryote_read_run_post_data(fmt: str = "tsv") -> dict[str, str]:
    """POST body for ENA search (limit=0 fetches all records)."""
    query, fields = eukaryote_read_run_search()
    return {
        "result": "read_run",
        "query": query,
        "fields": ",".join(fields),
        "format": fmt,
        "limit": "0",
    }


def eukaryote_read_run_params(fmt: str = "tsv") -> dict[str, str]:
    """URL query parameters for ENA search (browser preview)."""
    query, fields = eukaryote_read_run_search()
    return {
        "result": "read_run",
        "query": query,
        "fields": ",".join(fields),
        "format": fmt,
        "limit": "0",
    }


def eukaryote_read_run_url(*, api: bool = False) -> str:
    """Full GET URL with encoded params (browser or portal API)."""
    base = ENA_SEARCH_API if api else ENA_BROWSER_URL
    return f"{base}?{urllib.parse.urlencode(eukaryote_read_run_params())}"


def fetch_eukaryote_read_runs():
    """POST ENA Portal API; returns streaming response (TSV)."""
    response = requests.post(
        ENA_SEARCH_API,
        data=eukaryote_read_run_post_data(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        stream=True,
        timeout=600,
    )
    response.raise_for_status()
    return response


def parse_ena_taxid(value: Any) -> int | None:
    """Return a single NCBI taxid; skip multi-taxid ENA values (e.g. '32644;483514')."""
    if value is None:
        return None
    s = str(value).strip()
    if not s or ";" in s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _normalize_run_row(row: dict[str, str]) -> dict[str, Any]:
    out = dict(row)
    tax_key = "tax_id" if "tax_id" in out else "taxid"
    taxid = parse_ena_taxid(out.get(tax_key))
    if taxid is not None:
        out["tax_id"] = taxid
    for key in ("base_count", "read_count"):
        if out.get(key):
            try:
                out[key] = int(out[key])
            except ValueError:
                out[key] = None
    return out


def iter_eukaryote_read_runs_tsv(path: Path) -> Iterator[dict[str, Any]]:
    """Stream read runs from a staged TSV file."""
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if row.get("tax_id") or row.get("taxid"):
                yield _normalize_run_row(row)


iter_eukaryote_read_runs = iter_eukaryote_read_runs_tsv


def write_eukaryote_read_runs_tsv(out_path: Path) -> int:
    """Fetch all matching ENA read runs and write staged TSV."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    response = fetch_eukaryote_read_runs()
    count = 0
    header: list[str] | None = None

    with open(out_path, "w", encoding="utf-8", newline="") as out_f:
        writer: csv.DictWriter | None = None
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            parts = line.split("\t")
            if header is None:
                header = parts
                writer = csv.DictWriter(out_f, fieldnames=header, delimiter="\t", extrasaction="ignore")
                writer.writeheader()
                continue
            if writer is None:
                continue
            row = {header[i]: parts[i] if i < len(parts) else "" for i in range(len(header))}
            writer.writerow(row)
            count += 1

    return count


if __name__ == "__main__":
    import argparse

    repo_root = Path(__file__).resolve().parent.parent
    default_out = repo_root / "data" / "staged" / "04_ena_read_runs.tsv"

    parser = argparse.ArgumentParser(description="Export eukaryotic ENA read runs to TSV")
    parser.add_argument("-o", "--output", type=Path, default=default_out)
    args = parser.parse_args()

    print(f"Query: {EUKARYOTE_READ_RUN_QUERY}", file=sys.stderr)
    print(f"Writing to {args.output}…", file=sys.stderr)
    n = write_eukaryote_read_runs_tsv(args.output)
    print(f"Wrote {n} read runs to {args.output}", file=sys.stderr)
