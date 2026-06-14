# Taxon rollups — design for a taxon-first app

Design for pivoting euka-tracker from species-scatter exploration to **taxon-centric** navigation: precomputed statistics on each NCBI taxon, rolled up from `data/staged/05_eukaryotic_species_matrix.tsv` over the hierarchy in `data/ncbi_taxonomy_tree.tsv.gz`.

---

## Taxonomy source facts

| File | Status | Notes |
|------|--------|-------|
| `data/ncbi_taxonomy_tree.tsv.gz` | **Use this** | Full eukaryotic subtree (~1.81M nodes) |
| `data/staged/01_ncbi_taxonomy_tree.tsv.gz` | Broken stub | 1 row only — do not use for rollups |

### Species-level taxa in NCBI taxonomy (eukaryotes)

Counted from `data/ncbi_taxonomy_tree.tsv.gz` (rank = `species`):

| Metric | Count |
|--------|------:|
| **Total nodes** | 1,812,857 |
| **Species-rank taxa** | **1,585,178** |
| Genus-rank | 104,007 |
| Subspecies | 30,340 |
| Family | 9,302 |
| Order | 1,438 |
| Class | 290 |

Matrix overlap (for context):

| Metric | Count |
|--------|------:|
| Species in `05_eukaryotic_species_matrix.tsv` | 105,223 |
| Matrix species found in taxonomy tree | ~104,086 |
| Induced taxon nodes (ancestors of matrix species) | ~156,197 |

So the matrix covers **~6.6%** of NCBI eukaryotic species-rank taxa (105k / 1.59M), and the app’s taxon tree should always show **NCBI total vs matrix total** side by side.

---

## What we are building (one sentence)

A **taxon table** where each row is an NCBI taxon on the path from Eukaryota to at least one matrix species, carrying:

1. **Taxonomy structure** — parent, rank, name, depth  
2. **NCBI subtree counts** — how large the clade is in taxonomy  
3. **Matrix coverage counts** — how much of that clade appears in the species matrix  
4. **Per-rank node counts** — e.g. Mammalia: 29 orders, 163 families, … plus how many of those have matrix data  
5. **Rolled-up matrix stats** — sums and averages of species-level columns over matrix species in the subtree  

---

## Two universes (never conflate)

| Metric | Meaning | Example (Mammalia) |
|--------|---------|---------------------|
| **NCBI subtree** | All taxa under this node in NCBI | 10,037 species, 29 orders, 163 families |
| **Matrix subtree (catalog)** | Species in `05_eukaryotic_species_matrix.tsv` with `catalog_source=catalog` under this node | ~104k species with ENA/NCBI catalog data |
| **IUCN-only matrix rows** | Species appended from IUCN with no catalog data (`catalog_source=iucn_only`) | ~80k additional rows at Y≈0 in conservation scatter |

Always show catalog vs NCBI totals side by side, e.g. `1,942 / 10,037 species (19%)`. IUCN-only rows inflate total matrix row count but **do not** increment `species_count_matrix` — that counter stays catalog-only so atlas dual-count semantics remain valid.

---

## Conservation-gap rollup columns

Appended to each induced taxon row (subtree sums over matrix rows):

```
species_count_iucn_only           # iucn_only rows in subtree (no catalog)
species_threatened_no_reads       # threatened + run_count == 0
species_threatened_dark_matter    # threatened + reads + no assembly
```

`species_count_matrix` counts **catalog** species only. IUCN assessed/threatened counters include both catalog and iucn_only rows.

---

## Induced tree vs full tree

**Recommended app output:** the **induced subtree** — every taxon that is either:

- a matrix species, or  
- an ancestor of a matrix species  

~**156k rows** (vs 1.8M full tree): large enough for drill-down, small enough for SQLite and a taxon browser.

**Optional:** full eukaryotic tree with zeros for taxa without matrix descendants (Lifemap / global view).

---

## Per-taxon row schema (proposed)

### Identity

```
taxid
parent_taxid
scientific_name
rank                    # NCBI rank string
rank_level              # normalized int (canonical ladder)
depth_from_eukaryota
has_matrix_descendant   # bool
```

### Species counts

```
species_count_ncbi          # species-rank descendants in NCBI subtree
species_count_matrix        # catalog matrix species in subtree (excludes iucn_only)
species_count_iucn_only     # IUCN-only matrix rows in subtree
species_with_reads
species_with_assembly
species_with_annotation
species_full_triple         # reads + assembly + annotation
species_iucn_assessed
species_threatened          # VU / EN / CR / EW
species_threatened_no_reads
species_threatened_dark_matter
```

### Per-rank node counts (Mammalia-style)

For taxon **T**, count ranks **strictly below T’s rank** down to `species`.

Fixed columns (0 when rank does not apply below T):

```
# Totals in NCBI subtree of T
kingdom_nodes_total
phylum_nodes_total
class_nodes_total
order_nodes_total
family_nodes_total
genus_nodes_total
species_nodes_total

# Nodes where ≥1 matrix species exists in that node's subtree
kingdom_nodes_with_data
phylum_nodes_with_data
...
species_nodes_with_data   # equals species_count_matrix for most taxa
```

**Example — Mammalia (class):**

| Field | NCBI total | With matrix data |
|-------|----------:|-----------------:|
| order | 29 | (computed) |
| family | 163 | (computed) |
| genus | 1,383 | (computed) |
| species | 10,037 | ~1,942 |

**Genus row:** primarily `species_nodes_total` / `species_nodes_with_data`.

### Rolled-up matrix metrics

Split into **sum**, **mean** (over species with non-null values), and **count_non_null**:

| Column group | Sum | Mean |
|--------------|-----|------|
| Reads | `sum_run_count`, per-bucket counts | `mean_run_count` |
| Assembly | `sum_assembly_count` | `mean_genome_size`, `mean_gc_percent`, `mean_scaffold_n50`, `mean_ungapped_fraction` |
| Annotation | `sum_annotation_count` | `mean_total_genes`, `mean_mrna_genes`, `mean_busco_complete` |
| IUCN | — | `pct_threatened` (over assessed) |

**Rules:**

- **Counts / flags** → sum over matrix species in subtree  
- **Sizes, genes, BUSCO, coverage** → mean where present; store `n_with_assembly`, `n_with_annotation`  
- **Do not sum** `best_wgs_coverage` — use mean or max; label as “mean of best-run coverage per species”  
- Use **true run counts** from buckets, not summed representative `base_count` (see `SCATTER_METRICS.md`)  
- Derive species facts via `scatter_export.py` / shared helpers before rollup  

### Optional quality fields

```
pct_species_with_reads       = species_with_reads / species_count_matrix
pct_species_with_assembly    = species_with_assembly / species_count_matrix
pct_ncbi_species_with_data   = species_count_matrix / species_count_ncbi
best_data_tier_in_subtree    # best (min) data_tier among matrix species
```

---

## Rank normalization (NCBI is messy)

NCBI uses `no rank`, `suborder`, `tribe`, `subspecies`, `strain`, etc. Use a **canonical ladder** for UI columns:

```text
domain → kingdom → phylum → class → order → family → genus → species
```

Map NCBI ranks explicitly; log unmapped ranks. For v1, bucket into canonical ranks only.

**Subspecies / strain:** exclude from `species_count_ncbi` unless explicitly included (default: **species rank only**).

---

## Pipeline (implemented — memory-efficient)

**Preferred entry point:** unified orchestrator in [pipeline/build_species_matrix.py](pipeline/build_species_matrix.py):

```bash
# Full chain (skip network fetch if staged files exist):
.venv/bin/python pipeline/build_species_matrix.py --step all --skip-fetch

# Individual downstream steps:
.venv/bin/python pipeline/build_species_matrix.py --step finalize   # lineage + IUCN on matrix
.venv/bin/python pipeline/build_species_matrix.py --step rollups
.venv/bin/python pipeline/build_species_matrix.py --step scatter    # parquet + UMAP + tiles
```

**Standalone rollups** (matrix must already have `tax_lineage` from finalize):

```bash
python pipeline/build_taxon_rollups.py \
  --taxonomy data/ncbi_taxonomy_tree.tsv.gz \
  --matrix data/staged/05_eukaryotic_species_matrix.tsv \
  --db data/staged/taxonomy.sqlite \
  --output data/staged/06_taxon_rollups.tsv \
  --skip-lineage-patch
```

| Stage | Script / module | Output |
|-------|-----------------|--------|
| 1 | [pipeline/taxonomy_index.py](pipeline/taxonomy_index.py) | `data/staged/taxonomy.sqlite` (~1.8M rows on disk) |
| 2 | [pipeline/remap_invalid_matrix_taxids.py](pipeline/remap_invalid_matrix_taxids.py) + [pipeline/patch_species_tax_lineage.py](pipeline/patch_species_tax_lineage.py) | Valid taxids + `tax_lineage` on matrix |
| 3–5 | [pipeline/build_taxon_rollups.py](pipeline/build_taxon_rollups.py) + [pipeline/taxon_rollup.py](pipeline/taxon_rollup.py) | `data/staged/06_taxon_rollups.tsv` (~245k induced taxa) |

Flags: `--skip-index-build`, `--skip-lineage-patch`, `--force-rebuild-index`.

### Stage 1 — Stream taxonomy into SQLite

Stream via `iter_taxonomy_rows()` from [pipeline/ncbi_taxonomy_fetch.py](pipeline/ncbi_taxonomy_fetch.py). Batch `INSERT` into `taxa(taxid, parent_taxid, name, rank, depth, species_count_ncbi)`.

### Stage 2 — Patch `tax_lineage`

For each matrix species, walk parents via indexed SQLite lookups; write root→tip CSV (ENA convention) into `tax_lineage` on [data/staged/05_eukaryotic_species_matrix.tsv](data/staged/05_eukaryotic_species_matrix.tsv).

### Stage 3 — Matrix rollup from `tax_lineage`

Stream matrix; split lineage; aggregate into `RollupAgg` dict (~157k keys in RAM) using `matrix_row_to_taxon_facts()`.

### Stage 4 — NCBI `species_count_ncbi` in SQLite

BFS `depth` from Eukaryota (2759), then bottom-up `UPDATE` by depth using `SUM` over children. Only `rank = species` contributes 1.

### Stage 4b — Per-rank node counters in SQLite

After matrix rollups, sync `matrix_species_count` to SQLite, then bottom-up by depth for each canonical rank (`domain` … `species`):

- `{rank}_nodes_total` — descendant nodes of that rank in the NCBI subtree  
- `{rank}_nodes_with_data` — same, where `matrix_species_count > 0` on that node  

Implemented in `compute_rank_node_counts()` in [pipeline/taxon_rollup.py](pipeline/taxon_rollup.py).

### Stage 5 — Emit induced hierarchy TSV

Join SQLite identity + NCBI counts with `RollupAgg` matrix stats. Column list: `TAXON_ROLLUP_FIELDS` in [pipeline/taxon_rollup.py](pipeline/taxon_rollup.py).

---

## Pipeline algorithm (superseded design — do not use)

The in-memory `nodes` / `children` dict approach below was replaced by SQLite + `tax_lineage` (see above).

### Pass 1 — Load taxonomy (in memory) — REMOVED

### Pass 2 — Species matrix → normalized species facts

One row per matrix species:

- parsed numerics from TSV  
- booleans: `has_reads`, `has_assembly`, `has_annotation`, `has_iucn`, `threatened`  
- derived: `run_count`, bucket counts, `data_tier`  

### Pass 3 — Bottom-up matrix aggregation

For each matrix species, walk ancestors to Eukaryota (2759):

```text
agg[taxon].species_count_matrix += 1
agg[taxon].sum_run_count += ...
agg[taxon].sum_has_assembly += ...
... (all sum fields)
collect values for running means where non-null
mark has_matrix_descendant = true
```

Each node accumulates `matrix_species_count` for its subtree.

### Pass 4 — Post-order NCBI subtree stats

DFS from root. Each node returns counters for **its subtree**:

- `ncbi_species_count` (rank = species only)  
- `rank_nodes_total[r]` — descendant nodes of rank r  
- `rank_nodes_with_data[r]` — descendant nodes of rank r with `matrix_species_count > 0`  

Merge at parent: add child counters + count self if rank matches.

### Pass 5 — Emit

Output: `data/staged/06_taxon_rollups.tsv` or `.parquet`, and/or SQLite `taxa` table.

One row per **induced** node (recommended) or per full-tree node.

---

## App architecture (taxon-first)

```
/taxonomy/:taxid     — taxon detail (primary)
/taxonomy            — root at Eukaryota
/species             — species catalogue filtered by taxon
/explore             — optional scatter deep-dive (secondary)
```

**Taxon detail page:**

- Breadcrumb + children table (sort by `species_count_matrix`, `% assembly`)  
- Clade funnel: reads → assembly → annotation  
- Rank breakdown: “29 orders, N with data”  
- Rolled-up means with `n=`  
- Link: “Show N species” → filtered catalogue  

**Tree widget:** Lifemap layout (`TREE_OF_LIFE.md`), node color/size from rollups (`pct_ncbi_species_with_data`).

Scatter is optional: “compare species in this clade” from taxon page.

---

## Relation to existing code

| Artifact | Role |
|----------|------|
| `MODELS.txt` `TAXON` | Target schema — extend with rank node columns |
| `scripts/build_rank_statistics.py` | Prototype (phylum-only) — supersede with full rollups |
| `scripts/build_tree_layout.py` + `TREE_OF_LIFE.md` | Tree viz colored by rollup fields |
| `pipeline/scatter_export.py` | Species fact derivation before rollup |
| `pipeline/build_species_matrix.py` | Upstream unchanged |
| `SCATTER_METRICS.md` | Read-count semantics for rollup sums |

---

## Design decisions (decide before implementation)

1. **Induced tree only vs full 1.8M** — induced (~156k) for app DB; full tree for Lifemap.  
2. **Which ranks get columns** — fixed 8 canonical ranks vs dynamic “ranks below me”.  
3. **Subspecies / strain** — exclude from `species_count_ncbi` (default: species rank only).  
4. **Mean denominator** — mean over species with non-null field + report `n`.  
5. **Storage** — SQLite for API; Parquet for rebuild/analytics.

---

## Suggested build order

1. ~~Fix staged taxonomy~~ — use [data/ncbi_taxonomy_tree.tsv.gz](data/ncbi_taxonomy_tree.tsv.gz) directly.
2. **Done:** `build_taxon_rollups.py` — SQLite index, `tax_lineage` patch, matrix sums + species counts → `06_taxon_rollups.tsv`.
3. **Done:** per-rank node totals + `with_data` counters (`order_nodes_total`, …) in SQLite + TSV.
4. Export SQLite + `GET /api/taxa/{id}`.
5. Replace mock `/taxonomy` with real rollups.
6. Wire species catalogue as `?taxon={taxid}` filter.

---

## Why this direction vs species scatter

- Natural unit: **clade**, not point cloud  
- Honest sparsity: “6.6% of eukaryotic species have any row in the matrix”  
- Actionable drill-down: phylum → class → order → species list  
- Aligns with `MODELS.txt`, Lifemap tree, and biodiversity-genomics questions  
- Scatter remains useful **within** a taxon filter, not as the home screen  

---

## Related docs

- [TAXONOMY_UX.md](./TAXONOMY_UX.md) — six UX concepts & implementation guide for taxonomy UI
- [MODELS.txt](./MODELS.txt) — `TAXON` / `ORGANISM` schemas  
- [TREE_OF_LIFE.md](./TREE_OF_LIFE.md) — dendrogram tiles  
- [SCATTER_METRICS.md](./SCATTER_METRICS.md) — species-level metric caveats  
- [WEB_APP_STACK.md](./WEB_APP_STACK.md) — API and deployment
