# Taxonomy UX — six concepts & implementation guide

Creative UX direction for **EukaryoBase** taxonomy navigation: hierarchy drill-down, clade statistics, species lists, and species detail — powered by `data/staged/06_taxon_rollups.tsv` and the species matrix.

**Related docs:** [TAXON_ROLLUPS.md](./TAXON_ROLLUPS.md) (data schema & pipeline), [WEB_APP_STACK.md](./WEB_APP_STACK.md) (API & deploy), [MODELS.txt](./MODELS.txt) (catalog models).

**Live demos (mock JSON from rollups):** `/taxonomy/concepts` in `next-app/` — run `npm run extract:taxonomy-mock` after rebuilding `06_taxon_rollups.tsv`.

---

## North star

**Metaphor:** *The tree is not a chart — it is a place you descend into.*

| Visual language | Meaning | Primary rollup fields |
|-----------------|---------|------------------------|
| Dark / ghost | Unknown biodiversity (NCBI universe) | `species_count_ncbi` |
| Bioluminescence | Catalog coverage (matrix) | `species_count_matrix`, `pct_ncbi_species_with_data` |
| Depth | Taxonomic depth | `depth_from_eukaryota`, `rank` |
| Amber glow | Conservation risk | `species_threatened`, `species_iucn_assessed` |
| Pulse / teal core | Sequencing & annotation depth | `species_with_reads`, `species_with_assembly`, `species_with_annotation`, `species_full_triple` |

**One-sentence pitch:** EukaryoBase Taxonomy is a bioluminescent descent through the tree of life — each clade shows how much of nature exists in the dark, and how much we have illuminated in the catalog.

**Dual-universe rule (non-negotiable):** Always show NCBI totals alongside matrix totals (e.g. `1,942 / 10,037 species`). Never display matrix counts alone without NCBI context.

---

## Shared architecture

All six concepts share one **focus model** — do not build six separate pages with different state.

### Focus state

```ts
type TaxonomyFocus = {
  taxid: number                    // current clade (default: 2759 Eukaryota)
  lens: "catalog" | "genome" | "risk" | "reads"
  compareTaxid?: number            // Concept 6 only
  speciesOpen: boolean             // Specimen Stream / drawer
  vizMode: "descent" | "biolume" | "constellation"  // primary nav surface
}
```

### URL contract

```
/taxonomy                           → Eukaryota, default viz
/taxonomy/[taxid]                 → deep link
/taxonomy/[taxid]?viz=biolume       → switch primary nav surface
/taxonomy/[taxid]?lens=risk         → color encoding
/taxonomy/[taxid]?compare=33208     → symbiosis compare
/taxonomy/[taxid]?species=1         → specimen stream open
/explore?taxon=[taxid]              → portal to deepscatter (secondary)
```

Use **taxid in routes**, not scientific names (names collide; names change).

### API surface (minimal)

Tiles and scatter stay static via nginx. Taxonomy uses a thin read-only API over `data/staged/taxonomy.sqlite` (rollup columns synced by pipeline).

```
GET  /api/taxa/search?q=homarus&limit=20
GET  /api/taxa/[taxid]                              # single rollup row + ancestors[]
GET  /api/taxa/[taxid]/children                     # direct children only, flat rows
GET  /api/taxa/[taxid]/ancestors                    # root → focus, ordered
GET  /api/taxa/[taxid]/species?limit=50&offset=0    # matrix rows under clade
GET  /api/organisms/[taxid]                         # species detail + outbound URLs
```

**Performance targets:**

| Endpoint | Expected latency | Notes |
|----------|------------------|-------|
| `/children` | < 20 ms | indexed `parent_taxid`; typically 1–400 rows |
| `/ancestors` | < 10 ms | ≤ 36 hops |
| `/species` | < 50 ms | paginated; filter matrix by `tax_lineage` contains taxid |
| Full induced subtree | avoid | 156k rows — never return in one response |

**Prefetch:** on child hover, prefetch `/api/taxa/{childId}` and `/children`.

### Data mapping cheat sheet

| UI need | Rollup / matrix field |
|---------|------------------------|
| Segment / cell area | `species_count_ncbi` (use `log1p` for layout) |
| Fill / brightness | `pct_ncbi_species_with_data` or `species_count_matrix / species_count_ncbi` |
| Ghost / outline only | `species_count_matrix === 0` |
| Funnel bands | `species_count_ncbi` → `species_with_reads` → `species_with_assembly` → `species_with_annotation` → `species_full_triple` |
| Rank tile count label | `{nextRank}_nodes_total` / `{nextRank}_nodes_with_data` |
| Genome lens color | `mean_genome_size`, `n_with_assembly` |
| Risk lens | `species_threatened / species_iucn_assessed` (guard divide-by-zero) |
| Reads lens | `sum_run_count`, `species_with_reads` |
| Next rank below focus | derive from canonical ladder: domain → kingdom → … → species |

Canonical ranks: `domain, kingdom, phylum, class, order, family, genus, species` (see [TAXON_ROLLUPS.md](./TAXON_ROLLUPS.md)).

### Visual tokens (extend existing theme)

Add to `next-app/app/globals.css` when implementing:

```css
:root {
  --biolume-core: var(--primary);           /* catalog glow */
  --biolume-dim: oklch(0.72 0.16 152 / 0.15);
  --ghost-clade: oklch(1 0 0 / 4%);
  --ghost-border: oklch(1 0 0 / 12%);
  --depth-fog: oklch(0.16 0.012 160);       /* shift hue +2° per rank in JS */
  --risk-amber: var(--chart-3);
  --annotation-teal: var(--chart-2);
}
```

- **UI font:** Geist Sans (existing).
- **Scientific names:** italic serif or italic Geist — e.g. `<em class="taxon-name">Homo sapiens</em>`.
- **Motion default:** 300–400 ms ease-out; animate focus swaps, not full-tree relayout.

### Component map (`next-app/`)

```
components/taxonomy/
  TaxonomyShell.tsx           # layout chrome, focus context, URL sync
  AncestorRail.tsx            # vertical ancestor minimap (shared)
  DiveComputer.tsx            # floating stats panel (shared)
  DescentHorizon.tsx          # Concept 1
  BiolumeField.tsx            # Concept 2
  RankConstellation.tsx       # Concept 3
  FunnelCathedral.tsx         # Concept 4
  SpecimenStream.tsx          # Concept 5
  SymbiosisCompare.tsx        # Concept 6
  TaxonSearch.tsx             # omni search → fly to taxid
  lensEncoding.ts             # lens → color/size getters from rollup row
hooks/
  useTaxonFocus.ts
  useTaxonChildren.ts
  useTaxonSpecies.ts
app/(browse)/taxonomy/
  page.tsx                    # redirect or Eukaryota
  [taxid]/page.tsx            # TaxonomyShell
```

Reuse: `species-detail-sheet.tsx`, `page-header.tsx`, `iucn-badge.tsx`, `stat-card.tsx`.

---

## Concept 1 — The Descent

### Idea

Full-viewport **vertical descent** through taxonomy. Each drill-down feels like going deeper into the tree: the current clade is a **horizon ring**; direct children are the next layer down. Ancestors collapse to a glowing thread at the top.

### User flow

1. Land at Eukaryota — faint outer ring, ~6.6% inner glow on first paint.
2. Kingdom cells sit on the horizon; click one → zoom/descend animation.
3. Background hue shifts subtly per kingdom (`depth-fog` + rank-based hue).
4. At genus+, optional transition to Specimen Stream (Concept 5) for species orbs.
5. `Esc` or ancestor thread → ascend one level.

### Data → visuals

| Element | Mapping |
|---------|---------|
| Outer ring radius | `species_count_ncbi` (sqrt or log scale) |
| Inner filled arc | `species_count_matrix / species_count_ncbi` |
| Ring label | `scientific_name`, `rank` |
| Subtitle | `{matrix} / {ncbi} species catalogued` |
| Ghost ring | `species_count_matrix === 0` — stroke only, 4% fill |
| Dive computer depth meter | `depth_from_eukaryota` |

### Implementation

- **Tech:** SVG or Canvas 2D for rings; Framer Motion for scale/translate on drill.
- **Scope per view:** direct **children only** from `GET /api/taxa/[taxid]/children`.
- **Cap:** none for table fallback; for rings, if children > 24, switch to paginated arc sectors or fall back to Biolume Field.
- **Entry animation:** stagger child rings 40 ms apart on first paint.
- **Accessibility:** listbox role on child rings; keyboard ↑↓ to select, Enter to drill.

### Do not

- Render full 156k induced tree.
- Use scientific name in URL.

---

## Concept 2 — Biolume Map

### Idea

Direct children as **living cells** in an organic field — area = NCBI diversity, brightness = catalog coverage, optional amber veins for threatened density, teal pulse for annotation-rich clades.

### User flow

1. Default child view inside Taxonomy Shell (toggle with Descent / Constellation).
2. Hover: neighbors dim, hovered cell brightens.
3. Click: cell inflates to center; siblings reflow (FLIP or d3-force transition).
4. **Light spill:** selected cell’s brightness propagates upward along Ancestor Rail.

### Data → visuals

| Channel | Field / formula |
|---------|-----------------|
| Area | `sqrt(species_count_ncbi)` or `log1p` |
| Fill opacity | `clamp(pct_ncbi_species_with_data, 0, 1)` |
| Pulse (CSS animation) | on if `species_with_assembly / species_count_matrix > 0.5` |
| Amber border | if `species_threatened > 0` |
| Teal inner core | if `species_with_annotation / species_count_matrix > 0.3` |

### Implementation

- **Layout:** `d3-hierarchy` not required — use **d3.pack** on flat children with synthetic root at focus taxid, or **d3-forceCollide** for organic feel.
- **Cap:** max **120 cells** per view; if more children, show top 119 by `species_count_matrix` + synthetic **“Dust (N clades)”** aggregate cell.
- **High fanout:** known max ~403 children — pagination or “importance filter” toggle required.
- **Performance:** single SVG layer + CSS transforms; avoid re-layout on every frame.
- **Lens switch:** call `lensEncoding.ts` to remap color without re-fetching.

### Do not

- Run force simulation on 156k nodes.
- Use matrix-only area (empty NCBI clades must still occupy space as ghosts).

---

## Concept 3 — Rank Constellation

### Idea

At each focus taxon, render the **next canonical rank** as a **constellation**: Mammalia → 29 order stars. Size = NCBI species; brightness = catalog %. Sister clades share subtle constellation lines; background is faint noise (phylogenetic fog), not flat black.

### User flow

1. Toggle viz mode to `constellation` or auto-switch when child count ≤ 40 and ranks are uniform.
2. Click star → warp animation (star → center, others orbit outward).
3. Breadcrumb becomes **orbital trail** of ancestor dots.
4. Lens toggles (catalog / genome / risk / reads) remap star color and pulse.

### Data → visuals

| Element | Mapping |
|---------|---------|
| Star count | `{nextRank}_nodes_total` (verify against actual child count) |
| Stars with data | `{nextRank}_nodes_with_data` |
| Star radius | per-child `species_count_ncbi` |
| Star brightness | per-child `pct_ncbi_species_with_data` |
| Constellation lines | connect siblings (same `parent_taxid`) — optional, low opacity |

**Next rank helper:**

```ts
const RANKS = ["domain","kingdom","phylum","class","order","family","genus","species"] as const
function nextRank(current: string): string | null {
  const i = RANKS.indexOf(normalizeRank(current))
  return i >= 0 && i < RANKS.length - 1 ? RANKS[i + 1] : null
}
```

### Implementation

- **Tech:** SVG + Framer Motion; radial positions computed deterministically (golden angle) to avoid force layout jank.
- **Cap:** designed for ≤ 50 stars; above that, fall back to Biolume Map.
- **Search fly-to:** animate camera from current focus to search result; ancestors light in sequence (200 ms stagger).

### Lens encodings

| Lens | Color | Motion |
|------|-------|--------|
| catalog | green brightness | none |
| genome | `mean_genome_size` gradient | none |
| risk | amber `species_threatened` | none |
| reads | teal + pulse speed ∝ `sum_run_count` | CSS pulse |

---

## Concept 4 — The Funnel Cathedral

### Idea

The genomic **data funnel** is vertical **stained glass** beside the navigator — not KPI cards. Band width = species count at each stage; leaks between bands show attrition from reads → assembly → annotation → full triple.

### User flow

1. Fixed left column (desktop) or bottom sheet (mobile) in Taxonomy Shell.
2. On taxon change, bands **morph** (FLIP / animated height).
3. Click a band → open Specimen Stream filtered to species at that tier.
4. Optional IUCN branch: assessed → threatened (parallel narrow column).

### Data → visuals

| Band | Count field |
|------|-------------|
| Full height (dim glass) | `species_count_ncbi` |
| Reads | `species_with_reads` |
| Assembly | `species_with_assembly` |
| Annotation | `species_with_annotation` |
| Full triple | `species_full_triple` |
| IUCN assessed | `species_iucn_assessed` |
| Threatened | `species_threatened` |

Labels show absolute count + `% of parent band`. Example: assembly band shows `3,102 (38% of reads)`.

### Implementation

- **Tech:** pure CSS/SVG rects; heights proportional to counts within column max height.
- **Shared:** mount once in `TaxonomyShell`; feed `GET /api/taxa/[taxid]` row.
- **Means elsewhere:** if showing `mean_busco_complete`, place in Dive Computer panel with `n_with_annotation` — not in the cathedral.
- **Empty clade:** single dim panel: “No catalog species — {ncbi} NCBI species”.

### Do not

- Sum `base_count` fields as effort metrics (see [SCATTER_METRICS.md](./SCATTER_METRICS.md)).
- Show means without `n_with_*` denominators.

---

## Concept 5 — Specimen Stream

### Idea

Species list as a **horizontal museum drawer** — scroll-snap cards with photo, data-tier glyphs, and field-journal detail sheet. Replaces table-first species UX at genus and below (or any taxon with `species_count_matrix > 0`).

### User flow

1. Tab or auto-open when `rank` ≥ `genus` or user clicks “N species in catalog”.
2. Horizontal scroll-snap stream; keyboard ←/→.
3. Pin card → floats above stream while browsing clades.
4. Card click → `species-detail-sheet` reskinned as field journal.
5. **Open in Explore** → `/explore?taxon={focusTaxid}` with portal transition.

### Data sources

| Field | Source |
|-------|--------|
| Species list | `GET /api/taxa/[taxid]/species` from `05_eukaryotic_species_matrix.tsv` |
| Photo | `data/species_photos.tsv` (iNaturalist) |
| Detail | `GET /api/organisms/[taxid]` |
| Data tier glyph | derived: 3 dots for reads / assembly / annotation |

### Implementation

- **Virtualization:** `@tanstack/react-virtual` if vertical fallback; horizontal scroll-snap for ≤ 200 species per genus.
- **Pagination:** 50 per page; infinite scroll or “load more”.
- **Filter by funnel tier:** query param `?tier=assembly` maps to matrix boolean columns.
- **Reuse:** extend existing `species-detail-sheet.tsx`; add taxonomy ribbon and outbound INSDC links per [MODELS.txt](./MODELS.txt).

### Card content (keep minimal)

- Scientific name (italic)
- Thumbnail or letter placeholder
- `{runs} · {assembly?} · {annot?}` shorthand
- IUCN badge if present

---

## Concept 6 — Compare as Symbiosis

### Idea

Pin two taxa to compare **catalog illumination** side by side — overlapping rings, funnel diff, rank breakdown comparison. For research storytelling: “Why is this phylum under-sequenced vs that one?”

### User flow

1. “Pin compare” on any taxon → sets `compareTaxid`.
2. Split view: focus clade left, pinned clade right; shared ancestor highlighted if nested.
3. Center overlap shows shared parent path stats (optional).
4. Venn-style funnel diff: assembly rate, threatened %, mean genome size (with n).

### Data → visuals

| Panel | Content |
|-------|---------|
| Left / right ring | same encoding as Descent horizon |
| Center connector | nearest shared ancestor taxid from `/ancestors` |
| Diff bars | pairwise delta on `pct_ncbi_species_with_data`, funnel stages |
| Table row | side-by-side rank node counters |

### Implementation

- **API:** two parallel fetches `/api/taxa/[id]`; compute shared ancestor client-side from ancestor taxid lists.
- **URL:** `?compare=33208`.
- **Scope:** v2 feature — build after Concepts 1, 4, 5 are stable.
- **Mobile:** stacked cards instead of overlapping rings.

---

## Concept 7 — The Lit Room

### Idea

Each clade is a **lit chamber**. Room brightness reflects catalog coverage (`pctCatalog`); ghost clades (matrix = 0) get a fog overlay. **Child threshold cards** below the details card lead deeper; **floor mosaic** tiles represent catalog species at genus rank (mock: Trichosanthes). Parent and child cards **morph into the hero details card** on ascend/drill.

### Route

`/taxonomy/lit-room` — standalone bespoke prototype; `/taxonomy/focus` unchanged.

### Bespoke components (v2 rebuild)

All UI is built under `components/taxonomy/lit-room/` with no reuse of Focus Stack spine, `DiveComputer`, `FunnelCathedral`, or `SpeciesDetailSheet`:

| Component | Role |
|-----------|------|
| `AncestryFilament` | Bioluminescent ancestor thread |
| `ParentAscendCard` | Compact clade card above details; morphs down on ascend |
| `ChamberStack` | Glow/fog chamber wrapper |
| `ChamberDetailsCard` | Hero details card (morph target) |
| `CladeCardShell` | Shared card chrome for parent/child/clone |
| `ChamberHeadline`, `CoverageArc`, `FunnelStrip`, `GhostVeil` | Details content |
| `ChildThreshold`, `ThresholdCard`, `DustPanel` | Horizontal child strip below details |
| `FloorMosaic`, `SpecimenStone`, `SpecimenGlyphs` | Floor mosaic |
| `TileLevitation` | Levitated specimen detail overlay |
| `useChamberMotion` | Card morph drill/ascend, jump, levitate |

### Layout (desktop)

Two zones: left ancestor filament, center stacked column.

```
grid-cols-[4rem_minmax(0,1fr)]
  ParentAscendCard
  ChamberDetailsCard (hero)
  ChildThreshold (horizontal scroll)
  FloorMosaic (optional)
```

### Mode rules (`getLitRoomMode`)

| Flag | Rule |
|------|------|
| `showDoorways` | `getChildDeck(focusTaxid).visible.length > 0` |
| `showFloor` | `getSpeciesForTaxid(focusTaxid).length > 0` |
| `isGhost` | `species_count_matrix === 0` |
| `chamberGlow` | `pctCatalog(focus)`, clamped 0–1 |
| `depthHue` | `160 + depth_from_eukaryota * 2` |

Both doorways and floor can render together; mock genus Trichosanthes is leaf-like (floor only).

### Motion

| Direction | Behavior |
|-----------|----------|
| `drill` | Child threshold card rises + expands into hero details card |
| `ascend` | Parent card drops + expands into hero details card |
| `jump` | View Transition on details card + relight |
| `levitate` | Floor stone scales to center overlay; chamber dims |

Keyboard: ←/→ (or ↑/↓) cycle threshold tiles; Enter drills or lifts; Esc/← ascends or closes levitation.

### Acceptance

| Check | Expected |
|-------|----------|
| Eukaryota load | Doorways visible; chamber glow > 0 |
| Drill first doorway | Chamber taxon name updates |
| Ascend parent | Returns to parent clade |
| Jump to Trichosanthes | `[data-species-tile]` floor grid visible |
| Click tile | Detail sheet or lift overlay opens |
| Ghost clade | Fog overlay, reduced glow |
| Reduced motion | Instant navigation, no FLIP |
| `npm run check:lit-room` | Passes with dev server |

---

## Concept 8 — The Lit Tree

### Idea

Merge Lit Room visuals with a **vertical collapsed-card tree**. Ancestors and children appear as compact [`CladeCardShell`](next-app/components/taxonomy/lit-room/CladeCardShell.tsx) cards; the **focused clade** expands via [`LitTreeCladeCollapse`](next-app/components/taxonomy/lit-tree/LitTreeCladeCollapse.tsx) into the reused [`ChamberDetailsCard`](next-app/components/taxonomy/lit-room/ChamberDetailsCard.tsx). Depth-based SVG connector lines in [`LitTreeGutter`](next-app/components/taxonomy/lit-tree/LitTreeGutter.tsx) — hover a segment to surface that ancestor in [`CladeTooltipCard`](next-app/components/taxonomy/CladeTooltip.tsx).

### Route

`/taxonomy/lit-tree` — standalone prototype (tree + details only; no floor mosaic in v1).

### Components

| Component | Role |
|-----------|------|
| `LitTreeShell` | Concept 8 header + live region |
| `LitTreePanel` | Scroll container + row registration |
| `LitTreeGutter` | SVG trunk/elbows + segment hover |
| `LitTreeRow` | Indented row (ancestor / focus / child) |
| `LitTreeCladeCollapse` | Collapsible wrapper around `ChamberDetailsCard` |
| `buildLitTreeRows` | Ancestor path + focus + child deck |
| `useLitTreeNav` | Jump, drill, ascend, selection |

### Layout

```
LitTreePanel (scroll)
  [optional root jump]
  LitTreeGutter (absolute SVG)
  LitTreeRow × N
    indent = depth × 1.25rem
    ancestor/child → compact CladeCardShell
    focus → LitTreeCladeCollapse → ChamberDetailsCard
```

### Interactions

| Input | Action |
|-------|--------|
| Click ancestor | Jump to that taxon |
| Click child | Drill (child becomes focus) |
| Esc | Ascend to parent |
| ↑/↓ | Cycle row selection |
| Enter | Activate selection; expand focus if collapsed |
| Hover `[data-tree-segment]` | Show ancestor tooltip |

### Acceptance

| Check | Expected |
|-------|----------|
| Eukaryota load | Focus expanded; children as collapsed cards below |
| Click child | Focus details title updates |
| Hover tree segment | Tooltip with ancestor name + stats |
| Esc | Ascends to parent |
| Jump to genus | Tree rebuilds at genus focus |
| `npm run check:lit-tree` | Passes with dev server |

---

## Shell layout (all concepts)

```
┌──────────────────────────────────────────────────────────────────┐
│  TaxonSearch          viz toggle: Descent | Biolume | Constellation │
├────────────┬─────────────────────────────────────────────────────┤
│ Ancestor   │  PRIMARY VIZ (Concept 1 / 2 / 3)                    │
│ Rail       │                                                     │
│            ├─────────────────────────────────────────────────────┤
│ Funnel     │  DiveComputer — dual headline, lens toggles         │
│ Cathedral  │  {matrix} / {ncbi} species · rank label             │
│ (Concept 4)│                                                     │
├────────────┴─────────────────────────────────────────────────────┤
│  Specimen Stream (Concept 5) — collapsible                       │
└──────────────────────────────────────────────────────────────────┘
```

**Symbiosis (Concept 6):** replaces primary viz with split compare when `compareTaxid` set.

---

## Interaction & motion spec

| Moment | Behavior | Duration |
|--------|----------|----------|
| First load | rings fade from 0 → target opacity; inner glow 0 → catalog % | 600 ms |
| Drill down | scale out parent, scale in children; ancestor thread persists | 350 ms |
| Ascend (Esc) | reverse drill | 350 ms |
| Search result | fly to taxid; ancestors light stagger | 200 ms × depth |
| Lens change | cross-fade color only | 200 ms |
| Empty clade | no animation; show ghost + copy | — |
| Reduced motion | respect `prefers-reduced-motion`; skip pulse/warp | — |

### Keyboard

| Key | Action |
|-----|--------|
| `/` | focus search |
| `↑` / `↓` | move selection among children |
| `Enter` | drill into selected child |
| `Esc` | up one ancestor |
| `s` | toggle Specimen Stream |
| `c` | pin compare (Concept 6) |

---

## Build order (recommended)

| Phase | Deliverable | Concepts |
|-------|-------------|----------|
| **0** | SQLite API routes + `TaxonomyShell` + URL focus | shared |
| **1** | Funnel Cathedral + Dive Computer + Ancestor Rail | 4 |
| **2** | Biolume Map (default children view) | 2 |
| **3** | Specimen Stream + species API + detail sheet reskin | 5 |
| **4** | The Descent horizon + drill animations | 1 |
| **5** | Rank Constellation + lens toggles | 3 |
| **6** | Symbiosis compare | 6 |

Phase 0–3 delivers a usable, distinctive taxonomy browser. Phases 4–6 add signature motion and delight.

---

## Testing & acceptance

| Check | Expected |
|-------|----------|
| Eukaryota (2759) | `104,086 / 1,585,178` species headline |
| Mammalia (40674) | `2,317 / 10,037`; 29 order stars in constellation mode |
| Ghost clade | matrix = 0 renders outline-only, no fake brightness |
| High fanout | > 120 children → aggregate “Dust” cell, no layout freeze |
| Species under genus | stream paginates; detail sheet opens |
| `/explore?taxon=` | preserves taxon filter |
| Reduced motion | no pulse animations |

---

## Anti-patterns

- Generic stat-card grid as the hero — underuses the data story.
- Recharts bar chart as primary navigation (fine for dev mock, not the product).
- Full-tree circle pack at Eukaryota root (156k induced nodes).
- Name-based routes or drill-down keys.
- Showing all 48 rollup columns in the UI.
- Light mode as default — dark forest theme is the brand ([globals.css](./next-app/app/globals.css)).
- Shipping means without `n_with_assembly` / `n_with_annotation`.

---

## Related files

| File | Role |
|------|------|
| [data/staged/06_taxon_rollups.tsv](./data/staged/06_taxon_rollups.tsv) | Flat induced hierarchy + metrics |
| [data/staged/taxonomy.sqlite](./data/staged/taxonomy.sqlite) | Runtime API database |
| [data/staged/05_eukaryotic_species_matrix.tsv](./data/staged/05_eukaryotic_species_matrix.tsv) | Species stream source |
| [pipeline/build_taxon_rollups.py](./pipeline/build_taxon_rollups.py) | Rebuild rollups |
| [next-app/app/(browse)/taxonomy/page.tsx](./next-app/app/(browse)/taxonomy/page.tsx) | Current mock (to replace) |
| [next-app/components/species-detail-sheet.tsx](./next-app/components/species-detail-sheet.tsx) | Detail sheet to extend |
