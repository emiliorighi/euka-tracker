"""NCBI name index (all taxonomy species) and genomic evidence index for IUCN resolution."""

from __future__ import annotations

import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path

from pipeline.match_keys import binom_key, norm_key
from pipeline.schema import READ_BUCKET_TO_FLAG, READ_COUNT_FIELDS
from pipeline.species_rollup import (
    SpeciesAccumulator,
    aggregate_annotations,
    aggregate_assemblies,
    aggregate_goat,
    aggregate_reads,
)
from pipeline.taxonomy_db import TaxonomyDb

DEFAULT_CACHE_SIZE = -262144


@dataclass
class SpeciesEvidence:
    has_goat: bool = False
    has_assemblies: bool = False
    has_annotations: bool = False
    read_flags: dict[str, bool] = field(default_factory=dict)

    def any_genomic(self) -> bool:
        return (
            self.has_goat
            or self.has_assemblies
            or self.has_annotations
            or any(self.read_flags.values())
        )


@dataclass
class NcbiNameIndex:
    name_to_sp: dict[str, int]
    binom_to_sp: dict[str, set[int]]
    lineage_by_taxid: dict[int, tuple[str, str, str, str, str]]


@dataclass
class NcbiEvidenceIndex:
    accum: dict[int, SpeciesAccumulator]
    evidence_by_taxid: dict[int, SpeciesEvidence]

    @property
    def genomic_species(self) -> set[int]:
        return set(self.accum.keys())


def _accum_to_evidence(accum: SpeciesAccumulator) -> SpeciesEvidence:
    read_flags = {
        READ_BUCKET_TO_FLAG[bucket]: accum.read_buckets.get(bucket, 0) > 0
        for bucket in READ_COUNT_FIELDS
    }
    return SpeciesEvidence(
        has_goat=accum.goat_ordinal > 0,
        has_assemblies=accum.assembly_count > 0,
        has_annotations=accum.annotation_count > 0,
        read_flags=read_flags,
    )


def _add_name_mapping(
    name_to_sp: dict[str, int],
    binom_to_sp: dict[str, set[int]],
    *,
    species_taxid: int,
    name: str,
) -> None:
    key = norm_key(name)
    if not key:
        return
    if key not in name_to_sp:
        name_to_sp[key] = species_taxid
    bk = binom_key(name)
    if bk:
        binom_to_sp.setdefault(bk, set()).add(species_taxid)


def build_ncbi_name_index(taxonomy: TaxonomyDb) -> NcbiNameIndex:
    print("Building NCBI name index from all taxonomy species...", file=sys.stderr)
    species_taxids = set(taxonomy.iter_species_taxids())
    print(f"  {len(species_taxids):,} species taxids", file=sys.stderr)

    name_to_sp: dict[str, int] = {}
    binom_to_sp: dict[str, set[int]] = {}
    for species_taxid, name in taxonomy.iter_names_for_taxids(species_taxids):
        _add_name_mapping(
            name_to_sp,
            binom_to_sp,
            species_taxid=species_taxid,
            name=name,
        )
    print(f"  {len(name_to_sp):,} normalized names, {len(binom_to_sp):,} binomial keys", file=sys.stderr)

    print("  building species lineage context...", file=sys.stderr)
    lineage_by_taxid = taxonomy.build_species_lineage_context()
    print(f"  {len(lineage_by_taxid):,} species with lineage context", file=sys.stderr)

    return NcbiNameIndex(
        name_to_sp=name_to_sp,
        binom_to_sp=binom_to_sp,
        lineage_by_taxid=lineage_by_taxid,
    )


def build_gbif_to_ncbi_bridge(cross_universe_path: Path) -> dict[int, int]:
    """Map GBIF accepted ids to NCBI species taxids (all cross_universe links, not genomic-only)."""
    conn = sqlite3.connect(cross_universe_path)
    conn.execute(f"PRAGMA cache_size={DEFAULT_CACHE_SIZE}")
    gbif_to_sp: dict[int, int] = {}

    for taxid, gid in conn.execute("SELECT taxid, gbif_id FROM gbif_ncbi_taxid"):
        gbif_to_sp.setdefault(int(gid), int(taxid))

    ott_sql = """
        SELECT DISTINCT n.taxid, g.gbif_id
        FROM ncbi_to_ott n
        INNER JOIN ott_to_gbif g ON g.ott_id = n.ott_id
    """
    for taxid, gid in conn.execute(ott_sql):
        gbif_to_sp.setdefault(int(gid), int(taxid))

    conn.close()
    print(f"  {len(gbif_to_sp):,} GBIF ids in bridge (direct + OTL join)", file=sys.stderr)
    return gbif_to_sp


def build_ncbi_evidence_index(
    datasets_dir: Path,
    *,
    taxonomy: TaxonomyDb | None = None,
) -> NcbiEvidenceIndex:
    taxonomy_path = datasets_dir / "taxonomy.db"
    owns_taxonomy = taxonomy is None
    taxonomy = taxonomy or TaxonomyDb(taxonomy_path)

    accum: dict[int, SpeciesAccumulator] = {}
    print("Aggregating GOAT...", file=sys.stderr)
    n_goat = aggregate_goat(taxonomy, datasets_dir / "goat_sequencing_status.tsv", accum)
    print(f"  {n_goat:,} GOAT rows -> {len(accum):,} species", file=sys.stderr)

    print("Aggregating assemblies...", file=sys.stderr)
    n_asm = aggregate_assemblies(taxonomy, datasets_dir / "ncbi_assemblies.tsv", accum)
    print(f"  {n_asm:,} assembly rows -> {len(accum):,} species", file=sys.stderr)

    print("Aggregating annotations...", file=sys.stderr)
    n_ann = aggregate_annotations(taxonomy, datasets_dir / "annotrieve_annotations.tsv", accum)
    print(f"  {n_ann:,} annotation rows -> {len(accum):,} species", file=sys.stderr)

    print("Aggregating ENA reads (streaming)...", file=sys.stderr)
    n_reads = aggregate_reads(taxonomy, datasets_dir / "ena_read_runs.tsv", accum)
    print(f"  {n_reads:,} read rows -> {len(accum):,} species", file=sys.stderr)

    evidence_by_taxid = {
        taxid: _accum_to_evidence(species_accum) for taxid, species_accum in accum.items()
    }

    if owns_taxonomy:
        taxonomy.close()

    return NcbiEvidenceIndex(accum=accum, evidence_by_taxid=evidence_by_taxid)
