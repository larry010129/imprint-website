# Imprint Diamond — Website Layout & Functions

Planning reference for the full site: routes, UI shell, user flows, APIs, and data model.  
Generated from the current FastAPI + Jinja + React-islands codebase (`config/routes.py`, controllers, schema).

---

## 1. Stack at a glance

| Layer | Technology | Role |
|-------|------------|------|
| Server | **FastAPI** (`main.py` → `app/create_app`) | HTML pages + JSON APIs |
| Pages | **Jinja2** (`app/views/`) | Server-rendered HTML, SEO metadata |
| Page registry | **`config/routes.py`** | Single source of truth for URLs → templates |
| Database | **Postgres** (Supabase) | Users, catalog, cart, orders, leads |
| Global chrome | **React islands** (`frontend/` → `public/react/`) | Nav, footer, price table, stories, FAQ, checkout |
| Shop | **Vanilla JS** (`public/js/shop.js`) | 3-step jewelry calculator wizard |
| Member area | **Client MVC** (`public/js/mvc/`) | Cart, login, account, history, etc. |
| Admin | **Static SPA shell** (`admin.html` + `public/js/admin*.js`) | Staff dashboard, orders, products |
| Static assets | **`public/`** mounted at `/static/` and `/css/` | CSS, images, built JS |

**Local dev:** `npm run dev` → uvicorn `:8080`  
**Frontend build:** `npm run build:frontend` → Vite bundles into `public/react/`

---

## 2. Global page shell

Every marketing / member page (except admin) extends `app/views/layouts/base.html`:

```
┌─────────────────────────────────────────────┐
│  topbar.html          (utility links)       │
├─────────────────────────────────────────────┤
│  nav.html + React SiteNav  (main menu)      │
├─────────────────────────────────────────────┤
│  <main>                                     │
│    {% block content %}  ← page body         │
│  </main>                                    │
├─────────────────────────────────────────────┤
│  footer.html + React SiteFooter             │
├─────────────────────────────────────────────┤
│  nav-dropdown.js, site-layout.js, main.js   │
│  + page-specific scripts (MVC / shop / React)│
└─────────────────────────────────────────────┘
```

**Shared head:** canonical URL, OG/Twitter tags, base CSS (`base`, `nav`, `home`, `pages`, `responsive`), React nav/footer CSS.

**Auth layout:** `layouts/base-auth.html` — stripped shell for login/register/reset-password.

**Body hook:** `data-mvc="{page-id}"` on member pages activates the matching client MVC controller on load.

---

## 3. Primary navigation (React `NAV_ITEMS`)

| Menu | Href | Notes |
|------|------|-------|
| 珠寶試算 | `/shop/calculator/` | Main commerce entry |
| ↳ 戒台試算 | `/shop/calculator/` | Same wizard |
| ↳ DNA 鑽石價格 | `/price.html` | React price table |
| ↳ 台銀金價 | `/gold-price.html` | Live BOT gold quote |
| DNA 鑽石 | `/diamonds.html` | Product/education hub |
| 時尚珠寶 | `/jewelry/` | Category hub |
| ↳ 戒指 / 項鍊 / 耳環 / 手鍊 | `/jewelry/{category}/` | Category landing pages |
| 鑽石知識 | `/what-is-dna-diamond.html` | |
| ↳ DNA 鑽石的誕生 | `/what-is-dna-diamond.html` | |
| ↳ 常見問題 | `/faq.html` | React FAQ |
| 關於我們 | `/about.html` | |
| ↳ 品牌故事 | `/about.html` | |
| ↳ 客戶見證 | `/stories.html` | React stories |
| 查詢訂製進度 | `/track-order.html` | Guest + member order lookup |

Member-only links (cart, account, notifications) appear in nav when session exists — driven by React nav + `/api/auth/session`.

---

## 4. Complete site map

### 4.1 Marketing & content

| URL | Template | Rendering | Purpose |
|-----|----------|-----------|---------|
| `/` | `pages/index.html` | Jinja + home CSS | Homepage, hero, FAQ schema, JewelryStore JSON-LD |
| `/about.html` | `pages/about.html` | Jinja | Brand story |
| `/stories.html` | `pages/stories.html` | Jinja + **React stories** | Customer testimonials |
| `/what-is-dna-diamond.html` | `pages/what-is-dna-diamond.html` | Jinja | DNA diamond education |
| `/diamonds.html` | `pages/diamonds.html` | Jinja | DNA diamond product overview |
| `/faq.html` | `pages/faq.html` | Jinja + **React FAQ** | FAQ accordion |
| `/contact.html` | `pages/contact.html` | Jinja + **MVC contact** | Contact form → `/api/contact` |
| `/404.html` | `pages/404.html` | Jinja + MVC | Error page |

### 4.2 Pricing & reference

| URL | Template | Rendering | Purpose |
|-----|----------|-----------|---------|
| `/price.html` | `pages/price.html` | Jinja + **React price table** | DNA diamond price reference |
| `/gold-price.html` | `pages/gold-price.html` | Jinja + `gold-price.js` | Taiwan Bank gold/platinum/silver rates via `/api/bot-gold` |

### 4.3 Jewelry catalog (SEO landing pages)

Static Jinja pages with HTML **fragments** from `app/views/fragments/`:

| Hub | Categories | Style detail pages (examples) |
|-----|------------|-------------------------------|
| `/jewelry/` | rings, necklaces, earrings, bracelets | 4 categories × multiple styles |
| `/jewelry/rings/` | — | classic-solitaire, modern-band, pave-halo, vintage-vine |
| `/jewelry/necklaces/` | — | bar, classic-pendant, double-layer, halo-pendant |
| `/jewelry/earrings/` | — | stud, hoop, drop, ear-cuff |
| `/jewelry/bracelets/` | — | bangle, chain, charm, tennis |

**Note:** Admin-managed `products` table is the live catalog for the **shop calculator**; jewelry/* pages are marketing/SEO content that can link into the wizard.

### 4.4 Memorial series (emotion-led landing)

| URL | Fragment |
|-----|----------|
| `/series/family/` | `fragments/series/family.html` |
| `/series/first-love/` | `fragments/series/first-love.html` |
| `/series/heirloom/` | `fragments/series/heirloom.html` |
| `/series/love/` | `fragments/series/love.html` |
| `/series/pet/` | `fragments/series/pet.html` |

### 4.5 Shop & checkout (core commerce)

| URL | Template | Rendering | Purpose |
|-----|----------|-----------|---------|
| `/shop/calculator/` | `pages/shop/calculator.html` | Jinja + **`shop.js` wizard** | Configure jewelry (3 steps) |
| `/shop/quote-sheet.html` | `pages/shop/quote-sheet.html` | Jinja + quote render JS | Printable quote sheet |
| `/quote-sheet` | same | alias route | Short URL |
| `/share/summary.html` | `pages/share/summary.html` | Jinja | Shared config summary |
| `/s/{token}` | share summary (dynamic) | Jinja | Tokenized share link |
| `/cart.html` | `pages/cart.html` | Jinja + **MVC cart** | Saved configurations |
| `/checkout.html` | `pages/checkout.html` | Jinja + **React CheckoutPage** | Contact + fulfillment + submit |
| `/success.html` | `pages/success.html` | Jinja + MVC | Post-checkout confirmation |

### 4.6 Member area (login required for most)

| URL | MVC id | Purpose |
|-----|--------|---------|
| `/login.html` | `login` | Email/password login |
| `/register.html` | `register` | Signup (+ invite code optional) |
| `/reset-password.html` | `reset-password` | Password reset flow |
| `/account.html` | `account` | Member dashboard |
| `/profile.html` | `profile` | Edit name, phone, store |
| `/history.html` | `history` | Past orders list |
| `/favorites.html` | `favorites` | Saved favorite configs |
| `/notifications.html` | `notifications` | In-app notifications |
| `/track-order.html` | `track-order` | Lookup by order # + phone |

### 4.7 Admin (staff only)

| URL | File | Purpose |
|-----|------|---------|
| `/admin.html` | root `admin.html` | Standalone admin SPA (no site nav) |

**Panels:** 儀表板 · 訂單管理 · 商品上架 · 帳戶管理 · 邀請碼 · 諮詢名單 · 價格設定 · 內容管理

### 4.8 System / SEO files

| URL | Handler |
|-----|---------|
| `/robots.txt` | static file |
| `/sitemap.xml` | static file |
| `/favicon.svg` | static file |

---

## 5. Shop calculator wizard (`/shop/calculator/`)

Implemented in `public/js/shop.js`. Three views map to stepper UI:

| Step | View key | UI label | User action |
|------|----------|----------|-------------|
| 1 | `catalog` | 選擇類別 | Pick category (ring, necklace, earring, bracelet) |
| 2 | `styles` | 選擇款式 | Pick style/type within category |
| 3 | `product` | 配置下單 | Configure metal, carat, diamond, engraving, qty; live price |

**Pricing source:** tries `/api/prices` + `/api/quote`; falls back to bundled `shop-pricing-local.js` if API unavailable (see ponytail comment in `shop.js`).

**Catalog source:** `/api/catalog` (DB products + variants + images).

**Actions from step 3:**
- Add to cart → `POST /api/cart`
- Add to favorites → `POST /api/favorites` *(client calls this; server route may be missing — see §8 gaps)*
- Generate quote sheet → `/quote-sheet?…` (client-side render)
- Share link → encodes config to `/s/{token}`

**Cart edit flow (from checkout):**
- URL: `/shop/calculator/?cart_edit={id}&returnTo=checkout&items=…`
- Loads item via `GET /api/cart-item?id=…`
- Restores state at **step 3** (`product` view)
- Save → `PUT /api/cart-item` → redirect back to checkout if `returnTo=checkout`

---

## 6. Primary user journeys

### 6.1 Browse → configure → order

```mermaid
flowchart LR
  A[Marketing page] --> B[/shop/calculator/]
  B --> C[Step 1–3 wizard]
  C --> D{Logged in?}
  D -->|No| E[/login.html]
  E --> C
  D -->|Yes| F[POST /api/cart]
  F --> G[/cart.html]
  G --> H[/checkout.html]
  H --> I[POST /api/cart-checkout]
  I --> J[/success.html]
  J --> K[Staff confirms offline]
```

**Checkout behavior:**
- React `CheckoutPage` loads selected cart items via `GET /api/cart-item` (per id from `?items=` query)
- Shows **訂製明細** (spec grid + price breakdown + 編輯規格 button)
- Warning alert: submit ≠ finalized order; consultant contact required
- Collects: name, phone, email, pickup vs delivery, address, note
- Submit creates **one order per cart line**, clears those cart rows, returns `orderNumbers[]`

### 6.2 Guest order tracking

`/track-order.html` → `POST /api/track-order` (order number + phone) → status timeline from `order-display.js` status flow.

### 6.3 Member order history

`/history.html` → `GET /api/orders` (session) → list with status badges.

**Editable orders:** while `status === 'received'`, member can `PUT /api/order` to change config.

### 6.4 Lead capture (non-checkout)

- Contact form → `POST /api/contact` → `contact_messages`
- Quote request (price page / diamonds) → `POST /api/quote-request` → `quote_requests`
- Admin → 諮詢名單 panel

### 6.5 Admin fulfillment

Staff updates order status via `POST /api/order-update` / bulk endpoints. Customer sees updates on track-order / history.

---

## 7. Order lifecycle

**Statuses** (from `public/js/order-display.js`):

| Code | Typical meaning |
|------|-----------------|
| `received` | Application received; customer can still edit |
| `dna_lab` | Sample / DNA processing |
| `deposit_confirmed` | Deposit paid |
| `in_production` | Manufacturing |
| `quality_check` | QC |
| `shipped` | Shipped or ready for pickup |
| `completed` | Delivered / picked up |
| `cancelled` | Cancelled |

**DB normalization** (one order header, related rows):

```
orders
├── order_contacts      (customer_name, phone, email)
├── order_fulfillment   (pickup|delivery, address, note)
└── order_items[]       (config_json, pricing_json snapshot per line)
```

---

## 8. API surface

All JSON routes mount under `/api` except auth which is `/api/auth/*`.

### 8.1 Auth — `auth_controller.py`

| Method | Path | Function |
|--------|------|----------|
| POST | `/api/auth/signup` | Register (+ optional invite code) |
| POST | `/api/auth/login` | Session cookie |
| POST | `/api/auth/logout` | Clear session |
| GET | `/api/auth/session` | Current user + profile flags |

### 8.2 General — `api_controller.py`

| Method | Path | Function |
|--------|------|----------|
| POST | `/api/contact` | Contact form → `contact_messages` |
| POST | `/api/quote-request` | Lead quote form → `quote_requests` |
| GET | `/api/bot-gold` | Cached Taiwan Bank gold quote |
| POST | `/api/track-order` | Guest order lookup |
| GET | `/api/orders` | Member order list |
| GET | `/api/catalog` | Shop product catalog |

### 8.3 Shop / cart — `shop_controller.py`

| Method | Path | Function |
|--------|------|----------|
| GET | `/api/cart` | List cart items (+ `image_url`) |
| POST | `/api/cart` | Add configured item |
| GET/PUT/DELETE | `/api/cart-item` | Read / update / delete one item (+ breakdown on GET) |
| POST | `/api/cart-checkout` | Create order(s), clear cart lines |
| GET | `/api/order` | Fetch single editable order |
| PUT | `/api/order` | Update order while `received` |

### 8.4 Notifications — `notifications_controller.py`

| Method | Path | Function |
|--------|------|----------|
| GET | `/api/notifications/recent` | Unread/recent notifications |
| POST | `/api/notifications/mark-read` | Mark read |
| POST | `/api/notifications/delete` | Delete notification |

### 8.5 Admin — `admin_controller.py` (staff session required)

| Area | Key endpoints |
|------|----------------|
| Dashboard | `GET /api/dashboard`, `GET /api/dashboard/export` |
| Leads | `GET/POST /api/leads` |
| Orders | `GET/POST /api/orders`, `POST /api/order-update`, `POST /api/order-cancel`, `POST /api/order-delete`, `POST /api/orders-bulk-update` |
| Products | `GET/POST /api/products`, `POST /api/product-upload`, `POST /api/product-update`, `POST /api/product-action`, `POST /api/products-reorder` |
| Invites | `GET/POST /api/invites`, `POST /api/invite-action` |
| Accounts | `GET /api/accounts`, `POST /api/account-action` |

### 8.6 Client-expected but not yet in FastAPI (gaps)

These are referenced in `public/js/api-client.js` / `shop.js` but **no matching Python routes** were found:

| Path | Used by | Fallback today |
|------|---------|----------------|
| `/api/prices` | Shop wizard weight constants | `shop-pricing-local.js` |
| `/api/quote` | Server-side quote validation | Client-side pricing math |
| `/api/favorites` (+ DELETE by id) | Favorites page, shop heart button | Likely broken until implemented |
| `/api/pricing` | Admin price overrides panel | Admin UI may error |

**Planning note:** Port from legacy `backend/lib/pricing.js` is partially done in `app/pricing.py`; wire remaining routes when consolidating pricing authority.

---

## 9. Database entities (summary)

| Table | Purpose |
|-------|---------|
| `users`, `profiles`, `staff_admins` | Auth & roles |
| `invite_codes` | Registration invites (admin/partner flags) |
| `password_reset_tokens`, `login_lockouts` | Security |
| `products`, `product_variants`, `product_images` | Admin catalog |
| `cart_items` | Saved shop configs per user |
| `favorite_items` | Saved favorites per user |
| `orders`, `order_contacts`, `order_fulfillment`, `order_items` | Orders |
| `user_notifications` | Member notifications |
| `contact_messages`, `quote_requests` | Leads |
| `pricing_settings`, `gold_price_cache` | Pricing overrides & live metal rates |
| `audit_log` | Admin action trail |

Full DDL: `backend/schema.sql`

---

## 10. Frontend architecture split

### 10.1 React islands (Vite entry configs)

| Bundle | Entry config | Mount point | Page(s) |
|--------|--------------|-------------|---------|
| `nav.js` | `vite.nav.config.ts` | `#react-nav-root` | All base-layout pages |
| `footer.js` | `vite.footer.config.ts` | `#react-footer-root` | All base-layout pages |
| `price.js` | `vite.price.config.ts` | price page root | `/price.html` |
| `stories.js` | `vite.stories.config.ts` | stories root | `/stories.html` |
| `checkout.js` | `vite.checkout.config.ts` | `[data-checkout-root]` | `/checkout.html` |
| `admin-tables.js` | `vite.admin-tables.config.ts` | admin product tables | `/admin.html` |

Checkout stack: HeroUI Alert/Button, `CheckoutItemDetail`, `checkout-item-display.ts` for spec/breakdown rows.

### 10.2 Client MVC pages

Pattern: `public/js/mvc/{models,views,controllers}/{page}-*.js`  
Bootstrapped via `data-mvc` on `<body>` + `imprintAPI` (`public/js/api-client.js`).

| MVC page id | Scripts loaded by template |
|-------------|----------------------------|
| `cart` | cart-model/view/controller |
| `login`, `register`, `reset-password` | auth controllers |
| `account`, `profile`, `history` | member controllers |
| `favorites`, `notifications` | saved items / alerts |
| `contact`, `track-order`, `success` | forms & lookup |
| `error-404` | 404 handler |

### 10.3 Shop (non-React)

| File | Role |
|------|------|
| `public/js/shop.js` | Wizard UI, cart/favorite actions, cart_edit restore |
| `public/js/shop-catalog-data.js` | Static fallback catalog metadata |
| `public/js/shop-pricing-local.js` | Client pricing engine |
| `public/js/shop-quote-render.js` | Quote sheet / share summary HTML |
| `public/js/shop-assets.js` | Image path helpers (mirrored server-side in `app/image_urls.py`) |
| `app/static/js/shop-catalog-data.js` | Served catalog seed |

### 10.4 Shared utilities

| File | Role |
|------|------|
| `public/js/api-client.js` | `imprintAPI` fetch wrapper |
| `public/js/order-display.js` | Order status labels, timeline, formatting |
| `public/js/main.js` | Site-wide init |
| `public/js/nav-dropdown.js` | Mobile nav |

---

## 11. Images & product photos

**Resolution order** (`app/image_urls.py`):

1. Admin `product_images.file_path` matching config color
2. Static files under `/static/images/shop-product/`
3. Category/style marketing images
4. No SVG placeholders in order/checkout paths (real photos only)

Cart/checkout API attaches `image_url` on each item via `config_image_url()`.

---

## 12. Key files quick index

| Concern | Path |
|---------|------|
| Route registry | `config/routes.py` |
| Page registration | `app/controllers/web_controller.py` |
| Shop API | `app/controllers/shop_controller.py` |
| Pricing logic | `app/pricing.py` |
| Image URLs | `app/image_urls.py` |
| Orders hydration | `app/orders.py` |
| Checkout React | `frontend/src/components/CheckoutPage.tsx` |
| Checkout display helpers | `frontend/src/lib/checkout-item-display.ts` |
| Shop wizard | `public/js/shop.js` |
| Admin shell | `admin.html`, `public/css/admin-*.css` |
| Architecture overview | `docs/ARCHITECTURE.md` |
| DB schema | `backend/schema.sql` |

---

## 13. Adding a new public page

1. Create `app/views/pages/my-page.html` extending `layouts/base.html`
2. Add `PageMeta(...)` to `config/routes.py` → `ALL_PAGES`
3. No change to `web_controller.py` (auto-registers)
4. Optional: set `mvc_page='my-page'` + add MVC scripts if interactive
5. Optional: add React bundle if complex UI island needed

---

## 14. Suggested planning dimensions

Use this doc with these axes when prioritizing work:

1. **Revenue path** — calculator → cart → checkout → admin order confirm  
2. **Trust/education** — homepage, DNA explainer, FAQ, stories, gold/price reference  
3. **SEO** — jewelry/* and series/* landing pages, schema.org on home  
4. **Member retention** — history, notifications, favorites (needs API)  
5. **Ops** — admin orders, products, leads, pricing overrides (needs API)  
6. **API parity** — close gaps in §8.6 so client and server share one pricing/favorites source of truth  

---

*Last synced with codebase structure. For deployment and directory layout, see also `docs/ARCHITECTURE.md`.*
