#!/usr/bin/env python3
"""
Build a species matrix for all eukaryotic species with assemblies, annotations, and reads.

Fetches data from:
- NCBI datasets CLI: assemblies (genome_size, gc_content)
- ENA API: RNA-seq reads (tax_tree + library_strategy=rna-seq)
- Annotrieve API: genome annotations (genome.crg.es/annotrieve)

Output TSV: taxid | has_assembly | has_annotation | has_reads | genome_size | gc_content
"""

import json
import subprocess
import sys
from pathlib import Path

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

EUKARYOTA_TAXID = 2759
ENA_BASE = "https://www.ebi.ac.uk/ena/portal/api/search"
ANNOTRIEVE_BASE = "https://genome.crg.es/annotrieve/api/v0"


def _escape_tsv(val) -> str:
    """Escape for TSV output."""
    if val is None or val == "":
        return ""
    s = str(val).replace("\t", " ").replace("\n", " ").replace("\r", " ")
    return s


def fetch_assemblies_from_ncbi_datasets() -> dict:
    """
    Fetch eukaryotic assemblies via NCBI datasets CLI. Streams stdout line-by-line.
    Returns dict: taxid -> {genome_size, gc_content}
    """
    print("Fetching assemblies from NCBI datasets CLI...")
    try:
        proc = subprocess.Popen(
            [
                "datasets",
                "summary",
                "genome",
                "taxon",
                str(EUKARYOTA_TAXID),
                "--as-json-lines",
            ],
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
        sys.exit(1)

    result = {}
    try:
        for line in proc.stdout:
            line = line.rstrip("\n")
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            org = rec.get("organism") or {}
            tax_id = org.get("tax_id")
            if tax_id is None:
                continue
            tax_id = int(tax_id)
            stats = rec.get("assembly_stats") or {}
            genome_size = stats.get("total_sequence_length")
            if isinstance(genome_size, str):
                try:
                    genome_size = int(genome_size)
                except ValueError:
                    genome_size = None
            gc_content = stats.get("gc_percent")
            gs = genome_size if isinstance(genome_size, int) else 0
            prev_gs = result.get(tax_id, {}).get("genome_size") or 0
            if tax_id not in result or prev_gs < gs:
                result[tax_id] = {
                    "genome_size": genome_size,
                    "gc_content": gc_content,
                }
    finally:
        proc.wait()
        if proc.returncode != 0:
            stderr = proc.stderr.read() if proc.stderr else ""
            print(f"Error: datasets command failed ({proc.returncode}): {stderr}", file=sys.stderr)
            sys.exit(1)

    print(f"  Found assemblies for {len(result)} taxa")
    return result


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=60))
def _ena_search():
    """Query ENA portal API (POST) for RNA-seq reads. Limit=0 fetches all records in one request."""
    payload = {
        "result": "read_run",
        "query": f'tax_tree({EUKARYOTA_TAXID}) AND library_strategy="rna-seq"',
        "fields": "tax_id,scientific_name",
        "format": "tsv",
        "limit": 0,  # 0 = fetch all records in one request
    }
    r = requests.post(
        ENA_BASE,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=120,
        stream=True,
    )
    r.raise_for_status()
    tax_ids = []
    taxid_col = None
    for i, line in enumerate(r.iter_lines(decode_unicode=True)):
        if line is None:
            continue
        parts = line.split("\t")
        if i == 0:
            # Header: read accession, taxid, scientific name (column names may vary)
            for j, h in enumerate(parts):
                if h.lower() in ("taxid", "tax_id"):
                    taxid_col = j
                    break
            if taxid_col is None:
                taxid_col = 1  # fallback: taxid is typically 2nd column
            continue
        if taxid_col is not None and len(parts) > taxid_col:
            try:
                tax_ids.append(int(parts[taxid_col]))
            except (ValueError, TypeError):
                pass
    return tax_ids, len(tax_ids)


def fetch_ena_reads() -> set:
    """
    Fetch ENA RNA-seq reads. Returns set of taxids.
    Uses limit=0 to fetch all records in a single request.
    """
    print("Fetching ENA RNA-seq reads...")
    tax_ids, count = _ena_search()
    read_taxids = set(tax_ids)
    print(f"  Fetched {count} runs, {len(read_taxids)} unique taxa")
    return read_taxids


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=60))
def fetch_annotrieve_annotations() -> set:
    """
    Fetch Annotrieve taxids with annotations from /annotations/frequencies/taxid.
    Returns object {taxid: count}; keys are the taxids.
    """
    print("Fetching annotations from Annotrieve...")
    url = f"{ANNOTRIEVE_BASE}/annotations/frequencies/taxid"
    r = requests.get(url, headers={"Content-Type": "application/json"}, timeout=120)
    r.raise_for_status()
    data = r.json()
    taxids = set()
    for tid_str in data.keys():
        try:
            taxids.add(int(tid_str))
        except (ValueError, TypeError):
            pass
    print(f"  Found annotations for {len(taxids)} taxa")
    return taxids


def write_matrix(
    assemblies: dict,
    read_taxids: set,
    annot_taxids: set,
    out_path: Path,
) -> int:
    """Write species matrix to file, streaming rows without building full list."""
    all_taxids = sorted(set(assemblies.keys()) | read_taxids | annot_taxids)
    count = 0
    with open(out_path, "w") as f:
        f.write("taxid\thas_assembly\thas_annotation\thas_reads\tgenome_size\tgc_content\n")
        for taxid in all_taxids:
            asm = assemblies.get(taxid, {})
            has_assembly = "1" if taxid in assemblies else "0"
            has_annotation = "1" if taxid in annot_taxids else "0"
            has_reads = "1" if taxid in read_taxids else "0"
            genome_size = asm.get("genome_size") or ""
            gc_content = asm.get("gc_content") or ""
            f.write(
                f"{taxid}\t{has_assembly}\t{has_annotation}\t{has_reads}\t"
                f"{_escape_tsv(genome_size)}\t{_escape_tsv(gc_content)}\n"
            )
            count += 1
    return count


def main():
    repo_root = Path(__file__).parent.parent
    data_dir = repo_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    assemblies = fetch_assemblies_from_ncbi_datasets()
    read_taxids = fetch_ena_reads()
    annot_taxids = fetch_annotrieve_annotations()

    out_path = data_dir / "eukaryotic_species_matrix.tsv"
    print(f"Writing {out_path}...")
    count = write_matrix(assemblies, read_taxids, annot_taxids, out_path)

    print(f"Done. Wrote {count} species to {out_path}")
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
