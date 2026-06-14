#!/usr/bin/env python3
"""Derive slim deepscatter-ready rows from the species matrix TSV."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pipeline.scatter_metrics import scatter_metric_fields

EUKARYOTA_TAXID = 2759

# Depth 0 (Eukaryota) is omitted; ancestor_d1 = lineage[1], etc.
ANCESTOR_MIN_DEPTH = 1
ANCESTOR_MAX_DEPTH = 36

ANCESTOR_FIELDS = [
    f"ancestor_d{d}" for d in range(ANCESTOR_MIN_DEPTH, ANCESTOR_MAX_DEPTH + 1)
]

IUCN_CODE = {
    "least concern": 1,
    "near threatened": 2,
    "vulnerable": 3,
    "endangered": 4,
    "critically endangered": 5,
    "data deficient": 6,
    "extinct in the wild": 7,
    "extinct": 7,
    "lower risk/near threatened": 2,
    "lower risk/least concern": 1,
}


@dataclass
class ScatterExportContext:
    """Precomputed maps for pack layout and clade study-gap coordinates."""

    pack_layout: dict[int, tuple[float, float, float]] = field(default_factory=dict)
    study_coords: dict[int, tuple[float, float]] = field(default_factory=dict)
    phylum_by_species: dict[int, tuple[int, str]] = field(default_factory=dict)
    view_extent: dict[str, list[float]] = field(default_factory=dict)


def _int(value: Any) -> int:
    if value is None or value == "":
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _iucn_code(category: str | None) -> int:
    if not category:
        return 0
    key = category.strip().lower()
    for prefix, code in IUCN_CODE.items():
        if key == prefix or key.startswith(prefix):
            return code
    return 0


def _parse_lineage(lineage: str) -> list[int]:
    if not lineage or not lineage.strip():
        return []
    out: list[int] = []
    for part in lineage.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except ValueError:
            continue
    return out


def _lineage_taxids(lineage: str, species_taxid: int) -> list[int]:
    """Root→tip taxids from Eukaryota to the species."""
    taxids = _parse_lineage(lineage)
    if not taxids:
        if species_taxid and species_taxid != EUKARYOTA_TAXID:
            return [EUKARYOTA_TAXID, species_taxid]
        return [EUKARYOTA_TAXID] if species_taxid == EUKARYOTA_TAXID else []

    try:
        start = taxids.index(EUKARYOTA_TAXID)
        taxids = taxids[start:]
    except ValueError:
        taxids = [EUKARYOTA_TAXID, *taxids]

    if species_taxid:
        if species_taxid in taxids:
            taxids = taxids[: taxids.index(species_taxid) + 1]
        elif taxids[-1] != species_taxid:
            taxids.append(species_taxid)

    return taxids


def _ancestor_depth_fields(lineage: list[int]) -> dict[str, int]:
    """Map lineage[d] → ancestor_d{d} for d >= 1; pad missing depths with 0."""
    out: dict[str, int] = {}
    for d in range(ANCESTOR_MIN_DEPTH, ANCESTOR_MAX_DEPTH + 1):
        out[f"ancestor_d{d}"] = lineage[d] if d < len(lineage) else 0
    return out


def matrix_row_to_scatter(
    row: dict[str, Any],
    *,
    context: ScatterExportContext | None = None,
) -> dict[str, Any]:
    """Map one species matrix TSV row to a slim scatter export row."""
    species_taxid = _int(row.get("taxid"))
    lineage = _lineage_taxids(row.get("tax_lineage") or "", species_taxid)

    layout_x = 0.0
    layout_y = 0.0
    x = 0.0
    y = 0.0
    phylum_taxid = 0
    phylum_name = ""

    if context:
        if species_taxid in context.pack_layout:
            layout_x, layout_y, _ = context.pack_layout[species_taxid]
        if species_taxid in context.study_coords:
            x, y = context.study_coords[species_taxid]
        elif species_taxid in context.pack_layout:
            x, y = layout_x, layout_y
        if species_taxid in context.phylum_by_species:
            phylum_taxid, phylum_name = context.phylum_by_species[species_taxid]

    return {
        "taxid": species_taxid,
        "scientific_name": row.get("scientific_name") or "",
        "redlist_category": row.get("redlist_category") or "",
        "iucn_code": _iucn_code(row.get("redlist_category")),
        "phylum_taxid": phylum_taxid,
        "phylum_name": phylum_name,
        "layout_x": layout_x,
        "layout_y": layout_y,
        "x": x,
        "y": y,
        **scatter_metric_fields(row),
        **_ancestor_depth_fields(lineage),
    }


SCATTER_METRIC_FIELDS: list[str] = [
    "run_count",
    "assembly_count",
    "annotation_count",
    "log10_run_count",
    "attention_score",
    "data_tier",
    "conservation_need",
]

SCATTER_BASE_FIELDS: list[str] = [
    "taxid",
    "scientific_name",
    "redlist_category",
    "iucn_code",
    "phylum_taxid",
    "phylum_name",
    "layout_x",
    "layout_y",
    "x",
    "y",
    *SCATTER_METRIC_FIELDS,
]

SCATTER_FIELDS: list[str] = [*SCATTER_BASE_FIELDS, *ANCESTOR_FIELDS]
