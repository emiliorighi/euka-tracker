#!/usr/bin/env python3
"""Weekly IUCN pipeline: fetch datasets → matrix → publish artifacts → site-data."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_DIR = Path(__file__).resolve().parent
DATASETS_DIR = REPO_ROOT / "datasets"
OUTPUT_DIR = PIPELINE_DIR / "output"
SITE_DATA_DIR = REPO_ROOT / "site-data"

FETCH_STEPS = (
    "iucn",
    "gbif",
    "inat",
    "ncbi_taxonomy",
    "assemblies",
    "annotations",
    "reads",
    "goat",
    "cross_universe",
)

PUBLISH_STEPS = (
    "matrix",
    "rollups",
    "scatter",
    "tiles",
    "labels",
    "manifest",
)

DEFAULT_WEEKLY_STEPS = (*FETCH_STEPS, "matrix", "manifest")

ALL_STEPS = (*DEFAULT_WEEKLY_STEPS, "rollups", "scatter", "tiles", "labels")

DOWNLOAD_STEPS = frozenset(
    {"iucn", "gbif", "inat", "ncbi_taxonomy", "assemblies", "annotations", "reads", "goat"}
)

# refresh: always re-fetch (--force)
REFRESH_FETCH_STEPS = frozenset({"iucn", "assemblies", "annotations", "reads", "goat"})

ASSEMBLE_STEPS = frozenset({"rollups", "scatter", "tiles", "labels", "manifest", "matrix"})


def _python() -> str:
    venv_py = REPO_ROOT / ".venv" / "bin" / "python"
    if venv_py.is_file():
        return str(venv_py)
    return sys.executable


def _run(cmd: list[str]) -> None:
    print(f"\n→ {' '.join(cmd)}", file=sys.stderr)
    subprocess.run(cmd, check=True, cwd=REPO_ROOT)


def _format_elapsed(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, rem = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes}m {rem}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m {rem}s"


def _tile_version() -> str:
    return datetime.now(timezone.utc).strftime("v%Y%m%d")


def _count_matrix_rows(matrix_path: Path) -> int:
    if not matrix_path.is_file():
        return 0
    with open(matrix_path, encoding="utf-8") as f:
        return max(0, sum(1 for _ in f) - 1)


def _count_parquet_rows(parquet_path: Path) -> int:
    if not parquet_path.is_file():
        return 0
    try:
        import pyarrow.parquet as pq

        return pq.read_metadata(parquet_path).num_rows
    except Exception:
        return 0


def run_step(
    step: str,
    *,
    skip_download: bool,
    limit: int | None,
    tile_version: str,
    force_scatter: bool,
) -> None:
    py = _python()
    refresh = step in REFRESH_FETCH_STEPS and not skip_download
    force_flag = ["--force"] if refresh else []

    if step == "iucn":
        _run([py, "-m", "pipeline.fetch.iucn", *force_flag])
    elif step == "gbif":
        _run([py, "-m", "pipeline.fetch.gbif", *force_flag])
    elif step == "inat":
        _run([py, "-m", "pipeline.fetch.inat", *force_flag])
    elif step == "ncbi_taxonomy":
        _run([py, "-m", "pipeline.fetch.ncbi_taxonomy", *force_flag])
    elif step == "assemblies":
        _run([py, "-m", "pipeline.fetch.assemblies", *force_flag])
    elif step == "annotations":
        _run([py, "-m", "pipeline.fetch.annotations", *force_flag])
    elif step == "reads":
        _run([py, "-m", "pipeline.fetch.reads", *force_flag])
    elif step == "goat":
        _run([py, "-m", "pipeline.fetch.goat", *force_flag])
    elif step == "cross_universe":
        _run(
            [
                py,
                "-m",
                "pipeline.build.cross_universe",
                "--output",
                str(DATASETS_DIR / "cross_universe.db"),
            ]
        )
    elif step == "matrix":
        cmd = [py, "-m", "pipeline.build.matrix"]
        if limit:
            cmd.extend(["--limit", str(limit)])
        _run(cmd)
    elif step == "rollups":
        _run([py, "-m", "pipeline.build.taxon_rollups"])
    elif step == "scatter":
        cmd = [py, "-m", "pipeline.build.scatter_layout"]
        if force_scatter:
            cmd.append("--force")
        _run(cmd)
    elif step == "tiles":
        _run(
            [
                py,
                "-m",
                "pipeline.build.scatter_tiles",
                "--version",
                tile_version,
            ]
        )
    elif step == "labels":
        _run([py, "-m", "pipeline.build.clade_labels"])
    elif step == "manifest":
        print(
            "\n— manifest step: no subprocess (site manifest written during assemble_site_data)",
            file=sys.stderr,
        )
    else:
        raise ValueError(f"Unknown step: {step}")


def write_site_manifest(*, tile_version: str, site_data_dir: Path) -> Path:
    matrix_path = OUTPUT_DIR / "iucn_species_matrix.tsv"
    parquet_path = OUTPUT_DIR / "iucn_species_scatter.parquet"
    manifest = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "scatter_version": tile_version,
        "tile_version": tile_version,
        "tile_url": f"/tiles/iucn/{tile_version}/",
        "scatter_parquet_url": "/data/iucn_species_scatter.parquet",
        "scatter_arrow_url": "/data/iucn_species_scatter.arrow",
        "rollups_url": "/data/iucn_taxon_rollups.tsv",
        "geojson_url": "/data/iucn_clade_labels.geojson",
        "matrix_rows": _count_matrix_rows(matrix_path),
        "parquet_rows": _count_parquet_rows(parquet_path),
    }
    output_manifest = OUTPUT_DIR / "site-manifest.json"
    output_manifest.parent.mkdir(parents=True, exist_ok=True)
    output_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    site_data_dir.mkdir(parents=True, exist_ok=True)
    site_manifest = site_data_dir / "manifest.json"
    manifest_text = json.dumps(manifest, indent=2) + "\n"
    site_manifest.write_text(manifest_text, encoding="utf-8")
    data_dir = site_data_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "manifest.json").write_text(manifest_text, encoding="utf-8")
    return site_manifest


def assemble_site_data(*, tile_version: str, site_data_dir: Path) -> None:
    site_data_dir.mkdir(parents=True, exist_ok=True)
    data_dir = site_data_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    rollups = OUTPUT_DIR / "iucn_taxon_rollups.tsv"
    if rollups.is_file():
        shutil.copy2(rollups, data_dir / "iucn_taxon_rollups.tsv")

    labels = OUTPUT_DIR / "iucn_clade_labels.geojson"
    if labels.is_file():
        shutil.copy2(labels, data_dir / "iucn_clade_labels.geojson")

    scatter_parquet = OUTPUT_DIR / "iucn_species_scatter.parquet"
    scatter_arrow = OUTPUT_DIR / "iucn_species_scatter.arrow"
    if scatter_parquet.is_file():
        shutil.copy2(scatter_parquet, data_dir / "iucn_species_scatter.parquet")
    if scatter_arrow.is_file():
        shutil.copy2(scatter_arrow, data_dir / "iucn_species_scatter.arrow")
    elif scatter_parquet.is_file():
        import pyarrow.ipc as ipc
        import pyarrow.parquet as pq

        table = pq.read_table(scatter_parquet)
        arrow_dst = data_dir / "iucn_species_scatter.arrow"
        with arrow_dst.open("wb") as handle:
            with ipc.new_file(handle, table.schema) as writer:
                writer.write_table(table)
        print(f"Wrote {arrow_dst} from parquet", file=sys.stderr)

    tiles_src = OUTPUT_DIR / "tiles" / "iucn" / tile_version
    tiles_dst = site_data_dir / "tiles" / "iucn" / tile_version
    if tiles_src.is_dir():
        if tiles_dst.exists():
            shutil.rmtree(tiles_dst)
        shutil.copytree(tiles_src, tiles_dst)

    write_site_manifest(tile_version=tile_version, site_data_dir=site_data_dir)
    print(f"\nSite-data artifact ready at {site_data_dir}", file=sys.stderr)


def run_pipeline(
    *,
    steps: list[str],
    skip_download: bool,
    limit: int | None,
    site_data_dir: Path,
    keep_going: bool,
    force_scatter: bool,
) -> None:
    tile_version = _tile_version()
    pipeline_t0 = time.perf_counter()
    failed_steps: list[str] = []

    for step in steps:
        if skip_download and step in DOWNLOAD_STEPS:
            print(f"\n— skipping download step: {step}", file=sys.stderr)
            continue

        step_t0 = time.perf_counter()
        try:
            run_step(
                step,
                skip_download=skip_download,
                limit=limit,
                tile_version=tile_version,
                force_scatter=force_scatter,
            )
            elapsed = time.perf_counter() - step_t0
            print(f"✓ {step} finished in {_format_elapsed(elapsed)}", file=sys.stderr)
        except subprocess.CalledProcessError as exc:
            elapsed = time.perf_counter() - step_t0
            print(
                f"✗ {step} failed after {_format_elapsed(elapsed)} (exit {exc.returncode})",
                file=sys.stderr,
            )
            if keep_going:
                failed_steps.append(step)
                continue
            raise

    if ASSEMBLE_STEPS.intersection(steps):
        assemble_t0 = time.perf_counter()
        assemble_site_data(tile_version=tile_version, site_data_dir=site_data_dir)
        assemble_elapsed = time.perf_counter() - assemble_t0
        print(f"✓ assemble_site_data finished in {_format_elapsed(assemble_elapsed)}", file=sys.stderr)

    total_elapsed = time.perf_counter() - pipeline_t0
    print(f"\nPipeline finished in {_format_elapsed(total_elapsed)}", file=sys.stderr)
    if failed_steps:
        raise SystemExit(f"Steps failed (kept going): {', '.join(failed_steps)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run weekly IUCN pipeline")
    parser.add_argument(
        "--steps",
        default=",".join(DEFAULT_WEEKLY_STEPS),
        help=f"Comma-separated steps (default: weekly CI). Choices: {', '.join(ALL_STEPS)}",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip fetch/download steps (reuse cached datasets/ and cache/)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit matrix build to N species (smoke tests)",
    )
    parser.add_argument(
        "--site-data-dir",
        type=Path,
        default=SITE_DATA_DIR,
        help="Directory for GitHub Actions artifact output",
    )
    parser.add_argument(
        "--keep-going",
        action="store_true",
        help="Continue running remaining steps after a step fails",
    )
    parser.add_argument(
        "--force-scatter",
        action="store_true",
        help="Rebuild scatter parquet even when output is newer than matrix",
    )
    args = parser.parse_args()

    steps = [s.strip() for s in args.steps.split(",") if s.strip()]
    unknown = [s for s in steps if s not in ALL_STEPS]
    if unknown:
        raise SystemExit(f"Unknown steps: {unknown}")

    run_pipeline(
        steps=steps,
        skip_download=args.skip_download,
        limit=args.limit,
        site_data_dir=args.site_data_dir,
        keep_going=args.keep_going,
        force_scatter=args.force_scatter,
    )


if __name__ == "__main__":
    main()
