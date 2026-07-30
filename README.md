# Imprint Diamond (imprint-website)

FastAPI + Jinja2 SSR + HTMX. One public origin on **Render** (`imprint-api` in `render.yaml`).

## Stack

| Piece | Location | Notes |
|-------|----------|--------|
| Site + API | `app/`, `main.py`, `content/site/templates/` | Browse `http://127.0.0.1:8080/` — HTML, `/api/...`, `/htmx/...`, `/static` |
| Admin | `admin.html` | Product/orders UI + `admin-tables` React island |
| Database | Postgres (Supabase or local) | `backend/schema.sql`, `docs/SUPABASE.md` |
| Gold quote | `scripts/fetch_gold_quote.py` | GitHub Actions cron (`.github/workflows/update-gold-quote.yml`) |
| React | `frontend/` → `public/react/admin-tables.*` | Admin only — `npm run build:frontend` |

See **`docs/ARCHITECTURE.md`** for directory layout.

## Local dev

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env            # DATABASE_URL, JWT_SECRET, …
dev.bat                         # or: npm run dev
```

Open the site at `http://127.0.0.1:8080/`.

## Deploy (Render) — production

1. Connect repo → Blueprint from `render.yaml` (service: `imprint-api` only)
2. Set env vars: `DATABASE_URL`, `JWT_SECRET`, etc. (see `.env.example`)
3. Run `backend/schema.sql` once on the database
4. **Start Command** must be `bash scripts/render-start.sh`

## Cloudflare Workers (stub only)

`src/entry.py` is a **JSON health stub** so Cloudflare Git/`wrangler deploy` succeeds.
It is **not** the FastAPI site (`psycopg`, uploads, Jinja will not run on Workers/Pyodide).

| Host | What runs |
|------|-----------|
| **Render** (`render.yaml`) | Real site + API |
| **Cloudflare Worker** | Stub `{"ok":true,...}` only |

Dashboard deploy command (current Git integration):

```bash
npx wrangler deploy
```

Requires `compatibility_flags = ["python_workers", "disable_python_external_sdk"]` (already in `wrangler.toml`).

Optional local package tooling (still not the full app):

```bash
uv sync
uv run pywrangler deploy
```
