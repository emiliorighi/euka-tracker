#!/usr/bin/env python3
"""Download IUCN Red List saved export and extract simple_summary.csv."""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import requests

from pipeline.schema import DATASET_FILES, SIMPLE_SUMMARY_FIELDS

ENV_URL = "IUCN_REDLIST_DOWNLOAD_URL"
SIMPLE_SUMMARY_NAMES = frozenset({"simple_summary.csv", "simple summary.csv"})


def resolve_download_url(cli_url: str | None) -> str:
    if cli_url:
        return cli_url.strip()
    env_url = os.environ.get(ENV_URL, "").strip()
    if env_url:
        return env_url
    raise SystemExit(
        f"Missing download URL. Set {ENV_URL} or pass --url "
        "(e.g. https://www.iucnredlist.org/saved_downloads/<uuid>)"
    )


def _find_simple_summary(root: Path) -> Path:
    direct = root / "simple_summary.csv"
    if direct.is_file():
        return direct
    for path in root.rglob("*"):
        if path.is_file() and path.name.lower() in SIMPLE_SUMMARY_NAMES:
            return path
    raise FileNotFoundError(f"No simple_summary.csv found under {root}")


def _validate_csv(path: Path) -> None:
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("simple_summary.csv has no header row")
        missing = [col for col in SIMPLE_SUMMARY_FIELDS if col not in reader.fieldnames]
        if missing:
            raise ValueError(f"simple_summary.csv missing columns: {missing}")


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} → {dest}", file=sys.stderr)
    with requests.get(url, stream=True, timeout=600) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as out:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    out.write(chunk)


def fetch_simple_summary(
    output: Path,
    *,
    url: str | None = None,
    force: bool = False,
) -> Path:
    if output.is_file() and not force:
        print(f"Using cached {output}", file=sys.stderr)
        return output

    download_url = resolve_download_url(url)
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="iucn_redlist_") as tmp:
        tmp_path = Path(tmp)
        archive_path = tmp_path / "redlist_export.zip"
        _download(download_url, archive_path)

        extract_root = tmp_path / "extract"
        extract_root.mkdir()
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(extract_root)

        source_csv = _find_simple_summary(extract_root)
        _validate_csv(source_csv)
        shutil.copy2(source_csv, output)

    print(f"Wrote {output}", file=sys.stderr)
    return output


def main() -> None:
    repo = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Fetch IUCN simple_summary.csv from saved export")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=repo / "datasets" / DATASET_FILES["simple_summary"],
    )
    parser.add_argument(
        "--url",
        default=None,
        help=f"Saved download URL (default: ${ENV_URL} env var)",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    fetch_simple_summary(args.output, url=args.url, force=args.force)


if __name__ == "__main__":
    main()
