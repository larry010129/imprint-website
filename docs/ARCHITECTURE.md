# Imprint Diamond — project structure (MVC)

Production is a **single FastAPI** service. Public pages are **Jinja SSR + HTMX**. React is **admin-tables only** (`admin.html`).

## Directory map

```
imprint-website/
├── config/                  # App configuration and routing
│   ├── settings.py          # Paths, env, Render URLs
│   └── routes.py            # URL → view template + SEO metadata (PageMeta)
├── public/                  # Static assets (CSS, JS, images)
│   ├── css/
│   ├── js/
│   ├── images/
│   └── react/               # Vite output: admin-tables (+ frozen chrome CSS)
├── content/site/
│   ├── templates/           # Jinja SSR root (layouts/, pages/, partials/)
│   ├── bodies/              # Optional slot-seed HTML (export_site_content)
│   └── fragments/           # HTML chunks for jewelry/series pages
├── app/
│   ├── controllers/         # Request handlers (web, htmx_*, api, admin, …)
│   ├── models/              # Data structures
│   ├── schemas/             # Pydantic API shapes
│   ├── catalog.py           # Catalog formatting (service layer)
│   ├── database.py          # Postgres connection
│   └── seed_catalog.py      # Auto-seed empty DB on startup
├── frontend/                # Admin React only (Vite → public/react/admin-tables.*)
├── scripts/                 # Build, deploy, gold quote fetch
├── backend/                 # schema.sql + catalog seed lib (build/DB setup only)
├── main.py                  # FastAPI entry
└── server/main.py           # Gunicorn shim for Render
```

## MVC mapping

| MVC role | This project |
|----------|----------------|
| **Model** | `app/models/`, Postgres via `app/database.py`, catalog seed data |
| **View** | `content/site/templates/` (Jinja HTML) + HTMX partials under `partials/htmx/` |
| **Controller** | `app/controllers/*.py` — parse request, call services, render view or JSON |

## History

Static-export and dual Next+API stacks are gone. **Only** `content/site/templates/` + `config/routes.py` define public pages.

## Adding a new page

1. Create `content/site/templates/pages/my-page.html` extending `layouts/base.html`.
2. Register route in `config/routes.py` (`PageMeta`).
3. No change needed in `web_controller.py` — it registers all entries from `config/routes.py`.

## Local dev

```bash
npm run dev              # FastAPI + Jinja on :8080 — browse http://127.0.0.1:8080/
# or: dev.bat
npm run build:frontend   # Admin React → public/react/admin-tables.*
```

## Deploy (Render)

Sole service `imprint-api`: `scripts/render-build.sh` → `scripts/render-start.sh` → `gunicorn server.main:app`
