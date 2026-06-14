#!/usr/bin/env python3
"""Taxon rollup aggregation from species matrix + tax_lineage."""

from __future__ import annotations

import csv
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pipeline.ncbi_taxonomy_fetch import EUKARYOTA_TAXID

READ_BUCKETS = ("wgs_long", "wgs_short", "rnaseq_long", "rnaseq_short")


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> int:
    n = _num(value)
    return int(n) if n is not None else 0

THREATENED_CATEGORIES = frozenset(
    {
        "vulnerable",
        "endangered",
        "critically endangered",
        "extinct in the wild",
    }
)

LINEAGE_COL = "tax_lineage"

# Canonical NCBI ranks for subtree node counters (exact rank match on self).
CANONICAL_RANKS: tuple[str, ...] = (
    "domain",
    "kingdom",
    "phylum",
    "class",
    "order",
    "family",
    "genus",
    "species",
)

RANK_NODE_TOTAL_COLS: tuple[str, ...] = tuple(f"{r}_nodes_total" for r in CANONICAL_RANKS)
RANK_NODE_WITH_DATA_COLS: tuple[str, ...] = tuple(
    f"{r}_nodes_with_data" for r in CANONICAL_RANKS
)
RANK_NODE_COLS: tuple[str, ...] = RANK_NODE_TOTAL_COLS + RANK_NODE_WITH_DATA_COLS

ROLLUP_EXTRA_COLUMNS: tuple[str, ...] = ("matrix_species_count",) + RANK_NODE_COLS


def _is_threatened(category: str | None) -> bool:
    if not category:
        return False
    key = category.strip().lower()
    return any(key == t or key.startswith(t) for t in THREATENED_CATEGORIES)


def _best_wgs_coverage(row: dict[str, Any]) -> float | None:
    vals = [_num(row.get("wgs_long_coverage")), _num(row.get("wgs_short_coverage"))]
    nums = [v for v in vals if v is not None]
    return max(nums) if nums else None


def matrix_row_to_taxon_facts(row: dict[str, Any]) -> dict[str, Any]:
    """Slim species facts for taxon rollups (true run counts, not rep base sums)."""
    bucket_counts = {b: _int(row.get(f"{b}_count")) for b in READ_BUCKETS}
    run_count = sum(bucket_counts.values())
    assembly_count = _int(row.get("assembly_count"))
    annotation_count = _int(row.get("annotation_count"))
    has_reads = run_count > 0
    has_assembly = assembly_count > 0
    has_annotation = annotation_count > 0
    redlist = (row.get("redlist_category") or "").strip()
    catalog_source = (row.get("catalog_source") or "catalog").strip().lower()
    in_catalog = catalog_source != "iucn_only"
    is_threatened = _is_threatened(redlist)
    is_dark_matter = in_catalog and has_reads and not has_assembly

    genome_size = _num(row.get("ref_assembly_total_sequence_length"))
    ungapped = _num(row.get("ref_assembly_total_ungapped_length"))
    scaffold_n50 = _num(row.get("ref_assembly_scaffold_n50"))
    gc_percent = _num(row.get("ref_assembly_gc_percent"))
    total_genes = _num(row.get("ref_annotation_total_genes_count"))
    busco_complete = _num(row.get("ref_annotation_busco_complete"))
    best_cov = _best_wgs_coverage(row)

    ungapped_fraction = (
        ungapped / genome_size if genome_size and ungapped and genome_size > 0 else None
    )

    return {
        "taxid": _int(row.get("taxid")),
        "run_count": run_count,
        "bucket_counts": bucket_counts,
        "assembly_count": assembly_count,
        "annotation_count": annotation_count,
        "has_reads": has_reads,
        "has_assembly": has_assembly,
        "has_annotation": has_annotation,
        "has_full_triple": has_reads and has_assembly and has_annotation,
        "has_iucn": bool(redlist),
        "is_threatened": is_threatened,
        "in_catalog": in_catalog,
        "is_iucn_only": not in_catalog,
        "is_dark_matter": is_dark_matter,
        "is_threatened_no_reads": is_threatened and run_count == 0,
        "is_threatened_dark_matter": is_threatened and is_dark_matter,
        "genome_size": genome_size,
        "gc_percent": gc_percent,
        "scaffold_n50": scaffold_n50,
        "ungapped_fraction": ungapped_fraction,
        "total_genes": total_genes,
        "busco_complete": busco_complete,
        "best_wgs_coverage": best_cov,
    }


@dataclass
class MeanAgg:
    total: float = 0.0
    n: int = 0

    def add(self, value: float | None) -> None:
        if value is None:
            return
        self.total += value
        self.n += 1

    def mean(self) -> float | None:
        return self.total / self.n if self.n else None


@dataclass
class RollupAgg:
    species_count_matrix: int = 0
    species_count_with_data: int = 0
    species_with_reads: int = 0
    species_with_assembly: int = 0
    species_with_annotation: int = 0
    species_full_triple: int = 0
    species_iucn_assessed: int = 0
    species_threatened: int = 0
    species_count_iucn_only: int = 0
    species_threatened_no_reads: int = 0
    species_threatened_dark_matter: int = 0
    sum_run_count: int = 0
    sum_assembly_count: int = 0
    sum_annotation_count: int = 0
    sum_bucket_counts: dict[str, int] = field(default_factory=lambda: {b: 0 for b in READ_BUCKETS})
    mean_genome_size: MeanAgg = field(default_factory=MeanAgg)
    mean_gc_percent: MeanAgg = field(default_factory=MeanAgg)
    mean_scaffold_n50: MeanAgg = field(default_factory=MeanAgg)
    mean_ungapped_fraction: MeanAgg = field(default_factory=MeanAgg)
    mean_total_genes: MeanAgg = field(default_factory=MeanAgg)
    mean_busco_complete: MeanAgg = field(default_factory=MeanAgg)
    mean_best_wgs_coverage: MeanAgg = field(default_factory=MeanAgg)

    def add(self, facts: dict[str, Any]) -> None:
        if facts["in_catalog"]:
            self.species_count_matrix += 1
            if facts["has_reads"] or facts["has_assembly"] or facts["has_annotation"]:
                self.species_count_with_data += 1
            if facts["has_reads"]:
                self.species_with_reads += 1
            if facts["has_assembly"]:
                self.species_with_assembly += 1
            if facts["has_annotation"]:
                self.species_with_annotation += 1
            if facts["has_full_triple"]:
                self.species_full_triple += 1

            self.sum_run_count += facts["run_count"]
            self.sum_assembly_count += facts["assembly_count"]
            self.sum_annotation_count += facts["annotation_count"]
            for b in READ_BUCKETS:
                self.sum_bucket_counts[b] += facts["bucket_counts"][b]

            self.mean_genome_size.add(facts["genome_size"])
            self.mean_gc_percent.add(facts["gc_percent"])
            self.mean_scaffold_n50.add(facts["scaffold_n50"])
            self.mean_ungapped_fraction.add(facts["ungapped_fraction"])
            self.mean_total_genes.add(facts["total_genes"])
            self.mean_busco_complete.add(facts["busco_complete"])
            self.mean_best_wgs_coverage.add(facts["best_wgs_coverage"])
        else:
            self.species_count_iucn_only += 1

        if facts["has_iucn"]:
            self.species_iucn_assessed += 1
        if facts["is_threatened"]:
            self.species_threatened += 1
        if facts["is_threatened_no_reads"]:
            self.species_threatened_no_reads += 1
        if facts["is_threatened_dark_matter"]:
            self.species_threatened_dark_matter += 1

    def to_row(self) -> dict[str, Any]:
        n_asm = self.mean_genome_size.n
        n_ann = self.mean_total_genes.n
        n_cov = self.mean_best_wgs_coverage.n
        matrix_n = self.species_count_matrix
        row: dict[str, Any] = {
            "species_count_matrix": matrix_n,
            "species_count_with_data": self.species_count_with_data,
            "species_with_reads": self.species_with_reads,
            "species_with_assembly": self.species_with_assembly,
            "species_with_annotation": self.species_with_annotation,
            "species_full_triple": self.species_full_triple,
            "species_iucn_assessed": self.species_iucn_assessed,
            "species_threatened": self.species_threatened,
            "species_count_iucn_only": self.species_count_iucn_only,
            "species_threatened_no_reads": self.species_threatened_no_reads,
            "species_threatened_dark_matter": self.species_threatened_dark_matter,
            "sum_run_count": self.sum_run_count,
            "sum_assembly_count": self.sum_assembly_count,
            "sum_annotation_count": self.sum_annotation_count,
        }
        for b in READ_BUCKETS:
            row[f"sum_{b}_count"] = self.sum_bucket_counts[b]
        row["mean_genome_size"] = self.mean_genome_size.mean()
        row["n_with_assembly"] = n_asm
        row["mean_gc_percent"] = self.mean_gc_percent.mean()
        row["mean_scaffold_n50"] = self.mean_scaffold_n50.mean()
        row["mean_ungapped_fraction"] = self.mean_ungapped_fraction.mean()
        row["mean_total_genes"] = self.mean_total_genes.mean()
        row["n_with_annotation"] = n_ann
        row["mean_busco_complete"] = self.mean_busco_complete.mean()
        row["mean_best_wgs_coverage"] = self.mean_best_wgs_coverage.mean()
        row["n_with_wgs_coverage"] = n_cov
        row["has_matrix_descendant"] = 1 if matrix_n > 0 else 0
        return row


LEAF_RANKS = frozenset({"species", "subspecies", "strain", "varietas", "forma"})

LANDSCAPE_SCATTER_FIELDS: list[str] = [
    "landscape_cx",
    "landscape_cy",
    "landscape_bbox_x0",
    "landscape_bbox_x1",
    "landscape_bbox_y0",
    "landscape_bbox_y1",
]

TAXON_ROLLUP_FIELDS: list[str] = [
    "taxid",
    "parent_taxid",
    "scientific_name",
    "rank",
    "depth_from_eukaryota",
    "species_count_ncbi",
    "species_count_with_data",
    "species_with_reads",
    "species_with_assembly",
    "species_with_annotations",
    "sum_run_count",
    "sum_assembly_count",
    "sum_annotation_count",
    *LANDSCAPE_SCATTER_FIELDS,
]


def parse_lineage(lineage: str) -> list[int]:
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


def accumulate_rollups_from_matrix(
    matrix_path: Path,
) -> tuple[dict[int, RollupAgg], int, int]:
    """Stream matrix with tax_lineage; return aggregators and stats."""
    rollups: dict[int, RollupAgg] = {}
    rows = 0
    skipped_no_lineage = 0

    with matrix_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        if not reader.fieldnames or LINEAGE_COL not in reader.fieldnames:
            raise ValueError(f"Matrix missing {LINEAGE_COL} column: {matrix_path}")

        for row in reader:
            rows += 1
            lineage_ids = parse_lineage(row.get(LINEAGE_COL) or "")
            if not lineage_ids:
                skipped_no_lineage += 1
                continue

            facts = matrix_row_to_taxon_facts(row)
            for taxid in lineage_ids:
                if taxid not in rollups:
                    rollups[taxid] = RollupAgg()
                rollups[taxid].add(facts)

    return rollups, rows, skipped_no_lineage


def ensure_rollup_schema(conn: sqlite3.Connection) -> None:
    """Add rollup columns to taxa table if missing (existing DB migration)."""
    existing = {
        row[1]
        for row in conn.execute("PRAGMA table_info(taxa)").fetchall()
    }
    for col in ROLLUP_EXTRA_COLUMNS:
        if col not in existing:
            conn.execute(f"ALTER TABLE taxa ADD COLUMN {col} INTEGER")
    conn.commit()


def sync_matrix_species_counts(
    conn: sqlite3.Connection,
    rollups: dict[int, RollupAgg],
) -> None:
    """Write per-taxon matrix species counts from RAM rollups to SQLite."""
    conn.execute("UPDATE taxa SET matrix_species_count = 0")
    batch: list[tuple[int, int]] = []
    for taxid, agg in rollups.items():
        if agg.species_count_matrix <= 0:
            continue
        batch.append((agg.species_count_matrix, taxid))
        if len(batch) >= 500:
            conn.executemany(
                "UPDATE taxa SET matrix_species_count = ? WHERE taxid = ?",
                batch,
            )
            batch.clear()
    if batch:
        conn.executemany(
            "UPDATE taxa SET matrix_species_count = ? WHERE taxid = ?",
            batch,
        )
    conn.commit()


def compute_rank_node_counts(conn: sqlite3.Connection) -> None:
    """
    Bottom-up subtree counters per canonical rank (disk-only, by depth).

    For each taxon N:
      {rank}_nodes_total = (1 if rank(N)==rank else 0) + sum over children
      {rank}_nodes_with_data = (1 if rank(N)==rank and matrix_species_count>0 else 0) + sum
    """
    zero_assign = ", ".join(f"{col} = 0" for col in RANK_NODE_COLS)
    conn.execute(f"UPDATE taxa SET {zero_assign}")

    row = conn.execute("SELECT MAX(depth) FROM taxa WHERE depth IS NOT NULL").fetchone()
    if row is None or row[0] is None:
        conn.commit()
        return
    max_depth = int(row[0])

    set_clauses: list[str] = []
    for rank in CANONICAL_RANKS:
        total_col = f"{rank}_nodes_total"
        data_col = f"{rank}_nodes_with_data"
        set_clauses.append(
            f"{total_col} = (CASE WHEN rank = '{rank}' THEN 1 ELSE 0 END)"
            f" + (SELECT COALESCE(SUM({total_col}), 0) FROM taxa AS c"
            f" WHERE c.parent_taxid = taxa.taxid)"
        )
        set_clauses.append(
            f"{data_col} = (CASE WHEN rank = '{rank}' AND matrix_species_count > 0 THEN 1 ELSE 0 END)"
            f" + (SELECT COALESCE(SUM({data_col}), 0) FROM taxa AS c"
            f" WHERE c.parent_taxid = taxa.taxid)"
        )

    update_sql = f"UPDATE taxa SET {', '.join(set_clauses)} WHERE depth = ?"

    for d in range(max_depth, -1, -1):
        conn.execute(update_sql, (d,))

    conn.commit()


def assign_depths(conn: sqlite3.Connection, root: int = EUKARYOTA_TAXID) -> int:
    """BFS depth assignment from root. Returns max depth."""
    conn.execute("UPDATE taxa SET depth = NULL")
    row = conn.execute("SELECT 1 FROM taxa WHERE taxid = ?", (root,)).fetchone()
    if row is None:
        return 0

    conn.execute("UPDATE taxa SET depth = 0 WHERE taxid = ?", (root,))
    frontier = [root]
    current_depth = 0
    max_depth = 0

    while frontier:
        current_depth += 1
        next_frontier: list[int] = []
        for i in range(0, len(frontier), 500):
            chunk = frontier[i : i + 500]
            placeholders = ",".join("?" * len(chunk))
            rows = conn.execute(
                f"SELECT taxid FROM taxa WHERE parent_taxid IN ({placeholders}) AND depth IS NULL",
                chunk,
            ).fetchall()
            next_frontier.extend(int(r[0]) for r in rows)

        if not next_frontier:
            break

        conn.executemany(
            "UPDATE taxa SET depth = ? WHERE taxid = ?",
            [(current_depth, t) for t in next_frontier],
        )
        max_depth = current_depth
        frontier = next_frontier

    conn.commit()
    return max_depth


def compute_species_counts_ncbi(conn: sqlite3.Connection) -> None:
    """Bottom-up species_count_ncbi by depth (rank=species only)."""
    conn.execute("UPDATE taxa SET species_count_ncbi = NULL")
    row = conn.execute("SELECT MAX(depth) FROM taxa WHERE depth IS NOT NULL").fetchone()
    if row is None or row[0] is None:
        return
    max_depth = int(row[0])

    for d in range(max_depth, -1, -1):
        conn.execute(
            """
            UPDATE taxa
            SET species_count_ncbi =
              (CASE WHEN rank = 'species' THEN 1 ELSE 0 END)
              + (SELECT COALESCE(SUM(species_count_ncbi), 0)
                 FROM taxa AS c WHERE c.parent_taxid = taxa.taxid)
            WHERE depth = ?
            """,
            (d,),
        )
    conn.commit()


def fetch_taxon_meta(conn: sqlite3.Connection, taxids: list[int]) -> dict[int, dict[str, Any]]:
    """Batch-fetch identity + NCBI counts for taxids."""
    if not taxids:
        return {}
    result: dict[int, dict[str, Any]] = {}
    for i in range(0, len(taxids), 500):
        chunk = taxids[i : i + 500]
        placeholders = ",".join("?" * len(chunk))
        rank_cols = ", ".join(RANK_NODE_COLS)
        rows = conn.execute(
            f"""
            SELECT taxid, parent_taxid, name, rank, depth, species_count_ncbi,
                   {rank_cols}
            FROM taxa WHERE taxid IN ({placeholders})
            """,
            chunk,
        ).fetchall()
        for row in rows:
            taxid = int(row[0])
            meta: dict[str, Any] = {
                "parent_taxid": int(row[1]),
                "scientific_name": row[2] or "",
                "rank": row[3] or "",
                "depth_from_eukaryota": row[4] if row[4] is not None else "",
                "species_count_ncbi": row[5] if row[5] is not None else 0,
            }
            for i, col in enumerate(RANK_NODE_COLS, start=6):
                meta[col] = row[i] if row[i] is not None else 0
            result[taxid] = meta
    return result


def _fmt_val(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, float):
        if value != value:  # NaN
            return ""
        if value == int(value):
            return str(int(value))
        return f"{value:.6g}"
    return str(value)


def _pct(matrix_n: int, ncbi_n: int) -> str:
    if ncbi_n <= 0:
        return ""
    return f"{matrix_n / ncbi_n:.6f}"


def _prune_orphans_after_leaf_filter(
    taxids: set[int],
    meta: dict[int, dict[str, Any]],
    in_scope: frozenset[int],
) -> set[int]:
    """Drop nodes whose parent is in rollup scope but excluded (e.g. filtered leaf rank)."""
    ids = set(taxids)
    while True:
        remove: set[int] = set()
        for tid in ids:
            pid = int(meta.get(tid, {}).get("parent_taxid") or 0)
            if pid and pid in in_scope and pid not in ids:
                remove.add(tid)
        if not remove:
            break
        ids -= remove
    return ids


def emit_rollup_tsv(
    conn: sqlite3.Connection,
    rollups: dict[int, RollupAgg],
    output_path: Path,
) -> int:
    """Write induced taxon rollup TSV (slim columns, internal nodes only)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    induced = sorted(rollups.keys())
    meta = fetch_taxon_meta(conn, induced)
    in_scope = frozenset(rollups.keys())
    emit_ids: set[int] = set()
    for taxid in induced:
        rank = (meta.get(taxid, {}).get("rank") or "").strip().lower()
        if rank in LEAF_RANKS:
            continue
        emit_ids.add(taxid)
    emit_ids = _prune_orphans_after_leaf_filter(emit_ids, meta, in_scope)
    written = 0

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TAXON_ROLLUP_FIELDS, delimiter="\t", extrasaction="ignore")
        writer.writeheader()

        for taxid in sorted(emit_ids):
            m = meta.get(taxid, {})
            agg = rollups[taxid]
            agg_row = agg.to_row()
            ncbi_n = int(m.get("species_count_ncbi") or 0)

            out_row: dict[str, Any] = {
                "taxid": taxid,
                "parent_taxid": m.get("parent_taxid", ""),
                "scientific_name": m.get("scientific_name", ""),
                "rank": m.get("rank", ""),
                "depth_from_eukaryota": m.get("depth_from_eukaryota", ""),
                "species_count_ncbi": ncbi_n,
                "species_count_with_data": agg_row["species_count_with_data"],
                "species_with_reads": agg_row["species_with_reads"],
                "species_with_assembly": agg_row["species_with_assembly"],
                "species_with_annotations": agg_row["species_with_annotation"],
                "sum_run_count": agg_row["sum_run_count"],
                "sum_assembly_count": agg_row["sum_assembly_count"],
                "sum_annotation_count": agg_row["sum_annotation_count"],
                **{field: "" for field in LANDSCAPE_SCATTER_FIELDS},
            }
            writer.writerow({k: _fmt_val(out_row.get(k)) for k in TAXON_ROLLUP_FIELDS})
            written += 1

    return written


def iter_spot_check(conn: sqlite3.Connection, taxid: int) -> dict[str, Any] | None:
    rank_cols = ", ".join(RANK_NODE_COLS)
    row = conn.execute(
        f"""
        SELECT taxid, name, rank, species_count_ncbi, depth, matrix_species_count,
               {rank_cols}
        FROM taxa WHERE taxid = ?
        """,
        (taxid,),
    ).fetchone()
    if not row:
        return None
    out: dict[str, Any] = {
        "taxid": row[0],
        "name": row[1],
        "rank": row[2],
        "species_count_ncbi": row[3],
        "depth": row[4],
        "matrix_species_count": row[5],
    }
    for i, col in enumerate(RANK_NODE_COLS, start=6):
        out[col] = row[i]
    return out
