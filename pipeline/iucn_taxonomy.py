"""IUCN simple_summary rank hierarchy helpers for rollups and lineage features."""

from __future__ import annotations

from typing import Iterator

from pipeline.schema import normalize_name

# (rank label, matrix column name)
IUCN_RANKS: tuple[tuple[str, str], ...] = (
    ("kingdom", "kingdomName"),
    ("phylum", "phylumName"),
    ("class", "className"),
    ("order", "orderName"),
    ("family", "familyName"),
    ("genus", "genusName"),
    ("species", "speciesName"),
)

RANK_DEPTH = {rank: i for i, (rank, _) in enumerate(IUCN_RANKS)}


def taxon_key(rank: str, name: str) -> str:
    """Stable key for an induced IUCN taxon node, e.g. kingdom:Animalia."""
    cleaned = normalize_name(name)
    if not cleaned:
        return ""
    return f"{rank}:{cleaned}"


def _row_value(row: dict[str, str], column: str) -> str:
    return normalize_name(row.get(column, ""))


def iter_iucn_path(row: dict[str, str]) -> Iterator[tuple[str, str, str, str]]:
    """
    Yield (rank, taxonName, taxonKey, parentTaxonKey) for each non-empty rank on the path.
    Species row uses scientificName when speciesName is empty.
    """
    parent_key = ""
    for rank, column in IUCN_RANKS:
        if rank == "species":
            name = _row_value(row, column) or _row_value(row, "scientificName")
        else:
            name = _row_value(row, column)
        if not name:
            continue
        key = taxon_key(rank, name)
        if not key:
            continue
        yield rank, name, key, parent_key
        parent_key = key


def iucn_lineage_tokens(row: dict[str, str]) -> list[str]:
    """Lowercased lineage tokens from kingdom through genus (for UMAP features)."""
    tokens: list[str] = []
    for rank, column in IUCN_RANKS:
        if rank == "species":
            break
        name = _row_value(row, column)
        if name:
            tokens.append(name.lower())
    return tokens
