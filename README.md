# Imprint Diamond (imprint-website)

Static site + **FastAPI** API in one repo. Production deploys to **Render** (`render.yaml`), not Vercel.

## Stack

| Piece | Location | Notes |
|-------|----------|--------|
| Web + API | `app/`, `main.py` | FastAPI serves pages, `/api/*`, `/static/*` |
| Admin | `admin.html` | Product/orders/accounts UI |
| Database | Postgres (Neon or local) | `backend/schema.sql` |
| Gold quote fallback | `scripts/fetch_gold_quote.py` | GitHub Actions cron (`.github/workflows/update-gold-quote.yml`) |

## Local dev

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env            # DATABASE_URL, JWT_SECRET, …
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8080
```

Open `http://127.0.0.1:8080/`. API is same-origin (`/api/...`); leave `window.IMPRINT_API_BASE` unset.

## Deploy (Render)

1. Connect repo → Blueprint from `render.yaml`
2. Set env vars: `DATABASE_URL`, `JWT_SECRET`, etc. (see `.env.example`)
3. Run `backend/schema.sql` once on the database

## Legacy folders (not deployed)

- **`backend/`** — old Node serverless API; logic ported to `app/`. Reference only.
- **`gold-price-scraper/`** — old Puppeteer cron; replaced by `scripts/fetch_gold_quote.py` + GitHub Actions.
- **`api/bot-gold.php`** — PHP hosting fallback; production uses `app/bot_gold.py` at `/api/bot-gold`.
