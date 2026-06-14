#!/usr/bin/env python3
"""ENA study search — GET with URL params (eukaryotes, tax_tree 2759)."""

import urllib.parse

import requests

ENA_SEARCH_API = "https://www.ebi.ac.uk/ena/portal/api/search"
ENA_BROWSER_URL = "https://www.ebi.ac.uk/ena/browser/advanced-search"

EUKARYOTA_TAXID = 2759

EUKARYOTE_STUDY_QUERY = f"tax_tree({EUKARYOTA_TAXID})"

EUKARYOTE_STUDY_FIELDS = [
    "study_accession",
    "study_title",
    "tax_id",
    "tax_lineage",
    "parent_study_accession",
]


def eukaryote_study_search():
    """Return (query, fields) for the ENA study export."""
    return EUKARYOTE_STUDY_QUERY, EUKARYOTE_STUDY_FIELDS


def eukaryote_study_params(fmt: str = "tsv", limit: int | None = 0) -> dict[str, str]:
    """URL query parameters for ENA search. limit=0 fetches all records."""
    query, fields = eukaryote_study_search()
    params: dict[str, str] = {
        "result": "study",
        "query": query,
        "fields": ",".join(fields),
        "format": fmt,
    }
    if limit is not None:
        params["limit"] = str(limit)
    return params


def eukaryote_study_url(*, api: bool = False) -> str:
    """Full GET URL with encoded params (browser or portal API)."""
    base = ENA_SEARCH_API if api else ENA_BROWSER_URL
    return f"{base}?{urllib.parse.urlencode(eukaryote_study_params())}"


def fetch_eukaryote_studies(limit: int | None = 0):
    """GET ENA Portal API; returns streaming response (TSV by default)."""
    response = requests.get(
        ENA_SEARCH_API,
        params=eukaryote_study_params(limit=limit),
        stream=True,
        timeout=300,
    )
    response.raise_for_status()
    return response


if __name__ == "__main__":
    print(eukaryote_study_url(api=True))
    response = fetch_eukaryote_studies()
    for i, line in enumerate(response.iter_lines(decode_unicode=True)):
        print(line)
        if i >= 5:
            print("...")
            break
