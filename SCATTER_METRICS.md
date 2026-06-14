# Scatter metrics — design rationale and recommendations

Guidance for choosing deepscatter coordinates and colors for the eukaryotic species explorer. Derived from analysis of `data/staged/05_eukaryotic_species_matrix.tsv`, `pipeline/scatter_export.py`, and current presets in `pipeline/scatter_facets.json`.

**Unit of plot:** one point = one species (`taxid`).

---

## Why the current default feels flat

The default preset (`sequencing_map`) uses:

- **X:** `log10_wgs_bases`
- **Y:** `log10_rnaseq_bases`
- **Color:** `data_tier`

Three problems:

1. **It cross-plots two sparse, anti-correlated axes.** Most species have WGS *or* RNA-seq, not balanced amounts of both. Points collapse into an L-shape hugging the two axes — lots of pixels, little structure.
2. **It answers a methods question** (“does this species have both DNA and RNA reads?”), not a biodiversity-genomics question.
3. **It wastes the dataset’s strongest signal.** The superpower here is breadth of *reads* and the funnel down to genomes — none of that is the headline in this view.

Default tile partition columns in `scatter_export.py` mirror this:

```python
out["x"] = out["log10_wgs_bases"]
out["y"] = out["log10_rnaseq_bases"]
```

---

## Data completeness (105,223 species)

| Stage | Species | % |
|-------|---------|---|
| Has reads | 101,439 | **96%** |
| Has assembly | 27,650 | 26% |
| Has annotation | 8,525 | 8% |
| Has IUCN status | 25,657 | 24% |
| Full triple (reads + asm + ann) | 7,773 | 7% |
| **Reads but NO assembly (“dark genomes”)** | **77,573** | **74%** |
| Assembly but no annotation | 19,125 | 18% |
| Threatened (VU / EN / CR / EW) | 4,736 | — |
| → threatened with NO assembly | 3,401 | **72% of threatened** |
| → threatened with NO annotation | 4,336 | 92% of threatened |

**The dataset is a funnel:** reads → assembly → annotation, with massive attrition. Conservation-relevant species are disproportionately stuck at stage 0. That should drive encoding choices.

---

## Read columns: what is actually stored

In `select_species_runs` / `select_better_run`, for each of four buckets (`wgs_long`, `wgs_short`, `rnaseq_long`, `rnaseq_short`) the matrix stores **two different kinds of information**:

| Column pattern | Meaning |
|----------------|---------|
| `{bucket}_count` | **True count** — incremented on every qualifying run (`entry["counts"][bucket] += 1`). ENA search uses `limit=0` (all records) with quality floor (`base_count > 10M AND read_count > 100k`). Counts are uncapped. |
| `{bucket}_base_count`, `_read_count`, `_coverage` | **Single “best” run** in that bucket. “Best” = highest `(coverage, paired-end, base_count)` via `_run_sort_key`. |

Therefore:

- `total_bases` in `scatter_export.py` (`sum` of the 4 bucket base counts) = **sum of up to four single representative runs**, not cumulative sequencing volume.
- It systematically undercounts species with many runs.
- **`≤5 bioprojects/species` in `SCATTER_FACETS.md` was never implemented** — counts are uncapped.

### Field trustworthiness

| Field | Trustworthy? | What it actually answers |
|-------|-------------|--------------------------|
| `run_count`, per-bucket `_count`, `active_buckets` | **Yes — true counts** | *Breadth* / research attention: how many public datasets exist |
| `has_wgs_bases`, `has_long_reads`, `dominant_modality` | **Yes** | Which data *types* exist |
| `best_wgs_coverage`, `best_rnaseq_coverage` | **Yes** | *Depth of the single best library* — “is there one run deep enough to assemble?” (needs genome size → ~26% of species) |
| `{bucket}_base_count` (e.g. `wgs_short_bases`) | Yes, **if relabeled** | Size of the *single deepest* library in that bucket — not a species total |
| `total_bases`, `total_reads`, `wgs_bases`, `rnaseq_bases`, `long_bases`, `short_bases` (+ `log10_*`) | **No — misleading** | “Sum of up to 4 best runs.” Do not present as volume/effort |
| `genome_equivalents`, `wgs_bases_per_mb`, `long_read_fraction`, `rnaseq_to_wgs_ratio` | **No** | Built on the misleading sums |

**For adequacy (“can we assemble?”), best-single-run depth is actually the correct metric** — you assemble from the best library, not by naively concatenating everything. `best_wgs_coverage` is a feature, not a bug. The volume *aggregate* is what’s broken.

---

## Design rules

### 1. Sparse dimensions belong in color, not on axes

Discrete fields (`data_tier`, `iucn_code`, `dominant_modality`, `active_buckets`) make great **color** but weak **axes** (banded, uninformative layouts).

### 2. Three population regimes — declare which one a preset serves

| Regime | ~N | Axis constraint |
|--------|-----|-----------------|
| **Global** | ~101k | Axes must be read-derived (counts, presence, best-run depth) |
| **Reference** | ~27k | Can use genome size, N50, coverage |
| **Annotation** | ~8k | Can use gene counts, BUSCO |

A preset that uses gene count on Y without filtering to `has_annotation=1` will look 92% empty.

### 3. Encoding swap without retiling

All columns live in one wide Parquet (~105k species, under the 200k single-export threshold). Swap `encoding.x.field`, `y.field`, and `color` via `plotAPI` without re-running quadfeather.

### 4. Normalize outliers

Human, mouse, zebrafish dominate `total_bases`, gene counts, coverage. Cap continuous color at 99th percentile or use percentile rank.

---

## Recommended coordinate + color presets

### Global views (~101k species)

| Question | X | Y | Color | Filter |
|----------|---|---|-------|--------|
| **Catalog breadth → pipeline stage** *(recommended default)* | `log10_run_count` | `data_tier` (+ jitter) | `data_tier` | — |
| **Conservation gap** | `log10_run_count` | `data_tier` (+ jitter) | `iucn_code` | optional: threatened only |
| **Dark genomes** (reads, no reference) | `log10_run_count` | `active_buckets` | `data_tier` | `sequencing_without_reference=1` |
| **Tech mix** (methods niche) | `log10_short_bases`* | `log10_long_bases`* | `dominant_modality` | — |

\*Relabel axes as “deepest short-read library” / “deepest long-read library”, not total volume.

### Reference-quality views (~27k with assemblies)

| Question | X | Y | Color | Filter |
|----------|---|---|-------|--------|
| **Coverage adequacy / oversequencing** | `log10_genome_size` | `best_wgs_coverage` (log) | coverage tier or `assembly_level_score` | `has_assembly=1` |
| **Is the reference any good?** | `log10_scaffold_n50` | `ungapped_fraction` | `assembly_level_score` | `has_assembly=1` |
| **Scaffold inflation** | `log10_contig_n50` | `log10_scaffold_n50` | `assembly_level_score` | `has_assembly=1` |

### Annotation views (~8k with genes)

| Question | X | Y | Color | Filter |
|----------|---|---|-------|--------|
| **Genome-size paradox** | `log10_genome_size` | `log10_total_genes` | `gene_density` | `has_annotation=1` |
| **Coding vs regulatory** | `log10_mrna_genes` | `log10_lncrna_genes` | `lnc_to_mrna` | `has_annotation=1` |
| **Annotation quality** | `log10_total_genes` | `busco_complete` | `busco_duplication` | `has_annotation=1` |

---

## Color strategy (where insight lives)

Ranked by biodiversity-genomics value:

1. **`data_tier` (0–3)** — the funnel (reads only → +assembly → +annotation → full). Best default color. Sequential ramp (e.g. viridis).
2. **`iucn_code`** — conservation. Red-list ramp (LC green → CR red; DD/NE gray). Only 24% have status — pair with filter or gray unknowns.
3. **`best_wgs_coverage`** (binned 0–5 tiers per `SCATTER_FACETS.md`) — adequacy. Best on genome-size axes.
4. **`assembly_level_score` (1–4)** — reference maturity (contig → complete genome).

---

## Recommended default

Replace `sequencing_map` as launch preset with **“Catalog breadth → pipeline stage”**:

```json
{
  "id": "catalog_funnel",
  "world": "sequencing",
  "label": "Catalog funnel",
  "x": "log10_run_count",
  "y": "data_tier",
  "color": "data_tier",
  "filter": null,
  "default": true
}
```

- **X** spreads all species by true research attention (run count).
- **Color** shows the funnel instantly.
- **Second tab:** same X, `color = iucn_code` — “3,401 threatened species have reads but no genome.”

Demote `sequencing_map` (WGS vs RNA-seq L-shape) to a methods niche or remove.

Update default tile partition in `scatter_export.py`:

```python
out["x"] = out["log10_run_count"]  # or log10p1(run_count)
out["y"] = out["data_tier"]        # with jitter in encoding
```

---

## Fields to deprecate or relabel in UI

Until the pipeline accumulates true sums, avoid or relabel:

- `total_bases`, `total_reads`, `wgs_bases`, `rnaseq_bases`
- `genome_equivalents`, `wgs_bases_per_mb`
- `long_read_fraction`, `rnaseq_to_wgs_ratio` (derived from misleading sums)
- Any preset in `scatter_facets.json` whose primary X/Y is `log10_total_bases` or `log10_wgs_bases` without explicit “best-run” labeling

---

## Future pipeline fix (true cumulative volume)

In `select_species_runs`, alongside `entry["counts"][bucket] += 1`, accumulate over **all** runs:

- `entry["sum_bases"][bucket] += base_count`
- `entry["sum_reads"][bucket] += read_count`
- distinct `study_accession` → `bioproject_count`

Keep best-run coverage as the depth metric. Then `total_bases` becomes a real sum and effort-vs-complexity presets from `SCATTER_FACETS.md` (presets A, M, etc.) become valid again.

---

## Related docs

- [SCATTER_FACETS.md](./SCATTER_FACETS.md) — original facet brainstorm (some fields assume cumulative volume; see caveats above)
- [.cursor/skills/deepscatter/SKILL.md](./.cursor/skills/deepscatter/SKILL.md) — deepscatter / quadfeather integration
- [pipeline/scatter_export.py](./pipeline/scatter_export.py) — derived metrics
- [pipeline/species_matrix_select.py](./pipeline/species_matrix_select.py) — best-run selection logic
