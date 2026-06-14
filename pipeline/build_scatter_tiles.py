#!/usr/bin/env python3
"""
Export species matrix to scatter Parquet and tile with quadfeather.

Steps: export → [layout coords] → labels sidecars → tile
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from pipeline.patch_tile_metadata import patch_tile_metadata  # noqa: E402
from pipeline.scatter_build_labels import write_scatter_sidecars  # noqa: E402
from pipeline.scatter_clade_study_layout import (  # noqa: E402
    compute_clade_study_layout,
    load_phylum_rollups_from_db,
    load_taxid_ranks,
    resolve_phylum_from_lineage,
    resolve_phylum_names,
)
from pipeline.scatter_conservation_layout import apply_conservation_coords  # noqa: E402
from pipeline.scatter_export import (  # noqa: E402
    ANCESTOR_FIELDS,
    ANCESTOR_MAX_DEPTH,
    SCATTER_FIELDS,
    ScatterExportContext,
    _lineage_taxids,
    matrix_row_to_scatter,
)
from pipeline.scatter_gap_layout import apply_gap_coords  # noqa: E402
from pipeline.scatter_landscape import apply_landscape_coords  # noqa: E402
from pipeline.scatter_layouts import (  # noqa: E402
    DEFAULT_SCATTER_DIR,
    DEFAULT_UMAP_VIEW_EXTENT,
    LEGACY_PARQUET,
    all_layout_ids,
    needs_umap_labels,
    parquet_path,
    tile_dir,
)
from pipeline.scatter_phylo_pack import (  # noqa: E402
    assign_lineage_fallback_pack,
    compute_phylo_pack_layout,
)
from pipeline.scatter_threat_layout import apply_threat_coords  # noqa: E402

_INT_FIELDS = {
    "taxid",
    "iucn_code",
    "phylum_taxid",
    "run_count",
    "assembly_count",
    "annotation_count",
    "data_tier",
    *ANCESTOR_FIELDS,
}
_STRING_FIELDS = {
    "scientific_name",
    "redlist_category",
    "phylum_name",
}
_BATCH_SIZE = 10_000

COORD_APPLIERS = {
    "landscape": "landscape",
    "conservation": "conservation",
    "threat": "threat",
    "gap": "gap",
}


def _scatter_schema() -> pa.Schema:
    fields: list[pa.Field] = []
    for name in SCATTER_FIELDS:
        if name in _INT_FIELDS:
            fields.append(pa.field(name, pa.int64()))
        elif name in _STRING_FIELDS:
            fields.append(pa.field(name, pa.string()))
        else:
            fields.append(pa.field(name, pa.float64()))
    return pa.schema(fields)


def _default_matrix_path() -> Path:
    return _REPO / "data" / "staged" / "05_eukaryotic_species_matrix.tsv"


def _default_rollups_path() -> Path:
    return _REPO / "data" / "staged" / "06_taxon_rollups.tsv"


def _default_iucn_path() -> Path:
    return _REPO / "data" / "iucn_assessments.tsv"


def _default_threat_cache_dir() -> Path:
    return _REPO / "data" / "cache" / "iucn_text_embeddings"


def _default_parquet_path() -> Path:
    return parquet_path("landscape")


def _default_tile_dir(embedding: str = "landscape", version: str | None = None) -> Path:
    if embedding == "study-map":
        stamp = version or f"v{date.today():%Y%m%d}"
        return _REPO / "tiles" / "species" / "study-map" / stamp
    return tile_dir("landscape", version)


def _build_phylum_context(
    matrix_rows: list[dict[str, str]],
    *,
    db_path: Path,
    rollups_path: Path,
) -> ScatterExportContext:
    """Resolve phylum metadata only (no pack / study layout)."""
    lineage_by_taxid: dict[int, list[int]] = {}
    all_taxids: set[int] = set()

    for row in matrix_rows:
        try:
            taxid = int(row["taxid"])
        except (KeyError, ValueError):
            continue
        lineage = _lineage_taxids(row.get("tax_lineage") or "", taxid)
        lineage_by_taxid[taxid] = lineage
        all_taxids.update(lineage)

    ranks = load_taxid_ranks(db_path, all_taxids)
    rollups = load_phylum_rollups_from_db(db_path)

    phylum_by_species: dict[int, tuple[int, str]] = {}
    phylum_taxids: set[int] = set()
    for taxid, lineage in lineage_by_taxid.items():
        phylum_taxid, _ = resolve_phylum_from_lineage(lineage, ranks)
        phylum_taxids.add(phylum_taxid)
        phylum_by_species[taxid] = (phylum_taxid, "")

    phylum_names = resolve_phylum_names(phylum_taxids, rollups, db_path)
    for taxid, (phylum_taxid, _) in phylum_by_species.items():
        phylum_by_species[taxid] = (
            phylum_taxid,
            phylum_names.get(phylum_taxid, ""),
        )

    return ScatterExportContext(
        pack_layout={},
        study_coords={},
        phylum_by_species=phylum_by_species,
        view_extent=DEFAULT_UMAP_VIEW_EXTENT,
    )


def _build_export_context(
    matrix_rows: list[dict[str, str]],
    *,
    db_path: Path,
    rollups_path: Path,
) -> ScatterExportContext:
    matrix_taxids: set[int] = set()
    lineage_by_taxid: dict[int, list[int]] = {}

    for row in matrix_rows:
        try:
            taxid = int(row["taxid"])
        except (KeyError, ValueError):
            continue
        matrix_taxids.add(taxid)
        lineage_by_taxid[taxid] = _lineage_taxids(row.get("tax_lineage") or "", taxid)

    pack_layout, _leaf_index = compute_phylo_pack_layout(matrix_taxids, db_path)
    missing = matrix_taxids - set(pack_layout)
    if missing:
        fallback_layout, _fallback_index = assign_lineage_fallback_pack(
            missing,
            lineage_by_taxid,
            start_index=0,
        )
        pack_layout.update(fallback_layout)

    study = compute_clade_study_layout(
        pack_layout,
        lineage_by_taxid,
        rollups_path=rollups_path,
        db_path=db_path,
    )

    return ScatterExportContext(
        pack_layout=pack_layout,
        study_coords=study.coords,
        phylum_by_species=study.phylum_by_species,
        view_extent=study.view_extent,
    )


def _flush_batch(batch: list[dict], schema: pa.Schema, writer: pq.ParquetWriter) -> None:
    table = pa.Table.from_pydict(
        {k: [row.get(k) for row in batch] for k in SCATTER_FIELDS},
        schema=schema,
    )
    writer.write_table(table)


def export_scatter_parquet(
    matrix_path: Path,
    parquet_path: Path,
    *,
    db_path: Path,
    rollups_path: Path,
    embedding: str = "landscape",
) -> dict[str, int | dict[str, list[float]]]:
    """Stream matrix TSV → slim scatter Parquet."""
    parquet_path.parent.mkdir(parents=True, exist_ok=True)

    with matrix_path.open(newline="", encoding="utf-8") as f:
        matrix_rows = list(csv.DictReader(f, delimiter="\t"))

    if embedding == "landscape":
        context = _build_phylum_context(
            matrix_rows,
            db_path=db_path,
            rollups_path=rollups_path,
        )
    else:
        context = _build_export_context(
            matrix_rows,
            db_path=db_path,
            rollups_path=rollups_path,
        )

    schema = _scatter_schema()
    writer: pq.ParquetWriter | None = None
    batch: list[dict] = []
    row_count = 0
    iucn_assessed = 0
    lineage_depth_overruns = 0

    for row in matrix_rows:
        species_taxid = int(row.get("taxid") or 0)
        lineage = _lineage_taxids(row.get("tax_lineage") or "", species_taxid)
        if len(lineage) - 1 > ANCESTOR_MAX_DEPTH:
            lineage_depth_overruns += 1

        scatter = matrix_row_to_scatter(row, context=context)
        batch.append(scatter)
        row_count += 1
        if scatter.get("iucn_code", 0) > 0:
            iucn_assessed += 1
        if len(batch) >= _BATCH_SIZE:
            if writer is None:
                writer = pq.ParquetWriter(parquet_path, schema, compression="zstd")
            _flush_batch(batch, schema, writer)
            batch.clear()

    if batch:
        if writer is None:
            writer = pq.ParquetWriter(parquet_path, schema, compression="zstd")
        _flush_batch(batch, schema, writer)

    if writer is not None:
        writer.close()
    else:
        empty = pa.Table.from_pydict({k: [] for k in SCATTER_FIELDS}, schema=schema)
        pq.write_table(empty, parquet_path, compression="zstd")

    if lineage_depth_overruns:
        print(
            f"Warning: {lineage_depth_overruns:,} rows exceed ANCESTOR_MAX_DEPTH "
            f"({ANCESTOR_MAX_DEPTH}); deepest taxids truncated to 0 in high columns",
            file=sys.stderr,
        )

    return {
        "row_count": row_count,
        "iucn_assessed": iucn_assessed,
        "view_extent": context.view_extent,
    }


def _quadfeather_bin() -> str | None:
    found = shutil.which("quadfeather")
    if found:
        return found
    venv_root = os.environ.get("VIRTUAL_ENV")
    if venv_root:
        candidate = Path(venv_root) / "bin" / "quadfeather"
        if candidate.is_file():
            return str(candidate)
    repo_venv = Path(__file__).resolve().parent.parent / ".venv" / "bin" / "quadfeather"
    if repo_venv.is_file():
        return str(repo_venv)
    return None


def run_quadfeather(parquet_path: Path, tile_dir_path: Path, tile_size: int) -> None:
    quadfeather = _quadfeather_bin()
    if not quadfeather:
        print(
            "Error: quadfeather CLI not found. Install with:\n"
            "  uv pip install git+https://github.com/bmschmidt/quadfeather",
            file=sys.stderr,
        )
        sys.exit(1)

    tile_dir_path.mkdir(parents=True, exist_ok=True)
    cmd = [
        quadfeather,
        "--files",
        str(parquet_path),
        "--tile_size",
        str(tile_size),
        "--destination",
        str(tile_dir_path),
    ]
    print(f"Running: {' '.join(cmd)}", file=sys.stderr)
    subprocess.run(cmd, check=True)


def run_coords(
    layout: str,
    parquet_path: Path,
    *,
    matrix_path: Path,
    iucn_path: Path,
    threat_cache_dir: Path,
) -> dict[str, float | dict[str, list[float]]]:
    if not parquet_path.is_file():
        print(f"Error: Parquet not found at {parquet_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Applying {layout} coordinates → {parquet_path}…", file=sys.stderr)

    if layout == "landscape":
        stats = apply_landscape_coords(
            parquet_path,
            matrix_path=matrix_path,
            iucn_tsv=iucn_path,
        )
        stats["view_extent"] = DEFAULT_UMAP_VIEW_EXTENT
        print(
            f"Landscape: {int(stats['row_count']):,} species, "
            f"corr(x,y)={stats.get('corr_xy', 0):.3f}, "
            f"corr(x,knowledge)={stats.get('corr_x_knowledge', 0):.3f}",
            file=sys.stderr,
        )
        return stats

    if layout == "conservation":
        stats = apply_conservation_coords(
            parquet_path,
            matrix_path=matrix_path,
            threat_cache_dir=threat_cache_dir,
        )
        print(
            f"Conservation: {int(stats['row_count']):,} species, "
            f"corr(x,y)={stats.get('corr_xy', 0):.3f}, "
            f"corr(x,iucn)={stats.get('corr_x_iucn', 0):.3f}",
            file=sys.stderr,
        )
        return stats

    if layout == "threat":
        stats = apply_threat_coords(
            parquet_path,
            matrix_path=matrix_path,
            threat_cache_dir=threat_cache_dir,
        )
        print(
            f"Threat: {int(stats['row_count']):,} species, "
            f"corr(x,y)={stats.get('corr_xy', 0):.3f}",
            file=sys.stderr,
        )
        return stats

    if layout == "gap":
        stats = apply_gap_coords(parquet_path)
        extent = stats.get("view_extent", DEFAULT_UMAP_VIEW_EXTENT)
        print(
            f"Gap: {int(stats['row_count']):,} species, "
            f"x [{stats.get('x_min', 0):.2f}, {stats.get('x_max', 0):.2f}], "
            f"y [{stats.get('y_min', 0):.2f}, {stats.get('y_max', 0):.2f}]",
            file=sys.stderr,
        )
        return stats

    print(f"Error: unknown layout {layout!r}", file=sys.stderr)
    sys.exit(1)


def run_landscape(
    parquet_path: Path,
    *,
    matrix_path: Path,
    iucn_path: Path,
) -> dict[str, float]:
    """Backward-compatible alias for landscape coords."""
    stats = run_coords(
        "landscape",
        parquet_path,
        matrix_path=matrix_path,
        iucn_path=iucn_path,
        threat_cache_dir=_default_threat_cache_dir(),
    )
    return {k: float(v) for k, v in stats.items() if isinstance(v, (int, float))}


def run_export(
    matrix_path: Path,
    parquet_path: Path,
    *,
    db_path: Path,
    rollups_path: Path,
    embedding: str = "landscape",
) -> dict[str, int | dict[str, list[float]]]:
    if not matrix_path.is_file():
        print(f"Error: matrix not found at {matrix_path}", file=sys.stderr)
        sys.exit(1)
    if not db_path.is_file():
        print(f"Error: taxonomy db not found at {db_path}", file=sys.stderr)
        sys.exit(1)
    if not rollups_path.is_file():
        print(f"Error: rollups not found at {rollups_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Exporting {matrix_path} → {parquet_path}…", file=sys.stderr)
    stats = export_scatter_parquet(
        matrix_path,
        parquet_path,
        db_path=db_path,
        rollups_path=rollups_path,
        embedding=embedding,
    )
    print(
        f"Wrote {int(stats['row_count']):,} rows ({len(SCATTER_FIELDS)} columns), "
        f"{int(stats['iucn_assessed']):,} with IUCN category",
        file=sys.stderr,
    )
    return stats


def run_labels(
    parquet_path: Path,
    tile_dir_path: Path,
    view_extent: dict[str, list[float]],
    *,
    rollups_path: Path | None = None,
    layout: str | None = None,
) -> None:
    if not parquet_path.is_file():
        print(f"Error: Parquet not found at {parquet_path}", file=sys.stderr)
        sys.exit(1)
    labels_path, extent_path = write_scatter_sidecars(
        parquet_path,
        tile_dir_path,
        view_extent,
        rollups_path=rollups_path or _default_rollups_path(),
        layout=layout,
    )
    print(f"Wrote {labels_path.name}, {extent_path.name} → {tile_dir_path}", file=sys.stderr)


def run_tile(parquet_path: Path, tile_dir_path: Path, tile_size: int) -> None:
    if not parquet_path.is_file():
        print(f"Error: Parquet not found at {parquet_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Tiling {parquet_path} → {tile_dir_path}…", file=sys.stderr)
    run_quadfeather(parquet_path, tile_dir_path, tile_size)
    patched = patch_tile_metadata(tile_dir_path)
    print(
        f"Tiles written to {tile_dir_path} ({patched} tiles patched for deepscatter metadata)",
        file=sys.stderr,
    )


def _resolve_layouts(layout_arg: str) -> list[str]:
    if layout_arg == "all":
        return all_layout_ids()
    if layout_arg not in SCATTER_LAYOUTS:
        print(
            f"Error: unknown layout {layout_arg!r}; expected one of "
            f"{[*all_layout_ids(), 'all']}",
            file=sys.stderr,
        )
        sys.exit(1)
    return [layout_arg]


def _copy_layout_parquet(source: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)


def _run_multi_layout_pipeline(args: argparse.Namespace) -> None:
    layouts = _resolve_layouts(args.layout)
    version = args.version or f"v{date.today():%Y%m%d}"
    scatter_dir = args.scatter_dir
    export_parquet = parquet_path("landscape", scatter_dir)
    legacy_parquet = scatter_dir / LEGACY_PARQUET

    view_extent_by_layout: dict[str, dict[str, list[float]]] = {
        lid: DEFAULT_UMAP_VIEW_EXTENT for lid in layouts
    }

    if args.step in ("export", "all"):
        stats = run_export(
            args.matrix,
            export_parquet,
            db_path=args.db,
            rollups_path=args.rollups,
            embedding="landscape",
        )
        view_extent_by_layout["landscape"] = stats.get(  # type: ignore[assignment]
            "view_extent",
            DEFAULT_UMAP_VIEW_EXTENT,
        )

    coord_steps = ("coords", "landscape", "all")
    if args.step in coord_steps:
        for layout in layouts:
            pq = parquet_path(layout, scatter_dir)
            if layout != "landscape":
                if not export_parquet.is_file():
                    print(
                        f"Error: export parquet missing at {export_parquet}; "
                        "run --step export first",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                _copy_layout_parquet(export_parquet, pq)
            stats = run_coords(
                layout,
                pq,
                matrix_path=args.matrix,
                iucn_path=args.iucn,
                threat_cache_dir=args.threat_cache,
            )
            extent = stats.get("view_extent")
            if isinstance(extent, dict):
                view_extent_by_layout[layout] = extent

    tile_steps = ("tile", "all")
    label_steps = ("labels", "all")

    for layout in layouts:
        pq = parquet_path(layout, scatter_dir)
        td = tile_dir(layout, version)

        if args.step in tile_steps:
            if not pq.is_file():
                print(f"Error: Parquet not found at {pq}", file=sys.stderr)
                sys.exit(1)
            run_tile(pq, td, args.tile_size)

        if args.step in label_steps:
            if args.step == "labels":
                extent_file = td / "view_extent.json"
                if extent_file.is_file():
                    view_extent_by_layout[layout] = json.loads(
                        extent_file.read_text(encoding="utf-8")
                    )
            if not pq.is_file():
                print(f"Error: Parquet not found at {pq}", file=sys.stderr)
                sys.exit(1)
            run_labels(
                pq,
                td,
                view_extent_by_layout[layout],
                rollups_path=args.rollups,
                layout=layout,
            )

    if args.step in ("export", "all") and export_parquet.is_file():
        _copy_layout_parquet(export_parquet, legacy_parquet)


def _run_study_map_pipeline(args: argparse.Namespace) -> None:
    tile_dir_path = args.tile_dir or _default_tile_dir("study-map", args.version)
    view_extent: dict[str, list[float]] = DEFAULT_UMAP_VIEW_EXTENT

    if args.step in ("export", "all"):
        stats = run_export(
            args.matrix,
            args.parquet,
            db_path=args.db,
            rollups_path=args.rollups,
            embedding="study-map",
        )
        view_extent = stats.get("view_extent", view_extent)  # type: ignore[assignment]

    if args.step in ("labels", "all"):
        if args.step == "labels":
            extent_file = tile_dir_path / "view_extent.json"
            if extent_file.is_file():
                view_extent = json.loads(extent_file.read_text(encoding="utf-8"))
        run_labels(
            args.parquet,
            tile_dir_path,
            view_extent,
            rollups_path=args.rollups,
        )

    if args.step == "patch":
        patched = patch_tile_metadata(tile_dir_path)
        print(f"Patched {patched} tiles in {tile_dir_path}", file=sys.stderr)

    if args.step in ("tile", "all"):
        run_tile(args.parquet, tile_dir_path, args.tile_size)
        if args.step == "all":
            run_labels(
                args.parquet,
                tile_dir_path,
                view_extent,
                rollups_path=args.rollups,
            )


# Import for layout validation in _resolve_layouts
from pipeline.scatter_layouts import SCATTER_LAYOUTS  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export species scatter Parquet and build quadfeather tiles"
    )
    parser.add_argument(
        "--step",
        choices=("export", "coords", "landscape", "labels", "tile", "patch", "all"),
        default="all",
        help="Pipeline step (default: all); landscape is alias for coords on landscape layout",
    )
    parser.add_argument(
        "--layout",
        choices=(*all_layout_ids(), "all"),
        default="all",
        help="Scatter layout to build (default: all)",
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Tile folder version stamp (default: vYYYYMMDD)",
    )
    parser.add_argument(
        "--embedding",
        choices=("landscape", "study-map"),
        default="landscape",
        help="Coordinate embedding; study-map keeps legacy single-parquet path",
    )
    parser.add_argument(
        "--matrix",
        type=Path,
        default=_default_matrix_path(),
        help="Input species matrix TSV",
    )
    parser.add_argument(
        "--parquet",
        type=Path,
        default=_default_parquet_path(),
        help="Output scatter Parquet path (study-map legacy)",
    )
    parser.add_argument(
        "--scatter-dir",
        type=Path,
        default=DEFAULT_SCATTER_DIR,
        help="Directory for per-layout parquet files",
    )
    parser.add_argument(
        "--tile-dir",
        type=Path,
        default=None,
        help="quadfeather destination (study-map legacy override)",
    )
    parser.add_argument(
        "--iucn",
        type=Path,
        default=_default_iucn_path(),
        help="IUCN assessments TSV for landscape text features",
    )
    parser.add_argument(
        "--threat-cache",
        type=Path,
        default=_default_threat_cache_dir(),
        help="IUCN text embedding cache root (taxids.npy + threats/)",
    )
    parser.add_argument(
        "--tile-size",
        type=int,
        default=50_000,
        help="quadfeather tile_size (default: 50000)",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=_REPO / "data" / "staged" / "taxonomy.sqlite",
        help="Taxonomy SQLite for phylo pack + phylum resolution",
    )
    parser.add_argument(
        "--rollups",
        type=Path,
        default=_default_rollups_path(),
        help="Taxon rollups TSV for phylum study scores",
    )
    args = parser.parse_args()

    if args.embedding == "study-map":
        _run_study_map_pipeline(args)
        return

    _run_multi_layout_pipeline(args)


if __name__ == "__main__":
    main()
