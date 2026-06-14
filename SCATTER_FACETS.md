# Scatter facets — bioinformatically meaningful views

Curated coordinate presets and color encodings for the species-level DeepScatter explorer. All metrics derive from fields defined in [TODO.txt](./TODO.txt): read runs (≤5 bioprojects/species), assembly stats, and gene annotation counts.

**Unit of plot:** one point = one species (`species_tax_id`).

**Notation:** `log(x)` = `log10(x + 1)` unless noted. Coverage uses `genome_size` = `totalSequenceLength` from the reference assembly.

---

## Derived metrics (reference)

### Reads rollup (per species, ≤5 bioprojects)

| Field | Formula |
|-------|---------|
| `total_bases` | Σ `base_count` |
| `total_reads` | Σ `read_count` |
| `bioproject_count` | number of selected bioprojects (max 5) |
| `mean_read_length` | `total_bases / total_reads` |
| `median_coverage` | median of `coverage_run` per bioproject |
| `genome_equivalents` | `total_bases / genome_size` |

### Coverage tiers (from TODO)

| Tier | `coverage_run` | Label |
|------|----------------|-------|
| 0 | &lt; 0.1× | unusable |
| 1 | 0.1–1× | shallow |
| 2 | 1–10× | usable |
| 3 | 10–50× | deep |
| 4 | 50–200× | very deep |
| 5 | &gt; 200× | over-sequenced |

### Assembly (reference per species)

`genome_size`, `scaffoldN50`, `contigN50`, `ungapped_fraction` = `totalUngappedLength / totalSequenceLength`, `gapsBetweenScaffoldsCount`, `numberOfComponentSequences`, `gc_percent`, `chromosome_count`.

### Annotation

`total_genes`, `mrna_genes`, `lncrna_genes`, `avg_mrna_len`, `avg_lncrna_len`, `gene_density` = `total_genes / (genome_size / 1e6)`, `lnc_mrna_ratio` = `lncrna_genes / mrna_genes`.

### Cross-stream diagnostics

| Field | Formula | Meaning |
|-------|---------|---------|
| `knowledge_gap` | z(`log(total_bases)`) − z(`log(total_genes)`) | High sequencing, low annotated complexity |
| `quality_gap` | z(`log(total_bases)`) − z(`ungapped_fraction`) | High sequencing, poor assembly completeness |
| `annotation_yield` | `total_genes / genome_equivalents` | Genes per unit of sequencing depth |

---

## Recommended coordinate combinations

Only views **fully supported** by TODO fields, ordered by biological interpretability.

| ID | Preset name | X (effort) | Y (complexity / quality) | Biological question | Quadrant story |
|----|-------------|------------|--------------------------|---------------------|----------------|
| **A** | **Effort vs genes** *(default)* | `log(total_bases)` | `log(total_genes)` | How much have we sequenced vs how complex is the annotated gene repertoire? | Top-right = well-studied; bottom-right = data-rich deserts; top-left = complex but under-sequenced |
| **B** | **Coverage vs genes** | `median_coverage` | `log(total_genes)` | Is sequencing depth adequate for the apparent genomic complexity? | Left = under-sequenced; right = deep; highlights species where depth may not support annotation |
| **C** | **Genome equivalents vs gene density** | `genome_equivalents` | `log(gene_density)` | Normalized sequencing vs genes per Mb (size-independent complexity) | Fair cross-species compare; reduces genome size paradox |
| **D** | **Effort vs coding capacity** | `log(total_bases)` | `log(mrna_genes)` | Sequencing mass vs protein-coding gene count | Focus on coding repertoire; precursor to proteome views |
| **E** | **Effort vs regulatory load** | `log(total_bases)` | `log(lncrna_genes)` | Sequencing vs non-coding RNA gene count | Regulatory / ncRNA dimension of complexity |
| **F** | **Attention vs regulatory balance** | `log(bioproject_count)` | `lnc_mrna_ratio` | Research focus vs balance of ncRNA to mRNA genes | High projects + low ratio = coding-centric models; high ratio = regulatory-rich lineages |
| **G** | **Depth vs contiguity** | `median_coverage` | `log(scaffoldN50)` | Did sequencing depth coincide with a contiguous assembly? | Separates “lots of reads, fragmented asm” from “modest reads, good asm” |
| **H** | **Effort vs assembly completeness** | `log(total_bases)` | `ungapped_fraction` | Sequencing effort vs gap-free assembly fraction | Quality gap: well-funded but incomplete reference |
| **I** | **Coverage vs transcript architecture** | `median_coverage` | `avg_mrna_len` | Depth vs mean mRNA transcript length | Longer transcripts may reflect intron-rich genomes; needs consistent annotation |
| **J** | **Effort vs transcript mass** | `log(total_bases)` | `log(mrna_genes × avg_mrna_len)` | Sequencing vs total coding transcript “bulk” | Combines gene count and length — richer than mRNA count alone |
| **K** | **Effort vs regulatory mass** | `log(total_bases)` | `log(lncrna_genes × avg_lncrna_len)` | Sequencing vs ncRNA transcript bulk | Regulatory complexity beyond gene counts |
| **L** | **Technology vs genome scale** | `mean_read_length` | `log(genome_size)` | Dominant read technology vs genome size | Illumina cluster (short reads) vs long-read species; tech bias visible |
| **M** | **Effective coverage vs genes** | `log(total_bases / genome_size)` | `log(total_genes)` | Genome-normalized effort vs gene count | Best single “effort vs complexity” when assembly exists |
| **N** | **Bioprojects vs fragmentation** | `log(bioproject_count)` | `log(numberOfComponentSequences)` | Study attention vs assembly fragmentation | Bias + assembly maturity; high projects + high components = troubled references |
| **O** | **Composite dashboard** | `effort_score` | `complexity_score` | Stable default overview | See composite formulas below |

### Composite scores (preset O)

```text
effort_score =
    0.40 * log(total_bases)
  + 0.30 * log(total_reads)
  + 0.30 * log(bioproject_count)

complexity_score =
    0.35 * log(total_genes)
  + 0.25 * log(mrna_genes)
  + 0.25 * log(lncrna_genes)
  + 0.15 * log(gene_density)
```

Normalize `effort_score` and `complexity_score` to percentile rank (0–1) before tiling if outliers (human, mouse) dominate.

### Suggested defaults

| Role | Preset |
|------|--------|
| App launch | **A** or **O** |
| Biodiversity “data gap” narrative | **B**, **M**, + color `knowledge_gap` |
| Assembly / reference quality | **G**, **H** |
| Regulatory / ncRNA biology | **E**, **F**, **K** |
| Technology / platform bias | **L** + color `read_length_class` |

---

## Color encodings

Use **numeric codes** in Parquet for DeepScatter; map labels in the UI.

### Universal (work on most presets)

| Color field | Type | Values | When to use |
|-------------|------|--------|-------------|
| **`coverage_tier`** | ordinal | 0–5 (unusable → over-sequenced) | **Best default color.** Shows whether X-axis effort is *meaningful* coverage. Viridis or stepped palette. |
| **`knowledge_gap`** | continuous | z-score | Effort vs complexity presets (A, M, O). Diverging: blue = under-sequenced complex, red = over-sequenced simple. |
| **`quality_gap`** | continuous | z-score | Presets G, H, N. Highlights high effort + poor assembly. |
| **`has_assembly`** | binary | 0/1 | Gray out species without reference when coverage-based X is used. |
| **`has_annotation`** | binary | 0/1 | Gray out species without gene counts on Y. |

### Biology-focused

| Color field | Type | Values | When to use |
|-------------|------|--------|-------------|
| **`iucn_category`** | categorical | LC, NT, VU, EN, CR, DD, NE | Conservation context on any effort/complexity view. Red-list ramp for threatened. |
| **`lnc_mrna_ratio`** | continuous | ratio | Presets A, D, E. Regulatory balance; cap outliers at 99th percentile. |
| **`coding_fraction`** | continuous | `mrna_genes / total_genes` | How “coding-dominated” the annotation is. |
| **`regulatory_fraction`** | continuous | `lncrna_genes / total_genes` | ncRNA share of annotated genes. |
| **`gene_density`** | continuous | genes/Mb | On effort-only X presets; shows compact vs gene-rich genomes. |
| **`gc_percent`** | continuous | 0–100 | Compositional bias; weak complexity proxy but useful for outliers. |

### Technology & bias

| Color field | Type | Values | When to use |
|-------------|------|--------|-------------|
| **`read_length_class`** | categorical | short (&lt;500 bp), medium, long (&gt;1 kb), ultra-long (&gt;10 kb) | Presets A–E, L. Surfaces Illumina vs ONT/PacBio dominance from `mean_read_length`. |
| **`bioproject_count`** | discrete | 1–5 (+ flag if capped) | Research intensity; size scale alternative. |
| **`bioprojects_at_cap`** | binary | 0/1 | Tooltip + border: “≥5 projects exist, showing top 5.” |

### Taxonomy (when clade filter inactive)

| Color field | Type | When to use |
|-------------|------|-------------|
| **`kingdom_id`** / phylum | categorical | Exploratory global view only; disable when taxon filter applied. |

---

## Recommended color pairings per preset

| Preset | Primary color | Size (optional) | Filter suggestion |
|--------|---------------|-----------------|-------------------|
| **A** Effort vs genes | `coverage_tier` | `bioproject_count` | `has_annotation` |
| **B** Coverage vs genes | `knowledge_gap` | `total_bases` | `has_assembly` |
| **C** Equiv vs gene density | `iucn_category` | `total_genes` | `has_assembly` |
| **D** Effort vs mRNA | `coding_fraction` | `mrna_genes` | `has_annotation` |
| **E** Effort vs lncRNA | `regulatory_fraction` | `lncrna_genes` | `has_annotation` |
| **F** Projects vs lnc/mRNA | `read_length_class` | `total_bases` | `mrna_genes > 0` |
| **G** Depth vs N50 | `quality_gap` | `scaffoldN50` | `has_assembly` |
| **H** Effort vs ungapped | `coverage_tier` | `gapsBetweenScaffoldsCount` | `has_assembly` |
| **I** Coverage vs mRNA length | `gc_percent` | `mrna_genes` | `has_annotation` |
| **J** Effort vs transcript mass | `coding_fraction` | `avg_mrna_len` | `has_annotation` |
| **K** Effort vs regulatory mass | `lnc_mrna_ratio` | `avg_lncrna_len` | `has_annotation` |
| **L** Read length vs genome | `coverage_tier` | `total_bases` | `has_runs` |
| **M** Eff vs genes (normalized) | `knowledge_gap` | `annotation_yield` | `has_assembly & has_annotation` |
| **N** Projects vs components | `ungapped_fraction` | `contigL50` | `has_assembly` |
| **O** Composite | `coverage_tier` | `bioproject_count` | at least one data stream |

---

## Interpretation guide (for UI copy)

### High effort, low complexity (bottom-right in preset A)
Species with many bases sequenced but relatively few annotated genes — may indicate poor annotation, non-model lineage, repetitive genome, or incomplete gene prediction.

### Low effort, high complexity (top-left)
Under-sequenced species with surprisingly rich annotation (often borrowed reference or related-species annotation) — **priority targets for new sequencing**.

### High effort, low `ungapped_fraction` (preset H)
Well-funded sequencing but gappy assembly — long-read or scaffolding gap; reference not fit for variant calling.

### High `lnc_mrna_ratio` (presets E, F, K)
Regulatory-rich annotation profile relative to coding genes — interpret cautiously across annotation pipelines.

### `coverage_tier` 0 or 5
Unusable (&lt;0.1×) or over-sequenced (&gt;200×) — down-weight biological interpretation of effort axes.

---

## Data requirements matrix

| Preset | Needs reads | Needs assembly | Needs annotation |
|--------|-------------|----------------|------------------|
| A, D, E, J, K, L | ✓ | optional | ✓ for Y |
| B, G, I, M | ✓ | ✓ | ✓ for Y (except G Y only) |
| C, H, N | ✓/optional | ✓ | ✓ for C Y |
| F | ✓ | — | ✓ |
| O | ✓ | optional | ✓ for full complexity |

Species missing a required stream: plot with null Y or exclude via filter; show counts in UI (“n = 12,431 with full triple”).

---

## Implementation notes

1. Store **raw + log** columns in `species_scatter.parquet`; DeepScatter `encoding.field` points at `log_*` variants.
2. Default tile columns: `x`, `y` from preset **A** or **O**; swap axes via encoding without retiling (&lt;200k species).
3. **`bioproject_count` capped at 5** — store `bioprojects_at_cap` so effort views are not silently truncated.
4. **`coverage_run`** undefined without `genome_size` — use `total_bases` on X and `has_assembly = false` color for those species.
5. When **PROTEINS** fields are added to TODO, add presets: effort vs protein count, coverage vs mean protein length.

---

## Related docs

- [TODO.txt](./TODO.txt) — source fields per model
- [tiles-coords.md](./tiles-coords.md) — earlier broad facet brainstorm
- [MODELS.txt](./MODELS.txt) — database schemas
- [WEB_APP_STACK.md](./WEB_APP_STACK.md) — app architecture and tiling pipeline
