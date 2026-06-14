# Landscape feature recipe — conservation species map

Specification for the **landscape** deepscatter view in the taxonomy atlas. One point = one species (`taxid`). Position comes from a precomputed UMAP embedding on a 94-dim feature vector. **Color** uses IUCN status only (atlas default).

**Related docs:** [DEEPSCATTER_FACETS.md](./DEEPSCATTER_FACETS.md) (atlas wiring), [SCATTER_METRICS.md](./SCATTER_METRICS.md) (field trustworthiness), [.cursor/skills/deepscatter/SKILL.md](./.cursor/skills/deepscatter/SKILL.md) (tiling and Next.js integration).

---

## Design rule (PubMed pattern)

The [Nomic PubMed map](https://static.nomic.ai/pubmed.html) embeds high-dimensional **content** features, then colors by metadata. Same contract here:

| Layer | Role | Source |
|-------|------|--------|
| **Position (`x`, `y`)** | Similarity in taxonomy + conservation + knowledge | UMAP on 94-dim vector |
| **Color** | IUCN status | `iucn_code` (atlas default) |
| **Labels** | Phylum names at cluster centroids | `labels.geojson` from mean `(x,y)` per phylum |
| **Foreground** | Selected tree clade | `ancestor_d{N}` eq selected taxid (N = tree depth) |

Phylum labels overlay the map; phylum is **not** a hard spatial cage (clusters can bleed when IUCN/realm/knowledge differ).

---

## Data sources

| Source | Fields used | Notes |
|--------|-------------|-------|
| `data/staged/05_eukaryotic_species_matrix.tsv` | `tax_lineage`, structured IUCN, read/assembly/annotation counts | ~184k species |
| `data/iucn_assessments.tsv` | `habitat`, `threats`, `population` text | Text lengths for knowledge features |
| `data/staged/taxonomy.sqlite` | `rank`, `name` | Phylum resolution for GeoJSON labels only |

---

## Feature vector (94 dimensions)

Implemented in `pipeline/landscape_features.py`. All columns **z-scored** before UMAP.

### A. IUCN / biogeography block (26 dims)

| Block | Dims |
|-------|------|
| IUCN category one-hot | 9 |
| Population trend one-hot | 4 |
| Systems multi-hot | 3 |
| Realm one-hot (7 standard + other/multi) | 8 |
| Possibly extinct flags | 2 |

### B. Tax lineage hash bag (64 dims)

Full path Eukaryota → species from `tax_lineage`. For each taxid on the path (skip Eukaryota root):

```python
buckets[hash(tid) % 64] = 1.0
```

Shared lineage prefixes → shared buckets → phylogenetic neighborhoods without 69-way phylum one-hot cages.

### C. Weighted knowledge (4 dims)

Four separate **log1p** features (not a single composite axis):

| Feature | Source | Relative weight in QA scalar |
|---------|--------|------------------------------|
| `log1p_read_count` | sum of `wgs_*_count` + `rnaseq_*_count` | 1.0 |
| `log1p_assembly_count` | `assembly_count` | 3.0 |
| `log1p_annotation_count` | `annotation_count` | 5.0 |
| `log1p_iucn_text_len` | `len(habitat)+len(threats)+len(population)` | 0.5 |

Weighted sum `knowledge_score` is computed for **QA only** (warn if `|corr(x, knowledge_score)| > 0.65`).

**Not included:** binary `in_catalog` / `catalog_source` flags (hard two-lobe split).

---

## Total dimension count

| Block | Dims |
|-------|------|
| IUCN / biogeography | 26 |
| Lineage hash bag | 64 |
| Knowledge logs | 4 |
| **Total** | **94** |

---

## Fields excluded from embedding

| Field | Reason |
|-------|--------|
| `catalog_source`, `in_catalog` (binary) | Hard catalog vs iucn_only split |
| Raw `run_count` without log1p split | Dominant effort axis → diagonal band |
| Assembly quality (BUSCO, N50, gene counts) | Sparse (~8.5k annotated) |
| Parsed threat taxonomy from free text | Noisy |

---

## UMAP and coordinate export

**Scripts:** `pipeline/scatter_landscape.py`, wired from `pipeline/build_scatter_tiles.py --embedding landscape`.

1. Export slim parquet (`scatter_export.py`) with phylum metadata.
2. Build `(n × 94)` matrix from matrix TSV + IUCN text by `taxid`.
3. Fit UMAP (cosine, `n_neighbors=30`, `min_dist=0.5`, `spread=1.5`).
4. Scale to ±250; write `landscape_x/y` and tile columns `x`/`y`.
5. Build `labels.geojson` at phylum centroids on UMAP coords.

```bash
pipenv run python pipeline/build_scatter_tiles.py --embedding landscape --step all
```

Tiles: `tiles/species/landscape/vYYYYMMDD/`

---

## Band risk notes

| Signal | Effect |
|--------|--------|
| Lineage hash | Soft phylum/kingdom neighborhoods; can bleed |
| IUCN + realm | Biogeography and threat blobs (expected) |
| Knowledge (4 dims) | Moderate catalog gradient; softened vs binary flags |
| Single composite knowledge axis | **Avoid** — recreates study-gap diagonal |

---

## Atlas encoding defaults

| Channel | Default |
|---------|---------|
| `x`, `y` | UMAP landscape |
| `color` | `iucn_code` |
| `foreground` | `ancestor_d{depth} == selectedTaxid` when clade selected |
| Labels | `labels.geojson` phylum centroids |

---

## Pipeline checklist

- [x] `pipeline/landscape_features.py` — 94-dim recipe + z-score
- [x] `pipeline/scatter_landscape.py` — UMAP + QA correlations
- [x] `pipeline/build_scatter_tiles.py` — `--embedding landscape` default
- [x] `labels.geojson` — phylum centroids on UMAP coords
- [x] Docker `TILE_URL` → `tiles/species/landscape/v*`
