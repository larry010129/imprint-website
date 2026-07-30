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

## Cloudflare Workers (experimental only)

`wrangler.toml` → `src/entry.py` (ASGI bridge). **Do not use for full production** — Workers/Pyodide cannot run `psycopg`, disk uploads, and most of this stack. Production stays on Render.

```bash
# needs Node + uv (https://docs.astral.sh/uv/)
uvx --from workers-py pywrangler dev
uvx --from workers-py pywrangler deploy
```

Plain `npx wrangler deploy` will fail or mis-handle Python packages — use **pywrangler**.
