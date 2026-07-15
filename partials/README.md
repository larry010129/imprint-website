# Component-based layout (MVC View Structure)

Public pages share chrome from **`partials/`**, baked into HTML by **`npm run build:layout`**.

## Directory layout

```
partials/
  layout/          ← topbar, nav, footer, head-common
  views/
    content/       ← homepage, gold-price, price-reference
    member/        ← cart, auth, profile, contact form, etc.

js/mvc/
  core.js          ← ImprintMVC helpers
  models/          ← API / data
  views/           ← DOM rendering
  controllers/     ← bind model → view
```

Registry: **`scripts/mvc-registry.mjs`** (partials map + page list for `generate-pages`).

## Partials (slot ids)

| Slot id | File |
|---|---|
| `layout-topbar` | `layout/topbar.html` |
| `layout-nav` | `layout/nav.html` |
| `layout-footer` | `layout/footer.html` |
| `layout-head` | `layout/head-common.html` |
| `view-home` | `views/content/home-main.html` |
| `view-price-ref` | `views/content/price-reference.html` |
| `view-gold-price` | `views/content/gold-price.html` |
| `view-cart` … `view-404` | `views/member/*.html` |

## MVC pages

Member/auth pages are generated from the registry:

```bash
npm run generate:pages
npm run build:layout
```

Each generated page sets `data-mvc="cart"` (etc.) on `<body>`; controllers boot via `ImprintMVC.isPage()`.

Shared styles: `css/member-app.css`.

## Page structure

```html
<body data-site-root="" data-site-active="shop" data-mvc="cart" class="site-layout">
  <div data-site-include="layout-topbar"></div>
  <div data-site-include="layout-nav"></div>
  <main>
    <div data-site-include="view-cart"></div>
  </main>
  <div data-site-include="layout-footer"></div>
  <script src="js/site-layout.js?v=1.2"></script>
  <script src="js/main.js?v=2.1"></script>
  <!-- MVC bundle from registry -->
</body>
```

### `data-site-root`

Relative path back to site root (`../` for nested pages).

### `data-site-active`

Highlights nav: `price`, `shop`, `diamonds`, `jewelry`, `knowledge`, `about`, `track-order`, `account`.

## Requirements

- Serve over HTTP — `fetch` does not work from `file://`.
- Load **`site-layout.js` before `main.js`**.
