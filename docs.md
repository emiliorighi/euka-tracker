# Serverless Lifemap Migration Specification

**Purpose:** This document provides a complete specification for implementing a serverless, Lifemap-like hierarchical tree visualization application. An agent in a separate repository can use this document to build the full application from scratch.

**Input format (simplified from Lifemap):**
- **Hierarchy TSV:** `parent_id`, `id` columns (one row per parent-child edge)
- **Lookup TSV:** `id`, `has_genomes`, `has_annotations`, `has_reads` (boolean flags per species/node)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Reference: Lifemap Architecture](#2-reference-lifemap-architecture)
3. [Target Serverless Architecture](#3-target-serverless-architecture)
4. [Input Data Specification](#4-input-data-specification)
5. [Pipeline Steps (Detailed)](#5-pipeline-steps-detailed)
6. [Data Models and Schemas](#6-data-models-and-schemas)
7. [Vector Tile Style Specification](#7-vector-tile-style-specification)
8. [API Endpoints](#8-api-endpoints)
9. [Frontend Implementation](#9-frontend-implementation)
10. [Deployment Checklist](#10-deployment-checklist)

---

## 1. Overview

### 1.1 Lifemap (Reference)

Lifemap is an interactive tool to explore the tree of life (NCBI taxonomy) using a zoom-and-pan interface similar to Google Maps. The tree is pre-rendered as map tiles by a backend pipeline and served as PNG tiles.

**Lifemap WEBSITE (from WEBSITE/README.md):**
- Three variants: `index.html` (general public), `ncbi.index.html` (Pro/NCBI), `mobile.index.html` (mobile)
- Leaflet loads PNG tiles from `/osm_tiles/{z}/{x}/{y}.png`
- Search/autocomplete via Solr
- Click-on-map popups show node details

### 1.2 Target Application

A serverless version that:
- Accepts **hierarchy TSV** (parent_id, id) and **lookup TSV** (id, has_genomes, has_annotations, has_reads)
- Builds a radial tree layout
- Generates **vector tiles** (MVT) and stores them in object storage
- Serves tiles via CDN
- Renders the map client-side with MapLibre GL
- Provides search via managed search (Algolia/Elasticsearch/OpenSearch) or serverless API

---

## 2. Reference: Lifemap Architecture

### 2.1 Data Flow (Current)

```
NCBI taxonomy (taxdump) → Tree build (ete3) → Layout (x,y coords) → PostGIS DB
                                                      ↓
Apache mod_tile ← renderd ← Mapnik (osm.xml) ← PostGIS (points, lines, polygons)
       ↓
/osm_tiles/{z}/{x}/{y}.png
       ↓
Leaflet L.TileLayer in WEBSITE
```

### 2.2 Lifemap Pipeline (PIPELINE/)

| Step | Script | Input | Output |
|------|--------|-------|--------|
| 1 | `getTrees_fun.py` | taxo/nodes.dmp, names.dmp | In-memory trees (Archaea, Eukaryotes, Bacteria) |
| 2 | `Traverse_To_Pgsql_2.py` | Trees | PostGIS (points, lines, polygons), TreeFeatures{1,2,3}.json |
| 3 | `Additional.info.py` | genomes/*.txt | ADDITIONAL.{1,2,3}.json |
| 4 | `StoreWholeNcbiInSolr.py` | Trees | ADDITIONAL.FULLNCBI.json |
| 5 | `updateSolr.py` | JSON files | Solr cores (taxo, addi, ncbi) |
| 6 | `CreateIndex.py` | PostGIS | GIST indexes |
| 7 | `GetAllTilesCoord.py` | TreeFeatures1.json | XYZcoordinates |
| 8 | `OnReboot.sh` + render_list | XYZcoordinates | Pre-rendered PNG tiles |
| 9 | mod_tile + Apache | Tile requests | Serve `/osm_tiles/{z}/{x}/{y}.png` |

### 2.3 Key Lifemap Components

| Component | Path / Setting |
|-----------|----------------|
| Mapnik style | `OTHER/style/osm.xml` |
| PostGIS tables | `points`, `lines`, `polygons` |
| Tile storage | `/var/lib/mod_tile/default/` |
| Tile URL pattern | `{base}/osm_tiles/{z}/{x}/{y}.png` |
| Solr cores | taxo (tree nodes), addi (genome info), ncbi (full tree) |

### 2.4 Radial Layout Algorithm (from Traverse_To_Pgsql_2.py)

- Root node has `x`, `y`, `alpha` (angle), `ray` (radius)
- Children distributed by angle; child angle proportional to `sqrt(len(child)) / sum(sqrt(len(sibling)))`
- Child `ray` = `ray * sin(ang) / cos(ang) / (1 + sin(ang)/cos(ang))`
- Child position: `x = parent.x + dist * cos(alpha)`, `y = parent.y + dist * sin(alpha)`
- `zoomview = ceil(log2(30 / ray))` (controls visibility at zoom levels)
- Polygons: half-circle + ellipse for clade wedges (60 points)

---

## 3. Target Serverless Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  BATCH PIPELINE (Scheduled or event-triggered)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. HierarchyBuilder: TSV → tree structure (any tree lib or custom)         │
│  2. TreeLayout: radial layout → points, lines, polygons GeoJSON             │
│  3. LookupEnricher: merge has_genomes, has_annotations, has_reads           │
│  4. VectorTileGenerator: GeoJSON → MVT tiles (tippecanoe/martin)            │
│  5. SearchIndexer: build search index (Algolia/Elasticsearch)               │
│  Output: MVT tiles → S3/GCS/R2, Search index updated                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STATIC ASSETS + CDN                                                         │
│  • Tiles: /tiles/{z}/{x}/{y}.mvt                                            │
│  • Style JSON: /styles/lifemap-style.json                                   │
│  • Frontend: SPA (Vercel/Netlify/Cloudflare Pages)                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  CLIENT                                                                      │
│  • MapLibre GL JS: vector tiles + style JSON                                │
│  • Search: Algolia/Elasticsearch API (or serverless function proxy)         │
│  • Node lookup: REST API or search API                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Input Data Specification

### 4.1 Hierarchy TSV

**File:** `hierarchy.tsv` (or `hierarchy.csv` with tab separator)

**Columns:**

| Column     | Type   | Required | Description                                      |
|------------|--------|----------|--------------------------------------------------|
| parent_id  | string | Yes      | ID of parent node. Use `"0"` or `""` for root.  |
| id         | string | Yes      | ID of this node (unique)                         |

**Example:**
```tsv
parent_id	id
0	1
1	2
1	3
2	4
2	5
3	6
```

**Rules:**
- One root: exactly one row with `parent_id` = 0 or empty
- No cycles
- All `id` values unique
- Optional: add `name` column for display label (else use `id`)

### 4.2 Lookup TSV

**File:** `lookup.tsv`

**Columns:**

| Column          | Type    | Required | Description                    |
|-----------------|---------|----------|--------------------------------|
| id              | string  | Yes      | Node ID (must exist in hierarchy) |
| has_genomes     | boolean | No       | 1/0 or true/false             |
| has_annotations | boolean | No       | 1/0 or true/false             |
| has_reads       | boolean | No       | 1/0 or true/false             |

**Example:**
```tsv
id	has_genomes	has_annotations	has_reads
4	1	1	0
5	0	1	1
6	1	0	0
```

**Rules:**
- Not all nodes need a row; missing rows → all booleans false
- Used for styling (e.g., color by has_genomes) and filtering

### 4.3 Optional: Node Metadata TSV

**File:** `nodes.tsv` (optional, for names/ranks)

| Column   | Type   | Description                    |
|----------|--------|--------------------------------|
| id       | string | Node ID                        |
| name     | string | Display name (scientific name) |
| rank     | string | Optional rank/category label   |
| common_name | string | Optional common name       |

---

## 5. Pipeline Steps (Detailed)

### Step 1: Build Tree from Hierarchy TSV

**Input:** `hierarchy.tsv`  
**Output:** In-memory tree (dict of nodes with parent/children)

**Pseudocode:**
```python
def build_tree(tsv_path):
    edges = []  # (parent_id, child_id)
    with open(tsv_path) as f:
        header = next(f).strip().split('\t')
        pi, ii = header.index('parent_id'), header.index('id')
        for line in f:
            row = line.strip().split('\t')
            parent, child = row[pi], row[ii]
            if parent in ('0', ''):
                parent = None  # root
            edges.append((parent, child))
    # Build tree: find root, recurse
    children = defaultdict(list)
    for p, c in edges:
        children[p].append(c)
    root_id = next(c for p, c in edges if p is None)
    return build_node(root_id, children)
```

**Agent task:** Implement tree builder; support single root; validate no cycles.

---

### Step 2: Compute Radial Layout

**Input:** Tree from Step 1  
**Output:** GeoJSON FeatureCollections for points, lines, polygons

**Layout parameters (configurable):**
- Root position: `(x=0, y=-4.226497)` for single tree, or three roots for Archaea/Eukaryotes/Bacteria
- Initial `ray`: 10.0
- `zoomview = ceil(log2(30 / ray))` for each node

**Geometry types:**
1. **Points:** One per node (lon, lat) = (x, y) in pseudo-geographic coords
2. **Lines:** Parent-to-child segments; also rank label lines (subset of line segments)
3. **Polygons:** Clade wedges (half-circle + ellipse, 60 vertices) for internal nodes

**Required properties per feature:**
- `id`, `ref` (group: 1,2,3 or 1 for single tree)
- `sci_name`, `common_name`, `rank` (or `name`)
- `zoomview`, `nbdesc` (descendant count)
- `tip` (boolean, is leaf)
- `clade`, `cladecenter`, `branch`, `rankname` (booleans for layer filtering)
- `has_genomes`, `has_annotations`, `has_reads` (from lookup merge)

**Agent task:** Port layout logic from Traverse_To_Pgsql_2.py; output GeoJSON.

---

### Step 3: Merge Lookup Data

**Input:** Tree nodes with layout, `lookup.tsv`  
**Output:** Enriched node features with has_genomes, has_annotations, has_reads

```python
lookup = {}
with open('lookup.tsv') as f:
    header = next(f).strip().split('\t')
    for line in f:
        row = dict(zip(header, line.strip().split('\t')))
        lookup[row['id']] = {
            'has_genomes': row.get('has_genomes', '0') in ('1', 'true', 'yes'),
            'has_annotations': row.get('has_annotations', '0') in ('1', 'true', 'yes'),
            'has_reads': row.get('has_reads', '0') in ('1', 'true', 'yes'),
        }
for node in traverse(tree):
    node.update(lookup.get(node['id'], {}))
```

---

### Step 4: Export GeoJSON

**Output files:**
- `points.geojson` – Point features
- `lines.geojson` – LineString features  
- `polygons.geojson` – Polygon features

**CRS:** EPSG:4326 (WGS84). Vector tiles will use Web Mercator (EPSG:3857) in the tile generator.

---

### Step 5: Generate Vector Tiles (MVT)

**Tool:** tippecanoe or martin (Rust) or mapbox/tilekiln

**Command (tippecanoe):**
```bash
tippecanoe -o tiles.mbtiles -z 14 -Z 0 \
  -l polygons polygons.geojson \
  -l lines lines.geojson \
  -l points points.geojson
```

**Extract to XYZ:**
```bash
mb-util --image_format=pbf tiles.mbtiles output_dir
# or use tippecanoe-decode / tile-join
```

**Alternative (martin):** Serve tiles on-the-fly from PostGIS or GeoJSON; or pre-generate with a script.

**Output structure:** `{z}/{x}/{y}.pbf` or `.mvt`

---

### Step 6: Upload Tiles to Object Storage

**Target:** S3, GCS, or Cloudflare R2

**Path pattern:** `tiles/{z}/{x}/{y}.pbf`

**Agent task:** Use AWS CLI / gsutil / R2 API to upload. Set Cache-Control headers (e.g., 1 year for immutable tiles).

---

### Step 7: Build Search Index

**Index schema (Algolia/Elasticsearch):**
- `id` (string)
- `name` or `sci_name` (string)
- `coordinates` [lat, lon]
- `zoom` (int)
- `nbdesc` (int)
- `lat`, `lon` (for filtering)
- `has_genomes`, `has_annotations`, `has_reads` (boolean)
- `all` (concat for search: "name | common_name | rank | id")

**Suggest/autocomplete:** Use prefix search on `name` or `all`.

**Agent task:** Index each node; implement suggest API.

---

## 6. Data Models and Schemas

### 6.1 TreeFeatures JSON (for search index)

Each node document:
```json
{
  "id": "9606",
  "sci_name": "Homo sapiens",
  "common_name": "human",
  "rank": "species",
  "zoom": 8,
  "nbdesc": 1,
  "lat": 9.66,
  "lon": -6.0,
  "coordinates": [9.66, -6.0],
  "all": "Homo sapiens | human | species | 9606",
  "has_genomes": true,
  "has_annotations": true,
  "has_reads": false
}
```

### 6.2 Vector Tile Properties (per layer)

**polygons:** `id`, `ref`, `clade`, `sci_name`, `common_name`, `rank`, `nbdesc`, `zoomview`, `has_genomes`, `has_annotations`, `has_reads`

**lines:** `id`, `ref`, `branch`, `rankname`, `zoomview`, `name`, `rank`

**points:** `id`, `tip`, `cladecenter`, `zoomview`, `sci_name`, `common_name`, `nbdesc`

---

## 7. Vector Tile Style Specification

**Format:** Mapbox GL Style JSON (v8)

**Source:**
```json
{
  "type": "vector",
  "url": "https://cdn.example.com/tiles/{z}/{x}/{y}.pbf"
}
```

**Layers (simplified from osm.xml):**

1. **clade-fill** – polygons, fill by `ref` (color Archaea/Eukaryotes/Bacteria differently, or single color)
2. **branches** – lines, stroke
3. **clade-labels** – symbol layer, text from `sci_name` where `cladecenter`
4. **node-labels** – symbol layer, text where not tip and not cladecenter
5. **tip-labels** – symbol layer, text where `tip`
6. **branch-labels** – symbol layer, text on lines
7. **rank-labels** – symbol layer, text on rank lines

**Zoom-based visibility:** Use `minzoom`/`maxzoom` or filter: `["<=", ["get", "zoomview"], ["+", ["zoom"], 4]]`

**Color by data flags (optional):**
```json
{
  "fill-color": [
    "case",
    ["get", "has_genomes"], "#00ff00",
    ["get", "has_annotations"], "#0000ff",
    ["get", "has_reads"], "#ff0000",
    "#666666"
  ]
}
```

---

## 8. API Endpoints

### 8.1 Search / Autocomplete

**GET** `/api/search?q={query}&limit=10`

**Response:**
```json
{
  "suggestions": [
    {
      "id": "9606",
      "sci_name": "Homo sapiens",
      "common_name": "human",
      "coordinates": [9.66, -6.0],
      "zoom": 8
    }
  ]
}
```

### 8.2 Node Lookup by ID

**GET** `/api/node/{id}`

**Response:**
```json
{
  "id": "9606",
  "sci_name": "Homo sapiens",
  "common_name": "human",
  "rank": "species",
  "lat": 9.66,
  "lon": -6.0,
  "zoom": 8,
  "nbdesc": 1,
  "has_genomes": true,
  "has_annotations": true,
  "has_reads": false
}
```

### 8.3 BBox Query (click-on-map)

**GET** `/api/nodes?lat1=&lat2=&lon1=&lon2=&zoom=`

Returns nodes visible in the viewport for popup content.

---

## 9. Frontend Implementation

### 9.1 Stack

- **Map:** MapLibre GL JS
- **Tiles:** Vector (MVT) from CDN
- **Style:** Mapbox Style JSON
- **Search:** Fetch from API or Algolia JS client
- **UI:** Plain HTML/JS or React/Vue

### 9.2 Map Init

```javascript
const map = new maplibregl.Map({
  container: 'map',
  style: '/styles/lifemap-style.json',  // or full URL
  center: [-5, 0],
  zoom: 5
});
```

### 9.3 Search → Fly To

```javascript
// On search select:
map.flyTo({
  center: [node.lon, node.lat],
  zoom: node.zoom
});
```

### 9.4 Click Popup

```javascript
map.on('click', 'polygons', (e) => {
  const props = e.features[0].properties;
  new maplibregl.Popup()
    .setLngLat(e.lngLat)
    .setHTML(`<b>${props.sci_name}</b><br>${props.common_name}`)
    .addTo(map);
});
```

### 9.5 Config (Environment)

- `VITE_TILE_URL` or `NEXT_PUBLIC_TILE_URL`: base URL for tiles
- `VITE_API_URL`: base URL for search/node API
- `VITE_ALGOLIA_APP_ID`, `VITE_ALGOLIA_SEARCH_KEY` (if using Algolia)

---

## 10. Deployment Checklist

### Pipeline (Batch)

- [ ] Hierarchy TSV and lookup TSV available
- [ ] Tree builder implemented
- [ ] Layout module implemented (radial)
- [ ] GeoJSON export
- [ ] Vector tile generation (tippecanoe/martin)
- [ ] Upload tiles to S3/GCS/R2
- [ ] Search index populated (Algolia/Elasticsearch)
- [ ] Pipeline runnable as Lambda/Cloud Run/cron job

### Storage

- [ ] Bucket created for tiles
- [ ] CDN configured (CloudFront/Cloudflare)
- [ ] CORS allowed for tile and style requests
- [ ] Cache headers set

### API

- [ ] Search endpoint
- [ ] Node-by-ID endpoint
- [ ] BBox endpoint (optional)
- [ ] Deployed as Lambda/Cloud Run/serverless

### Frontend

- [ ] MapLibre GL + style JSON
- [ ] Search bar with autocomplete
- [ ] Click popups
- [ ] Fly-to on search select
- [ ] Deployed to Vercel/Netlify/Cloudflare Pages

### End-to-End

- [ ] Full pipeline run produces tiles + index
- [ ] Frontend loads tiles from CDN
- [ ] Search and navigation work
- [ ] No server-side tile rendering (fully serverless)

---

## Appendix A: Lifemap WEBSITE README (Integrated)

*(Content from WEBSITE/README.md for reference.)*

### How the Tree is Generated (Lifemap)

The displayed tree is **not** rendered in the browser. It is pre-rendered as map tiles by a backend pipeline and served as PNG tiles. The WEBSITE loads these tiles in a Leaflet map.

### Lifemap Tile Layer

```javascript
var tolUrl = 'http://umr5558-treezoom.univ-lyon1.fr/osm_tiles/{z}/{x}/{y}.png';
var tol = new L.TileLayer(tolUrl, { minZoom: 4, maxZoom: 42 });
map.addLayer(tol);
```

### Lifemap Search / Lookup

- Autocomplete: Solr suggest API
- Lookup by taxid: `.../solr/taxo/select?q=taxid:"{taxid}"&wt=json`
- Click-on-map popups: Solr query by lat/lon/zoom bbox

### Lifemap Coordinate Convention

- Tree layout uses (lon, lat) ≈ (x, y) as pseudo-geographic coordinates
- Map view: `map.setView([-5, 0], 5)` (latitude, longitude, zoom)

### Lifemap Dependencies (WEBSITE)

- Leaflet
- jQuery, jQuery UI (searchbar, autocomplete)
- Bootstrap, Font Awesome
- Leaflet.label (labels on map)

---

## Appendix B: File Structure for New Repo

```
project/
├── pipeline/
│   ├── build_tree.py          # Step 1: TSV → tree
│   ├── layout.py              # Step 2: radial layout
│   ├── enrich_lookup.py       # Step 3: merge lookup
│   ├── export_geojson.py      # Step 4: GeoJSON
│   ├── generate_tiles.sh      # Step 5: tippecanoe
│   ├── upload_tiles.sh        # Step 6: S3/GCS
│   ├── index_search.py        # Step 7: search index
│   └── run_pipeline.py        # Orchestrator
├── styles/
│   └── lifemap-style.json     # Mapbox GL style
├── api/                       # Serverless API (e.g. Vercel/Netlify)
│   ├── search.js
│   └── node/[id].js
├── frontend/
│   ├── index.html
│   ├── main.js
│   └── style.css
├── hierarchy.tsv              # Input
├── lookup.tsv                 # Input
└── README.md
```

---

*Document version: 1.0. Generated from Lifemap analysis and WEBSITE/README.md.*
