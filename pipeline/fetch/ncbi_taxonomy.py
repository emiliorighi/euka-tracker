#!/usr/bin/env python3
"""Fetch eukaryotic NCBI taxonomy.db and species backbone (names, synonyms, lineage)."""

from __future__ import annotations

import sys
from pathlib import Path

from pipeline.schema import DATASET_FILES
from pipeline.taxonomy_db import build_taxonomy_db, open_taxonomy_db


def fetch_taxonomy_and_backbone(
    datasets_dir: Path,
    *,
    force: bool = False,
) -> tuple[Path, Path]:
    db_path = datasets_dir / DATASET_FILES["taxonomy_db"]
    backbone_path = datasets_dir / DATASET_FILES["species_backbone"]

    build_taxonomy_db(db_path, force=force)

    if force or not backbone_path.is_file():
        print(f"Streaming species backbone → {backbone_path}", file=sys.stderr)
        with open_taxonomy_db(db_path, build=False) as taxdb:
            n = taxdb.write_species_backbone_tsv(backbone_path)
        print(f"Wrote {n:,} species backbone rows", file=sys.stderr)
    else:
        print(f"Using cached backbone {backbone_path}", file=sys.stderr)

    return db_path, backbone_path


if __name__ == "__main__":
    import argparse

    repo = Path(__file__).resolve().parents[2]
    default_datasets = repo / "datasets"

    parser = argparse.ArgumentParser(description="Fetch NCBI taxonomy.db + species backbone")
    parser.add_argument("--datasets-dir", type=Path, default=default_datasets)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    fetch_taxonomy_and_backbone(args.datasets_dir, force=args.force)
