# Web App Stack — DeepScatter Explorer

Architecture and stack for a taxonomy-centric web app with a **DeepScatter-focused explore UI** and a **small discovery section**. Metadata only (no local file downloads); pointers to INSDC / Annotrieve / IUCN.

See also: [MODELS.txt](./MODELS.txt) (data schemas), [docs.md](./docs.md) (Lifemap / tree pipeline), [TREE_OF_LIFE.md](./TREE_OF_LIFE.md).

---

## Goals

| Goal | Approach |
|------|----------|
| Main UX | Interactive scatterplot of **species** with swappable x/y metrics |
| Taxon filter | User selects a clade; only species under that taxon remain visible |
| Discovery | Lightweight home: search, stats, curated entry points into explore |
| Backend RAM | ~1–2 GB (SQLite catalog, thin API) |
| Viz data | Static Apache Arrow tiles on disk (quadfeather), served via nginx |
| Sequences / GFF | Remote URLs only — never downloaded or stored locally |

---

## Recommended stack

| Layer | Choice | Why |
|-------|--------|-----|
| **Framework** | **Next.js App Router** (`next-app/`) | Already in repo; routing, layouts, shareable URLs |
| **Scatter UI** | **[deepscatter](https://github.com/nomic-ai/deepscatter)** (client-only) | WebGL + tiled Arrow; millions of points in browser |
| **Tiling** | **[quadfeather](https://github.com/bmschmidt/quadfeather)** | Builds feather tile pyramid from Parquet/CSV |
| **Discovery UI** | **shadcn/ui** + Tailwind | Cards, combobox, sheet, tabs — already in `next-app/` |
| **Scatter state** | **URL search params** (+ optional Zustand) | e.g. `?taxon=337687&x=genome_size&y=run_count` |
| **API** | **FastAPI** + read-only **SQLite** | Taxon tree, search, point detail; low memory |
| **Catalog DB** | **SQLite** (taxa, organisms, assemblies, annotations, bioprojects) | See MODELS.txt |
| **Fact tables** | **Parquet** (runs; optional biosamples) | Queried at ETL time, not at API hot path |
| **ETL / layout** | **Python + DuckDB** (cron) | Sync INSDC, build `species_scatter.parquet`, tile |
| **Tile hosting** | **nginx** static files on local disk | Zero RAM for tile serving |
| **Deploy** | **Single VPS** (large disk, 1–2 GB RAM) | nginx + FastAPI + `next start` |

**Omit for v1:** Redis, Postgres, MongoDB, Elasticsearch / Meilisearch (SQLite FTS5 is enough for taxon search).

---

## App layout

```
┌────────────────────────────────────────────────────────────┐
│  Nav: Home | Explore | Taxonomy                            │
├────────────────────────────────────────────────────────────┤
│                                                            │
│   HOME (/)  — Discovery (small)                            │
│   • Taxon search → /explore?taxon=…                        │
│   • Global stat cards (species with data, CR count, …)     │
│   • Curated entry points ("Mammalia", "RNA-seq rich")      │
│                                                            │
│   EXPLORE (/explore)  — DeepScatter (~90% viewport)        │
│   ┌──────────┬─────────────────────────────────────────┐ │
│   │ Controls │                                         │ │
│   │ Taxon    │         DeepScatter canvas              │ │
│   │ X / Y    │                                         │ │
│   │ Color    │                                         │ │
│   └──────────┴─────────────────────────────────────────┘ │
│   Click point → species detail sheet + INSDC links         │
│                                                            │
│   TAXONOMY (/taxonomy)  — compact tree / table (optional)  │
│   SPECIES (/species/[id]) — detail fallback page           │
└────────────────────────────────────────────────────────────┘
```

**DeepScatter is the product.** Discovery is a landing layer that deep-links into `/explore`, not a second heavy visualization.

---

## Frontend structure

```
next-app/
  app/
    page.tsx                  # Discovery home
    explore/
      page.tsx                # Full-viewport scatter (client component)
    taxonomy/page.tsx         # Light taxonomy browse
    species/[id]/page.tsx     # Species detail fallback
  components/
    scatter/
      DeepScatterPlot.tsx     # 'use client'; dynamic import deepscatter
      ScatterControls.tsx     # taxon picker, x/y/color selects
      useScatterEncoding.ts   # URL params ↔ deepscatter encoding
    discovery/
      TaxonSearch.tsx
      FeaturedClades.tsx
      GlobalStats.tsx
    species-detail-sheet.tsx  # Reused on point click
```

### DeepScatter in Next.js

- Mark the plot component with `'use client'`.
- Use `dynamic(() => import(...), { ssr: false })` — WebGL cannot SSR.
- Set `source_url` to static tiles, e.g. `/tiles/species/v20250611/`.
- On axis or taxon change: update deepscatter `encoding` and sync URL params (no full page reload).

### Discovery section (keep small)

| Block | Data source | Action |
|-------|-------------|--------|
| Taxon search | SQLite FTS via API | Navigate to `/explore?taxon={id}` |
| Global stats | API or `data/rank_statistics.json` | Stat cards on home |
| Featured clades | Config JSON or hardcoded | Link to `/explore?taxon=…` |
| Top species tables | API | Open detail sheet or explore |

Reuse existing components: `stat-card.tsx`, `page-header.tsx`, `app-sidebar.tsx`, `species-detail-sheet.tsx`.

---

## Species scatter data model

One row per species. All plottable metrics as columns in a single wide export for deepscatter.

### Core columns

```
species_tax_id
scientific_name

# Taxon filter (rank ancestry — see below)
kingdom_id, phylum_id, class_id, order_id, family_id, genus_id

# Counts / flags
assembly_count, run_count, bioproject_count
has_assembly, has_runs, has_annotations

# Metrics (raw + log10 precomputed for skewed fields)
genome_size, log10_genome_size
contig_n50, log10_contig_n50
gc_percent
coding_genes, lncrna_genes, transcripts

# Conservation
iucn_code          # numeric: LC=1, NT=2, … NE=0

# Optional tree layout preset
tree_x, tree_y
```

Build via DuckDB join from SQLite catalog tables defined in MODELS.txt.

### Dynamic x / y (interchangeable axes)

DeepScatter encodes axes via a Vega-Lite–style `encoding` object. **x and y are field mappings**, not fixed column names:

```js
encoding: {
  x: { field: "log10_genome_size", transform: "literal" },
  y: { field: "log10_run_count",    transform: "literal" },
  color: { field: "iucn_code", range: "category10" },
  size:  { field: "run_count", transform: "log" },
  filter: { field: "passes_filter", domain: [1, 1] },
}
```

**UI:** dropdowns for X axis, Y axis, color, and size. On change, update `encoding.x.field` / `encoding.y.field` and call the plot update API.

**Presets** (optional UX): named views that set x + y + color together, e.g. “Genome quality”, “Annotation richness”, “Conservation”.

### Tiling note

quadfeather partitions tiles using the x/y columns present **at tile time**. For ~50k–200k species with data, a **single wide Parquet file** plus one quadfeather build (default x/y pair) is sufficient; swap displayed fields via encoding without retiling.

If zoom performance degrades, pre-tile a small set of popular axis pairs (`genome_vs_runs`, `genes_vs_lncrna`, …) and switch `source_url` in the UI.

### Taxon filter (GPU-friendly)

Store **ancestor tax_id per rank** on each species row. When the user selects taxon `T` with rank `class`:

```js
filter: { field: "class_id", domain: [T.tax_id, T.tax_id] }
```

Map rank → column: `kingdom` → `kingdom_id`, `phylum` → `phylum_id`, etc. Works for any taxon without fetching large species ID lists.

Default filter: show only species with data (`has_runs OR has_assembly OR has_annotations`).

---

## Backend API (minimal)

Tiles are **not** served by the API — static files only.

```
GET  /api/taxa/search?q=homarus
GET  /api/taxa/{tax_id}                 # name, rank, subtree rollup stats
GET  /api/taxa/{tax_id}/ancestors       # rank → tax_id map for filter UI
GET  /api/organisms/{tax_id}            # species detail + outbound URLs
GET  /api/stats/summary                 # discovery home cards
```

**Alternative:** Next.js Route Handlers + `better-sqlite3` for a single-process deploy. FastAPI is preferable if sync/ETL already lives in Python.

### URL templates (metadata pointers)

```
ENA browser:     https://www.ebi.ac.uk/ena/browser/view/{accession}
NCBI bioproject: https://www.ncbi.nlm.nih.gov/bioproject/{accession}
NCBI taxonomy:   https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id={tax_id}
NCBI dataset:    https://www.ncbi.nlm.nih.gov/datasets/genome/{accession}/
Annotrieve:      https://genome.crg.es/annotrieve/#!species/{tax_id}
```

---

## Data and build pipeline

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────────────┐
│ INSDC bulk  │────▶│ SQLite       │────▶│ DuckDB                  │
│ Annotrieve  │     │ catalog      │     │ species_scatter.parquet │
│ IUCN        │     │ + Parquet    │     └───────────┬─────────────┘
└─────────────┘     └──────────────┘                 │
                                                     ▼
                                          ┌─────────────────────┐
                                          │ quadfeather         │
                                          │ → feather tiles     │
                                          └──────────┬──────────┘
                                                     ▼
                                          /var/www/tiles/species/v{date}/
```

**Weekly cron:**

1. Sync INSDC metadata → SQLite (+ Parquet for runs).
2. DuckDB: join organisms + assemblies + annotations + run rollups → `species_scatter.parquet`.
3. `quadfeather --files species_scatter.parquet --tile_size 50000 --destination tiles/species/v{date}`.
4. Rebuild SQLite FTS5 taxon search index.
5. Bump `NEXT_PUBLIC_TILE_VERSION` in frontend env.

**Sync order** (from MODELS.txt): taxa → organisms → assemblies → gene_annotations → bioprojects + runs → recompute rollups.

---

## Deployment (single machine, 1–2 GB RAM)

```
nginx
  /tiles/*     → disk (feather tiles, large volume OK)
  /api/*       → FastAPI (uvicorn, 1 worker)
  /*           → Next.js (next start)
```

| Component | RAM (steady) |
|-----------|----------------|
| FastAPI | ~256–512 MB |
| Next.js | ~256–512 MB |
| SQLite | disk + small cache |
| DeepScatter | **browser GPU** — not server RAM |

Pin SQLite pragmas for low memory: `cache_size = -65536` (64 MB), `mmap_size` for disk-backed reads.

---

## What to avoid

| Anti-pattern | Why |
|--------------|-----|
| SSR the deepscatter component | WebGL requires client-only render |
| Serve tiles through FastAPI | Wastes RAM; use nginx |
| Retile on every axis change | Slow; use wide Parquet + encoding swap |
| Store 25M biosamples in API hot path | Pre-aggregate to species rollups |
| Elasticsearch for v1 search | SQLite FTS5 is enough |
| MapLibre + deepscatter coordinate sync | Defer to v2; use feature-space scatter in v1 |

---

## Phased rollout

| Phase | Scope | Outcome |
|-------|-------|---------|
| **0** | `species_scatter.parquet` + quadfeather + `/explore` fixed axes | Prove tiling pipeline |
| **1** | Dynamic x/y/color + taxon filter + URL state | Core explore UX |
| **2** | Discovery home + taxon search + detail sheet on click | Full app shell |
| **3** | Extra layers (assemblies, runs as separate scatter tables) | Multi-entity views |
| **4** | Tree-layout coordinates (`tree_x`, `tree_y`) | Points on tree of life |
| **5** | MapLibre tree + deepscatter overlay | Unified coordinate space |

---

## Stack alternatives (not recommended for v1)

| Option | Verdict |
|--------|---------|
| SvelteKit | Good deepscatter examples, but would rewrite existing `next-app/` |
| Vite SPA only | Loses App Router and existing pages |
| Observable | Prototyping only |
| Always-on ClickHouse | Unnecessary for species-scale scatter exports |
| Postgres / MongoDB server | Higher RAM; SQLite sufficient for catalog |

---

## Summary

> **Next.js + shadcn** (discovery + chrome) · **deepscatter** (explore viewport) · **FastAPI + SQLite** (metadata API) · **DuckDB + quadfeather** (species scatter export + static tiles on nginx)

DeepScatter handles rendering; DuckDB builds the wide species table; rank ancestry columns handle taxon filtering; URL params make views shareable.
