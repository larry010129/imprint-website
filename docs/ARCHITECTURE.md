# Imprint Diamond — project structure (MVC)

Production is a **FastAPI** app. Pages are **server-rendered Jinja views**; React bundles are **islands** (nav, footer, price table, checkout).

## Directory map

```
imprint-website/
├── config/                  # App configuration and routing
│   ├── settings.py          # Paths, env, Render URLs
│   └── routes.py            # URL → view template + SEO metadata (PageMeta)
├── public/                  # Static assets (CSS, JS, images, React build output)
│   ├── css/
│   ├── js/
│   ├── images/
│   └── react/               # Vite build output (nav.js, footer.js, …)
├── app/
│   ├── controllers/         # Request handlers (was app/routers/)
│   │   ├── web_controller.py    # HTML pages + static mounts
│   │   ├── api_controller.py    # /api/catalog, /api/bot-gold, …
│   │   ├── auth_controller.py
│   │   ├── shop_controller.py
│   │   └── admin_controller.py
│   ├── views/               # UI templates (was app/templates/)
│   │   ├── layouts/         # base.html, base-auth.html
│   │   ├── pages/           # One file per route (about, shop/calculator, …)
│   │   ├── partials/        # Nav/footer/React includes
│   │   └── fragments/       # HTML chunks for jewelry/series pages
│   ├── models/              # Data structures
│   ├── schemas/             # Pydantic API shapes
│   ├── catalog.py           # Catalog formatting (service layer)
│   ├── database.py          # Postgres connection
│   └── seed_catalog.py      # Auto-seed empty DB on startup
├── frontend/                # React source (Vite → public/react/)
├── scripts/                 # Build, deploy, gold quote fetch
├── _legacy/static-export/   # Old static HTML (not served — see README there)
├── main.py                  # FastAPI entry
└── server/main.py           # Gunicorn shim for Render
```

## MVC mapping

| MVC role | This project |
|----------|----------------|
| **Model** | `app/models/`, Postgres via `app/database.py`, catalog seed data |
| **View** | `app/views/` (Jinja HTML) + `public/js/mvc/` (client-side member pages) |
| **Controller** | `app/controllers/*.py` — parse request, call services, render view or JSON |

Member pages (cart, login, account) also use **client-side MVC** under `public/js/mvc/{models,views,controllers}/`.

## Why HTML was scattered before

Historically the repo had **two pipelines**:

| Location | Role |
|----------|------|
| Root `*.html`, `jewelry/`, `series/` | Old **static export** for Netlify-style hosting |
| `partials/` | Slots for `build-site-layout.mjs` to bake nav/footer into static HTML |
| `app/templates/` (now `app/views/`) | **Production** Jinja templates served by FastAPI |

Render deploys **Python only**, so root HTML was dead weight — duplicated content, wrong asset paths (`css/` vs `/static/css/`). Legacy files now live in `_legacy/static-export/`.

## Adding a new page

1. Create `app/views/pages/my-page.html` extending `layouts/base.html`.
2. Register route in `config/routes.py` (`PageMeta`).
3. No change needed in `web_controller.py` — it registers all entries from `config/routes.py`.

## Local dev

```bash
npm run dev          # uvicorn on :8080
npm run build:frontend   # React → public/react/
```

## Deploy (Render)

`scripts/render-build.sh` → `scripts/render-start.sh` → `gunicorn server.main:app`
