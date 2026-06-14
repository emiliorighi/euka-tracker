#!/usr/bin/env python3
"""Phylum-anchored clade study-gap layout for scatter x/y coordinates."""

from __future__ import annotations

import csv
import math
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

GOLDEN_ANGLE = math.pi * (3.0 - math.sqrt(5.0))
# Variable phylum neighborhood radius (species count → disc size).
MIN_PHYLUM_R = 8.0
MAX_PHYLUM_R = 68.0
# Fraction of phylum disc used by the normalized pack cloud.
LOCAL_FILL = 0.88
DISC_GAP = 3.0
# Small top-right drift for well-studied phyla within each neighborhood.
STUDY_NUDGE = 12.0
NORM_TARGET = 250.0
UNKNOWN_PHYLUM_TAXID = 0
UNKNOWN_PHYLUM_NAME = "Unknown"


@dataclass(frozen=True)
class PhylumRollup:
    taxid: int
    name: str
    species_count_matrix: int
    species_count_ncbi: int
    pct_ncbi_species_with_data: float


@dataclass(frozen=True)
class StudyLayoutResult:
    coords: dict[int, tuple[float, float]]
    pack_coords: dict[int, tuple[float, float]]
    phylum_by_species: dict[int, tuple[int, str]]
    phylum_study: dict[int, float]
    view_extent: dict[str, list[float]]


def _study_score(matrix_n: int, ncbi_n: int) -> float:
    if ncbi_n <= 0:
        return 0.0
    return math.log1p(max(matrix_n, 0)) / math.log1p(ncbi_n)


def load_phylum_rollups(rollups_path: Path) -> dict[int, PhylumRollup]:
    """Load phylum rows from a full legacy rollup TSV (requires ``species_count_matrix``).

    ``species_count_matrix`` counts catalog species (``in_catalog``, i.e. not iucn-only).
    It is **not** ``species_with_reads + species_with_assembly + species_with_annotations``
    nor reads plus IUCN-assessed counts — slim 12-column rollups omit this field.
    """
    out: dict[int, PhylumRollup] = {}
    if not rollups_path.is_file():
        return out
    with rollups_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        if not reader.fieldnames or "species_count_matrix" not in reader.fieldnames:
            return out
        for row in reader:
            if (row.get("rank") or "").strip().lower() != "phylum":
                continue
            try:
                taxid = int(row["taxid"])
            except (KeyError, ValueError):
                continue
            matrix_n = int(float(row.get("species_count_matrix") or 0))
            ncbi_n = int(float(row.get("species_count_ncbi") or 0))
            pct_raw = row.get("pct_ncbi_species_with_data")
            if pct_raw not in (None, ""):
                pct = float(pct_raw)
            else:
                pct = (matrix_n / ncbi_n) if ncbi_n > 0 else 0.0
            out[taxid] = PhylumRollup(
                taxid=taxid,
                name=(row.get("scientific_name") or "").strip(),
                species_count_matrix=matrix_n,
                species_count_ncbi=ncbi_n,
                pct_ncbi_species_with_data=pct,
            )
    return out


def load_phylum_rollups_from_db(db_path: Path) -> dict[int, PhylumRollup]:
    """Load phylum catalog counts from taxonomy.sqlite (``matrix_species_count`` + NCBI totals).

    Study-map phylum scores must use this (or legacy TSV ``species_count_matrix``), not a
    sum of slim TSV ``species_with_*`` columns — those measure data coverage, not catalog size.
    """
    out: dict[int, PhylumRollup] = {}
    if not db_path.is_file():
        return out
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            """
            SELECT taxid, name, species_count_ncbi, matrix_species_count
            FROM taxa
            WHERE lower(rank) = 'phylum'
            """
        ).fetchall()
        for taxid, name, ncbi_n, matrix_n in rows:
            matrix_n = int(matrix_n or 0)
            ncbi_n = int(ncbi_n or 0)
            pct = (matrix_n / ncbi_n) if ncbi_n > 0 else 0.0
            out[int(taxid)] = PhylumRollup(
                taxid=int(taxid),
                name=(name or "").strip(),
                species_count_matrix=matrix_n,
                species_count_ncbi=ncbi_n,
                pct_ncbi_species_with_data=pct,
            )
    finally:
        conn.close()
    return out


def load_taxid_ranks(db_path: Path, taxids: set[int]) -> dict[int, str]:
    """Batch-load rank for taxids from taxonomy.sqlite."""
    if not taxids:
        return {}
    conn = sqlite3.connect(db_path)
    try:
        ranks: dict[int, str] = {}
        batch = list(taxids)
        chunk_size = 900
        for i in range(0, len(batch), chunk_size):
            chunk = batch[i : i + chunk_size]
            placeholders = ",".join("?" * len(chunk))
            rows = conn.execute(
                f"SELECT taxid, rank FROM taxa WHERE taxid IN ({placeholders})",
                chunk,
            ).fetchall()
            for taxid, rank in rows:
                ranks[int(taxid)] = (rank or "").strip().lower()
        return ranks
    finally:
        conn.close()


def resolve_phylum_from_lineage(
    lineage: list[int],
    ranks: dict[int, str],
) -> tuple[int, str]:
    """Return deepest phylum ancestor (root→tip walk)."""
    phylum_taxid = UNKNOWN_PHYLUM_TAXID
    for taxid in lineage:
        if ranks.get(taxid) == "phylum":
            phylum_taxid = taxid
    return phylum_taxid, ""


def resolve_phylum_names(
    phylum_taxids: set[int],
    rollups: dict[int, PhylumRollup],
    db_path: Path,
) -> dict[int, str]:
    """Resolve phylum scientific names from rollups or taxonomy.sqlite."""
    names: dict[int, str] = {}
    missing: set[int] = set()
    for tid in phylum_taxids:
        if tid == UNKNOWN_PHYLUM_TAXID:
            names[tid] = UNKNOWN_PHYLUM_NAME
            continue
        if tid in rollups and rollups[tid].name:
            names[tid] = rollups[tid].name
        else:
            missing.add(tid)
    if missing and db_path.is_file():
        conn = sqlite3.connect(db_path)
        try:
            batch = list(missing)
            placeholders = ",".join("?" * len(batch))
            rows = conn.execute(
                f"SELECT taxid, name FROM taxa WHERE taxid IN ({placeholders})",
                batch,
            ).fetchall()
            for taxid, name in rows:
                names[int(taxid)] = (name or "").strip()
        finally:
            conn.close()
    for tid in missing:
        names.setdefault(tid, f"Phylum {tid}")
    return names


def _phylum_disc_radius(member_count: int, max_count: int) -> float:
    """Map species count to neighborhood disc radius (PubMed-style blob size)."""
    if max_count <= 0:
        return MIN_PHYLUM_R
    t = math.sqrt(math.log1p(member_count) / math.log1p(max_count))
    return MIN_PHYLUM_R + (MAX_PHYLUM_R - MIN_PHYLUM_R) * t


def _pack_phylum_discs(
    phylum_radii: dict[int, float],
) -> dict[int, tuple[float, float]]:
    """
    Non-overlapping phylum disc centers via golden-angle spiral search.

    Large phyla (Streptophyta, Chordata, …) are placed first at the core;
    smaller phyla fill the periphery — similar separated neighborhoods on PubMed.
    """
    ordered = sorted(phylum_radii.keys(), key=lambda p: -phylum_radii[p])
    positions: dict[int, tuple[float, float]] = {}
    placed: list[tuple[float, float, float]] = []

    for idx, ptid in enumerate(ordered):
        r = phylum_radii[ptid]
        if idx == 0:
            positions[ptid] = (0.0, 0.0)
            placed.append((0.0, 0.0, r))
            continue

        found = False
        avg_r = sum(d[2] for d in placed) / len(placed)
        for ring in range(1, 96):
            dist = (avg_r + r) * (0.55 + 0.14 * ring)
            steps = max(10, ring * 5)
            for step in range(steps):
                theta = step * GOLDEN_ANGLE + idx * 0.31
                cx = dist * math.cos(theta)
                cy = dist * math.sin(theta)
                if all(
                    math.hypot(cx - ox, cy - oy) >= r + orad + DISC_GAP
                    for ox, oy, orad in placed
                ):
                    positions[ptid] = (cx, cy)
                    placed.append((cx, cy, r))
                    found = True
                    break
            if found:
                break

        if not found:
            theta = idx * GOLDEN_ANGLE
            cx = (avg_r + r) * (idx + 1) * 0.42 * math.cos(theta)
            cy = (avg_r + r) * (idx + 1) * 0.42 * math.sin(theta)
            positions[ptid] = (cx, cy)
            placed.append((cx, cy, r))

    return positions


def _phylum_pack_stats(
    by_phylum: dict[int, list[int]],
    pack_coords: dict[int, tuple[float, float]],
) -> tuple[dict[int, tuple[float, float]], dict[int, float]]:
    """Centroid and max radial extent of pack coords per phylum."""
    centroids: dict[int, tuple[float, float]] = {}
    extents: dict[int, float] = {}
    for phylum_taxid, members in by_phylum.items():
        xs = [pack_coords[t][0] for t in members if t in pack_coords]
        ys = [pack_coords[t][1] for t in members if t in pack_coords]
        if not xs:
            centroids[phylum_taxid] = (0.0, 0.0)
            extents[phylum_taxid] = 1.0
            continue
        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)
        centroids[phylum_taxid] = (cx, cy)
        max_r = max(math.hypot(x - cx, y - cy) for x, y in zip(xs, ys, strict=True))
        extents[phylum_taxid] = max(max_r, 1e-6)
    return centroids, extents


def _study_nudge(study: float, study_min: float, study_range: float) -> tuple[float, float]:
    """Small diagonal bias: dark → bottom-left, studied → top-right."""
    norm = (study - study_min) / study_range
    half = STUDY_NUDGE / 2.0
    return STUDY_NUDGE * norm - half, STUDY_NUDGE * norm - half


def _normalize_coords(
    coords: dict[int, tuple[float, float]],
    *,
    target: float = NORM_TARGET,
) -> None:
    if not coords:
        return
    xs = [v[0] for v in coords.values()]
    ys = [v[1] for v in coords.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(max_x - min_x, 1e-9)
    span_y = max(max_y - min_y, 1e-9)
    scale = (2.0 * target) / max(span_x, span_y)
    mid_x = (min_x + max_x) / 2.0
    mid_y = (min_y + max_y) / 2.0
    for taxid, (x, y) in list(coords.items()):
        coords[taxid] = ((x - mid_x) * scale, (y - mid_y) * scale)


def compute_view_extent(
    coords: dict[int, tuple[float, float]],
    *,
    padding_frac: float = 0.04,
) -> dict[str, list[float]]:
    """Full-map bbox (PubMed uses ±250); prefer square canvas over tight crop."""
    if not coords:
        return {"x": [-NORM_TARGET, NORM_TARGET], "y": [-NORM_TARGET, NORM_TARGET]}
    xs = [v[0] for v in coords.values()]
    ys = [v[1] for v in coords.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    pad_x = (max_x - min_x) * padding_frac
    pad_y = (max_y - min_y) * padding_frac
    half = NORM_TARGET
    return {
        "x": [max(min_x - pad_x, -half), min(max_x + pad_x, half)],
        "y": [max(min_y - pad_y, -half), min(max_y + pad_y, half)],
    }


def compute_clade_study_layout(
    pack_layout: dict[int, tuple[float, float, float]],
    lineage_by_taxid: dict[int, list[int]],
    *,
    rollups_path: Path,
    db_path: Path,
) -> StudyLayoutResult:
    """
    Variable-size phylum disc pack + normalized phylo cloud per neighborhood.

    Taxonomy: pack layout inside each phylum disc.
    Knowledge: small study-score nudge per phylum (not a global diagonal axis).
    """
    rollups = load_phylum_rollups_from_db(db_path)
    matrix_taxids = set(pack_layout)

    all_lineage_taxids: set[int] = set()
    for lineage in lineage_by_taxid.values():
        all_lineage_taxids.update(lineage)
    ranks = load_taxid_ranks(db_path, all_lineage_taxids)

    phylum_by_species: dict[int, tuple[int, str]] = {}
    phylum_taxids: set[int] = set()
    for taxid in matrix_taxids:
        lineage = lineage_by_taxid.get(taxid, [taxid])
        phylum_taxid, _ = resolve_phylum_from_lineage(lineage, ranks)
        phylum_taxids.add(phylum_taxid)
        phylum_by_species[taxid] = (phylum_taxid, "")

    phylum_names = resolve_phylum_names(phylum_taxids, rollups, db_path)
    for taxid, (phylum_taxid, _) in list(phylum_by_species.items()):
        phylum_by_species[taxid] = (
            phylum_taxid,
            phylum_names.get(phylum_taxid, UNKNOWN_PHYLUM_NAME),
        )

    phylum_study: dict[int, float] = {}
    for phylum_taxid in phylum_taxids:
        rollup = rollups.get(phylum_taxid)
        if rollup:
            phylum_study[phylum_taxid] = _study_score(
                rollup.species_count_matrix,
                rollup.species_count_ncbi,
            )
        else:
            phylum_study[phylum_taxid] = 0.0

    study_vals = list(phylum_study.values()) or [0.0]
    study_min = min(study_vals)
    study_max = max(study_vals)
    study_range = max(study_max - study_min, 1e-9)

    pack_coords: dict[int, tuple[float, float]] = {
        tid: (layout[0], layout[1]) for tid, layout in pack_layout.items()
    }

    by_phylum: dict[int, list[int]] = defaultdict(list)
    for taxid, (phylum_taxid, _) in phylum_by_species.items():
        by_phylum[phylum_taxid].append(taxid)

    centroids, extents = _phylum_pack_stats(by_phylum, pack_coords)
    counts = {ptid: len(members) for ptid, members in by_phylum.items()}
    max_count = max(counts.values()) if counts else 1
    phylum_radii = {
        ptid: _phylum_disc_radius(counts.get(ptid, 1), max_count) for ptid in phylum_taxids
    }
    anchors = _pack_phylum_discs(phylum_radii)

    coords: dict[int, tuple[float, float]] = {}
    for taxid in matrix_taxids:
        phylum_taxid, _ = phylum_by_species[taxid]
        anchor_x, anchor_y = anchors.get(phylum_taxid, (0.0, 0.0))
        study = phylum_study.get(phylum_taxid, 0.0)
        nudge_x, nudge_y = _study_nudge(study, study_min, study_range)
        anchor_x += nudge_x
        anchor_y += nudge_y

        phylum_r = phylum_radii.get(phylum_taxid, MIN_PHYLUM_R)
        pack_x, pack_y = pack_coords.get(taxid, (0.0, 0.0))
        cx, cy = centroids.get(phylum_taxid, (0.0, 0.0))
        extent = extents.get(phylum_taxid, 1.0)
        local_x = (pack_x - cx) / extent * phylum_r * LOCAL_FILL
        local_y = (pack_y - cy) / extent * phylum_r * LOCAL_FILL

        coords[taxid] = (anchor_x + local_x, anchor_y + local_y)

    _normalize_coords(coords, target=NORM_TARGET)
    view_extent = compute_view_extent(coords)

    return StudyLayoutResult(
        coords=coords,
        pack_coords=pack_coords,
        phylum_by_species=phylum_by_species,
        phylum_study=phylum_study,
        view_extent=view_extent,
    )
