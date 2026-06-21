"""Build IUCN taxon rollups TSV from species matrix (IUCN rank hierarchy)."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from pipeline.iucn_taxonomy import RANK_DEPTH, iter_iucn_path
from pipeline.schema import (
    IUCN_CATEGORY_CODES,
    IUCN_CATEGORY_COUNT_FIELDS,
    IUCN_ROLLUP_FIELDS,
    READ_FLAG_FIELDS,
    normalize_redlist_category,
)

PIPELINE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = PIPELINE_DIR / "output" / "iucn_species_matrix.tsv"
DEFAULT_OUTPUT = PIPELINE_DIR / "output" / "iucn_taxon_rollups.tsv"

CATEGORY_CODE_TO_FIELD = {
    code: f"speciesCount{suffix}" for code, suffix in IUCN_CATEGORY_CODES.items()
}

DATASET_FLAG_MAP = {
    "speciesCountGbif": "hasGbif",
    "speciesCountInat": "hasInat",
    "speciesCountGoat": "hasGoat",
    "speciesCountAssemblies": "hasAssemblies",
    "speciesCountAnnotations": "hasAnnotations",
}

BUCKET_FLAG_MAP = {
    count_field: flag_field
    for count_field, flag_field in zip(
        tuple(f.replace("has", "speciesCount", 1) for f in READ_FLAG_FIELDS),
        READ_FLAG_FIELDS,
        strict=True,
    )
}


@dataclass
class RollupNode:
    taxon_key: str
    taxon_name: str
    rank: str
    parent_taxon_key: str
    species_count_total: int = 0
    category_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    dataset_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    bucket_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def to_row(self) -> dict[str, str]:
        row: dict[str, str] = {
            "taxonKey": self.taxon_key,
            "taxonName": self.taxon_name,
            "rank": self.rank,
            "parentTaxonKey": self.parent_taxon_key,
            "speciesCountTotal": str(self.species_count_total),
        }
        for field_name in IUCN_CATEGORY_COUNT_FIELDS:
            code_key = next(
                (c for c, f in CATEGORY_CODE_TO_FIELD.items() if f == field_name),
                "",
            )
            row[field_name] = str(self.category_counts.get(code_key, 0))
        for field_name in DATASET_FLAG_MAP:
            row[field_name] = str(self.dataset_counts.get(field_name, 0))
        for field_name in BUCKET_FLAG_MAP:
            row[field_name] = str(self.bucket_counts.get(field_name, 0))
        return row


def _flag_true(row: dict[str, str], field: str) -> bool:
    return row.get(field, "0").strip() in ("1", "true", "True")


def _accumulate_row(nodes: dict[str, RollupNode], row: dict[str, str]) -> None:
    category = normalize_redlist_category(row.get("redlistCategory"))
    has_ncbi = bool(row.get("ncbiTaxid", "").strip())

    for rank, name, key, parent_key in iter_iucn_path(row):
        node = nodes.get(key)
        if node is None:
            node = RollupNode(
                taxon_key=key,
                taxon_name=name,
                rank=rank,
                parent_taxon_key=parent_key,
            )
            nodes[key] = node

        node.species_count_total += 1
        if category:
            node.category_counts[category] += 1

        if _flag_true(row, "hasGbif"):
            node.dataset_counts["speciesCountGbif"] += 1
        if _flag_true(row, "hasInat"):
            node.dataset_counts["speciesCountInat"] += 1
        if has_ncbi:
            node.dataset_counts["speciesCountNcbi"] += 1
        for count_field, flag_field in DATASET_FLAG_MAP.items():
            if count_field in ("speciesCountGbif", "speciesCountInat"):
                continue
            if _flag_true(row, flag_field):
                node.dataset_counts[count_field] += 1

        for count_field, flag_field in BUCKET_FLAG_MAP.items():
            if _flag_true(row, flag_field):
                node.bucket_counts[count_field] += 1


def build_taxon_rollups(
    *,
    matrix_path: Path = DEFAULT_MATRIX,
    output_path: Path = DEFAULT_OUTPUT,
) -> Path:
    if not matrix_path.is_file():
        raise FileNotFoundError(f"Matrix not found: {matrix_path}")

    nodes: dict[str, RollupNode] = {}
    species_rows = 0

    with open(matrix_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            _accumulate_row(nodes, row)
            species_rows += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sorted_nodes = sorted(
        nodes.values(),
        key=lambda n: (RANK_DEPTH.get(n.rank, 99), n.taxon_name.lower(), n.taxon_key),
    )

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(IUCN_ROLLUP_FIELDS), delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for node in sorted_nodes:
            writer.writerow(node.to_row())

    print(
        f"Wrote {output_path} ({len(sorted_nodes):,} taxon nodes from {species_rows:,} species)",
        file=sys.stderr,
    )
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build IUCN taxon rollups TSV")
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build_taxon_rollups(matrix_path=args.matrix, output_path=args.output)


if __name__ == "__main__":
    main()
