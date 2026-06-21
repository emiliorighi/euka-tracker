#!/usr/bin/env python3
"""ENA read_run export for eukaryotes (library_source filter, minimal fields)."""

from __future__ import annotations

import csv
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Iterator

import requests

ENA_SEARCH_API = "https://www.ebi.ac.uk/ena/portal/api/search"

EUKARYOTE_READ_RUN_QUERY = (
    "tax_tree(2759) AND "
    "not_tax_tree(2) AND "
    "not_tax_eq(2157) AND "
    '(library_source="GENOMIC" OR library_source="TRANSCRIPTOMIC" OR '
    'library_source="GENOMIC SINGLE CELL" OR library_source="TRANSCRIPTOMIC SINGLE CELL")'
)

EUKARYOTE_READ_RUN_FIELDS = [
    "tax_id",
    "run_accession",
    "library_source",
    "instrument_platform",
]


def eukaryote_read_run_post_data(fmt: str = "tsv") -> dict[str, str]:
    return {
        "result": "read_run",
        "query": EUKARYOTE_READ_RUN_QUERY,
        "fields": ",".join(EUKARYOTE_READ_RUN_FIELDS),
        "format": fmt,
        "limit": "0",
    }


def fetch_eukaryote_read_runs() -> requests.Response:
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
    if value is None:
        return None
    s = str(value).strip()
    if not s or ";" in s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def iter_read_runs_tsv(path: Path) -> Iterator[dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            yield row


def write_eukaryote_read_runs_tsv(out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    response = fetch_eukaryote_read_runs()
    count = 0
    header: list[str] | None = None

    print(f"Query: {EUKARYOTE_READ_RUN_QUERY}", file=sys.stderr)
    print(f"Writing to {out_path}...", file=sys.stderr)

    with open(out_path, "w", encoding="utf-8", newline="") as out_f:
        writer: csv.DictWriter | None = None
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            parts = line.split("\t")
            if header is None:
                header = parts
                writer = csv.DictWriter(
                    out_f,
                    fieldnames=header,
                    delimiter="\t",
                    extrasaction="ignore",
                )
                writer.writeheader()
                continue
            if writer is None:
                continue
            row = {header[i]: parts[i] if i < len(parts) else "" for i in range(len(header))}
            writer.writerow(row)
            count += 1
            if count % 500_000 == 0:
                print(f"  … {count:,} runs", file=sys.stderr)

    print(f"Wrote {count:,} read runs to {out_path}", file=sys.stderr)
    return count


def fetch_reads(datasets_dir: Path, *, force: bool = False) -> Path:
    out_path = datasets_dir / "ena_read_runs.tsv"
    if out_path.is_file() and not force:
        print(f"Using cached {out_path}", file=sys.stderr)
        return out_path
    write_eukaryote_read_runs_tsv(out_path)
    return out_path


if __name__ == "__main__":
    import argparse

    repo = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Export eukaryotic ENA read runs")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=repo / "datasets" / "ena_read_runs.tsv",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.force or not args.output.is_file():
        write_eukaryote_read_runs_tsv(args.output)
    else:
        print(f"Using cached {args.output}", file=sys.stderr)
