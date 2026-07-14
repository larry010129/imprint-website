# Component-based layout

All public pages share chrome from **`partials/`**, loaded at runtime by **`js/site-layout.js`**.

Edit nav / footer / topbar **once** in `partials/` — every page updates automatically.

## Partials

| File | Loaded on |
|---|---|
| `head-common.html` | Optional head injection (favicon + CSS baseline) |
| `topbar.html` | Every page |
| `nav.html` | Every page — canonical menu from landing page |
| `footer.html` | Every page |
| `home-main.html` | `index.html` only — homepage sections |

## Page structure

```html
<body data-site-root="../../../" data-site-active="jewelry" class="site-layout">
  <div data-site-include="topbar"></div>
  <div data-site-include="nav"></div>
  <main>
    <!-- page-only content here -->
  </main>
  <div data-site-include="footer"></div>
  <script src="../../../js/site-layout.js?v=1.1"></script>
  <script src="../../../js/main.js?v=1.9"></script>
</body>
```

### `data-site-root`

Relative path back to site root:

| Location | Value |
|---|---|
| `about.html` | *(empty)* |
| `jewelry/index.html` | `../` |
| `jewelry/rings/classic-solitaire/index.html` | `../../../` |
| `shop/calculator/index.html` | `../../` |

### `data-site-active` (optional)

Highlights the current nav item: `price`, `shop`, `diamonds`, `jewelry`, `knowledge`, `about`, `account`.

## New pages

1. Copy `template.html` from repo root.
2. Replace `{{ROOT}}`, `{{NAV_ACTIVE}}`, and page content placeholders.
3. Keep the four `data-site-include` slots + layout scripts.

Homepage uses an extra slot inside `<main>`:

```html
<div data-site-include="home-main"></div>
```

## Requirements

- Serve over HTTP (`npx serve .` or your host) — `fetch` does not work from `file://`.
- Load **`site-layout.js` before `main.js`** so nav/burger init runs after injection.

## Migration script

Re-apply layout to HTML files (safe to re-run; skips already-migrated pages):

```bash
node scripts/migrate-layout-components.mjs
```

`admin.html` and `index.html` are excluded — admin uses its own UI; index uses `home-main` partial.
