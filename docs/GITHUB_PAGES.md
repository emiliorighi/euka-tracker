# GitHub Pages deployment

Static Next.js export + pipeline `site-data` artifact served from the same origin.

## Architecture

```mermaid
flowchart LR
  weekly[weekly-iucn-pipeline.yml] --> artifact[site-data artifact]
  artifact --> deploy[deploy-pages.yml]
  deploy --> pages[GitHub Pages]
```

**Site URL:** user/org Pages (`https://<user>.github.io/`) — no `basePath`.

## Setup

1. **Secret:** `IUCN_REDLIST_DOWNLOAD_URL` — full IUCN saved-export URL (required for weekly fetch; validated before pipeline run).
2. **Pages:** Settings → Source → GitHub Actions.
3. Run **Weekly IUCN pipeline**; **Deploy GitHub Pages** runs on success.

## Pipeline

[`pipeline/run.py`](../pipeline/run.py) — entry: `python -m pipeline`

| Step | Output |
|------|--------|
| fetch IUCN (refresh) / GBIF+iNat+NCBI taxonomy (ensure) | `datasets/`, `cache/` |
| fetch genomic TSVs (refresh) | `datasets/*.tsv` |
| build cross_universe + matrix | `datasets/cross_universe.db`, `pipeline/output/` |
| manifest | `site-data/` artifact (manifest + rollups stub; full matrix not copied) |

Optional local publish steps: `--steps matrix,rollups,scatter,tiles,labels,manifest` (see [pipeline/README.md](../pipeline/README.md)).

## Deepscatter tiles (future)

Static feather pyramid at `/tiles/iucn/v{YYYYMMDD}/`.  
Client config: [`next-app/lib/iucn/config.ts`](../next-app/lib/iucn/config.ts).

## Local smoke

```bash
python -m pipeline --skip-download --steps matrix,rollups,scatter,labels,manifest --limit 1000
cd next-app && GITHUB_PAGES=1 npm run build:pages
```

## CI notes

- GBIF backbone (~3 GB) cached under `cache/gbif/`; ensure-mode fetch skips re-download when cache hit.
- Genomic TSVs cached under `datasets/` (keyed on fetch script hash); refreshed weekly with `--force`.
- Manual **Deploy GitHub Pages** dispatch fails without `site-data/manifest.json` — run weekly pipeline first or use `workflow_run` trigger.
- Datasets and cache stay gitignored.
