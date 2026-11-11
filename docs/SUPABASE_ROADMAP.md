# Supabase Roadmap & Learning Guide

What we use today (from the code): **Supabase Postgres** (via `psycopg` pool, `app/database.py`) and **Supabase Storage** (bucket `shop-media`, `app/storage.py`). Auth, API, email (Resend), 2FA, Google login, gold scraping and site-visit tracking all live in our FastAPI app on Render.

Supabase is a Postgres database plus a bundle of services around it. We use two pieces; the rest of this file lists what else could improve UX, safety and maintainability. Tags: **[UX]** visitor/customer experience, **[SAFE]** security/reliability, **[OPS]** developer/admin workflow.

---

## How to learn it (in this order)

1. **Postgres basics inside the dashboard** – Table Editor, SQL Editor, Database → Indexes / Extensions. We already have 30+ migrations in `supabase/migrations/`; read them as the real schema.
2. **RLS (Row Level Security)** – the one concept that matters most. Docs: *Database → Row Level Security*.
3. **Storage** – buckets, public vs private, image transformations.
4. **Advisors** – Dashboard → Advisors (Security + Performance). It tells you what is wrong in plain language. Free and the best teacher.
5. **Cron / Edge Functions / Realtime** – only when a task needs them (see items below).
6. **Supabase CLI** – `supabase start` runs a full local copy; `supabase db diff` / `db push` manage migrations.

Docs: https://supabase.com/docs

---

## HIGH priority (do first: safety / data loss / money)

### H1. RLS on every table [SAFE] — CHECKED 2026-11-10, mostly OK
- **Live check (Security Advisor, project `imprint-website`):** RLS is **enabled on all 46 public tables** (`users`, `orders`, `order_contacts`, `profiles`, etc.), with **no policies**. That means the Data API / anon key can read nothing, while our FastAPI direct connection still works. This is the correct setup for an app that does its own auth. No ERROR/WARN-level security issues were reported.
- **Gap:** the migration files only show RLS for 3 tables, so RLS was enabled outside the repo (dashboard or ad-hoc SQL). A fresh `supabase start` or a rebuilt project from `supabase/migrations/` would **not** have it.
- **Do:** add one migration that runs `ALTER TABLE … ENABLE ROW LEVEL SECURITY` for all 46 tables (idempotent), and add `ALTER DEFAULT PRIVILEGES`/an event trigger or a checklist step so new tables get RLS. Optionally disable the Data API (Settings → API) since we never use it. Re-run the Advisor after each new table.

### H2. Stop local development from writing to production [OPS]
- **Finding:** local `.env` points at the production DB (known gotcha: pytest DB tests write live data).
- **Do (pick one):**
  - **Local stack:** `supabase start` → local Postgres + Storage on your PC, `DATABASE_URL` points to it, migrations replay from `supabase/migrations/`.
  - **Branching:** Supabase DB Branches give a throwaway copy of the schema per feature (paid plans).
  - **Second free project** named `imprint-staging` for dev/test.
- Update `tests/conftest.py` to refuse to run when `DATABASE_URL` host matches production.

### H3. Backups & recovery [SAFE]
- Confirm which plan we are on: Free has **no** point-in-time recovery; Pro has daily backups; PITR is an add-on.
- Orders, users and CMS content live only in this DB. At minimum schedule a weekly `pg_dump` (Render cron job or GitHub Action) to a separate storage location, and do **one restore test**.

### H4. Secrets hygiene [SAFE]
- `SUPABASE_SERVICE_ROLE_KEY` bypasses all RLS. Keep it only in Render env vars (already `sync: false`); never in the frontend, `wrangler.toml`, `public/`, or `video/`/`brag-output/` folders.
- Rotate it if it was ever pasted in chat/logs. Move to the new `sb_secret_…` keys (already supported in `app/storage.py`).

### H5. Connection pooling sanity [SAFE]
- Render + Supabase: use **Session pooler (5432)** (already documented). Check `psycopg_pool` max size against the Supabase plan's connection limit; a gunicorn worker count × pool size can exceed it and cause "too many connections" during traffic spikes.

---

## MID priority (clear UX or operational gain)

### M1. Storage image transformations + CDN caching [UX]
- Product/banner images are the heaviest part of the site. Supabase can resize/convert on the fly: `…/storage/v1/render/image/public/shop-media/<path>?width=600&quality=75`.
- Use for product grids, mobile banners, thumbnails; keeps original uploads. Pair with `cacheControl` on upload (e.g. 1 year, immutable filenames). Directly improves page speed and Core Web Vitals / SEO. (Transformations require Pro plan; check. Our own `app/image_convert.py` webp path is the fallback.)

### M2. Slow-query and index audit [UX]
- **Live check 2026-11-10 (Performance Advisor):** 9 foreign keys have no covering index: `coupon_redemptions.order_id` and `.user_id`, `coupons.created_by_id`, `favorite_items.product_id`, `invite_codes.created_by_id` and `.used_by_id`, `password_reset_tokens.user_id`, `products.created_by_id`, `user_notifications.order_id`. Most important for speed: `password_reset_tokens.user_id`, `favorite_items.product_id`, `user_notifications.order_id`, `coupon_redemptions.user_id/order_id`. Add them in one migration (`CREATE INDEX IF NOT EXISTS …`).
- 7 indexes were never used (`orders_summary_zh_idx`, `order_contacts_phone_idx`, `order_items_product_id_idx`, `coupon_redemptions_batch_idx`, `cms_pages_status_idx`, `cart_items_product_id_idx`, `share_links_last_seen_idx`). With low traffic this is not proof they are useless; re-check after a month before dropping any.
- Enable `pg_stat_statements` (Database → Extensions) and look at the top 10 slowest queries. Fixes pages that feel slow without code changes.

### M3. Replace in-process loops with `pg_cron` [OPS]
- The FastAPI process currently runs background tasks: gold price scrape interval, site-visit flush loop, featured-video sync. If Render restarts or scales to 2 instances, jobs can double-run or miss.
- `pg_cron` runs SQL on a schedule inside the DB (cleanup of expired `password_reset_tokens`, `login_lockouts`, old `site_visits`, expired `share_links`). Scraping itself stays in Python (or an Edge Function, see L2).

### M4. Database webhooks / triggers for notifications [UX][OPS]
- We already have `discord_notify.py` and `mail.py`. A DB webhook (Database → Webhooks) or a trigger can fire when a row is inserted into `orders`, `consult_bookings`, `contact_messages`, `quote_requests`, so notifications cannot be skipped if a code path forgets to call them.

### M5. Search that works in Chinese [UX]
- Product/catalog search: use `pg_trgm` (fuzzy / partial match, works for CJK substring search) with a GIN index; standard `tsvector` full-text search does not segment Chinese well. Gives "type a few characters and find the product" behavior.

### M6. Supabase Realtime for the admin dashboard [OPS]
- Admin orders / consult bookings page can update live when a new row arrives (Realtime on selected tables, subscribed by the admin page). Replaces manual refresh. Must be paired with RLS (H1) and a read-only policy or a server-issued token, never the service key in the browser.

### M7. Log & error visibility [OPS]
- Dashboard → Logs (Postgres, API, Storage). Learn to filter slow queries and failed uploads. The MCP `get_logs`/advisors tools can also surface problems when debugging.

---

## LOW priority (nice to have / bigger bets)

### L1. Supabase Auth instead of custom auth [SAFE][UX]
- We built our own: bcrypt, JWT cookies, Google login, TOTP 2FA, lockouts, reset tokens. Supabase Auth gives magic links, phone OTP (useful in Taiwan), more social providers, MFA, session management.
- **Risk:** large migration of `users`/`profiles`, rewrites login flows and tests, and `token_version` logic. Only worth it if we want phone/LINE login or want to delete auth code. Not recommended now; revisit after H1–H5.

### L2. Edge Functions [OPS]
- Small serverless TypeScript endpoints close to the DB (webhook receivers, gold-price fetch, image processing). Useful if we ever want to shrink the Render service. Not needed while FastAPI works.

### L3. Private buckets + signed URLs [SAFE]
- For anything not public (customer uploads, memorial diamond reference photos, invoices): private bucket + short-lived signed URLs instead of public URLs.

### L4. Vault / encrypted columns [SAFE]
- Store third-party tokens (e.g. API keys saved by admin) with Supabase Vault instead of plain columns. Check whether any `*_token`/`*_secret` columns hold sensitive plaintext.

### L5. Read-only analytics views [OPS]
- Replace parts of `admin_dashboard.py` aggregation code with SQL views / materialized views (daily visits, sales per category, coupon usage), refreshed by `pg_cron`.

### L6. Vector search with `pgvector` [UX]
- "Find similar rings" or a chat assistant grounded in product/knowledge content (`llms.txt` content could be embedded). Experimental; do after M5.

### L7. Typed schema docs [OPS]
- `supabase gen types` (TypeScript) or generate an ERD (the repo already has a drawDB skill) from the migrations so new contributors can see the schema at a glance.

---

## Suggested 4-week order

| Week | Do |
|------|----|
| 1 | H1 (run Security Advisor, enable RLS), H4, H5 |
| 2 | H2 (local stack or staging project), H3 (backup + restore test) |
| 3 | M2 (indexes), M1 (image transforms on product grid) |
| 4 | M3 (`pg_cron` cleanup), M4 (order/booking webhooks), then evaluate M5/M6 |

## Questions to answer before starting
- Which Supabase **plan** are we on? (decides PITR, transformations, branching)
- Is the Data API / anon key actually exposed or already disabled?
- Is there a staging project, or only production?

> Note: H1 and M2 were verified against the live project with the Security and Performance Advisors on 2026-11-10 (read-only). The other items still come from reading the repo; confirm plan, backups and Data API status in the dashboard.
