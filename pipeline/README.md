# IUCN Pipeline

One matrix row per IUCN-assessed species from `simple_summary.csv`, with boolean flags for GBIF, iNaturalist, and NCBI genomic evidence.

See **[PIPELINE.md](PIPELINE.md)** for the resolution cascade and publish flow.

## Layout

```
pipeline/
  run.py                  # weekly orchestrator
  schema.py               # shared constants + column schemas
  iucn_taxonomy.py        # IUCN rank hierarchy for rollups
  scatter_features.py     # lineage + conservation UMAP features
  load_iucn_species.py
  iucn_resolver.py
  ncbi_evidence.py
  taxonomy_db.py
  fetch/                  # download scripts
  build/                  # matrix, rollups, scatter, tiles, labels
  output/                 # matrix + publish artifacts (gitignored)
```

## Run

**Weekly CI (fetch + matrix + manifest):**

```bash
python -m pipeline
python -m pipeline --skip-download --limit 1000
```

**Local publish (matrix + rollups + UMAP parquet + tiles + GeoJSON):**

```bash
python -m pipeline --skip-download \
  --steps matrix,rollups,scatter,tiles,labels,manifest --limit 1000
```

Requires `.venv` with `requirements.txt` (pyarrow, umap-learn). Tiles step requires [quadfeather](https://github.com/bmschmidt/quadfeather) on PATH.

Fetch modes: **ensure** for GBIF/iNat/NCBI taxonomy (reuse cache), **refresh** for IUCN export and genomic TSVs.

## Inputs and caches

| Path | Role |
|------|------|
| `datasets/simple_summary.csv` | IUCN Red List export |
| `datasets/taxonomy.db` | NCBI species tree |
| `datasets/cross_universe.db` | GBIF + iNat + OTL bridge |
| `datasets/*.tsv` | assemblies, annotations, reads, GOAT |
| `cache/gbif/backbone.zip` | GBIF backbone |
| `cache/inaturalist/taxonomy.dwca.zip` | iNat taxonomy |
| `cache/otl/` | Open Tree synthesis (optional) |

## Outputs

| File | Description |
|------|-------------|
| `output/iucn_species_matrix.tsv` | ~172k species rows, camelCase columns |
| `output/iucn_flag_counts.tsv` | per-flag summary |
| `output/iucn_taxon_rollups.tsv` | IUCN rank hierarchy rollups (counts by category/dataset/bucket) |
| `output/iucn_species_scatter.parquet` | matrix fields + UMAP `x`/`y` |
| `output/iucn_clade_labels.geojson` | kingdom/phylum label centroids |
| `output/tiles/iucn/v{date}/` | quadfeather deepscatter pyramid |
| `../site-data/` | manifest + rollups + geojson + tiles for Pages |

Matrix columns use camelCase (`hasGbif`, `ncbiTaxid`, …). `hasNcbi` is not exported; use non-empty `ncbiTaxid`.

## CI

`.github/workflows/weekly-iucn-pipeline.yml` runs `python -m pipeline` weekly (matrix only, no scatter/tiles).  
Deploy: **[docs/GITHUB_PAGES.md](../docs/GITHUB_PAGES.md)**.

## Deferred

Next.js wiring for `/explore` deepscatter route.
