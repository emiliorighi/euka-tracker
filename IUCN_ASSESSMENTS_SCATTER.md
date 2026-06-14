# IUCN assessments → deepscatter field analysis

Analysis of `redlist_species_data_*/assessments.csv` for building three atlas scatter views: **conservation similarity map**, **threat landscape**, and **conservation attention gap**.

**Related docs:** [DEEPSCATTER_BEST_LAYOUTS.md](./DEEPSCATTER_BEST_LAYOUTS.md) (design rationale), [LANDSCAPE_FEATURES.md](./LANDSCAPE_FEATURES.md) (current 94-dim UMAP recipe), [SCATTER_METRICS.md](./SCATTER_METRICS.md) (attention/gap metrics), [DEEPSCATTER_FACETS.md](./DEEPSCATTER_FACETS.md) (atlas wiring).

**Source file:** `redlist_species_data_2f02b1b4-6088-405f-8387-1e285bb770f2/assessments.csv`  
**Rows:** 172,620 (1 assessment per taxon in this download)  
**Join path:** `assessments.csv` → `pipeline/iucn_assessments_convert.py` → `data/iucn_assessments.tsv` (NCBI `taxid`) → species matrix → `data/scatter/species_{layout}.parquet` (default: `species_landscape.parquet`)

---

## Column inventory

| # | Field | Fill rate | Structure | Usability |
|---|-------|-----------|-----------|-----------|
| 1 | `assessmentId` | 100% | ID | Join key only |
| 2 | `internalTaxonId` | 100% | ID | IUCN-only ID; map to NCBI via scientific name |
| 3 | `scientificName` | 100% | string | Join key only |
| 4 | `redlistCategory` | 100% | categorical | **Excellent** — primary status signal |
| 5 | `redlistCriteria` | 33% | coded (A–E) | Good for threatened subset; empty for LC/DD |
| 6 | `yearPublished` | 100% | date | Metadata; weak feature |
| 7 | `assessmentDate` | 100% | date | Metadata; weak feature |
| 8 | `criteriaVersion` | 100% | version | Metadata |
| 9 | `language` | 100% | string | Not a feature |
| 10 | `rationale` | 97% | free text | Too noisy for embedding |
| 11 | `habitat` | 89% | **free text** | Needs NLP or keyword lexicon |
| 12 | `threats` | 88% | **free text** | Needs keyword lexicon or embeddings |
| 13 | `population` | 91% | **free text** | Narrative, not numeric abundance |
| 14 | `populationTrend` | 96% | categorical | **Excellent** |
| 15 | `range` | 90% | free text | Geographic narrative; hard to parse |
| 16 | `useTrade` | 72% | free text | Exploitation/trade pressure |
| 17 | `systems` | ~100% | pipe-delimited | **Excellent** — terrestrial / freshwater / marine |
| 18 | `conservationActions` | 87% | free text | Response signal; better for gap map than position |
| 19 | `realm` | 92% | pipe-delimited | **Good** — biogeographic realm |
| 20 | `yearLastSeen` | **2.2%** | year | High signal when present; very sparse |
| 21 | `possiblyExtinct` | 100% | bool | 1,406 `true` |
| 22 | `possiblyExtinctInTheWild` | 100% | bool | 64 `true` |
| 23 | `scopes` | 100% | categorical | 91% `Global` — weak discriminator |

**Critical constraint:** `threats`, `habitat`, `conservationActions`, `useTrade`, `range`, and `population` are almost all prose, not structured IUCN classification codes. The HTML export (`assessments_with_html.csv`) has the same structure — no machine-readable threat headings.

---

## Distribution summary (172,620 rows)

### `redlistCategory`

| Category | Count |
|----------|------:|
| Least Concern | 89,628 |
| Data Deficient | 22,760 |
| Endangered | 19,873 |
| Vulnerable | 17,999 |
| Critically Endangered | 10,774 |
| Near Threatened | 9,825 |
| Extinct | 935 |
| Extinct in the Wild | 81 |
| Lower Risk (legacy) | 745 |

### `populationTrend`

| Trend | Count |
|-------|------:|
| Unknown | 83,091 |
| Decreasing | 41,837 |
| Stable | 39,061 |
| Increasing | 1,253 |
| (empty) | 7,378 |

### `realm`

| Realm | Count |
|-------|------:|
| Neotropical | 51,724 |
| Afrotropical | 32,843 |
| Indomalayan | 30,692 |
| Palearctic | 23,954 |
| Australasian | 19,604 |
| Nearctic | 9,961 |
| Oceanian | 5,598 |
| Antarctic | 265 |
| (empty) | 13,659 |

### `systems` (multi-label; counts overlap)

| System | Count |
|--------|------:|
| Terrestrial | 129,832 |
| Freshwater | 41,325 |
| Marine | 19,516 |

### `redlistCriteria` (letter codes, when present)

| Code | Count |
|------|------:|
| (empty) | 116,309 |
| B (range/restriction) | 41,543 |
| D (population size) | 8,108 |
| A (population reduction) | 7,992 |
| C (small population + decline) | 2,989 |
| E (quantitative analysis) | 10 |

### Extinction flags

| Field | `true` | `false` |
|-------|-------:|--------:|
| `possiblyExtinct` | 1,406 | 171,214 |
| `possiblyExtinctInTheWild` | 64 | 172,556 |

### Threat keyword hits (substring, non-exclusive)

Top hits in `threats` prose:

| Keyword | Hits |
|---------|-----:|
| habitat | 61,833 |
| agriculture | 26,643 |
| deforestation | 18,824 |
| logging | 17,520 |
| fire | 16,618 |
| development | 15,856 |
| mining | 11,862 |
| climate | 11,333 |
| pollution | 10,906 |
| invasive | 7,504 |
| fishing | 5,858 |
| trade | 5,516 |
| dams | 2,935 |
| disease | 2,855 |
| hunting | 2,345 |

Keywords overlap heavily (`habitat` appears in ~41% of threat texts). A naive lexicon needs IUCN-aligned categories, not raw substring counts.

### `conservationActions` keyword hits

| Keyword | Hits |
|---------|-----:|
| protected | 71,811 |
| research | 39,751 |
| habitat | 28,069 |
| management | 14,132 |
| monitoring | 13,245 |
| legislation | 4,149 |
| trade | 4,172 |
| harvest | 3,178 |
| education | 2,757 |
| captive | 1,796 |
| reintroduction | 931 |

Useful as a **response/attention** signal, not for threat-position UMAP.

### Other notes

- **Assessment multiplicity:** 172,620 unique taxa, 0 duplicate assessments in this download.
- **`scopes`:** 157,501 `Global` (91%); regional scope variants are rare.
- **`yearLastSeen`:** filled for 3,807 species only.

---

## What the pipeline already uses

`pipeline/iucn_assessments_convert.py` extracts into `data/iucn_assessments.tsv`:

| CSV field | TSV column |
|-----------|------------|
| `redlistCategory` | `redlist_category` |
| `populationTrend` | `population_trend` |
| `systems` | `systems` |
| `realm` | `realm` |
| `possiblyExtinct` | `possibly_extinct` |
| `possiblyExtinctInTheWild` | `possibly_extinct_ew` |
| `habitat` | `habitat` (text) |
| `threats` | `threats` (text) |
| `population` | `population` (text) |

Structured fields are joined onto the species matrix (`build_species_matrix.py`). Text fields feed **length only** into the landscape UMAP via `log1p_iucn_text_len` (`landscape_features.py`).

**Not yet extracted:** `redlistCriteria`, `conservationActions`, `useTrade`, `range`, `yearLastSeen`, `scopes`.

**Current landscape UMAP (94 dims)** mixes three blocks — not a pure conservation map:

| Block | Dims | Source |
|-------|-----:|--------|
| IUCN / biogeography | 26 | category, trend, systems, realm, extinct flags |
| Tax lineage hash bag | 64 | `tax_lineage` |
| Knowledge logs | 4 | read/assembly/annotation counts + IUCN text length |

`LANDSCAPE_FEATURES.md` explicitly excludes parsed threat taxonomy from free text as noisy.

---

## Three deepscatter views

### Option 1 — Conservation similarity map

**Question:** Which species face similar conservation situations, regardless of taxonomy?

**Position:** `UMAP(conservation_vector)` — use IUCN metadata only; **exclude lineage** from position.

| Block | Source fields | Encoding |
|-------|---------------|----------|
| Status | `redlistCategory` | one-hot (9) or ordinal `iucn_code` |
| Trend | `populationTrend` | one-hot: Decreasing / Stable / Increasing / Unknown |
| Biogeography | `realm` | one-hot (7 realms + other) |
| Environment | `systems` | multi-hot: terrestrial / freshwater / marine |
| Extinction flags | `possiblyExtinct`, `possiblyExtinctInTheWild` | 2 binary dims |
| Criteria | `redlistCriteria` | letter multi-hot A/B/C/D/E |
| Last sighting | `yearLastSeen` | `log1p(2026 − year)` or missingness flag (sparse) |

**Optional text enrichment** (largest quality lift):

```text
concat(habitat, threats, conservationActions, useTrade)
  → TF-IDF top-N terms
  → or sentence embedding (MiniLM) → 32–64 PCA dims
```

Without text, clusters collapse to coarse buckets (e.g. “Neotropical terrestrial decreasing VU”).

| Channel | Field |
|---------|-------|
| x, y | `UMAP(conservation_vector)` → e.g. `conservation_x`, `conservation_y` |
| color | `iucn_code` |
| size | `log10_run_count` or `log1p(assembly_count)` |
| foreground | `ancestor_d{depth}` eq pinned taxid (atlas scatter) |

---

### Option 2 — Threat landscape

**Question:** Which threat regimes dominate, and do different phyla share threat space?

**Position:** `UMAP(threat_vector)` — primary signal from `threats` (88% filled).

**Tier A — Keyword lexicon (fast, interpretable)**  
Map prose to IUCN's 12 threat categories:

| Category | Example keywords in data |
|----------|--------------------------|
| Agriculture & aquaculture | agriculture, deforestation, logging |
| Biological resource use | fishing, hunting, harvest, trade |
| Natural system modification | dams, fire, habitat (noisy) |
| Pollution | pollution |
| Climate change | climate |
| Invasive species | invasive |
| Energy & mining | mining |
| Residential/development | development |
| … | disease, etc. |

~12–20 binary dims; optionally add `useTrade` keywords.

**Tier B — Text embeddings (better similarity)**  
Embed `threats` (+ optionally `useTrade`) → UMAP on embedding dims.

**Context dims** (keep threat space from collapsing to status):

- `systems` (3) — marine fisheries ≠ terrestrial logging
- `realm` (8)
- Do **not** include `redlistCategory` in the threat vector

| Channel | Field |
|---------|-------|
| x, y | `UMAP(threat_vector)` → e.g. `threat_x`, `threat_y` |
| color | `phylum_name` or dominant threat category |
| size | `log10_run_count` |
| filter | optional: `iucn_code >= 3` (threatened only) |

---

### Option 3 — Conservation attention gap map

**Question:** High conservation need, low scientific attention — where are the gaps?

**No UMAP needed** — direct axes are clearer and swappable via `plotAPI` without retiling.

#### Conservation need (Y) — from assessments

| Signal | Field | Weight idea |
|--------|-------|-------------|
| Status severity | `redlistCategory` → `iucn_code` | 0–7 ordinal |
| Trajectory | `populationTrend` | Decreasing +1, Stable 0, Increasing −0.5 |
| Extinction flags | `possiblyExtinct`, `possiblyExtinctInTheWild` | +2 / +3 |
| Criteria depth | `redlistCriteria` | A-series vs B-series severity |
| Last seen | `yearLastSeen` | boost if filled and old |

Example composite:

```text
conservation_need =
  iucn_code
  + 0.5 × decreasing
  + 2 × possibly_extinct
  + criteria_severity_bonus
```

#### Scientific attention (X) — from matrix, not assessments

Per `SCATTER_METRICS.md`, trust **counts**, not summed bases:

| Signal | Matrix field |
|--------|--------------|
| Dataset breadth | `run_count` → `log10_run_count` |
| Reference depth | `assembly_count`, `annotation_count` (log1p) |
| Pipeline stage | `data_tier` (0–3) |

**Already in repo:** `pipeline/scatter_facet_layers.py` defines:

```python
layer_c_y = iucn_code - log10_catalog_signal
```

`layer_c_y` is the attention-gap axis (need minus attention). `landscape_features.py` also computes a weighted `knowledge_score` for QA.

| Channel | Field |
|---------|-------|
| x | `log10_run_count` or `knowledge_score` |
| y | `conservation_need` or `layer_c_y` |
| color | `iucn_code` or `data_tier` |
| filter | optional: threatened only |

**Interpretation:** upper-left = high need, low attention.

---

## Recommended tile presets

```text
Preset A — conservation_similarity
  position: UMAP([category, trend, realm, systems, extinct flags, criteria, text_embedding?])
  color:    iucn_code
  size:     log10_run_count

Preset B — threat_landscape
  position: UMAP([threat_keywords or threat_embedding, systems, realm])
  color:    phylum_name
  size:     log10_run_count

Preset C — attention_gap
  x:        log10_run_count  (or knowledge_score)
  y:        conservation_need  (or layer_c_y)
  color:    iucn_code
  filter:   optional threatened-only
```

---

## Coverage caveats

| Population | ~N | Notes |
|------------|---:|-------|
| IUCN assessments (CSV) | 172,620 | Full Red List download |
| Matrix species | ~105k | Catalog + iucn_only union |
| Catalog with IUCN | ~25k | 24% of catalog |
| IUCN-only matrix rows | ~80k | No sequencing data; sit at Y≈0 in gap views |
| Threatened (VU/EN/CR/EW) | ~4.7k | 72% have reads but no assembly |

Gap map is most actionable on **threatened + catalog** species.

---

## IUCN text embedding cache

Offline sentence-transformers embeddings per assessment text field, built independently (no concat at encode time). **Current cache: `threats` only** (~108k taxids, 85% with text). Other fields are supported via `--fields` when needed.

### Fields

| Field | TSV column | Status |
|-------|------------|--------|
| Threats | `threats` | **cached** (`data/cache/iucn_text_embeddings/threats/`) |
| Habitat | `habitat` | optional (`--fields habitat`) |
| Population | `population` | optional |
| Conservation actions | `conservation_actions` | optional (from CSV `conservationActions`) |

Module: `pipeline/iucn_text_embeddings.py`, CLI: `pipeline/build_iucn_text_embeddings.py`

### Model choice

| Model | Default? | Raw dims |
|-------|----------|----------|
| `all-MiniLM-L6-v2` | **yes** | 384 |
| `all-mpnet-base-v2` | `--model` flag | 768 |

First run downloads weights to `~/.cache/torch/sentence_transformers/`.

### CLI

```bash
# Re-convert TSV (includes conservation_actions)
pipenv run python pipeline/iucn_assessments_convert.py

# Build threats cache (default; MiniLM, PCA 32)
pipenv run python pipeline/build_iucn_text_embeddings.py

# Optional: additional fields
pipenv run python pipeline/build_iucn_text_embeddings.py \
  --fields habitat,population,conservation_actions
```

Flags: `--force` (re-embed), `--skip-embed` (reuse raw `.npy`, re-run PCA only), `--cache-dir` (default `data/cache/iucn_text_embeddings/`).

**Built cache (threats):** 107,864 taxids; 92,117 with threat text (85.4%); PCA explained variance sum 0.60 (32 dims).

### Cache layout (gitignored)

```
data/cache/iucn_text_embeddings/
  taxids.npy                          # shared index, taxids with NCBI mapping
  manifest.json
  threats/
    embeddings_all-MiniLM-L6-v2.npy   # (n, 384)
    pca_all-MiniLM-L6-v2_32.npz
    features_all-MiniLM-L6-v2_32.npy  # (n, 32) z-scored PCA
    has_text.npy
    field_manifest.json
  habitat/ …   # not built yet
```

PCA is fit on non-empty text rows only; empty text → zero vector.

### Downstream composition (not yet wired)

| View | Assembly |
|------|----------|
| Threat landscape | `features_threats` (32) + systems/realm (11) → UMAP |
| Conservation similarity | threats + habitat + population PCA + structured IUCN (26) → UMAP |
| Attention gap | structured scalars; `conservation_actions` optional for color |

---

## Implementation checklist

- [x] Extend `iucn_assessments_convert.py` with `conservation_actions`
- [x] Per-field sentence-transformers cache (`build_iucn_text_embeddings.py`) — threats field built
- [x] Add `conservation_need`, `attention_score`, and catalog metrics to scatter parquet export (`scatter_metrics.py`)
- [x] Conservation similarity UMAP (IUCN block 26 + threats PCA 32, no lineage) → `species_conservation.parquet` + tiles
- [x] Threat landscape UMAP (threats PCA 32 + systems/realm 11) → `species_threat.parquet` + tiles
- [x] Attention gap layout (`x=attention_score`, `y=conservation_need`) → `species_gap.parquet` + tiles
- [x] Multi-layout pipeline (`build_scatter_tiles.py --layout all`) + layout registry (`scatter_layouts.py`)
- [x] Atlas UI layout switcher (`AtlasScatterPanel` + `lib/scatter/layouts.ts`); color always `iucn_code`
- [ ] Extend `iucn_assessments_convert.py` with `redlist_criteria`, `year_last_seen`, `use_trade`
- [ ] Build habitat / population / conservation_actions text embedding caches (threats only today)

**Tile paths** (version `v20260614`):

| Layout | Parquet | Tiles |
|--------|---------|-------|
| `landscape` | `data/scatter/species_landscape.parquet` | `/tiles/species/landscape/v20260614` |
| `conservation` | `data/scatter/species_conservation.parquet` | `/tiles/species/conservation-similarity/v20260614` |
| `threat` | `data/scatter/species_threat.parquet` | `/tiles/species/threat-landscape/v20260614` |
| `gap` | `data/scatter/species_gap.parquet` | `/tiles/species/attention-gap/v20260614` |

**Smoke check:** `BASE_URL=http://localhost:8080 npm run check:atlas-scatter`
