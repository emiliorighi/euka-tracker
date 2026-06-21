# euka-tracker

IUCN-centric species matrix linking Red List assessments to GBIF, iNaturalist, and NCBI genomic evidence. Static Next.js site deployed via GitHub Pages.

## Layout

```
euka-tracker/
  pipeline/     # python -m pipeline — fetch, build matrix, site-data artifact
  next-app/     # static site (GitHub Pages)
  datasets/     # pipeline inputs (gitignored)
  cache/        # GBIF / iNat / OTL downloads (gitignored)
  site-data/    # CI artifact for Pages deploy (gitignored)
  docs/         # deployment runbooks
```

## Quick start

```bash
pip install -r requirements.txt

# Smoke test (reuse existing datasets/ + cache/)
python -m pipeline --skip-download --limit 1000

# Full weekly run (requires IUCN_REDLIST_DOWNLOAD_URL)
python -m pipeline
```

Output: `pipeline/output/iucn_species_matrix.tsv` (~172k rows) and `site-data/` for deploy.

## Next.js app

```bash
cd next-app
npm install
npm run dev          # http://localhost:3000
GITHUB_PAGES=1 npm run build:pages   # static export
```

## Deployment

1. Add GitHub secret **`IUCN_REDLIST_DOWNLOAD_URL`** (IUCN saved export URL).
2. Enable **Pages → GitHub Actions**.
3. Run **Weekly IUCN pipeline** workflow; **Deploy GitHub Pages** follows on success.

See **[docs/GITHUB_PAGES.md](docs/GITHUB_PAGES.md)** and **[pipeline/README.md](pipeline/README.md)**.

## Pipeline modules

| Command | Purpose |
|---------|---------|
| `python -m pipeline` | Full weekly orchestrator |
| `python -m pipeline.fetch.iucn --force` | IUCN simple_summary.csv |
| `python -m pipeline.fetch.gbif --force` | GBIF backbone zip |
| `python -m pipeline.fetch.inat --force` | iNat taxonomy DwCA |
| `python -m pipeline.fetch.ncbi_taxonomy --force` | NCBI taxonomy.db |
| `python -m pipeline.build.matrix` | IUCN species matrix |
| `python -m pipeline.build.cross_universe --force` | cross_universe.db |
