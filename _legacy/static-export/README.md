# Legacy static HTML export

These files are **not served in production**. Render runs FastAPI only; pages come from `app/views/` (Jinja).

## Why this folder exists

The site was built in two phases:

1. **Static site** — HTML at repo root, `jewelry/`, `series/`, `shop/`, baked with `partials/` and Node scripts (`generate-pages.mjs`, `build-site-layout.mjs`).
2. **FastAPI + Jinja** — Same pages migrated to `app/views/pages/` with routing in `config/routes.py`.

The old static copies were moved here so the repo root is no longer cluttered with duplicate `.html` files.

## Do not edit for production

- Edit **`app/views/pages/`** for page content.
- Edit **`config/routes.py`** for URLs and SEO metadata.
- Run **`npm run dev`** (uvicorn) to preview changes.

## Safe to delete?

After you confirm nothing references these paths, this entire `_legacy/` tree can be removed. Keep until you are confident the Jinja migration is complete.
