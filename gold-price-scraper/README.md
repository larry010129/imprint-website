# gold-price-scraper

JS/Node port of imprint-calculator's Python + Playwright BOT gold-price
scraper. Runs as a scheduled Vercel serverless function, writes the result
to Neon Postgres, and the static Diamond v3 site reads it through the
`/backend` API's `/api/gold-price` endpoint (`ImprintPricing.getLiveGoldPrice()`
in `js/pricing-config.js`). This project and `/backend` must point at the
same Neon `DATABASE_URL` — this one writes `gold_price_cache`, `/backend`
only reads it.

**Parsing + challenge-bypass verified live** against the real BOT site
during development (headless Chrome via full `puppeteer`, not yet the
serverless `@sparticuz/chromium` build): got a real price back both times,
no 75s challenge wait needed — a proper browser fingerprint sailed straight
through. Example run: `NT$4,228.43/gram, stamp 2026/07/14 14:29`.

Not yet deployed — this needs your Vercel + Neon access to actually run on
a schedule. What's unverified is specifically the Vercel-side pieces I can't
test without your accounts: the `@sparticuz/chromium` serverless Chromium
build launching correctly in Vercel's Lambda-like runtime, the Neon write,
and the Cron trigger/auth.

## Why this exists as a separate service

`rate.bot.com.tw` sits behind a bot-challenge (redirect + `sec_cpt` cookie)
that a plain `fetch()` cannot pass — confirmed by hand, a bare request gets
302'd to a challenge page. That's true regardless of language; it's why the
original Python version needs full Playwright with challenge-wait logic,
not a Python-specific requirement. The JS equivalent needs the same thing:
a real headless browser. Supabase Edge Functions (Deno) can't run one —
they're sandboxed V8 isolates with no ability to spawn a Chromium process.
A Vercel serverless function with `puppeteer-core` + `@sparticuz/chromium`
(a Lambda/serverless-compatible Chromium build) is the standard way to run
headless Chrome in a JS serverless environment, so that's what this is.

## Setup

1. Run `../backend/schema.sql` against your Neon project (creates
   `gold_price_cache` among other tables — same schema the `/backend`
   project's API reads). Only need to run it once total, not once per project.
2. `cd gold-price-scraper && npm install`
3. Deploy this folder as its own Vercel project (`vercel deploy`, or connect
   the repo/folder in the Vercel dashboard).
4. In Vercel project settings → Environment Variables, set:
   - `DATABASE_URL` (same Neon connection string as the `/backend` project)
   - `CRON_SECRET` (any long random string — Vercel auto-sends it as
     `Authorization: Bearer <value>` on Cron-triggered requests)
5. `vercel.json` already defines the cron schedule (hourly, 08:00-22:00
   Asia/Taipei = `0 0-14 * * *` UTC) and a 60s/1024MB function budget.

## Vercel plan note

Vercel Hobby caps function duration at 60s. The original Python scraper's
challenge-wait loop can take up to 75s in the worst case. If scrapes
time out under load, either upgrade to Pro (raises the cap) or shorten
`CHALLENGE_MAX_WAIT_MS` in `api/scrape-gold.js` (less patient with BOT's
challenge, more times it'll give up and keep the last cached price instead).

## Testing locally

```
npm install
node -e "process.env.DATABASE_URL='...'; process.env.CRON_SECRET='test'; require('./api/scrape-gold')({headers:{authorization:'Bearer test'}}, {status:(c)=>({json:(b)=>console.log(c,b)})})"
```

`@sparticuz/chromium` targets Amazon Linux (Vercel's runtime) — it will
likely fail to launch a real browser on Windows/macOS dev machines. Easiest
local test: temporarily swap in full `puppeteer` (not `-core`) for local
runs, or just deploy to a Vercel preview and hit that.

## What this does NOT fix

A working live gold price alone does not make V3's mounting-fee estimates
"real" — the actual metal-cost formula (`weight_grams × per_gram × purity`)
needs a weight-in-grams figure per product per metal, which lived in the
old app's database for a completely different product catalog (戒指A/B/C
generic variants, not V3's named ring/bracelet/necklace/earring designs).
That data doesn't exist for V3's current products. Until it does, V3's
mounting fee stays a flat admin-editable estimate; the live gold price is
informational only (nothing multiplies by it yet).
