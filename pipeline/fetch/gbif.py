#!/usr/bin/env python3
"""Download GBIF backbone taxonomy zip for cross_universe.db."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import requests

from pipeline.schema import CACHE_FILES

DEFAULT_GBIF_BACKBONE_URL = (
    "https://hosted-datasets.gbif.org/datasets/backbone/current/backbone.zip"
)
ENV_URL = "GBIF_BACKBONE_URL"


def resolve_url(cli_url: str | None) -> str:
    if cli_url:
        return cli_url.strip()
    return os.environ.get(ENV_URL, DEFAULT_GBIF_BACKBONE_URL).strip()


def fetch_gbif_backbone(output: Path, *, url: str | None = None, force: bool = False) -> Path:
    if output.is_file() and not force:
        print(f"Using cached {output}", file=sys.stderr)
        return output

    download_url = resolve_url(url)
    output.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {download_url} → {output}", file=sys.stderr)

    with requests.get(download_url, stream=True, timeout=3600) as resp:
        resp.raise_for_status()
        with open(output, "wb") as out:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    out.write(chunk)

    print(f"Wrote {output} ({output.stat().st_size / (1024**3):.2f} GB)", file=sys.stderr)
    return output


def main() -> None:
    repo = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Download GBIF backbone.zip")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=repo / CACHE_FILES["gbif_backbone"],
    )
    parser.add_argument("--url", default=None, help=f"Override URL (default: ${ENV_URL} or GBIF hosted)")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    fetch_gbif_backbone(args.output, url=args.url, force=args.force)


if __name__ == "__main__":
    main()
