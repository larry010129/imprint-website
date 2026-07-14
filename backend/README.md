# backend

Auth + data API for the static Diamond v3 site, on Neon Postgres. Started as
a Supabase replacement (Postgres + Auth + PostgREST + RLS → plain Postgres +
hand-written API), then grew to port the full imprint-calculator (Flask)
feature set: dynamic product catalog (real gold weights, admin-managed),
cart, favorites, invite codes, notifications, order search, account
management, and audit logging — same functions, rewritten in JS, not Python.

Not deployed or tested against a real Neon instance — needs your Neon +
Vercel access. Every file passes `node --check` (no syntax errors), and the
two highest-stakes pieces (auth flow, and the weight-based pricing engine)
are verified against hand-calculated expected values using a mocked DB layer
— see the bottom of this file for exactly what that covers and doesn't.

## Setup

1. Create a Neon project at console.neon.tech, copy the connection string.
2. Run `schema.sql` against it (Neon's SQL editor, or `psql "$DATABASE_URL" -f schema.sql`).
3. `cd backend && npm install`
4. Deploy as its own Vercel project (`vercel deploy`, or connect the repo/folder
   in the dashboard). Set env vars from `.env.example` in Vercel project settings.
5. Point the static site's `js/api-client.js` `API_BASE` constant at this
   project's deployed URL.

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
| POST | /api/contact | — | contact form submit |
| POST | /api/quote-request | — | calculator "send quote request" submit (static-page estimate) |
| POST | /api/quote | — | **real** quote using actual product weight + live gold price (the "臺金" calc) |
| GET | /api/catalog | — | public, published products grouped by category (shop frontend) |
| GET | /api/prices | — | live metal/diamond pricing metadata for the shop calculator |
| GET | /api/cart, POST /api/cart | customer | list / add to cart (server re-prices) |
| GET/PUT/DELETE | /api/cart-item?id= | customer | one cart item — detail+breakdown / edit / remove |
| POST | /api/cart-checkout | customer | converts cart items into real orders |
| GET/POST | /api/favorites | customer | list / save a configuration |
| DELETE | /api/favorite-item?id= | customer | remove a favorite |
| GET/POST | /api/notifications | customer | list / mark-read (e.g. "your order was removed") |
| GET | /api/pricing | — | public pricing overrides (static-page estimate model) |
| POST | /api/pricing | admin | save (`{overrides}`) or reset (`{reset:true}`) |
| GET | /api/gold-price | — | latest gold_price_cache row |
| GET | /api/admin/dashboard | admin | lead/order counts + 6-month order/revenue trend |
| GET/POST | /api/admin/leads | admin | list contact+quote leads / mark one handled |
| GET/POST | /api/admin/orders | admin | list (`?q=` searches order#/category/status/carat/metal/customer) / create |
| POST | /api/admin/order-update | admin | update an order's status |
| POST | /api/admin/order-delete | admin | delete an order; notifies the customer if it was theirs |
| GET/POST | /api/admin/products | admin | list all (incl. drafts) / create a product+variants+images |
| POST | /api/admin/product-update | admin | edit a product (replaces its variants+images wholesale) |
| POST | /api/admin/product-action | admin | `{action: publish\|unpublish\|delete\|duplicate}` |
| POST | /api/admin/products-reorder | admin | `{order: [id,...]}` sets catalog sort order |
| GET/POST | /api/admin/invites | admin | list / create registration invite codes |
| POST | /api/admin/invite-action | admin | `{action: revoke\|delete}` |
| GET | /api/admin/accounts | admin | list all user accounts |
| POST | /api/admin/account-action | admin | `{action: toggle-active\|clear-lockout\|delete\|reset-password}` |

## What's ported vs. what's genuinely not (be honest about this before relying on it)

**Ported, working, verified by logic tests (not yet against real Neon):**
diamond+metal weight-based pricing engine (`lib/pricing.js`), submission
validation (`lib/validation.js`), login/register lockout (`lib/rateLimit.js`),
invite codes (`lib/invites.js`), audit logging (`lib/audit.js`), the full
catalog/cart/favorites/orders/accounts/invites CRUD surface above, and the
dynamic shop calculator frontend at `shop/calculator/` (ported from
imprint-calculator's `shop/templates/calculator` + `shop/static/js/script.js`).

**Not ported — genuinely missing, not just "simplified":**
- **Cart / favorites pages.** The shop calculator can add to cart, checkout a
  single item, and save favorites via API, but there is no dedicated cart or
  favorites UI page yet (old Flask had `/cart` and `/favorites`).
- **Image upload.** `validateProductFields` expects `images: [{color, url}]`
  — i.e. already-hosted URLs. There's no upload endpoint; the original
  Flask app wrote files to its own disk via multipart form uploads, which
  doesn't translate directly to a serverless function (no persistent
  filesystem). Needs a real object storage service (Vercel Blob, S3,
  Cloudflare R2) wired in before admins can actually add product photos.
- **CSV export** of the dashboard (`dashboard.py`'s `dashboard_csv`) — not built.
- **Quote-sheet share links** (`/s/<token>` in the Flask app, for sending a
  shareable price breakdown) — not built.
- **Ring size guide data/UI** (`ring_sizes.py`) — not wired in anywhere.
- **Real-time rate limiting on `/api/track-order`** specifically (login/register
  are covered; this guessable-credential endpoint still has none).

## What's simplified vs. real Supabase Auth / Flask-Login

- **No email verification.** `signup.js` sets `email_verified = true`
  immediately and logs the user straight in.
- **No refresh tokens.** One 30-day JWT in an httpOnly cookie — simpler than
  Supabase's short-lived-access + refresh-token pair; a stolen cookie is
  valid for the full 30 days with no revocation beyond rotating `JWT_SECRET`
  (which logs out everyone).
- **Password reset emails need `RESEND_API_KEY`.** Without it, the token is
  generated and stored but the email never sends — check server logs for
  the reset URL while testing.

## CORS / cookies

The static site and this API are different origins, so session cookies use
`SameSite=None; Secure` and every fetch from the site must pass
`credentials: 'include'` (already done in `js/api-client.js`). `ALLOWED_ORIGIN`
must exactly match the site's deployed origin — wildcard `*` cannot be used
together with credentialed requests per the CORS spec.

## Verification performed this session (mocked DB, no real Neon access)

- Full auth flow: signup → cookie → session → login accept/reject → tampered
  JWT rejected.
- Admin gate: no session → 401, non-admin → 403, admin → 200.
- Pricing engine: hand-calculated an 18k ring, 0.5 chin weight, 0.5ct diamond
  against `computeOrderPricing` — matched exactly (NT$110,446: diamond
  98,000 + taxed metal 7,196 + taxed labor 5,250). Verified a missing variant
  is correctly rejected, and the multi-stone "above 0.3ct" tier math is
  correct (189,600 × 0.80 = 151,680).
- Everything else above (catalog CRUD, cart, favorites, invites, accounts,
  order search/delete) is untested beyond `node --check` passing — it
  hasn't run against a real database. Test these against your actual Neon
  instance before trusting them with real data.
