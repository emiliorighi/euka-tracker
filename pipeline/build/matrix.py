"""Build IUCN-centric species matrix with cross-universe and genomic flags."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

from pipeline.iucn_resolver import IucnResolver, ResolvedIucnSpecies
from pipeline.load_iucn_species import IucnSpecies, iter_iucn_species
from pipeline.schema import COUNT_FLAG_FIELDS, IUCN_MATRIX_FIELDS
from pipeline.ncbi_evidence import (
    build_gbif_to_ncbi_bridge,
    build_ncbi_evidence_index,
    build_ncbi_name_index,
)
from pipeline.taxonomy_db import TaxonomyDb

PIPELINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PIPELINE_DIR.parent
DEFAULT_DATASETS_DIR = REPO_ROOT / "datasets"
DEFAULT_OUTPUT_DIR = PIPELINE_DIR / "output"


def _escape_tsv(value: object) -> str:
    if value is None or value == "":
        return ""
    return str(value).replace("\t", " ").replace("\n", " ").replace("\r", " ")


def _matrix_row(species: IucnSpecies, resolved: ResolvedIucnSpecies) -> dict[str, str]:
    row = species.as_summary_dict()
    row.update(resolved.flag_dict())
    return row


def _update_flag_counts(counters: dict[str, Counter[str]], row: dict[str, str]) -> None:
    for field in COUNT_FLAG_FIELDS:
        if field == "hasNcbi":
            value = "1" if row.get("ncbiTaxid", "").strip() else "0"
        else:
            value = row.get(field, "0")
        counters[field][value] += 1


def write_flag_counts(
    counters: dict[str, Counter[str]],
    out_path: Path,
    *,
    total_rows: int,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["flag", "value", "count", "pct"],
            delimiter="\t",
        )
        writer.writeheader()
        for field in COUNT_FLAG_FIELDS:
            for value in ("1", "0"):
                count = counters[field].get(value, 0)
                pct = (100.0 * count / total_rows) if total_rows else 0.0
                writer.writerow(
                    {
                        "flag": field,
                        "value": value,
                        "count": count,
                        "pct": f"{pct:.2f}",
                    }
                )


def print_flag_counts(counters: dict[str, Counter[str]], *, total_rows: int) -> None:
    print(f"\nFlag counts ({total_rows:,} IUCN species):", file=sys.stderr)
    for field in COUNT_FLAG_FIELDS:
        true_count = counters[field].get("1", 0)
        false_count = counters[field].get("0", 0)
        pct = (100.0 * true_count / total_rows) if total_rows else 0.0
        print(f"  {field}: true={true_count:,} false={false_count:,} ({pct:.1f}%)", file=sys.stderr)


def build_iucn_matrix(
    *,
    datasets_dir: Path = DEFAULT_DATASETS_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    limit: int | None = None,
) -> tuple[Path, Path]:
    simple_summary_path = datasets_dir / "simple_summary.csv"
    cross_universe_path = datasets_dir / "cross_universe.db"
    taxonomy_path = datasets_dir / "taxonomy.db"
    matrix_path = output_dir / "iucn_species_matrix.tsv"
    counts_path = output_dir / "iucn_flag_counts.tsv"

    for required in (simple_summary_path, cross_universe_path, taxonomy_path):
        if not required.is_file():
            raise FileNotFoundError(f"Missing required dataset: {required}")

    output_dir.mkdir(parents=True, exist_ok=True)

    with TaxonomyDb(taxonomy_path) as taxonomy:
        name_index = build_ncbi_name_index(taxonomy)
        evidence = build_ncbi_evidence_index(datasets_dir, taxonomy=taxonomy)

    print("Building GBIF -> NCBI bridge...", file=sys.stderr)
    gbif_to_ncbi = build_gbif_to_ncbi_bridge(cross_universe_path)
    print(f"  {len(gbif_to_ncbi):,} GBIF ids mapped to NCBI species", file=sys.stderr)

    counters: dict[str, Counter[str]] = {field: Counter() for field in COUNT_FLAG_FIELDS}
    row_count = 0

    with IucnResolver(cross_universe_path, name_index, evidence, gbif_to_ncbi) as resolver:
        with open(matrix_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=list(IUCN_MATRIX_FIELDS),
                delimiter="\t",
                extrasaction="ignore",
            )
            writer.writeheader()
            for idx, species in enumerate(iter_iucn_species(simple_summary_path, limit=limit), start=1):
                resolved = resolver.resolve(species)
                row = _matrix_row(species, resolved)
                writer.writerow({k: _escape_tsv(row.get(k, "")) for k in IUCN_MATRIX_FIELDS})
                _update_flag_counts(counters, row)
                row_count += 1
                if idx % 25_000 == 0:
                    print(f"  … {idx:,} IUCN species resolved", file=sys.stderr)

    write_flag_counts(counters, counts_path, total_rows=row_count)
    print_flag_counts(counters, total_rows=row_count)
    print(f"\nWrote {matrix_path} ({row_count:,} rows)", file=sys.stderr)
    print(f"Wrote {counts_path}", file=sys.stderr)
    return matrix_path, counts_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build IUCN-centric species matrix.")
    parser.add_argument(
        "--datasets-dir",
        type=Path,
        default=DEFAULT_DATASETS_DIR,
        help="Directory containing simple_summary.csv and genomic datasets",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for matrix and flag count outputs",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N IUCN species (for smoke tests)",
    )
    args = parser.parse_args()
    build_iucn_matrix(
        datasets_dir=args.datasets_dir,
        output_dir=args.output_dir,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
