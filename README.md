# euka-tracker

Tracking taxonomy, assemblies, annotations and reads under Eukaryota, with a serverless Lifemap-style tree visualization.

## Overview

- **Data**: NCBI taxonomy tree + eukaryotic species matrix (assemblies, annotations, reads)
- **Pipeline**: Build tree → radial layout → GeoJSON → vector tiles (MVT) → search index
- **Frontend**: MapLibre GL vector map with search, click popups, fly-to

## Data Files

- `data/ncbi_taxonomy_tree.tsv`: hierarchy (parent_id, id, name, rank)
- `data/eukaryotic_species_matrix.tsv`: lookup (taxid, has_assembly, has_annotation, has_reads, ...)

## Quick Start

### 1. Run Pipeline

```bash
pip install -r requirements.txt
python3 -m pipeline.run_pipeline
```

Output:
- `output/geojson/` — points, lines, polygons
- `output/search_index.json` — search index
- `output/tiles.mbtiles` — vector tiles (if tippecanoe installed)

### 2. Generate Vector Tiles

Install [tippecanoe](https://github.com/felt/tippecanoe) and [mb-util](https://github.com/mapbox/mbutil):

```bash
# macOS
brew install tippecanoe
pip install mbutil

./scripts/make_tiles.sh
```

### 3. Serve Frontend

```bash
npm install
npm run serve
```

Open http://localhost:3000

## Project Structure

```
euka-tracker/
├── pipeline/
│   ├── build_tree.py       # TSV → tree
│   ├── layout.py           # (uses scripts/radial_layout.py)
│   ├── enrich_lookup.py    # Merge lookup data
│   ├── export_geojson.py   # GeoJSON export
│   └── run_pipeline.py     # Orchestrator
├── scripts/
│   ├── radial_layout.py    # Radial layout algorithm
│   └── make_tiles.sh       # tippecanoe → XYZ tiles
├── frontend/
│   ├── index.html
│   ├── main.js             # MapLibre + search
│   └── style.css
├── styles/
│   └── lifemap-style.json
├── tiles/                  # Vector tiles (after make_tiles.sh)
├── output/                 # Pipeline output
├── data/
│   ├── ncbi_taxonomy_tree.tsv
│   └── eukaryotic_species_matrix.tsv
└── docs.md                 # Full specification
```

## Environment

- `VITE_TILE_URL`: Tile base URL (default: `/tiles/tiles.json`)
- `VITE_API_URL`: API base URL (optional; uses `/output/search_index.json` if unset)

## License

MIT
