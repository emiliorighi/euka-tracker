# Atlas scatter — UMAP similarity landscape

The taxonomy atlas scatter is a **UMAP similarity map** (PubMed pattern): position from a 94-dim feature embedding; **IUCN color**; **phylum labels** overlaid at cluster centroids.

Tiles: `tiles/species/landscape/vYYYYMMDD/`  
Parquet: `data/scatter/species_scatter.parquet`

Legacy study-gap disc pack: `--embedding study-map` → `tiles/species/study-map/vYYYYMMDD/`

---

## Coordinate system

| Stage | Module | Output |
|-------|--------|--------|
| Feature matrix | `pipeline/landscape_features.py` | 94-dim vector per species |
| UMAP embed | `pipeline/scatter_landscape.py` | `x`, `y` scaled to ±250 |
| Phylum labels | `pipeline/scatter_build_labels.py` | `labels.geojson` at mean `(x,y)` per phylum |

**Features:** IUCN conservation/biogeography (26 dims) + tax lineage hash bag (64 dims) + weighted knowledge logs (4 dims). See [LANDSCAPE_FEATURES.md](./LANDSCAPE_FEATURES.md).

**Viewport:** UI zooms to full `±250` bbox like [Nomic PubMed](https://static.nomic.ai/pubmed.html).

---

## Parquet schema (slim)

| Column | Purpose |
|--------|---------|
| `taxid`, `scientific_name` | identity / tooltip |
| `redlist_category`, `iucn_code` | **only color channel** |
| `ancestor_d1` … `ancestor_d36` | Native feather columns for atlas clade highlight |
| `phylum_taxid`, `phylum_name` | cluster metadata + GeoJSON labels |
| `layout_x`, `layout_y` | zero in landscape mode |
| `x`, `y` | deepscatter position (UMAP) |
| `landscape_x`, `landscape_y` | same as x/y after landscape step |

Rebuild:

```bash
pipenv run python pipeline/build_scatter_tiles.py --embedding landscape --step all
```

Study-map legacy:

```bash
pipenv run python pipeline/build_scatter_tiles.py --embedding study-map --step all
```

---

## Sidecars (PubMed-style labels)

Written beside tiles by `pipeline/scatter_build_labels.py`:

| File | Purpose |
|------|---------|
| `labels.geojson` | Phylum name at UMAP centroid (`label_field: "labels"`) |
| `view_extent.json` | Padded bbox for initial camera fit |

---

## Frontend encoding

- **Color:** `iucn_code` only (linear 0–7, IUCN palette)
- **Foreground:** species in selected tree clade (`ancestor_d{depth} == selectedTaxid`)
- **Labels:** `plotAPI({ labels: { url: …/labels.geojson } })`
- **Viewport:** load `view_extent.json` after init, `zoom_align: "center"`

Config: `next-app/lib/scatter-facets.json`, `next-app/lib/atlas-scatter-encoding.ts`

Atlas page: full-height scatter in the right column (`next-app/app/taxonomy/atlas/page.tsx`).

---

## Docker / nginx

```yaml
NEXT_PUBLIC_TILE_URL: /tiles/species/landscape/v20260614
```

Serve tiles from `./tiles` via nginx (`docker-compose.yml`).

---

## Legacy layouts

| Layout | Flag | Tile path |
|--------|------|-----------|
| UMAP landscape (default) | `--embedding landscape` | `tiles/species/landscape/v*` |
| Phylum disc-pack study map | `--embedding study-map` | `tiles/species/study-map/v*` |
| Multi-layer Y facets | retired | `tiles/species/facets/v*` |

Previous facet layers (`layer_a_y` … `layer_e_y`) preserved in git history and `SCATTER_FACETS.md`.
