#!/usr/bin/env python3
"""Download Open Tree of Life taxonomy (stub — wired later).

OTL files are loaded from cache/otl/ by build_cross_universe.py.
When implemented, download ott synthesis taxonomy + forwards + synonyms TSVs.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Open Tree synthesis download portal (manual / future automation)
OTL_DOWNLOAD_INFO = "https://tree.opentreeoflife.org/about/ott"


def fetch_otl_taxonomy(output_dir: Path, *, force: bool = False) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    marker = output_dir / ".otl_fetch_stub"
    if marker.is_file() and not force:
        print(f"OTL fetch stub already present at {output_dir}", file=sys.stderr)
        return
    marker.write_text(
        f"OTL auto-fetch not implemented. See {OTL_DOWNLOAD_INFO}\n"
        "Place ott synthesis under cache/otl/ott*/ott*/taxonomy.tsv\n",
        encoding="utf-8",
    )
    print(
        f"OTL fetch stub written to {marker}. Matrix works without OTL; "
        f"manual download: {OTL_DOWNLOAD_INFO}",
        file=sys.stderr,
    )


def main() -> None:
    repo = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Fetch OTL taxonomy (stub)")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=repo / "cache" / "otl",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    fetch_otl_taxonomy(args.output_dir, force=args.force)


if __name__ == "__main__":
    main()
