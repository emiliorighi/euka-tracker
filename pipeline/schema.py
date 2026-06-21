"""Read-bucket classification and shared constants for pipeline."""

from __future__ import annotations

from typing import Literal

EUKARYOTA_TAXID = 2759

LONG_READ_PLATFORMS = frozenset({"OXFORD_NANOPORE", "PACBIO_SMRT", "PACBIO_RS", "PACBIO_RS_II"})

READ_COUNT_FIELDS = (
    "short_genomic_reads_count",
    "long_genomic_reads_count",
    "short_transcriptomic_reads_count",
    "long_transcriptomic_reads_count",
    "short_genomic_single_cell_count",
    "long_genomic_single_cell_count",
    "short_transcriptomic_single_cell_count",
    "long_transcriptomic_single_cell_count",
)

READ_FLAG_FIELDS = (
    "hasShortWgs",
    "hasLongWgs",
    "hasShortTranscriptomic",
    "hasLongTranscriptomic",
    "hasShortWgsSingleCell",
    "hasLongWgsSingleCell",
    "hasShortTranscriptomicSingleCell",
    "hasLongTranscriptomicSingleCell",
)

READ_BUCKET_TO_FLAG = {
    "short_genomic_reads_count": "hasShortWgs",
    "long_genomic_reads_count": "hasLongWgs",
    "short_transcriptomic_reads_count": "hasShortTranscriptomic",
    "long_transcriptomic_reads_count": "hasLongTranscriptomic",
    "short_genomic_single_cell_count": "hasShortWgsSingleCell",
    "long_genomic_single_cell_count": "hasLongWgsSingleCell",
    "short_transcriptomic_single_cell_count": "hasShortTranscriptomicSingleCell",
    "long_transcriptomic_single_cell_count": "hasLongTranscriptomicSingleCell",
}

GOAT_STATUS_ORDINAL = {
    "sample_collected": 1,
    "sample_acquired": 2,
    "data_generation": 3,
    "in_assembly": 4,
    "in_progress": 5,
    "insdc_open": 6,
    "open": 6,
    "published": 7,
}

ReadBucket = Literal[
    "short_genomic_reads_count",
    "long_genomic_reads_count",
    "short_transcriptomic_reads_count",
    "long_transcriptomic_reads_count",
    "short_genomic_single_cell_count",
    "long_genomic_single_cell_count",
    "short_transcriptomic_single_cell_count",
    "long_transcriptomic_single_cell_count",
]

SIMPLE_SUMMARY_FIELDS = (
    "assessmentId",
    "internalTaxonId",
    "scientificName",
    "kingdomName",
    "phylumName",
    "orderName",
    "className",
    "familyName",
    "genusName",
    "speciesName",
    "infraType",
    "infraName",
    "infraAuthority",
    "authority",
    "redlistCategory",
    "redlistCriteria",
    "criteriaVersion",
    "populationTrend",
    "scopes",
)

LINK_FLAG_FIELDS = ("hasGbif", "hasInat")
GENOMIC_FLAG_FIELDS = ("hasGoat", "hasAssemblies", "hasAnnotations")
TRACE_FIELDS = ("ncbiTaxid", "gbifId", "inatId", "ncbiMatchMethod")

IUCN_MATRIX_FIELDS = (
    *SIMPLE_SUMMARY_FIELDS,
    *LINK_FLAG_FIELDS,
    *GENOMIC_FLAG_FIELDS,
    *READ_FLAG_FIELDS,
    *TRACE_FIELDS,
)

# Precomputed in scatter_layout (see pipeline/scatter_derived.py)
SCATTER_DERIVED_FIELDS = ("iucnCode", "pipelineCode", "hasNcbi", "hasReads")

IUCN_SCATTER_FIELDS = (*IUCN_MATRIX_FIELDS, "x", "y", *SCATTER_DERIVED_FIELDS)

# Red List category short codes → rollup count column names (camelCase)
IUCN_CATEGORY_CODES: dict[str, str] = {
    "lc": "Lc",
    "nt": "Nt",
    "vu": "Vu",
    "en": "En",
    "cr": "Cr",
    "dd": "Dd",
    "ew": "Ew",
    "ex": "Ex",
    "ne": "Ne",
}

IUCN_CATEGORY_COUNT_FIELDS = tuple(
    f"speciesCount{suffix}" for suffix in IUCN_CATEGORY_CODES.values()
)

ROLLUP_CORE_FIELDS = (
    "taxonKey",
    "taxonName",
    "rank",
    "parentTaxonKey",
    "speciesCountTotal",
)

ROLLUP_DATASET_COUNT_FIELDS = (
    "speciesCountGbif",
    "speciesCountInat",
    "speciesCountNcbi",
    "speciesCountGoat",
    "speciesCountAssemblies",
    "speciesCountAnnotations",
)

# Mirror READ_FLAG_FIELDS as species-count columns on rollups
ROLLUP_BUCKET_COUNT_FIELDS = tuple(
    flag.replace("has", "speciesCount", 1) for flag in READ_FLAG_FIELDS
)

IUCN_ROLLUP_FIELDS = (
    *ROLLUP_CORE_FIELDS,
    *IUCN_CATEGORY_COUNT_FIELDS,
    *ROLLUP_DATASET_COUNT_FIELDS,
    *ROLLUP_BUCKET_COUNT_FIELDS,
)

# Diagnostic flag counts (ncbiTaxid non-empty replaces exported hasNcbi)
COUNT_FLAG_FIELDS = (
    *LINK_FLAG_FIELDS,
    *GENOMIC_FLAG_FIELDS,
    *READ_FLAG_FIELDS,
    "hasNcbi",
)

DATASET_FILES = {
    "taxonomy_db": "taxonomy.db",
    "species_backbone": "species_backbone.tsv",
    "assemblies": "ncbi_assemblies.tsv",
    "annotations": "annotrieve_annotations.tsv",
    "read_runs": "ena_read_runs.tsv",
    "goat": "goat_sequencing_status.tsv",
    "cross_universe_db": "cross_universe.db",
    "simple_summary": "simple_summary.csv",
}

CACHE_FILES = {
    "gbif_backbone": "cache/gbif/backbone.zip",
    "inat_taxonomy": "cache/inaturalist/taxonomy.dwca.zip",
    "otl_root": "cache/otl",
}


def normalize_name(name: str | None) -> str:
    if not name:
        return ""
    return " ".join(str(name).split()).strip()


def normalize_redlist_category(category: str | None) -> str:
    """Map redlistCategory to short code (LC, NT, …) for rollup buckets."""
    if not category:
        return ""
    key = category.strip().lower()
    if key in ("least concern", "lower risk/least concern"):
        return "lc"
    if key in ("near threatened", "lower risk/near threatened"):
        return "nt"
    if key == "vulnerable":
        return "vu"
    if key == "endangered":
        return "en"
    if key == "critically endangered":
        return "cr"
    if key == "data deficient":
        return "dd"
    if key == "extinct in the wild":
        return "ew"
    if key == "extinct":
        return "ex"
    if key in ("not evaluated", "not evaluated (ne)"):
        return "ne"
    for prefix, code in (
        ("least concern", "lc"),
        ("near threatened", "nt"),
        ("critically endangered", "cr"),
        ("endangered", "en"),
        ("vulnerable", "vu"),
        ("data deficient", "dd"),
        ("extinct in the wild", "ew"),
        ("extinct", "ex"),
    ):
        if key.startswith(prefix):
            return code
    return ""


def classify_read_bucket(library_source: str | None, instrument_platform: str | None) -> ReadBucket | None:
    """Map ENA library_source + platform to one of eight read count columns."""
    src = (library_source or "").strip().upper()
    plat = (instrument_platform or "").strip().upper()
    is_long = plat in LONG_READ_PLATFORMS

    if src == "GENOMIC":
        return "long_genomic_reads_count" if is_long else "short_genomic_reads_count"
    if src == "TRANSCRIPTOMIC":
        return "long_transcriptomic_reads_count" if is_long else "short_transcriptomic_reads_count"
    if src == "GENOMIC SINGLE CELL":
        return "long_genomic_single_cell_count" if is_long else "short_genomic_single_cell_count"
    if src == "TRANSCRIPTOMIC SINGLE CELL":
        return (
            "long_transcriptomic_single_cell_count"
            if is_long
            else "short_transcriptomic_single_cell_count"
        )
    return None


def goat_status_ordinal(status: str | None) -> int:
    if not status:
        return 0
    return GOAT_STATUS_ORDINAL.get(status.strip().lower(), 0)


def goat_status_from_ordinal(ordinal: int) -> str:
    if ordinal <= 0:
        return ""
    for status, val in GOAT_STATUS_ORDINAL.items():
        if val == ordinal:
            return status
    return ""
