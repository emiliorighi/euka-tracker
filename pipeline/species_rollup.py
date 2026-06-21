"""Per-source aggregation rolled up to species rank via taxonomy.db."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pipeline.schema import (
    READ_COUNT_FIELDS,
    classify_read_bucket,
    goat_status_from_ordinal,
    goat_status_ordinal,
)
from pipeline.taxonomy_db import TaxonomyDb


@dataclass
class SpeciesAccumulator:
    read_buckets: dict[str, int] = field(default_factory=lambda: {b: 0 for b in READ_COUNT_FIELDS})
    assembly_count: int = 0
    annotation_count: int = 0
    goat_ordinal: int = 0
    mrna_transcript_sum: float = 0.0
    lncrna_transcript_sum: float = 0.0
    mrna_gene_sum: float = 0.0
    lncrna_gene_sum: float = 0.0
    annotation_rows: int = 0

    def add_read(self, bucket: str) -> None:
        self.read_buckets[bucket] = self.read_buckets.get(bucket, 0) + 1

    def add_assembly(self) -> None:
        self.assembly_count += 1

    def add_annotation(
        self,
        *,
        mrna_transcript: float,
        lncrna_transcript: float,
        mrna_genes: float,
        lncrna_genes: float,
    ) -> None:
        self.annotation_count += 1
        self.annotation_rows += 1
        self.mrna_transcript_sum += mrna_transcript
        self.lncrna_transcript_sum += lncrna_transcript
        self.mrna_gene_sum += mrna_genes
        self.lncrna_gene_sum += lncrna_genes

    def add_goat_status(self, status: str | None) -> None:
        ordinal = goat_status_ordinal(status)
        if ordinal > self.goat_ordinal:
            self.goat_ordinal = ordinal

    @property
    def total_reads(self) -> int:
        return sum(self.read_buckets.values())

    def goat_status_str(self) -> str:
        return goat_status_from_ordinal(self.goat_ordinal)


class AncestorResolver:
    """Bounded memo: only taxids seen in source files."""

    def __init__(self, taxonomy: TaxonomyDb) -> None:
        self._taxonomy = taxonomy
        self._memo: dict[int, int | None] = {}

    def resolve(self, taxid: int) -> int | None:
        if taxid in self._memo:
            return self._memo[taxid]
        species = self._taxonomy.species_ancestor(taxid)
        self._memo[taxid] = species
        return species


def parse_ena_taxid(value: Any) -> int | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s or ";" in s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _float(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def aggregate_reads(
    taxonomy: TaxonomyDb,
    read_runs_path: Path,
    accum: dict[int, SpeciesAccumulator],
) -> int:
    resolver = AncestorResolver(taxonomy)
    count = 0
    with open(read_runs_path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            taxid = parse_ena_taxid(row.get("tax_id") or row.get("taxid"))
            if taxid is None:
                continue
            species = resolver.resolve(taxid)
            if species is None:
                continue
            bucket = classify_read_bucket(
                row.get("library_source"),
                row.get("instrument_platform"),
            )
            if bucket is None:
                continue
            accum.setdefault(species, SpeciesAccumulator()).add_read(bucket)
            count += 1
    return count


def aggregate_assemblies(
    taxonomy: TaxonomyDb,
    assemblies_path: Path,
    accum: dict[int, SpeciesAccumulator],
) -> int:
    resolver = AncestorResolver(taxonomy)
    count = 0
    with open(assemblies_path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            try:
                taxid = int(row["taxid"])
            except (KeyError, ValueError):
                continue
            species = resolver.resolve(taxid)
            if species is None:
                continue
            accum.setdefault(species, SpeciesAccumulator()).add_assembly()
            count += 1
    return count


def aggregate_annotations(
    taxonomy: TaxonomyDb,
    annotations_path: Path,
    accum: dict[int, SpeciesAccumulator],
) -> int:
    resolver = AncestorResolver(taxonomy)
    count = 0
    with open(annotations_path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            try:
                taxid = int(row["taxid"])
            except (KeyError, ValueError):
                continue
            species = resolver.resolve(taxid)
            if species is None:
                continue
            accum.setdefault(species, SpeciesAccumulator()).add_annotation(
                mrna_transcript=_float(row.get("mrna_transcript_count")),
                lncrna_transcript=_float(row.get("lncrna_transcript_count")),
                mrna_genes=_float(row.get("mrna_gene_count")),
                lncrna_genes=_float(row.get("lncrna_gene_count")),
            )
            count += 1
    return count


def aggregate_goat(
    taxonomy: TaxonomyDb,
    goat_path: Path,
    accum: dict[int, SpeciesAccumulator],
) -> int:
    resolver = AncestorResolver(taxonomy)
    count = 0
    with open(goat_path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            try:
                taxid = int(row["taxid"])
            except (KeyError, ValueError):
                continue
            species = resolver.resolve(taxid)
            if species is None:
                continue
            accum.setdefault(species, SpeciesAccumulator()).add_goat_status(
                row.get("sequencing_status")
            )
            count += 1
    return count
