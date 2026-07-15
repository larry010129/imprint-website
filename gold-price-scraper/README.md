# gold-price-scraper (legacy)

> **Not deployed.** Scheduled gold quotes use **`scripts/fetch_gold_quote.py`** and GitHub Actions (`.github/workflows/update-gold-quote.yml`). This folder is an older Puppeteer + Neon experiment.

JS port of imprint-calculator's BOT gold-price scraper. `rate.bot.com.tw` needs a real browser (bot challenge); plain `fetch()` fails.

## Production path (use this)

```bash
python scripts/fetch_gold_quote.py
```

Writes `data/gold-quote.json` and `js/gold-quote-data.js`. CI runs hourly 08:00–22:00 Taipei time.

Live API: FastAPI `GET /api/bot-gold` (`app/bot_gold.py`) when the site runs on Render.

## If you experiment with this folder

1. Same `gold_price_cache` table as `backend/schema.sql` (optional; production fallback files above are enough for static display).
2. `cd gold-price-scraper && npm install`
3. Set `DATABASE_URL`, `CRON_SECRET` in `.env` (see `.env.example`)
4. Invoke `api/scrape-gold.js` from your own cron host (systemd, GitHub Actions, Render cron job, etc.). **No `vercel.json`** — schedule it yourself.

`@sparticuz/chromium` targets Linux serverless; on Windows/macOS use full `puppeteer` for local tests or run in CI/Linux.

## What this does NOT fix

Live gold price alone does not replace per-product metal weights for mounting fees. V3 mounting fees remain admin-editable estimates until weight data exists per SKU.
