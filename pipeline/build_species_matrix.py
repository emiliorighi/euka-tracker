#!/usr/bin/env python3
"""
Staged, streaming eukaryote species matrix pipeline.

Steps: fetch → select → merge → finalize → rollups → scatter (parquet + UMAP + tiles)
"""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any, Iterator

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from pipeline.annotrieve_annotation_fetch import (  # noqa: E402
    iter_annotrieve_annotations_tsv,
    write_annotrieve_annotations_tsv,
)
from pipeline.ena_read_run_search import (  # noqa: E402
    iter_eukaryote_read_runs_tsv,
    parse_ena_taxid,
    write_eukaryote_read_runs_tsv,
)
from pipeline.ncbi_assembly_fetch import (  # noqa: E402
    iter_eukaryote_assemblies_tsv,
    write_eukaryote_assemblies_tsv,
)
from pipeline.ncbi_taxonomy_fetch import _fill_names  # noqa: E402
from pipeline.iucn_assessments_convert import (  # noqa: E402
    IUCN_STRUCTURED_FIELDS,
    load_iucn_by_taxid,
)
from pipeline.species_matrix_select import (  # noqa: E402
    annotrieve_source_url,
    classify_read_bucket,
    compute_coverage,
    ena_run_url,
    ncbi_assembly_url,
    select_better_run,
    select_reference_annotation,
    select_reference_assembly,
)

def _taxonomy_path(staged_dir: Path) -> Path:
    """Pre-built NCBI taxonomy for name lookup (fetch disabled; handled downstream)."""
    built = _REPO / "data" / "ncbi_taxonomy_tree.tsv.gz"
    if built.is_file():
        return built
    return staged_dir / "01_ncbi_taxonomy_tree.tsv.gz"


STAGED_FILES = {
    "assemblies": "02_ncbi_assemblies.tsv",
    "ref_assembly": "02_species_ref_assembly.tsv",
    "annotations": "03_annotrieve_annotations.tsv",
    "ref_annotation": "03_species_ref_annotation.tsv",
    "read_runs": "04_ena_read_runs.tsv",
    "rep_runs": "04_species_rep_runs.tsv",
    "matrix": "05_eukaryotic_species_matrix.tsv",
    "rollups": "06_taxon_rollups.tsv",
}

REF_ASSEMBLY_COLS = [
    "ref_assembly_accession",
    "ref_assembly_name",
    "ref_assembly_level",
    "ref_assembly_source",
    "ref_assembly_release_date",
    "ref_assembly_bioproject_accession",
    "ref_assembly_gc_percent",
    "ref_assembly_total_sequence_length",
    "ref_assembly_total_ungapped_length",
    "ref_assembly_contig_n50",
    "ref_assembly_scaffold_n50",
    "ref_assembly_total_number_of_chromosomes",
    "ref_assembly_url",
]

REF_ANNOTATION_COLS = [
    "ref_annotation_id",
    "ref_annotation_assembly_accession",
    "ref_annotation_db_source",
    "ref_annotation_release_date",
    "ref_annotation_busco_complete",
    "ref_annotation_busco_single_copy",
    "ref_annotation_busco_lineage",
    "ref_annotation_lncrna_gene_count",
    "ref_annotation_mrna_gene_count",
    "ref_annotation_mrna_avg_length_full",
    "ref_annotation_mrna_avg_length_exon_concat",
    "ref_annotation_mrna_avg_length_cds_concat",
    "ref_annotation_mrna_transcript_count",
    "ref_annotation_lncrna_avg_length_full",
    "ref_annotation_lncrna_avg_length_exon_concat",
    "ref_annotation_lncrna_transcript_count",
    "ref_annotation_total_genes_count",
    "ref_annotation_total_transcripts_count",
    "ref_annotation_url",
]

READ_BUCKETS = ("wgs_long", "wgs_short", "rnaseq_long", "rnaseq_short")

BUCKET_COUNT_COLS = [f"{b}_count" for b in READ_BUCKETS]

BUCKET_RUN_COLS: list[str] = []
for bucket in READ_BUCKETS:
    BUCKET_RUN_COLS.extend(
        [
            f"{bucket}_run_accession",
            f"{bucket}_base_count",
            f"{bucket}_read_count",
            f"{bucket}_coverage",
            f"{bucket}_ena_url",
        ]
    )

from pipeline.patch_species_tax_lineage import (  # noqa: E402
    LINEAGE_COL,
    patch_matrix_lineage,
)
from pipeline.remap_invalid_matrix_taxids import remap_invalid_matrix_taxids  # noqa: E402
from pipeline.taxonomy_index import build_taxonomy_index, needs_rebuild  # noqa: E402

ENRICH_FIELDS = list(IUCN_STRUCTURED_FIELDS)

MATRIX_FIELDS = (
    ["taxid", "scientific_name", "catalog_source", LINEAGE_COL]
    + ENRICH_FIELDS
    + ["assembly_count", "annotation_count"]
    + BUCKET_COUNT_COLS
    + REF_ASSEMBLY_COLS
    + REF_ANNOTATION_COLS
    + BUCKET_RUN_COLS
)


def _tsv_val(value: Any) -> str:
    if value is None or value == "":
        return ""
    return str(value)


def _project_ref_assembly(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "ref_assembly_accession": row.get("accession") or "",
        "ref_assembly_name": row.get("assembly_name") or "",
        "ref_assembly_level": row.get("assembly_level") or "",
        "ref_assembly_source": row.get("assembly_source") or "",
        "ref_assembly_release_date": row.get("release_date") or "",
        "ref_assembly_bioproject_accession": row.get("bioproject_accession") or "",
        "ref_assembly_gc_percent": row.get("gc_percent") or "",
        "ref_assembly_total_sequence_length": row.get("total_sequence_length") or "",
        "ref_assembly_total_ungapped_length": row.get("total_ungapped_length") or "",
        "ref_assembly_contig_n50": row.get("contig_n50") or "",
        "ref_assembly_scaffold_n50": row.get("scaffold_n50") or "",
        "ref_assembly_total_number_of_chromosomes": row.get("total_number_of_chromosomes") or "",
        "ref_assembly_url": ncbi_assembly_url(row.get("accession")),
    }


def _project_ref_annotation(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "ref_annotation_id": row.get("annotation_id") or "",
        "ref_annotation_assembly_accession": row.get("assembly_accession") or "",
        "ref_annotation_db_source": row.get("db_source") or "",
        "ref_annotation_release_date": row.get("release_date") or "",
        "ref_annotation_busco_complete": row.get("busco_complete") or "",
        "ref_annotation_busco_single_copy": row.get("busco_single_copy") or "",
        "ref_annotation_busco_lineage": row.get("busco_lineage") or "",
        "ref_annotation_lncrna_gene_count": row.get("lncrna_gene_count") or "",
        "ref_annotation_mrna_gene_count": row.get("mrna_gene_count") or "",
        "ref_annotation_mrna_avg_length_full": row.get("mrna_avg_length_full") or "",
        "ref_annotation_mrna_avg_length_exon_concat": row.get("mrna_avg_length_exon_concat") or "",
        "ref_annotation_mrna_avg_length_cds_concat": row.get("mrna_avg_length_cds_concat") or "",
        "ref_annotation_mrna_transcript_count": row.get("mrna_transcript_count") or "",
        "ref_annotation_lncrna_avg_length_full": row.get("lncrna_avg_length_full") or "",
        "ref_annotation_lncrna_avg_length_exon_concat": row.get("lncrna_avg_length_exon_concat") or "",
        "ref_annotation_lncrna_transcript_count": row.get("lncrna_transcript_count") or "",
        "ref_annotation_total_genes_count": row.get("total_genes_count") or "",
        "ref_annotation_total_transcripts_count": row.get("total_transcripts_count") or "",
        "ref_annotation_url": annotrieve_source_url(
            row.get("source_url"), row.get("annotation_id")
        ),
    }


def _empty_bucket_fields() -> dict[str, str]:
    out: dict[str, str] = {f"{b}_count": "0" for b in READ_BUCKETS}
    for bucket in READ_BUCKETS:
        out[f"{bucket}_run_accession"] = ""
        out[f"{bucket}_base_count"] = ""
        out[f"{bucket}_read_count"] = ""
        out[f"{bucket}_coverage"] = ""
        out[f"{bucket}_ena_url"] = ""
    return out


def _project_bucket_run(bucket: str, row: dict[str, Any], genome_size: int | None) -> dict[str, str]:
    coverage = compute_coverage(row.get("base_count"), genome_size)
    return {
        f"{bucket}_run_accession": row.get("run_accession") or "",
        f"{bucket}_base_count": _tsv_val(row.get("base_count")),
        f"{bucket}_read_count": _tsv_val(row.get("read_count")),
        f"{bucket}_coverage": _tsv_val(coverage) if coverage is not None else "",
        f"{bucket}_ena_url": ena_run_url(row.get("run_accession")),
    }


def _stream_ref_assembly(path: Path) -> Iterator[dict[str, Any]]:
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if not row.get("taxid"):
                continue
            try:
                row["taxid"] = int(row["taxid"])
            except ValueError:
                continue
            yield row


def load_ref_assembly_maps(
    ref_asm_path: Path,
) -> tuple[dict[int, str], dict[int, int | None]]:
    """Return taxid→ref accession and taxid→genome_size from staged ref assembly file."""
    accessions: dict[int, str] = {}
    genome_sizes: dict[int, int | None] = {}
    for row in _stream_ref_assembly(ref_asm_path):
        taxid = int(row["taxid"])
        acc = row.get("ref_assembly_accession") or ""
        accessions[taxid] = acc
        size_raw = row.get("ref_assembly_total_sequence_length")
        try:
            genome_sizes[taxid] = int(size_raw) if size_raw else None
        except ValueError:
            genome_sizes[taxid] = None
    return accessions, genome_sizes


REF_ASSEMBLY_STAGED_FIELDS = (
    ["taxid", "scientific_name", "assembly_count"] + REF_ASSEMBLY_COLS
)

REF_ANNOTATION_STAGED_FIELDS = (
    ["taxid", "scientific_name", "annotation_count"] + REF_ANNOTATION_COLS
)

REP_RUNS_STAGED_FIELDS = ["taxid", "scientific_name"] + BUCKET_COUNT_COLS + BUCKET_RUN_COLS


def select_species_assemblies(
    raw_path: Path,
    taxonomy_path: Path,
    out_path: Path,
) -> int:
    """Stream raw assemblies → per-species reference assembly TSV."""
    accum: dict[int, dict[str, Any]] = {}

    for row in iter_eukaryote_assemblies_tsv(raw_path):
        taxid = int(row["taxid"])
        entry = accum.get(taxid)
        if entry is None:
            entry = {
                "taxid": taxid,
                "scientific_name": "",
                "assembly_count": 0,
                "_ref": None,
            }
            accum[taxid] = entry
        entry["assembly_count"] += 1
        entry["_ref"] = select_reference_assembly(entry["_ref"], row)

    names = _fill_names(set(accum.keys()), taxonomy_path)
    for taxid, entry in accum.items():
        entry["scientific_name"] = names.get(taxid, "")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=REF_ASSEMBLY_STAGED_FIELDS, delimiter="\t", extrasaction="ignore"
        )
        writer.writeheader()
        for taxid in sorted(accum):
            entry = accum[taxid]
            ref = entry["_ref"] or {}
            out_row: dict[str, Any] = {
                "taxid": taxid,
                "scientific_name": entry["scientific_name"],
                "assembly_count": entry["assembly_count"],
                **_project_ref_assembly(ref),
            }
            writer.writerow({k: _tsv_val(out_row.get(k)) for k in REF_ASSEMBLY_STAGED_FIELDS})

    print(f"Wrote {len(accum)} species assemblies to {out_path}", file=sys.stderr)
    return len(accum)


def select_species_annotations(
    raw_path: Path,
    ref_assembly_path: Path,
    taxonomy_path: Path,
    out_path: Path,
) -> int:
    """Stream annotations; pick best per species matching ref assembly accession."""
    ref_accessions, _ = load_ref_assembly_maps(ref_assembly_path)
    accum: dict[int, dict[str, Any]] = {}

    for row in iter_annotrieve_annotations_tsv(raw_path):
        taxid = int(row["taxid"])
        entry = accum.get(taxid)
        if entry is None:
            entry = {
                "taxid": taxid,
                "scientific_name": "",
                "annotation_count": 0,
                "_ref": None,
            }
            accum[taxid] = entry
        entry["annotation_count"] += 1

        ref_acc = ref_accessions.get(taxid)
        if ref_acc and row.get("assembly_accession") == ref_acc:
            entry["_ref"] = select_reference_annotation(entry["_ref"], row)

    names = _fill_names(set(accum.keys()), taxonomy_path)
    for taxid, entry in accum.items():
        entry["scientific_name"] = names.get(taxid, "")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=REF_ANNOTATION_STAGED_FIELDS, delimiter="\t", extrasaction="ignore"
        )
        writer.writeheader()
        for taxid in sorted(accum):
            entry = accum[taxid]
            ref = entry["_ref"] or {}
            out_row: dict[str, Any] = {
                "taxid": taxid,
                "scientific_name": entry["scientific_name"],
                "annotation_count": entry["annotation_count"],
                **_project_ref_annotation(ref),
            }
            writer.writerow({k: _tsv_val(out_row.get(k)) for k in REF_ANNOTATION_STAGED_FIELDS})

    print(f"Wrote {len(accum)} species annotations to {out_path}", file=sys.stderr)
    return len(accum)


def select_species_runs(
    raw_path: Path,
    ref_assembly_path: Path,
    taxonomy_path: Path,
    out_path: Path,
) -> int:
    """Stream ENA runs → per-species bucket counts and best runs."""
    _, genome_sizes = load_ref_assembly_maps(ref_assembly_path)
    accum: dict[int, dict[str, Any]] = {}

    for row in iter_eukaryote_read_runs_tsv(raw_path):
        taxid = parse_ena_taxid(row.get("tax_id") or row.get("taxid"))
        if taxid is None:
            continue
        bucket = classify_read_bucket(
            row.get("library_strategy"),
            row.get("instrument_platform"),
        )
        if bucket is None:
            continue

        entry = accum.get(taxid)
        if entry is None:
            entry = {
                "taxid": taxid,
                "scientific_name": "",
                "counts": {b: 0 for b in READ_BUCKETS},
                "best": {b: None for b in READ_BUCKETS},
            }
            accum[taxid] = entry

        entry["counts"][bucket] += 1
        genome_size = genome_sizes.get(taxid)
        entry["best"][bucket] = select_better_run(
            entry["best"][bucket],
            row,
            genome_size=genome_size,
        )

    names = _fill_names(set(accum.keys()), taxonomy_path)
    for taxid, entry in accum.items():
        entry["scientific_name"] = names.get(taxid, "")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=REP_RUNS_STAGED_FIELDS, delimiter="\t", extrasaction="ignore"
        )
        writer.writeheader()
        for taxid in sorted(accum):
            entry = accum[taxid]
            genome_size = genome_sizes.get(taxid)
            out_row: dict[str, Any] = {
                "taxid": taxid,
                "scientific_name": entry["scientific_name"],
            }
            for bucket in READ_BUCKETS:
                out_row[f"{bucket}_count"] = entry["counts"][bucket]
            empty = _empty_bucket_fields()
            for bucket in READ_BUCKETS:
                best = entry["best"][bucket]
                if best:
                    out_row.update(_project_bucket_run(bucket, best, genome_size))
                else:
                    for key in (
                        f"{bucket}_run_accession",
                        f"{bucket}_base_count",
                        f"{bucket}_read_count",
                        f"{bucket}_coverage",
                        f"{bucket}_ena_url",
                    ):
                        out_row[key] = empty[key]
            writer.writerow({k: _tsv_val(out_row.get(k)) for k in REP_RUNS_STAGED_FIELDS})

    print(f"Wrote {len(accum)} species run summaries to {out_path}", file=sys.stderr)
    return len(accum)


def _stream_staged(path: Path) -> Iterator[dict[str, str]]:
    if not path.exists():
        return
    with open(path, encoding="utf-8", newline="") as f:
        yield from csv.DictReader(f, delimiter="\t")


def merge_species_matrix(
    ref_asm_path: Path,
    ref_ann_path: Path,
    rep_runs_path: Path,
    out_path: Path,
    *,
    copy_to: Path | None = None,
) -> int:
    """Union-merge per-species staged files into final matrix TSV."""
    rows: dict[int, dict[str, str]] = {}

    for path in (ref_asm_path, ref_ann_path, rep_runs_path):
        for row in _stream_staged(path):
            if not row.get("taxid"):
                continue
            taxid = int(row["taxid"])
            if taxid not in rows:
                rows[taxid] = {f: "" for f in MATRIX_FIELDS}
                rows[taxid]["taxid"] = str(taxid)
                rows[taxid]["catalog_source"] = "catalog"
            for key, val in row.items():
                if key in MATRIX_FIELDS and val:
                    rows[taxid][key] = val

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MATRIX_FIELDS, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for taxid in sorted(rows):
            writer.writerow(rows[taxid])

    if copy_to:
        copy_to.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out_path, copy_to)

    print(f"Wrote {len(rows)} species to {out_path}", file=sys.stderr)
    return len(rows)


def run_fetch(staged_dir: Path) -> None:
    paths = {k: staged_dir / v for k, v in STAGED_FILES.items()}
    # Taxonomy fetch disabled — use data/ncbi_taxonomy_tree.tsv.gz (downstream step).
    # print("Fetching taxonomy…", file=sys.stderr)
    # write_ncbi_taxonomy_tsv(staged_dir / "01_ncbi_taxonomy_tree.tsv.gz")
    print("Fetching assemblies…", file=sys.stderr)
    write_eukaryote_assemblies_tsv(paths["assemblies"])
    print("Fetching annotations…", file=sys.stderr)
    write_annotrieve_annotations_tsv(paths["annotations"])
    print("Fetching ENA read runs…", file=sys.stderr)
    write_eukaryote_read_runs_tsv(paths["read_runs"])


def run_select(staged_dir: Path) -> None:
    paths = {k: staged_dir / v for k, v in STAGED_FILES.items()}
    taxonomy_path = _taxonomy_path(staged_dir)
    select_species_assemblies(paths["assemblies"], taxonomy_path, paths["ref_assembly"])
    select_species_annotations(
        paths["annotations"],
        paths["ref_assembly"],
        taxonomy_path,
        paths["ref_annotation"],
    )
    select_species_runs(
        paths["read_runs"],
        paths["ref_assembly"],
        taxonomy_path,
        paths["rep_runs"],
    )


def run_merge(staged_dir: Path, data_dir: Path) -> None:
    paths = {k: staged_dir / v for k, v in STAGED_FILES.items()}
    merge_species_matrix(
        paths["ref_assembly"],
        paths["ref_annotation"],
        paths["rep_runs"],
        paths["matrix"],
        copy_to=data_dir / "eukaryotic_species_matrix.tsv",
    )


def load_matrix_taxids(matrix_path: Path) -> set[int]:
    """Stream matrix TSV and collect taxids."""
    taxids: set[int] = set()
    with open(matrix_path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if not row.get("taxid"):
                continue
            try:
                taxids.add(int(row["taxid"]))
            except ValueError:
                continue
    return taxids


def enrich_matrix_iucn(
    matrix_path: Path,
    iucn_path: Path,
    out_path: Path,
    *,
    copy_to: Path | None = None,
) -> int:
    """Left-join structured IUCN fields onto the species matrix."""
    iucn = load_iucn_by_taxid(iucn_path)
    count = 0
    matched_iucn = 0
    out_path.parent.mkdir(parents=True, exist_ok=True)

    same_path = matrix_path.resolve() == out_path.resolve()
    tmp_path: Path | None = None
    write_path = out_path
    if same_path:
        tmp_fd, tmp_name = tempfile.mkstemp(
            suffix=".tsv", dir=out_path.parent, text=True
        )
        os.close(tmp_fd)
        tmp_path = Path(tmp_name)
        write_path = tmp_path

    with open(matrix_path, encoding="utf-8", newline="") as in_f, open(
        write_path, "w", encoding="utf-8", newline=""
    ) as out_f:
        reader = csv.DictReader(in_f, delimiter="\t")
        writer = csv.DictWriter(
            f=out_f, fieldnames=MATRIX_FIELDS, delimiter="\t", extrasaction="ignore"
        )
        writer.writeheader()
        for row in reader:
            if not row.get("taxid"):
                continue
            try:
                taxid = int(row["taxid"])
            except ValueError:
                continue
            out_row = {f: row.get(f) or "" for f in MATRIX_FIELDS}
            out_row["taxid"] = str(taxid)
            if not out_row.get("catalog_source"):
                out_row["catalog_source"] = "catalog"
            rec = iucn.get(taxid, {})
            if rec:
                matched_iucn += 1
                for field in ENRICH_FIELDS:
                    if rec.get(field):
                        out_row[field] = rec[field]
            writer.writerow(out_row)
            count += 1

    if tmp_path is not None:
        shutil.move(str(tmp_path), out_path)

    if copy_to:
        copy_to.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out_path, copy_to)

    print(
        f"Enriched {count} species ({matched_iucn} with IUCN metadata) → {out_path}",
        file=sys.stderr,
    )
    return count


def enrich_species_matrix(
    matrix_path: Path,
    iucn_path: Path,
    out_path: Path,
    *,
    copy_to: Path | None = None,
) -> int:
    """Alias for enrich_matrix_iucn."""
    return enrich_matrix_iucn(matrix_path, iucn_path, out_path, copy_to=copy_to)


def patch_matrix_annotations(
    matrix_path: Path,
    ref_ann_path: Path,
    *,
    copy_to: Path | None = None,
) -> int:
    """Update ref_annotation_* columns on an existing matrix from staged ref-annotation TSV."""
    ref_by_taxid: dict[int, dict[str, str]] = {}
    for row in _stream_staged(ref_ann_path):
        if not row.get("taxid"):
            continue
        ref_by_taxid[int(row["taxid"])] = row

    count = 0
    matrix_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_name = tempfile.mkstemp(suffix=".tsv", dir=matrix_path.parent, text=True)
    os.close(tmp_fd)
    tmp_path = Path(tmp_name)

    with open(matrix_path, encoding="utf-8", newline="") as in_f, open(
        tmp_path, "w", encoding="utf-8", newline=""
    ) as out_f:
        reader = csv.DictReader(in_f, delimiter="\t")
        writer = csv.DictWriter(
            f=out_f, fieldnames=MATRIX_FIELDS, delimiter="\t", extrasaction="ignore"
        )
        writer.writeheader()
        for row in reader:
            if not row.get("taxid"):
                continue
            try:
                taxid = int(row["taxid"])
            except ValueError:
                continue
            out_row = {f: row.get(f) or "" for f in MATRIX_FIELDS}
            out_row["taxid"] = str(taxid)
            ref = ref_by_taxid.get(taxid)
            if ref:
                for col in REF_ANNOTATION_COLS:
                    if ref.get(col):
                        out_row[col] = ref[col]
                if ref.get("annotation_count"):
                    out_row["annotation_count"] = ref["annotation_count"]
            writer.writerow(out_row)
            count += 1

    shutil.move(str(tmp_path), matrix_path)
    if copy_to:
        copy_to.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(matrix_path, copy_to)

    print(
        f"Patched {count} matrix rows ({len(ref_by_taxid)} with ref annotations) → {matrix_path}",
        file=sys.stderr,
    )
    return count


def run_patch_annotations(staged_dir: Path, data_dir: Path) -> None:
    """Re-select ref annotations and patch them into the existing species matrix."""
    paths = {k: staged_dir / v for k, v in STAGED_FILES.items()}
    matrix_path = paths["matrix"]
    if not matrix_path.is_file():
        print(f"Error: matrix not found at {matrix_path}. Run --step merge first.", file=sys.stderr)
        sys.exit(1)
    taxonomy_path = _taxonomy_path(staged_dir)
    select_species_annotations(
        paths["annotations"],
        paths["ref_assembly"],
        taxonomy_path,
        paths["ref_annotation"],
    )
    patch_matrix_annotations(
        matrix_path,
        paths["ref_annotation"],
        copy_to=data_dir / "eukaryotic_species_matrix.tsv",
    )


def _default_taxonomy_path(staged_dir: Path) -> Path:
    return _taxonomy_path(staged_dir)


def _default_parquet_path() -> Path:
    return _REPO / "data" / "scatter" / "species_scatter.parquet"


def _default_tile_dir() -> Path:
    return _REPO / "tiles" / "species" / "facets" / f"v{date.today():%Y%m%d}"


def run_finalize(
    staged_dir: Path,
    data_dir: Path,
    *,
    taxonomy_path: Path,
    db_path: Path,
    iucn_tsv: Path,
    force_rebuild_index: bool = False,
) -> dict[str, int]:
    """Build taxonomy index, remap taxids, patch lineage, enrich IUCN, union iucn_only."""
    paths = {k: staged_dir / v for k, v in STAGED_FILES.items()}
    matrix_path = paths["matrix"]
    if not matrix_path.is_file():
        print(f"Error: matrix not found at {matrix_path}. Run --step merge first.", file=sys.stderr)
        sys.exit(1)
    if not iucn_tsv.is_file():
        print(
            f"Error: IUCN TSV not found at {iucn_tsv}. "
            "Run: python pipeline/iucn_assessments_convert.py",
            file=sys.stderr,
        )
        sys.exit(1)

    stats: dict[str, int] = {}

    rebuild = force_rebuild_index or needs_rebuild(db_path, taxonomy_path)
    if rebuild or not db_path.is_file():
        print(f"Building taxonomy index → {db_path}…", file=sys.stderr)
        stats["taxonomy_rows"] = build_taxonomy_index(
            taxonomy_path, db_path, force=force_rebuild_index or not db_path.is_file()
        )

    mirror = data_dir / "eukaryotic_species_matrix.tsv"
    conn = sqlite3.connect(db_path)
    try:
        print(f"Remapping invalid taxids on {matrix_path}…", file=sys.stderr)
        remap_stats = remap_invalid_matrix_taxids(
            conn, matrix_path, matrix_path, in_place=True
        )
        stats.update(remap_stats)

        print(f"Patching tax_lineage onto {matrix_path}…", file=sys.stderr)
        _, ok, missing, ete3 = patch_matrix_lineage(
            conn, matrix_path, matrix_path, in_place=True
        )
        stats["lineage_ok"] = ok
        stats["lineage_missing"] = missing
        stats["lineage_ete3"] = ete3
    finally:
        conn.close()

    enrich_matrix_iucn(matrix_path, iucn_tsv, matrix_path, copy_to=mirror)

    from pipeline.merge_iucn_species import merge_iucn_only_species  # noqa: E402

    union_stats = merge_iucn_only_species(
        matrix_path, iucn_tsv, db_path, copy_to=mirror
    )
    stats["appended_iucn_only"] = union_stats["appended_iucn_only"]

    conn = sqlite3.connect(db_path)
    try:
        print(f"Re-patching tax_lineage after IUCN union…", file=sys.stderr)
        _, ok2, missing2, ete3_2 = patch_matrix_lineage(
            conn, matrix_path, matrix_path, in_place=True
        )
        stats["lineage_ok_after_union"] = ok2
        stats["lineage_missing_after_union"] = missing2
        stats["lineage_ete3_after_union"] = ete3_2
    finally:
        conn.close()

    shutil.copy2(matrix_path, mirror)
    return stats


def run_rollups(
    staged_dir: Path,
    *,
    taxonomy_path: Path,
    db_path: Path,
) -> dict[str, int | float]:
    from pipeline.build_taxon_rollups import run_pipeline as run_rollup_pipeline  # noqa: E402

    paths = {k: staged_dir / v for k, v in STAGED_FILES.items()}
    return run_rollup_pipeline(
        taxonomy_path=taxonomy_path,
        matrix_path=paths["matrix"],
        db_path=db_path,
        output_path=paths["rollups"],
        skip_index_build=True,
        skip_lineage_patch=True,
    )


def run_scatter(
    staged_dir: Path,
    *,
    db_path: Path,
    parquet_path: Path,
    tile_dir: Path,
    iucn_tsv: Path,
    tile_size: int = 50_000,
    skip_tile: bool = False,
    skip_coords: bool = False,
    embedding: str = "facets",
) -> None:
    from pipeline.build_scatter_tiles import (  # noqa: E402
        run_export,
        run_landscape,
        run_tile,
    )

    matrix_path = staged_dir / STAGED_FILES["matrix"]
    run_export(matrix_path, parquet_path, db_path=db_path, iucn_tsv=iucn_tsv)
    if not skip_coords and embedding == "landscape":
        run_landscape(parquet_path, db_path)
    if not skip_tile:
        run_tile(parquet_path, tile_dir, tile_size)


def run_enrich(
    staged_dir: Path,
    data_dir: Path,
    *,
    iucn_tsv: Path,
) -> None:
    paths = {k: staged_dir / v for k, v in STAGED_FILES.items()}
    matrix_path = paths["matrix"]
    if not matrix_path.is_file():
        print(
            f"Error: matrix not found at {matrix_path}. Run --step merge first.",
            file=sys.stderr,
        )
        sys.exit(1)
    if not iucn_tsv.is_file():
        print(
            f"Error: IUCN TSV not found at {iucn_tsv}. "
            "Run: pipenv run python pipeline/iucn_assessments_convert.py",
            file=sys.stderr,
        )
        sys.exit(1)

    taxid_count = len(load_matrix_taxids(matrix_path))
    print(f"Enriching {taxid_count} matrix species with IUCN categories…", file=sys.stderr)

    enrich_species_matrix(
        matrix_path,
        iucn_tsv,
        matrix_path,
        copy_to=data_dir / "eukaryotic_species_matrix.tsv",
    )


def run_union_iucn(
    staged_dir: Path,
    data_dir: Path,
    *,
    iucn_tsv: Path,
    db_path: Path | None = None,
) -> None:
    paths = {k: staged_dir / v for k, v in STAGED_FILES.items()}
    matrix_path = paths["matrix"]
    if not matrix_path.is_file():
        print(
            f"Error: matrix not found at {matrix_path}. Run --step enrich first.",
            file=sys.stderr,
        )
        sys.exit(1)
    taxonomy_db = db_path or (staged_dir / "taxonomy.sqlite")
    if not taxonomy_db.is_file():
        print(
            f"Error: taxonomy db not found at {taxonomy_db}. "
            "Run: python pipeline/build_taxon_rollups.py --skip-lineage-patch",
            file=sys.stderr,
        )
        sys.exit(1)

    from pipeline.merge_iucn_species import merge_iucn_only_species  # noqa: E402

    stats = merge_iucn_only_species(
        matrix_path,
        iucn_tsv,
        taxonomy_db,
        copy_to=data_dir / "eukaryotic_species_matrix.tsv",
    )
    print(
        f"Appended {stats['appended_iucn_only']:,} iucn_only species "
        f"({stats['catalog_rows']:,} catalog retained)",
        file=sys.stderr,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build eukaryotic species matrix and downstream rollups/scatter"
    )
    parser.add_argument(
        "--step",
        choices=(
            "fetch",
            "select",
            "merge",
            "enrich",
            "union-iucn",
            "finalize",
            "rollups",
            "scatter",
            "patch-annotations",
            "all",
        ),
        default="all",
        help="Pipeline step to run (default: all)",
    )
    parser.add_argument(
        "--staged-dir",
        type=Path,
        default=_REPO / "data" / "staged",
        help="Directory for staged TSV files",
    )
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Skip fetch step when running all steps",
    )
    parser.add_argument(
        "--skip-tile",
        action="store_true",
        help="Skip quadfeather tiling when running scatter/all",
    )
    parser.add_argument(
        "--skip-coords",
        action="store_true",
        help="Skip coordinate embedding when running scatter/all",
    )
    parser.add_argument(
        "--skip-landscape",
        action="store_true",
        help="Deprecated alias for --skip-coords",
    )
    parser.add_argument(
        "--embedding",
        choices=("facets", "landscape"),
        default="facets",
        help="Scatter embedding: phylo facets (default) or UMAP landscape",
    )
    parser.add_argument(
        "--iucn-tsv",
        type=Path,
        default=_REPO / "data" / "iucn_assessments.tsv",
        help="IUCN assessments TSV",
    )
    parser.add_argument(
        "--taxonomy",
        type=Path,
        default=None,
        help="NCBI taxonomy tree (default: data/ncbi_taxonomy_tree.tsv.gz)",
    )
    parser.add_argument(
        "--taxonomy-db",
        type=Path,
        default=_REPO / "data" / "staged" / "taxonomy.sqlite",
        help="SQLite taxonomy index",
    )
    parser.add_argument(
        "--force-rebuild-index",
        action="store_true",
        help="Rebuild taxonomy.sqlite even if up to date",
    )
    parser.add_argument(
        "--parquet",
        type=Path,
        default=None,
        help="Scatter parquet output (default: data/scatter/species_scatter.parquet)",
    )
    parser.add_argument(
        "--tile-dir",
        type=Path,
        default=None,
        help="quadfeather tile destination (default: tiles/species/facets/vDATE)",
    )
    parser.add_argument(
        "--tile-size",
        type=int,
        default=50_000,
        help="quadfeather tile_size (default: 50000)",
    )
    args = parser.parse_args()

    staged_dir = args.staged_dir
    data_dir = _REPO / "data"
    taxonomy_path = args.taxonomy or _default_taxonomy_path(staged_dir)
    parquet_path = args.parquet or _default_parquet_path()
    tile_dir = args.tile_dir or _default_tile_dir()

    if args.step == "fetch":
        run_fetch(staged_dir)
    elif args.step == "select":
        run_select(staged_dir)
    elif args.step == "merge":
        run_merge(staged_dir, data_dir)
    elif args.step == "finalize":
        run_finalize(
            staged_dir,
            data_dir,
            taxonomy_path=taxonomy_path,
            db_path=args.taxonomy_db,
            iucn_tsv=args.iucn_tsv,
            force_rebuild_index=args.force_rebuild_index,
        )
    elif args.step == "rollups":
        run_rollups(staged_dir, taxonomy_path=taxonomy_path, db_path=args.taxonomy_db)
    elif args.step == "scatter":
        skip_coords = args.skip_coords or args.skip_landscape
        run_scatter(
            staged_dir,
            db_path=args.taxonomy_db,
            parquet_path=parquet_path,
            tile_dir=tile_dir,
            iucn_tsv=args.iucn_tsv,
            tile_size=args.tile_size,
            skip_tile=args.skip_tile,
            skip_coords=skip_coords,
            embedding=args.embedding,
        )
    elif args.step == "enrich":
        run_enrich(staged_dir, data_dir, iucn_tsv=args.iucn_tsv)
    elif args.step == "union-iucn":
        run_union_iucn(
            staged_dir,
            data_dir,
            iucn_tsv=args.iucn_tsv,
            db_path=args.taxonomy_db,
        )
    elif args.step == "patch-annotations":
        run_patch_annotations(staged_dir, data_dir)
    else:
        if not args.skip_fetch:
            run_fetch(staged_dir)
        run_select(staged_dir)
        run_merge(staged_dir, data_dir)
        run_finalize(
            staged_dir,
            data_dir,
            taxonomy_path=taxonomy_path,
            db_path=args.taxonomy_db,
            iucn_tsv=args.iucn_tsv,
            force_rebuild_index=args.force_rebuild_index,
        )
        run_rollups(staged_dir, taxonomy_path=taxonomy_path, db_path=args.taxonomy_db)
        skip_coords = args.skip_coords or args.skip_landscape
        run_scatter(
            staged_dir,
            db_path=args.taxonomy_db,
            parquet_path=parquet_path,
            tile_dir=tile_dir,
            iucn_tsv=args.iucn_tsv,
            tile_size=args.tile_size,
            skip_tile=args.skip_tile,
            skip_coords=skip_coords,
            embedding=args.embedding,
        )


if __name__ == "__main__":
    main()
