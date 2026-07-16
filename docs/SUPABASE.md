# Supabase migration guide

This project uses **Supabase Postgres** (standard PostgreSQL). Auth and API logic live in the FastAPI app (`app/`), not Supabase Auth/RLS.

## 1. Create a Supabase project

1. [supabase.com/dashboard](https://supabase.com/dashboard) → New project
2. Save the database password

## 2. Get connection strings

**Project Settings → Database → Connection string**

| Use case | Pool mode | Port |
|----------|-----------|------|
| FastAPI on Render (`app/database.py`) | Direct or **Session** | 5432 |
| Local dev / `scripts/apply_schema.py` | Direct or Session | 5432 |
| Legacy Node `backend/` serverless | **Transaction** | 6543 |

Set in `.env` (copy from **Connection string → URI**, pick **Session** mode if Direct fails locally):

```env
# Session pooler (works on IPv4-only networks; use for local dev on Windows)
DATABASE_URL=postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres

# Direct (IPv6-only on some projects — fine on Render if IPv6 works)
# DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
```

**Windows note:** Supabase Direct host (`db.*.supabase.co`) may resolve to IPv6 only. If `apply_schema.py` fails with `getaddrinfo failed` or `Network is unreachable`, switch to **Session pooler** (same dashboard page, mode = Session, port 5432). Username becomes `postgres.[PROJECT_REF]`, not plain `postgres`.

Optional (future Supabase SDK features):

```env
SUPABASE_URL=https://[PROJECT_REF].supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
```

## 3. Apply schema (empty database)

```bash
cp .env.example .env   # fill DATABASE_URL + JWT_SECRET
python scripts/apply_schema.py
```

Or via Node (legacy `backend/`):

```bash
cd backend && npm install && npm run schema
```

Or Supabase CLI:

```bash
supabase link --project-ref [PROJECT_REF]
supabase db push
```

## 4. Migrate data from Neon (optional)

If you have existing Neon data:

```bash
# Export from Neon
pg_dump "$NEON_DATABASE_URL" --no-owner --no-acl -F c -f imprint.dump

# Import to Supabase (use Direct connection URL)
pg_restore -d "$SUPABASE_DATABASE_URL" --no-owner --no-acl imprint.dump
```

Or use Supabase Dashboard → **Database → Backups / import**.

## 5. Deploy (Render)

Update Render env vars:

- `DATABASE_URL` → Supabase **Direct** or **Session pooler** URL (port 5432)
- `JWT_SECRET` → same as before (or rotate and force re-login)

Redeploy the web service.

## 6. Verify

```bash
python scripts/create_admin.py   # if needed
curl http://127.0.0.1:8080/api/auth/session
```

## Notes

- **Transaction pooler (6543)**: Node `postgres.js` sets `prepare: false` automatically when the URL contains `pooler.supabase.com` or `:6543`.
- **Extensions**: Schema uses `pgcrypto` (enabled by default on Supabase).
- **No Supabase Auth**: Users/passwords are in the `users` table; JWT cookies are issued by `app/auth.py`.
