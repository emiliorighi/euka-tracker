# Tree of Life Visualization

Serverless rectangular dendrogram visualization of the eukaryotic taxonomy (~2M taxa) with genome coverage states.

## Pipeline

### 1. Build tree layout

```bash
pipenv run python scripts/build_tree_layout.py
```

- Loads `data/ncbi_taxonomy_tree.tsv`
- Builds tree, computes DFS layout (x=depth, y=leaf order)
- Normalizes coordinates to [0,1]
- Output: `tree_layout/nodes.parquet` (taxid, parent_taxid, x, y, depth)

### 2. Build coverage

```bash
pipenv run python scripts/build_coverage.py
```

- Loads `data/eukaryotic_species_matrix.tsv` and `tree_layout/nodes.parquet`
- Assigns species-level coverage states (0–5)
- Propagates best state up the tree
- Output: `coverage/coverage_nodes.parquet` (taxid, coverage_state)

**Coverage states:**
- 5 FULL: annotation + reads
- 4 GENOME_ANNOTATION_ONLY
- 3 GENOME_READS_NO_ANNOTATION
- 2 GENOME_ONLY
- 1 READS_ONLY
- 0 NO_DATA

### 3. Build tiles

```bash
pipenv run python scripts/build_tree_tiles.py --json
```

- Merges layout + coverage + taxonomy (name, rank)
- LOD: collapse single-child chains, aggregate subtrees
- Tiles zoom levels 0–7 along Y axis: `tile_y = floor(y * 2^z)` (Lifemap-style)
- Max ~20k nodes per tile
- Output: `tree_tiles/z0/` … `z7/` with `.parquet` (zstd) and `.json` (optional with `--json`)
- Parquet schema: taxid, parent_taxid, x, y, depth, coverage_state, name, rank

## Frontend

**Lifemap-style serverless visualization** with Parquet-first tile loading:

- **Parquet tiles** (default): Uses parquet-wasm + apache-arrow to load `.parquet` tiles (smaller, faster)
- **JSON fallback**: If Parquet fails (e.g. CORS, missing files), falls back to `.json` tiles
- **Force JSON**: Add `?format=json` to URL to skip Parquet (e.g. when only JSON tiles are deployed)
- **Efficiency mode**: Fewer nodes when zoomed out (toggle in UI)
- **GitHub Pages**: Static hosting, no backend. Deploy both Parquet and JSON tiles for best compatibility.

### Local development

Serve from repo root (tiles and frontend must be same origin):

```bash
cd euka-tracker
python -m http.server 8000
```

Open http://localhost:8000/frontend/

### GitHub Pages deployment (CI)

The workflow `.github/workflows/deploy-tree-of-life.yml` builds the pipeline and deploys on push to `main`.

1. In repo **Settings → Pages**:
   - Source: **GitHub Actions**
   - (Deploy from the `deploy-tree-of-life` workflow)

2. Push to `main` (or trigger workflow manually). The workflow:
   - Runs build_tree_layout → build_coverage → build_tree_tiles
   - Uploads `frontend/` + `tree_tiles/` as Pages artifact

3. App URL: `https://<user>.github.io/euka-tracker/` (or your repo name)

### Manual deployment

If deploying manually (e.g. from `gh-pages` branch):

```bash
./scripts/run_pipeline.sh
cp frontend/index.html frontend/app.js frontend/tileLoader.js .
cp -r tree_tiles .
# Commit and push to gh-pages, or copy to your web server.
```

### Features

- **Viewport-based tile loading**: only fetches tiles visible in view
- **LOD depth filter**: `depth <= zoom_level + 3`
- Zoom/pan (mouse wheel, drag)
- Nodes colored by coverage state
- Edges drawn only for visible nodes
- Hover tooltip: taxid, name, rank, coverage
- Search by taxid (Enter)
- Color legend
- Toggle: show only nodes with data
- Tile caching (no duplicate fetches)
- Debounced pan/zoom (100ms)

## Output structure

```
tree_layout/
  nodes.parquet

coverage/
  coverage_nodes.parquet

tree_tiles/
  z0/ 0.{parquet,json}
  z1/ 0..1.{parquet,json}
  ...
  z7/ 0..127.{parquet,json}

frontend/
  index.html
  app.js
  tileLoader.js
```

## Performance

- ~2M nodes in source tree
- Tiles loaded on demand (viewport-based)
- Max 20k nodes per tile (LOD downsampling)
- Tile cache prevents duplicate fetches
- No full dataset in memory in frontend
