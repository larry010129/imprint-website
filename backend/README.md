# backend

Schema, seed helpers, and catalog data used at **build time** and for DB setup. The live API is **`app/controllers/`** (FastAPI on Render).

## What lives here

| Path | Purpose |
|------|---------|
| `schema.sql` | Postgres tables — run once on Supabase/local (see `docs/SUPABASE.md`) |
| `scripts/apply-schema.js` | Optional Node helper to apply schema |
| `scripts/seed-catalog.js` | Optional Node catalog seed |
| `lib/catalog-seed-data.js` | Catalog rows for `scripts/render-build.sh` → `app/data/catalog-seed-rows.json` |
| `.env.example` | Reference env vars (same as root `.env.example`) |

## Deploy

Render runs `scripts/render-build.sh`, which uses `backend/lib/catalog-seed-data.js` when Node is available. No Node server from this folder is deployed.
