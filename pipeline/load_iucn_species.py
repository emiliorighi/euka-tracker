"""Load IUCN simple_summary.csv rows."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from pipeline.schema import SIMPLE_SUMMARY_FIELDS


def _clean(value: str | None) -> str:
    return (value or "").strip()


@dataclass(frozen=True)
class IucnSpecies:
    assessment_id: str
    internal_taxon_id: str
    scientific_name: str
    kingdom_name: str
    phylum_name: str
    order_name: str
    class_name: str
    family_name: str
    genus_name: str
    species_name: str
    infra_type: str
    infra_name: str
    infra_authority: str
    authority: str
    redlist_category: str
    redlist_criteria: str
    criteria_version: str
    population_trend: str
    scopes: str

    def as_summary_dict(self) -> dict[str, str]:
        return {
            "assessmentId": self.assessment_id,
            "internalTaxonId": self.internal_taxon_id,
            "scientificName": self.scientific_name,
            "kingdomName": self.kingdom_name,
            "phylumName": self.phylum_name,
            "orderName": self.order_name,
            "className": self.class_name,
            "familyName": self.family_name,
            "genusName": self.genus_name,
            "speciesName": self.species_name,
            "infraType": self.infra_type,
            "infraName": self.infra_name,
            "infraAuthority": self.infra_authority,
            "authority": self.authority,
            "redlistCategory": self.redlist_category,
            "redlistCriteria": self.redlist_criteria,
            "criteriaVersion": self.criteria_version,
            "populationTrend": self.population_trend,
            "scopes": self.scopes,
        }

    @property
    def lineage_tokens(self) -> set[str]:
        tokens: set[str] = set()
        for value in (
            self.genus_name,
            self.family_name,
            self.order_name,
            self.class_name,
            self.phylum_name,
            self.kingdom_name,
        ):
            key = _clean(value).lower()
            if key:
                tokens.add(key)
        return tokens


def _row_to_species(row: dict[str, str]) -> IucnSpecies:
    return IucnSpecies(
        assessment_id=_clean(row.get("assessmentId")),
        internal_taxon_id=_clean(row.get("internalTaxonId")),
        scientific_name=_clean(row.get("scientificName")),
        kingdom_name=_clean(row.get("kingdomName")),
        phylum_name=_clean(row.get("phylumName")),
        order_name=_clean(row.get("orderName")),
        class_name=_clean(row.get("className")),
        family_name=_clean(row.get("familyName")),
        genus_name=_clean(row.get("genusName")),
        species_name=_clean(row.get("speciesName")),
        infra_type=_clean(row.get("infraType")),
        infra_name=_clean(row.get("infraName")),
        infra_authority=_clean(row.get("infraAuthority")),
        authority=_clean(row.get("authority")),
        redlist_category=_clean(row.get("redlistCategory")),
        redlist_criteria=_clean(row.get("redlistCriteria")),
        criteria_version=_clean(row.get("criteriaVersion")),
        population_trend=_clean(row.get("populationTrend")),
        scopes=_clean(row.get("scopes")),
    )


def iter_iucn_species(
    simple_summary_path: Path,
    *,
    limit: int | None = None,
) -> Iterator[IucnSpecies]:
    count = 0
    with open(simple_summary_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        missing = [field for field in SIMPLE_SUMMARY_FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"simple_summary.csv missing columns: {missing}")
        for row in reader:
            species = _row_to_species(row)
            if not species.internal_taxon_id:
                continue
            yield species
            count += 1
            if limit is not None and count >= limit:
                return


def load_iucn_species(
    simple_summary_path: Path,
    *,
    limit: int | None = None,
) -> list[IucnSpecies]:
    return list(iter_iucn_species(simple_summary_path, limit=limit))
