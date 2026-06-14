#!/usr/bin/env python3
"""Pure selection/ranking helpers for the species matrix pipeline."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

ASSEMBLY_LEVEL_RANK = {
    "complete genome": 4,
    "complete_genome": 4,
    "chromosome": 3,
    "scaffold": 2,
    "contig": 1,
}

ASSEMBLY_SOURCE_RANK = {
    "refseq": 2,
    "genbank": 1,
}

LONG_READ_PLATFORMS = frozenset(
    {"OXFORD_NANOPORE", "PACBIO_SMRT", "PACBIO", "LS454"}
)


def normalize_assembly_level(level: str | None) -> str:
    if not level:
        return ""
    normalized = level.replace("_", " ").strip().lower()
    mapping = {
        "complete genome": "Complete Genome",
        "chromosome": "Chromosome",
        "scaffold": "Scaffold",
        "contig": "Contig",
    }
    return mapping.get(normalized, level.strip())


def assembly_source_from_accession(accession: str | None) -> str:
    if not accession:
        return ""
    if accession.upper().startswith("GCF"):
        return "refseq"
    if accession.upper().startswith("GCA"):
        return "genbank"
    return ""


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    if "T" in s:
        s = s.split("T", 1)[0]
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def _assembly_sort_key(row: dict[str, Any]) -> tuple:
    level = normalize_assembly_level(str(row.get("assembly_level") or "")).lower()
    level_key = level.replace(" ", "_")
    level_rank = ASSEMBLY_LEVEL_RANK.get(level_key, ASSEMBLY_LEVEL_RANK.get(level, 0))
    source = str(row.get("assembly_source") or "").lower()
    source_rank = ASSEMBLY_SOURCE_RANK.get(source, 0)
    release = _parse_date(row.get("release_date"))
    release_ord = release.toordinal() if release else 0
    length = int(row.get("total_sequence_length") or 0)
    return (level_rank, source_rank, release_ord, length)


def select_reference_assembly(
    incumbent: dict[str, Any] | None,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    """Return the better assembly row."""
    if incumbent is None:
        return candidate
    if _assembly_sort_key(candidate) > _assembly_sort_key(incumbent):
        return candidate
    return incumbent


def _annotation_sort_key(row: dict[str, Any]) -> tuple:
    busco = float(row.get("busco_complete") or 0)
    release = _parse_date(row.get("release_date"))
    release_ord = release.toordinal() if release else 0
    transcripts = int(row.get("total_transcripts_count") or 0)
    return (busco, release_ord, transcripts)


def select_reference_annotation(
    incumbent: dict[str, Any] | None,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    if incumbent is None:
        return candidate
    if _annotation_sort_key(candidate) > _annotation_sort_key(incumbent):
        return candidate
    return incumbent


def classify_read_bucket(strategy: str | None, platform: str | None) -> str | None:
    strat = (strategy or "").strip().upper()
    plat = (platform or "").strip().upper()
    is_long = plat in LONG_READ_PLATFORMS
    if strat == "WGS":
        return "wgs_long" if is_long else "wgs_short"
    if strat == "RNA-SEQ":
        return "rnaseq_long" if is_long else "rnaseq_short"
    return None


def compute_coverage(base_count: Any, genome_size: Any) -> float | None:
    try:
        bases = int(base_count)
        genome = int(genome_size)
    except (TypeError, ValueError):
        return None
    if genome <= 0 or bases <= 0:
        return None
    return bases / genome


def _run_sort_key(row: dict[str, Any], genome_size: int | None) -> tuple:
    coverage = compute_coverage(row.get("base_count"), genome_size) if genome_size else None
    coverage_score = coverage if coverage is not None else 0.0
    layout = str(row.get("library_layout") or "").upper()
    paired = 1 if layout == "PAIRED" else 0
    bases = int(row.get("base_count") or 0)
    return (coverage_score, paired, bases)


def select_better_run(
    incumbent: dict[str, Any] | None,
    candidate: dict[str, Any],
    *,
    genome_size: int | None = None,
) -> dict[str, Any]:
    if incumbent is None:
        return candidate
    if _run_sort_key(candidate, genome_size) > _run_sort_key(incumbent, genome_size):
        return candidate
    return incumbent


def ncbi_assembly_url(accession: str | None) -> str:
    if not accession:
        return ""
    return f"https://www.ncbi.nlm.nih.gov/datasets/genome/{accession}/"


def ena_run_url(run_accession: str | None) -> str:
    if not run_accession:
        return ""
    return f"https://www.ebi.ac.uk/ena/browser/view/{run_accession}"


def annotrieve_source_url(source_url: str | None, annotation_id: str | None = None) -> str:
    if source_url:
        return source_url
    if annotation_id:
        return f"https://genome.crg.es/annotrieve/api/v0/annotations/{annotation_id}"
    return ""
