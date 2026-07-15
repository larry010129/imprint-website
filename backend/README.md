# backend (legacy)

> **Not deployed.** Production uses **`app/`** (FastAPI on Render). This folder is the original Node serverless API kept for reference while porting finished.

Auth + data API for the Diamond v3 site, on Neon Postgres. Started as a Supabase replacement, then grew to port the imprint-calculator feature set in JavaScript.

Most routes now live under `app/routers/` (`auth_router`, `admin_router`, `api_router`, `shop_router`). Prefer extending the Python app, not this folder.

## If you still run it locally

1. Create a Neon project, run `schema.sql`.
2. `cd backend && npm install`
3. Set env from `.env.example` (`DATABASE_URL`, `JWT_SECRET`, …)
4. Use a Node HTTP adapter of your choice (this tree has no `vercel.json` and is **not** intended for Vercel).

Point a test site's `window.IMPRINT_API_BASE` at wherever you host it. Production site uses same-origin `/api` on Render instead.

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | /api/auth/signup | — | create account (+ optional invite code), sets session cookie |
| POST | /api/auth/login | — | sets session cookie; locks out after 5 fails / 5 min |
| POST | /api/auth/logout | — | clears session cookie |
| GET | /api/auth/session | — | `{user, profile, isAdmin}` or `{user: null}` |
| POST | /api/auth/request-password-reset | — | emails a reset link (needs `RESEND_API_KEY`) |
| POST | /api/auth/reset-password | — | consumes the token from that email |
| GET | /api/orders | customer | the logged-in user's own orders |
| POST | /api/track-order | — | public lookup by order number + phone |
| … | … | … | See `app/routers/` for the current surface |

## What's simplified vs. real Supabase Auth

- No email verification on signup.
- One 30-day JWT cookie (no refresh rotation).
- Password reset needs `RESEND_API_KEY`.

## CORS / cookies

If the static site and this API are on different origins, set `ALLOWED_ORIGIN` and use `credentials: 'include'` on fetch. Same-origin Render deploy does not need a separate API base URL.
