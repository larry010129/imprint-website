# Imprint Diamond (imprint-website)

FastAPI site + API in one repo. Production deploys to **Render** (`render.yaml`).

## Stack

| Piece | Location | Notes |
|-------|----------|--------|
| Web + API | `app/controllers/`, `config/`, `main.py` | Jinja views in `app/views/`, static in `public/` |
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
npm run dev                     # uvicorn on :8080
```

Open `http://127.0.0.1:8080/`. API is same-origin (`/api/...`).

## Deploy (Render)

1. Connect repo → Blueprint from `render.yaml`
2. Set env vars: `DATABASE_URL`, `JWT_SECRET`, etc. (see `.env.example`)
3. Run `backend/schema.sql` once on the database
4. **Start Command** must be `bash scripts/render-start.sh`
