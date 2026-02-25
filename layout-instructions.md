# Eukaryote Tree from TSV → Vector Tiles (GitHub Pages)

Instructions for generating a **Lifemap-identical** Eukaryote tree from your existing **parent_id, id, name, rank** TSV, with **vector tiles** and deployment on **GitHub Pages**.

**Input:** One TSV with the full tree under Eukaryota (columns: `parent_id`, `id`, `name`, `rank`).  
**Output:** Vector tiles (MVT) + style + static frontend, all hostable on GitHub Pages.

---

## Table of Contents

1. [Input: Your TSV](#1-input-your-tsv)
2. [Load TSV into a Tree](#2-load-tsv-into-a-tree)
3. [Layout Algorithm (Exact Specification)](#3-layout-algorithm-exact-specification)
4. [Geometry Construction](#4-geometry-construction)
5. [Outputs: GeoJSON and Search JSON](#5-outputs-geojson-and-search-json)
6. [Vector Tiles](#6-vector-tiles)
7. [Style](#7-style)
8. [GitHub Pages Deployment](#8-github-pages-deployment)
9. [Verification](#9-verification)

---

## 1. Input: Your TSV

**Format:** Tab-separated, header row.

| Column     | Description |
|------------|-------------|
| parent_id  | Parent node id. Use empty or `0` for the root (Eukaryota). |
| id         | This node’s unique id (string or int). |
| name       | Display name (e.g. scientific name). |
| rank       | Rank label (e.g. kingdom, phylum, species). |

**Example:**

```tsv
parent_id	id	name	rank
	2759	Eukaryota	superkingdom
2759	33090	Viridiplantae	kingdom
33090	35493	Streptophyta	phylum
35493	3193	Streptophytina	subphylum
```

**Assumptions:** One root row (no parent_id or parent_id 0). No cycles. All ids unique. Tree is already restricted to Eukaryota (no need to filter by taxid).

---

## 2. Load TSV into a Tree

Build an in-memory tree so you can traverse parent → children and compute layout. Any representation with **parent**, **children**, **id**, **name**, **rank** is fine.

**Minimal approach (no ete3):**

```python
import csv
from collections import defaultdict

def load_tree(tsv_path):
    rows = []
    with open(tsv_path, newline='', encoding='utf-8') as f:
        r = csv.DictReader(f, delimiter='\t')
        for row in r:
            pid = (row.get('parent_id') or '').strip() or None
            if pid == '0':
                pid = None
            rows.append({
                'parent_id': pid,
                'id': row['id'].strip(),
                'name': row.get('name', '').strip(),
                'rank': row.get('rank', '').strip(),
            })

    # Build lookup and children list
    by_id = {row['id']: {**row, 'children': []} for row in rows}
    root_id = None
    for row in rows:
        pid = row['parent_id']
        if pid is None:
            root_id = row['id']
        else:
            by_id[pid]['children'].append(by_id[row['id']])

    return by_id[root_id]  # root node
```

Ensure each node has:
- `id`, `name`, `rank`
- `children` (list of child nodes)
- You will add `x`, `y`, `alpha`, `ray`, `zoomview`, `nbdesc`, etc. during layout.

---

## 3. Layout Algorithm (Exact Specification)

This is the **core step**: reproduce Lifemap’s radial layout so the map looks identical. Apply in a **single top-down traversal**; at each node compute layout for its children, then recurse.

### 3.1 Constants and Helpers

- **Degrees → radians:** `rad(deg) = deg * π / 180`
- **Eukaryote root parameters (fixed):**

| Symbol  | Value        | Meaning |
|---------|--------------|--------|
| root.x  | -6.0         | Longitude (same as map x) |
| root.y  | -0.339746    | Latitude; use `9.660254 - 10.0` |
| root.alpha | 150.0     | Opening angle of wedge (degrees) |
| root.ray   | 10.0      | Radius |

- **Display zoom:** `zoom_display = zoomview + 4` (map zoom 4–42).

### 3.2 Root Initialization

Before traversing, set on the root node only:

```python
root['x'] = -6.0
root['y'] = 9.660254 - 10.0   # -0.339746
root['alpha'] = 150.0
root['ray'] = 10.0
root['zoomview'] = max(0, ceil(log2(30.0 / root['ray'])))
```

### 3.3 Per-Node Layout (Pre-Order)

For **each node** (starting at root), do the following. Use the node’s **children list** only (already attached when loading the TSV).

#### 3.3.1 Descendant count

```python
def count_descendants(node):
    """Total number of nodes in subtree (including self)."""
    if 'nbdesc' in node:
        return node['nbdesc']
    n = 1
    for c in node['children']:
        n += count_descendants(c)
    node['nbdesc'] = n
    return n
```

Call once per node (e.g. in a first pass, or compute during layout and cache). Lifemap uses this for angle weighting and for properties.

#### 3.3.2 Angle allocation for children

For each child, assign a **half-angle** (degrees) proportional to √(subtree size):

```python
children = node['children']
nbdesc = node['nbdesc']   # total under this node

tot = sum(sqrt(count_descendants(ch)) for ch in children)
for ch in children:
    ch['ang'] = 180.0 * (sqrt(count_descendants(ch)) / tot) / 2.0
```

So: `child.ang = 180 * (sqrt(descendants(child)) / tot) / 2`.

#### 3.3.3 Special case: single child

If a node has exactly one child, reduce the child’s radius so the wedge doesn’t look like a full half-circle:

```python
n_children = len(children)
n_desc = node['nbdesc']
ray = node['ray']

if n_children == 1 and n_desc > 1:
    special = 1   # shrink child ray by 20%
elif n_children == 1 and n_desc == 1:
    special = 2   # shrink child ray by 50%
else:
    special = 0
```

#### 3.3.4 Child radius (`ray`) and distance

For each child:

```python
for ch in children:
    if special == 1:
        ch['ray'] = ray - (ray * 20) / 100
    elif special == 2:
        ch['ray'] = ray - (ray * 50) / 100
    else:
        tan_ang = sin(rad(ch['ang'])) / cos(rad(ch['ang']))
        ch['ray'] = (ray * tan_ang) / (1.0 + tan_ang)
    ch['dist'] = ray - ch['ray']
```

So:
- **special 1:** `child.ray = ray * 0.8`, `child.dist = ray * 0.2`
- **special 2:** `child.ray = ray * 0.5`, `child.dist = ray * 0.5`
- **normal:** `tan_ang = tan(rad(child.ang))`, `child.ray = ray * tan_ang / (1 + tan_ang)`, `child.dist = ray - child.ray`

#### 3.3.5 Cumulative angles for children

Children get wedge positions by converting the half-angles into cumulative start angles, then centering around the parent’s direction:

```python
angles = [ch['ang'] for ch in children]
# Double each angle and take cumulative sum, then take every 2nd element
ang_doubled = []
for a in angles:
    ang_doubled.append(a)
    ang_doubled.append(a)
ang_cumsum = []
s = 0
for a in ang_doubled:
    s += a
    ang_cumsum.append(s)
ang_final = [ang_cumsum[2*i] for i in range(len(angles))]  # [0], [2], [4], ...
# Center around parent's alpha (Lifemap: 90 - alpha)
ang_final = [a - (90.0 - node['alpha']) for a in ang_final]
```

So each child’s **center angle** (in degrees) is `ang_final[i]`.

#### 3.3.6 Child position and zoomview

```python
for i, ch in enumerate(children):
    ch['alpha'] = ang_final[i]
    ch['x'] = node['x'] + ch['dist'] * cos(rad(ch['alpha']))
    ch['y'] = node['y'] + ch['dist'] * sin(rad(ch['alpha']))
    ch['zoomview'] = ceil(log2(30.0 / ch['ray']))
    if ch['zoomview'] < 0:
        ch['zoomview'] = 0
```

Coordinates are in **pseudo-geographic** space: `(x, y) = (longitude, latitude)` for GeoJSON.

#### 3.3.7 Full layout pass (pseudocode)

```python
def layout(node):
    if not node.get('children'):
        return
    children = node['children']
    nbdesc = node['nbdesc']
    ray = node['ray']

    # Angle allocation
    tot = sum(sqrt(count_descendants(ch)) for ch in children)
    for ch in children:
        ch['ang'] = 180.0 * (sqrt(count_descendants(ch)) / tot) / 2.0

    # Special case
    special = 0
    if len(children) == 1 and nbdesc > 1:
        special = 1
    elif len(children) == 1 and nbdesc == 1:
        special = 2

    # Child ray and dist
    for ch in children:
        if special == 1:
            ch['ray'] = ray - (ray * 20) / 100
        elif special == 2:
            ch['ray'] = ray - (ray * 50) / 100
        else:
            tan_ang = sin(rad(ch['ang'])) / cos(rad(ch['ang']))
            ch['ray'] = (ray * tan_ang) / (1.0 + tan_ang)
        ch['dist'] = ray - ch['ray']

    # Cumulative angles
    angles = [ch['ang'] for ch in children]
    ang_doubled = [a for a in angles for _ in (0, 1)]
    ang_cumsum = cumsum(ang_doubled)[::2]
    ang_final = [a - (90.0 - node['alpha']) for a in ang_cumsum]

    # Positions and zoomview
    for i, ch in enumerate(children):
        ch['alpha'] = ang_final[i]
        ch['x'] = node['x'] + ch['dist'] * cos(rad(ch['alpha']))
        ch['y'] = node['y'] + ch['dist'] * sin(rad(ch['alpha']))
        ch['zoomview'] = max(0, ceil(log2(30.0 / ch['ray'])))

    for ch in children:
        layout(ch)
```

Run a **descendant-count pass** (or compute `nbdesc` during a first traversal), then set root `x, y, alpha, ray, zoomview` and call `layout(root)`.

### 3.4 Order of Traversal and IDs

- **Node IDs for features:** You can use a running integer (e.g. pre-order) for `id` in points/lines/polygons, or keep your TSV `id` as a string. Use the same convention in search JSON.
- **Leaves vs internal:** A node is a leaf iff `len(node.get('children', [])) == 0`. Use this for `tip` and for deciding whether to emit a polygon (internal only).

---

## 4. Geometry Construction

### 4.1 Points

- **Every node:** one Point at `(node['x'], node['y'])`. Properties: `id`, `name` (as sci_name), `rank`, `nbdesc`, `zoomview`, `tip` (boolean), `cladecenter` = false, `ref` = 2.
- **Internal nodes only:** one extra Point at the **clade polygon centroid** with `cladecenter` = true (same properties).

### 4.2 Lines

- **Branches:** For each non-root node, `LINESTRING(parent.x, parent.y, node.x, node.y)`. Properties: `branch` = true, `zoomview`, `ref` = 2, `name` = e.g. `"← parent_name     -     child_name →"` (swap left/right if `child.x >= parent.x`).
- **Rank lines:** For each internal node, a short line along the polygon boundary (indices 35–44 of the 60-point ring). Properties: `rankname` = true, `ref` = 2, `sci_name`, `zoomview`, `rank`, `nbdesc`.

### 4.3 Polygons (clade wedges)

For each **internal** node, build a 60-vertex polygon (half-circle + ellipse):

```python
def half_circle(x, y, r, start_rad, end_rad, n=30):
    t = np.linspace(start_rad, end_rad, n)
    return (x + r * np.cos(t), y + r * np.sin(t))

def ellipse(x, y, r, alpha_rad, n=30):
    t = np.linspace(0, np.pi, n)
    a, b = r, r / 6.0
    xs = x + (a * np.cos(t) * np.cos(alpha_rad) - b * np.sin(t) * np.sin(alpha_rad))
    ys = y + (a * np.cos(t) * np.sin(alpha_rad) + b * np.sin(t) * np.cos(alpha_rad))
    return (xs, ys)

def half_circ_plus_ellipse(x, y, r, alpha_deg, n=30):
    alpha = np.radians(alpha_deg)
    start = alpha + np.pi/2
    end   = alpha - np.pi/2
    xc, yc = half_circle(x, y, r, start, end, n)
    xe, ye = ellipse(x, y, r, alpha, n)
    return (np.concatenate([xc, xe]), np.concatenate([yc, ye]))
```

Ring: 60 points, then close by repeating the first point. **Clade center** = `(xs.mean(), ys.mean())`. **Rank line** = points at indices 35–44 (inclusive).

---

## 5. Outputs: GeoJSON and Search JSON

- **points.geojson** – FeatureCollection of Point features (node points + clade centers). Coordinates `[lon, lat]` = `[x, y]`.
- **lines.geojson** – FeatureCollection of LineStrings (branches + rank lines).
- **polygons.geojson** – FeatureCollection of Polygons (clade wedges).

Use property `ref` = 2 for Eukaryotes so the same style can be reused.

**Search JSON** (e.g. `nodes.json`): one object per node with `id`, `name`, `rank`, `zoom` (= `zoomview + 4`), `nbdesc`, `lat`, `lon`, and a concatenated `all` field for search (e.g. `"name | rank | id"`). This can be loaded by the frontend for autocomplete/lookup without a backend.

---

## 6. Vector Tiles

Generate MVT with tippecanoe:

```bash
tippecanoe -o tiles.mbtiles -z 14 -Z 0 \
  -L polygons:polygons.geojson -L lines:lines.geojson -L points:points.geojson
```

Extract to XYZ (e.g. with `mb-util --image_format=pbf tiles.mbtiles tiles_xyz`) and place under a folder `tiles/` with structure `tiles/{z}/{x}/{y}.pbf`. Layer names in the style: `polygons`, `lines`, `points`.

---

## 7. Style

Use a Mapbox GL v8 style. Eukaryote fill: **#6599ff**, opacity **0.15**. Rank labels: **#6599ff**, opacity **0.25**. Example source:

```json
{
  "type": "vector",
  "url": "tiles/{z}/{x}/{y}.pbf"
}
```

For GitHub Pages, use a **relative URL** or the full Pages base URL, e.g. `"url": "https://<user>.github.io/<repo>/tiles/{z}/{x}/{y}.pbf"` or `"./tiles/{z}/{x}/{y}.pbf"` if the style is in the same repo. Layers: fill (polygons), line (branches), symbol (clade labels, tip labels, rank labels). Filter layers by `ref` = 2 if you ever add other domains.

---

## 8. GitHub Pages Deployment

- **Repo structure (example):**
  - `index.html` – single page with MapLibre GL, style loaded from `style.json`, tile URL pointing to repo tiles.
  - `style.json` – style with vector source URL set to GitHub Pages base or relative path.
  - `tiles/` – folder with `{z}/{x}/{y}.pbf` (or `tiles/` in `docs/` if using docs branch).
  - `nodes.json` – search data for client-side autocomplete.

- **Tile URL:**  
  If the site is `https://<user>.github.io/<repo>/`, set the vector source to  
  `https://<user>.github.io/<repo>/tiles/{z}/{x}/{y}.pbf`  
  (or relative `./tiles/{z}/{x}/{y}.pbf` if your style and tiles are under the same path).

- **CORS:** GitHub Pages serves static files with permissive CORS; no extra config needed for same-origin or cross-origin tile/style requests from the same site.

- **Build step:** Run layout + GeoJSON + tippecanoe locally (or in CI); commit the generated `tiles/` and `nodes.json` (and optionally `style.json`) to the repo. No server or database required.

---

## 9. Verification

- **Root:** After layout, root coordinates should be `(-6.0, -0.339746)`.
- **Map:** Center map at `[-6, -0.34]`, default zoom 5. Tree should fit in roughly lon [-20, 10], lat [-15, 15].
- **Visual:** Compare with Lifemap’s Eukaryote view: same wedge directions, branch angles, and label positions.

---

## Summary Checklist

1. [ ] Load TSV (parent_id, id, name, rank) into a tree with `children` and optional `nbdesc`.
2. [ ] Set root: x=-6, y=-0.339746, alpha=150, ray=10, zoomview from `log2(30/ray)`.
3. [ ] Implement layout: angle allocation (√nbdesc), special cases for single child, ray/dist, cumulative angles, child x/y and zoomview.
4. [ ] Emit points (nodes + clade centers), lines (branches + rank lines), polygons (60-pt half-circle+ellipse).
5. [ ] Write points.geojson, lines.geojson, polygons.geojson and nodes.json (search).
6. [ ] Run tippecanoe → MVT; extract to `tiles/{z}/{x}/{y}.pbf`.
7. [ ] Add style.json (fill #6599ff, opacity 0.15; layers for polygons, lines, labels).
8. [ ] Add index.html with MapLibre GL and tile URL for GitHub Pages.
9. [ ] Push tiles, style, nodes.json, and index.html to repo; enable GitHub Pages.

---

*Based on Lifemap PIPELINE (Traverse_To_Pgsql_2.py) and style (clade2).*
