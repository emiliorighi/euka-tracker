#!/usr/bin/env python3
"""NCBI Datasets assembly export for eukaryotes (taxon 2759) → TSV."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterator

EUKARYOTA_TAXID = 2759

ASSEMBLY_FIELDS = [
    "accession",
    "assembly_name",
    "taxid",
    "assembly_level",
    "assembly_source",
    "release_date",
    "bioproject_accession",
    "gc_percent",
    "atgc_count",
    "contig_n50",
    "contig_l50",
    "scaffold_n50",
    "scaffold_l50",
    "total_sequence_length",
    "total_ungapped_length",
    "total_number_of_chromosomes",
]


def _normalize_assembly_level(level: str | None) -> str:
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


def _assembly_source_from_accession(accession: str) -> str:
    if accession.upper().startswith("GCF"):
        return "refseq"
    if accession.upper().startswith("GCA"):
        return "genbank"
    return ""


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def eukaryote_assembly_datasets_cmd() -> list[str]:
    return [
        "datasets",
        "summary",
        "genome",
        "taxon",
        str(EUKARYOTA_TAXID),
        "--as-json-lines",
    ]


def parse_assembly_record(rec: dict[str, Any]) -> dict[str, Any] | None:
    accession = rec.get("accession")
    org = rec.get("organism") or {}
    taxid = org.get("tax_id")
    if not accession or taxid is None:
        return None

    assembly_info = rec.get("assembly_info") or {}
    stats = rec.get("assembly_stats") or {}
    level = _normalize_assembly_level(assembly_info.get("assembly_level"))
    source = _assembly_source_from_accession(accession)
    if not source:
        db = str(rec.get("source_database") or rec.get("assembly_source") or "").lower()
        if "refseq" in db:
            source = "refseq"
        elif "genbank" in db:
            source = "genbank"

    return {
        "accession": accession,
        "assembly_name": assembly_info.get("assembly_name") or "",
        "taxid": int(taxid),
        "assembly_level": level,
        "assembly_source": source,
        "release_date": assembly_info.get("release_date") or "",
        "bioproject_accession": assembly_info.get("bioproject_accession") or "",
        "gc_percent": _as_float(stats.get("gc_percent")),
        "atgc_count": _as_int(stats.get("atgc_count")),
        "contig_n50": _as_int(stats.get("contig_n50")),
        "contig_l50": _as_int(stats.get("contig_l50")),
        "scaffold_n50": _as_int(stats.get("scaffold_n50")),
        "scaffold_l50": _as_int(stats.get("scaffold_l50")),
        "total_number_of_chromosomes": _as_int(stats.get("total_number_of_chromosomes")),
        "total_sequence_length": _as_int(stats.get("total_sequence_length")),
        "total_ungapped_length": _as_int(stats.get("total_ungapped_length")),
    }


def iter_eukaryote_assemblies() -> Iterator[dict[str, Any]]:
    try:
        proc = subprocess.Popen(
            eukaryote_assembly_datasets_cmd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError:
        print(
            "Error: NCBI datasets CLI not found. Install from: "
            "https://www.ncbi.nlm.nih.gov/datasets/docs/v2/command-line-tools/download-and-install/",
            file=sys.stderr,
        )
        raise

    assert proc.stdout is not None
    try:
        for line in proc.stdout:
            line = line.rstrip("\n")
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            row = parse_assembly_record(rec)
            if row is not None:
                yield row
    finally:
        proc.wait()
        if proc.returncode != 0:
            stderr = proc.stderr.read() if proc.stderr else ""
            raise RuntimeError(f"datasets command failed ({proc.returncode}): {stderr}")


def write_eukaryote_assemblies_tsv(out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    print(f"Fetching assemblies via datasets CLI...", file=sys.stderr)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ASSEMBLY_FIELDS, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in iter_eukaryote_assemblies():
            writer.writerow(row)
            count += 1
            if count % 10_000 == 0:
                print(f"  … {count:,} assemblies", file=sys.stderr)
    print(f"Wrote {count:,} assemblies to {out_path}", file=sys.stderr)
    return count


def _repo_datasets_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "datasets"


def fetch_assemblies(datasets_dir: Path, *, force: bool = False) -> Path:
    out_path = datasets_dir / "ncbi_assemblies.tsv"
    if out_path.is_file() and not force:
        print(f"Using cached {out_path}", file=sys.stderr)
        return out_path
    write_eukaryote_assemblies_tsv(out_path)
    return out_path


if __name__ == "__main__":
    import argparse

    repo = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Export eukaryotic NCBI assemblies")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=repo / "datasets" / "ncbi_assemblies.tsv",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.force or not args.output.is_file():
        write_eukaryote_assemblies_tsv(args.output)
    else:
        print(f"Using cached {args.output}", file=sys.stderr)
