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

EUKARYOTE_ASSEMBLY_FIELDS = [
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


def eukaryote_assembly_datasets_cmd() -> list[str]:
    """CLI command for `datasets summary genome taxon 2759`."""
    return [
        "datasets",
        "summary",
        "genome",
        "taxon",
        str(EUKARYOTA_TAXID),
        "--as-json-lines",
    ]


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


def parse_assembly_record(rec: dict[str, Any]) -> dict[str, Any] | None:
    """Map NCBI datasets JSON line to TSV row dict."""
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
    """Stream eukaryotic assemblies from NCBI datasets CLI (one row per assembly)."""
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
            raise RuntimeError(
                f"datasets command failed ({proc.returncode}): {stderr}"
            )


def iter_eukaryote_assemblies_tsv(path: Path) -> Iterator[dict[str, Any]]:
    """Stream assemblies from a staged TSV file."""
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row.get("taxid"):
                try:
                    row["taxid"] = int(row["taxid"])
                except ValueError:
                    continue
                yield row


def write_eukaryote_assemblies_tsv(out_path: Path) -> int:
    """Fetch all eukaryotic assemblies and write TSV. Returns row count."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=EUKARYOTE_ASSEMBLY_FIELDS, delimiter="\t", extrasaction="ignore"
        )
        writer.writeheader()
        for row in iter_eukaryote_assemblies():
            writer.writerow({k: "" if row.get(k) is None else row[k] for k in EUKARYOTE_ASSEMBLY_FIELDS})
            count += 1
    return count


if __name__ == "__main__":
    import argparse

    repo_root = Path(__file__).resolve().parent.parent
    default_out = repo_root / "data" / "staged" / "02_ncbi_assemblies.tsv"

    parser = argparse.ArgumentParser(
        description="Export eukaryotic genome assemblies from NCBI Datasets to TSV"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=default_out,
        help=f"Output TSV path (default: {default_out})",
    )
    args = parser.parse_args()

    print(f"Command: {' '.join(eukaryote_assembly_datasets_cmd())}", file=sys.stderr)
    print(f"Fields: {','.join(EUKARYOTE_ASSEMBLY_FIELDS)}", file=sys.stderr)
    n = write_eukaryote_assemblies_tsv(args.output)
    print(f"Wrote {n} assemblies to {args.output}", file=sys.stderr)
