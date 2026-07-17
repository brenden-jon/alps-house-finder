# Alps House Finder

Personal tool for two couples buying a house/chalet in the French Alps (≤€900k all-in
after renovation): scrapes live listings from free sources, scores them against 12
weighted criteria, and publishes a ranked dashboard.

## How it works

```
local Mac (launchd daily)
  └─ alpsfinder refresh
       ├─ scrape: Bien'ici (JSON API), Green-Acres, PAP, notaires, agencies, SeLoger (best-effort)
       ├─ trends: DVF official transaction data → median €/m² per commune per year
       ├─ str-snapshot: Airbnb market evidence per commune (quarterly)
       ├─ score: 12 dimensions per listing (0-1 each, stored unweighted)
       └─ export: SQLite → data/export/*.json → git push
             └─ GitHub Action builds static Next.js site → GitHub Pages (shareable URL)
```

Weights are applied client-side in the dashboard (sliders), so re-ranking is instant
and works on the static site.

## Setup

```bash
make setup          # uv venv (python 3.12) + install package
make init-db        # creates ~/alps-data/alps.db  (outside Dropbox — see below)
make load-communes  # loads data/communes/*.yaml knowledge base
```

⚠️ The SQLite DB deliberately lives at `~/alps-data/alps.db`, NOT inside this
(Dropbox-synced) folder — WAL files + Dropbox sync can corrupt the DB.
Override with `ALPS_DB=/path/to.db`.

## Commune knowledge base

`data/communes/*.yaml` — one file per candidate commune with objective facts
(INSEE, altitudes, Geneva drive time) and curated ratings (ski, backcountry, summer,
charm, village life, tourism-license risk with cited notes). See `data/communes/_schema.md`.
License-risk facts move quarterly (Le Meur law) — re-verify regularly.

## Scoring dimensions

ski_access, altitude_security (2700m+ = climate-safe), backcountry, summer, charm,
village_life, geneva_access, license_safety, rental_yield, price_value (vs DVF),
space_fit, condition (DPE; G = rental ban). Hard filters: all-in ≤€900k, bedrooms ≥3.

## ToS note

Personal, non-commercial use: low request rates, caching, always linking back to
source ads. Don't publish scraped data beyond the private dashboard.
