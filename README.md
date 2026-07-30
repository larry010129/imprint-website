# Imprint Diamond (imprint-website)

Next.js site (`apps/web`) + FastAPI JSON/static API. Production deploys to **Render** (`render.yaml`).

## Stack

| Piece | Location | Notes |
|-------|----------|--------|
| Site (Next) | `apps/web/` | Browse `http://127.0.0.1:3000/` in local dev |
| API (FastAPI) | `app/`, `main.py` | JSON `/api/...`, `/static`, `admin.html` on `:8080` |
| Admin | `admin.html` | Product/orders UI (static mockup + `/api/admin/*`) |
| Database | Postgres (Supabase or local) | `backend/schema.sql`, `docs/SUPABASE.md` |
| Gold quote | `scripts/fetch_gold_quote.py` | GitHub Actions cron (`.github/workflows/update-gold-quote.yml`) |
| React islands | `frontend/` → `public/react/` | Nav, footer, price table, checkout — run `npm run build:frontend` after changes |

See **`docs/ARCHITECTURE.md`** for directory layout.

## Local dev

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env            # DATABASE_URL, JWT_SECRET, …
npm install --prefix apps/web
dev.bat                         # FastAPI :8080 + Next :3000 (two windows)
# or manually:
#   npm run dev                 # uvicorn API on :8080
#   npm run dev:web             # Next site on :3000
```

Open the site at `http://127.0.0.1:3000/`. API stays on `http://127.0.0.1:8080/api/...`.

## Deploy (Render)

1. Connect repo → Blueprint from `render.yaml`
2. Set env vars: `DATABASE_URL`, `JWT_SECRET`, etc. (see `.env.example`)
3. Run `backend/schema.sql` once on the database
4. **Start Command** must be `bash scripts/render-start.sh`
