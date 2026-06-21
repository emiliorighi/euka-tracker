#!/usr/bin/env python3
"""Export GoaT sequencing status to TSV (all ranks for species rollup)."""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path
from typing import Any, Iterator

import requests

GOAT_API_BASE = "https://goat.genomehubs.org/api/v2"
GOAT_QUERY = "sequencing_status!=null"
GOAT_FIELDS = "sequencing_status,bioproject"
PAGE_SIZE = 5000
REQUEST_PAUSE_SEC = 0.25

TSV_FIELDS = ["taxid", "scientific_name", "sequencing_status", "bioprojects"]


def _escape_tsv(value: Any) -> str:
    if value is None or value == "":
        return ""
    return str(value).replace("\t", " ").replace("\n", " ").replace("\r", " ")


def _attribute_map(hit: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    nested = (
        hit.get("inner_hits", {})
        .get("attributes", {})
        .get("hits", {})
        .get("hits", [])
    )
    for node in nested:
        fields = node.get("fields") or {}
        key = (fields.get("attributes.key") or [None])[0]
        if not key:
            continue
        raw = fields.get("attributes.keyword_value.raw")
        if isinstance(raw, list) and len(raw) == 1:
            out[key] = raw[0]
        else:
            out[key] = raw
    return out


def _bioprojects_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value).strip()] if str(value).strip() else []


def parse_goat_hit(hit: dict[str, Any]) -> dict[str, Any] | None:
    source = hit.get("_source") or {}
    taxid_raw = source.get("taxon_id")
    if taxid_raw is None:
        return None
    try:
        taxid = int(taxid_raw)
    except (TypeError, ValueError):
        return None

    attrs = _attribute_map(hit)
    status = attrs.get("sequencing_status")
    if not status:
        return None

    bioprojects = _bioprojects_list(attrs.get("bioproject"))
    return {
        "taxid": taxid,
        "scientific_name": source.get("scientific_name") or "",
        "taxon_rank": source.get("taxon_rank") or "",
        "sequencing_status": str(status),
        "bioprojects": ",".join(bioprojects),
    }


def _search_page(
    session: requests.Session,
    *,
    search_after: list[Any] | None,
    limit: int,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "query": GOAT_QUERY,
        "result": "taxon",
        "fields": GOAT_FIELDS,
        "limit": limit,
    }
    if search_after is not None:
        params["searchAfter"] = json.dumps(search_after)
    response = session.get(f"{GOAT_API_BASE}/searchPaginated", params=params, timeout=300)
    response.raise_for_status()
    return response.json()


def iter_goat_rows(*, page_size: int = PAGE_SIZE) -> Iterator[dict[str, Any]]:
    session = requests.Session()
    session.headers["User-Agent"] = "euka-tracker/pipeline"
    search_after: list[Any] | None = None
    scanned = 0

    while True:
        payload = _search_page(session, search_after=search_after, limit=page_size)
        hits = payload.get("hits") or []
        pagination = payload.get("pagination") or {}
        if not hits:
            break

        for hit in hits:
            scanned += 1
            row = parse_goat_hit(hit)
            if row:
                yield {
                    "taxid": row["taxid"],
                    "scientific_name": row["scientific_name"],
                    "sequencing_status": row["sequencing_status"],
                    "bioprojects": row["bioprojects"],
                }

        if not pagination.get("hasMore"):
            break
        search_after = pagination.get("searchAfter")
        if not search_after:
            break
        time.sleep(REQUEST_PAUSE_SEC)

    print(f"GoaT: scanned {scanned:,} hits", file=sys.stderr)


def write_goat_status_tsv(out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    print("Fetching GoaT sequencing status (all ranks)...", file=sys.stderr)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TSV_FIELDS, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in iter_goat_rows():
            writer.writerow({k: _escape_tsv(row.get(k)) for k in TSV_FIELDS})
            count += 1
    print(f"Wrote {count:,} GoaT rows to {out_path}", file=sys.stderr)
    return count


def fetch_goat(datasets_dir: Path, *, force: bool = False) -> Path:
    out_path = datasets_dir / "goat_sequencing_status.tsv"
    if out_path.is_file() and not force:
        print(f"Using cached {out_path}", file=sys.stderr)
        return out_path
    write_goat_status_tsv(out_path)
    return out_path


if __name__ == "__main__":
    import argparse

    repo = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Export GoaT sequencing status")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=repo / "datasets" / "goat_sequencing_status.tsv",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.force or not args.output.is_file():
        write_goat_status_tsv(args.output)
    else:
        print(f"Using cached {args.output}", file=sys.stderr)
