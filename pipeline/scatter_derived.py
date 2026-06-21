"""Precomputed deepscatter columns (mirrors next-app/lib/iucn/scatter-transforms.ts)."""

from __future__ import annotations

import numpy as np
import pyarrow as pa

from pipeline.schema import READ_FLAG_FIELDS, normalize_redlist_category

# Matches next-app/lib/iucn/config.ts IUCN_CODE_BY_CATEGORY
IUCN_CODE_BY_CATEGORY: dict[str, float] = {
    "": 0.0,
    "ne": 0.0,
    "lc": 1.0,
    "nt": 2.0,
    "vu": 3.0,
    "en": 4.0,
    "cr": 5.0,
    "dd": 6.0,
    "ew": 7.0,
    "ex": 8.0,
}

# Matches next-app/lib/iucn/pipeline-legend.ts PIPELINE_TIER
PIPELINE_TIER_NONE = 0.0
PIPELINE_TIER_NCBI = 1.0
PIPELINE_TIER_OCCURRENCE = 2.0
PIPELINE_TIER_GOAT = 3.0
PIPELINE_TIER_READS = 4.0
PIPELINE_TIER_ASSEMBLIES = 5.0
PIPELINE_TIER_ANNOTATIONS = 6.0

SCATTER_DERIVED_FIELDS = ("iucnCode", "pipelineCode", "hasNcbi", "hasReads")


def _flag_array(column: pa.ChunkedArray | pa.Array) -> np.ndarray:
    """True when matrix flag is 1 / true / True."""
    values = column.to_pylist()
    out = np.empty(len(values), dtype=np.float32)
    for i, value in enumerate(values):
        text = str(value or "").strip()
        out[i] = 1.0 if text in ("1", "true", "True") else 0.0
    return out


def _iucn_code_array(categories: pa.ChunkedArray | pa.Array) -> np.ndarray:
    values = categories.to_pylist()
    out = np.empty(len(values), dtype=np.float32)
    for i, raw in enumerate(values):
        code = normalize_redlist_category(str(raw) if raw is not None else "")
        out[i] = IUCN_CODE_BY_CATEGORY.get(code, 0.0)
    return out


def _pipeline_code_array(table: pa.Table) -> np.ndarray:
    n = table.num_rows
    pipeline = np.zeros(n, dtype=np.float32)

    if "ncbiTaxid" in table.column_names:
        ncbi = table.column("ncbiTaxid").to_pylist()
        has_ncbi = np.array(
            [1.0 if str(v or "").strip() else 0.0 for v in ncbi],
            dtype=np.float32,
        )
        pipeline = np.where(has_ncbi > 0, PIPELINE_TIER_NCBI, pipeline)

    if "hasGbif" in table.column_names:
        has_gbif = _flag_array(table.column("hasGbif"))
        has_inat = _flag_array(table.column("hasInat")) if "hasInat" in table.column_names else np.zeros(n, dtype=np.float32)
        pipeline = np.where((has_gbif > 0) | (has_inat > 0), PIPELINE_TIER_OCCURRENCE, pipeline)

    if "hasGoat" in table.column_names:
        has_goat = _flag_array(table.column("hasGoat"))
        pipeline = np.where(has_goat > 0, PIPELINE_TIER_GOAT, pipeline)

    read_parts = [
        _flag_array(table.column(field))
        for field in READ_FLAG_FIELDS
        if field in table.column_names
    ]
    if read_parts:
        has_reads = np.maximum.reduce(read_parts)
        pipeline = np.where(has_reads > 0, PIPELINE_TIER_READS, pipeline)

    if "hasAssemblies" in table.column_names:
        has_asm = _flag_array(table.column("hasAssemblies"))
        pipeline = np.where(has_asm > 0, PIPELINE_TIER_ASSEMBLIES, pipeline)

    if "hasAnnotations" in table.column_names:
        has_ann = _flag_array(table.column("hasAnnotations"))
        pipeline = np.where(has_ann > 0, PIPELINE_TIER_ANNOTATIONS, pipeline)

    return pipeline


def scatter_has_derived_columns(table: pa.Table) -> bool:
    return all(name in table.column_names for name in SCATTER_DERIVED_FIELDS)


def append_derived_scatter_columns(table: pa.Table) -> pa.Table:
    """Append iucnCode, pipelineCode, hasNcbi, hasReads for deepscatter GPU filters."""
    if scatter_has_derived_columns(table):
        return table

    if "redlistCategory" not in table.column_names:
        raise ValueError("Scatter table missing redlistCategory for iucnCode")

    iucn_codes = _iucn_code_array(table.column("redlistCategory"))
    pipeline_codes = _pipeline_code_array(table)

    if "ncbiTaxid" in table.column_names:
        ncbi = table.column("ncbiTaxid").to_pylist()
        has_ncbi = np.array(
            [1.0 if str(v or "").strip() else 0.0 for v in ncbi],
            dtype=np.float32,
        )
    else:
        has_ncbi = np.zeros(table.num_rows, dtype=np.float32)

    read_parts = [
        _flag_array(table.column(field))
        for field in READ_FLAG_FIELDS
        if field in table.column_names
    ]
    if read_parts:
        has_reads = np.maximum.reduce(read_parts)
    else:
        has_reads = np.zeros(table.num_rows, dtype=np.float32)

    table = table.append_column("iucnCode", pa.array(iucn_codes, type=pa.float32()))
    table = table.append_column("pipelineCode", pa.array(pipeline_codes, type=pa.float32()))
    table = table.append_column("hasNcbi", pa.array(has_ncbi, type=pa.float32()))
    table = table.append_column("hasReads", pa.array(has_reads, type=pa.float32()))
    return table
