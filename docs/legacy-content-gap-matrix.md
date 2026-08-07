# Legacy content gap matrix (Phase 1)

Crawl date: 2026-08-07. Origin: `https://www.imprint-diamond.com` (also `https://imprint-diamond.com/`).  
Method: public HTTP only. Invent nothing on fetch fail.  
`missing`: unique public fact absent from closest new target (templates / fragments / `app/data/content-seed.json`). Clear paraphrase elsewhere = `no` + note.  
`unfetchable`: crawl failed / empty; no invented fill.

Columns: legacy block/URL | new target file | missing | notes

## Assumptions A1–A4

| ID | Result | Evidence |
|----|--------|----------|
| A1 | **Partial pass** | Home + live `/imprint/*` nav fetch OK. Redirect-map short paths (`/4c`, `/faq`, `/stories`, `/contact`, …) **404**. Real CMS paths used below. |
| A2 | **Pass — new NAP wins** | New `/contact`: 福德南路 43 號 1 樓、02-2977-0268、預約制 + LINE/FB/map/legalName. Legacy footer/article: same address/phone/預約制 + `sales1@imprint-diamond.com` + form slots 上午10am–12pm／下午1:30pm–6:30pm. **Keep new NAP authoritative**; do not overwrite with legacy email. |
| A3 | **Pass — 8 names present** | Legacy home + `/imprint/testimon`: 沈小姐、徐小姐、賴先生、朱小姐、張小姐、吳小姐、陳先生、簡小姐. All in `app/data/content-seed.json` (+ extra names). Quote bodies match; new cleans 賴「獨一無二」(legacy typo「屬獨一無二」). **No duplicate rows by name.** |
| A4 | **Pass — no new routes** | Signature｜專屬訂製 has no sixth shop slug; fold into `/` / `/series` / engagement / calculator. Knowledge already has `/diamond-4c`, `/lab-grown-diamond`, `/diamond-comparison`. Journal = existing `/journal`, not new route. |

## Unfetchable / map-path 404 (R3)

Do **not** invent for these. Content recovered only when alternate URL listed.

| Attempted URL | Status | Real public fetch |
|---------------|--------|-------------------|
| `/`, `/imprint/index` | 200 | home (source of truth for home blocks) |
| `/4c`, `/imprint/4c` | 404 | `/imprint/axbout` → redirects `about2` (鑽石4C) |
| `/lab-grown` | 404 | `/imprint/aybout` → `about3` (什麼是培育鑽石) |
| `/compare` | 404 | `/imprint/azbout` → `about4` (鑽石比較) |
| `/faq` | 404 | `/imprint/faq` |
| `/stories` | 404 | `/imprint/testimon` |
| `/journal` | 404 | `/imprint/news` |
| `/engagement` | 404 | jewelry `/imprint/shop_list?search_cate1_id=3` |
| `/contact` (root) | 404 | `/imprint/contact`, `/imprint/article/contact` |
| `/about` (root) | 404 | `/imprint/about` |
| `/price` (root) | 404 | `/imprint/article/price` |
| `/series` (root) | 404 | shops `/imprint/shop/{8,11,18,19,20}` |

## Gap matrix

| legacy block/URL | new target file | missing | notes |
|------------------|-----------------|---------|-------|
| Home `/` `/imprint/index` — DNA def「萃取毛髮…注入…晶化為專屬個性化鑽石」 | `content/site/templates/pages/what-is-dna-diamond.html` (+ home teaser) | no | DNA `sec-what-body` covers; home points to DNA page |
| Home — USP「全台唯一在地…不送海外…親眼見證」 | `index.html`, `what-is-dna-diamond.html` | no | Present (often softened「據本品牌營運說明」) |
| Home —「我們樂意傾聽您的故事」 | `index.html` | no | Now in hero-lead + poem-text |
| Home —「照片無法滿足思念…獨一無二的DNA專屬寶物」 | `index.html` | no | Folded into poem-text |
| Home —「一段思念，如何成為永恆」+「天然挖採 vs 摯愛」 | `index.html` | no | poem-title + poem-text |
| Home — First Love blurb | `index.html` card + `fragments/series/first-love.html` | no | Sense covered (reworded) |
| Home — Companion「即使離開…」 | `index.html`, `fragments/series/pet.html` | no | Sense covered |
| Home — Love「將彼此的故事…」 | `index.html`, `fragments/series/love.html` | no | Sense covered |
| Home — Family「代代珍藏…傳承」 | `index.html`, `fragments/series/family.html` | no | Sense covered |
| Home — Heirloom poem「回憶如汩汩泉湧…」 | `index.html` | no | On home hero + series card |
| Home — Signature｜專屬訂製「從紀念物…世界上不會有第二顆」 | `index.html` | no | In series-lead on home |
| Home — Signature pointer for overview | `content/site/templates/pages/series.html` and/or `jewelry/engagement.html` | **yes** | Home has Signature; series overview + engagement still lack fold |
| Home — **專業認證** full block (真品檢查／物化光與天然無異／保證卡或 GIA·IGI／絕對真品) | `what-is-dna-diamond.html` (canonical); home may keep short pointer | **yes** | Home has pointer only; DNA has 保證卡+GIA/IGI but **not** full authenticity paragraph (真品檢查／物化光／絕對真品) |
| Home — **無需漂洋過海**「萃取、培育到飾品設計，全程台灣」 | `index.html`, `what-is-dna-diamond.html` | no | On home dna-lead + DNA callout |
| Home — **製作成飾品**「時時刻刻配戴…在地更能瞭解需求」 | `index.html` | no | On home dna-lead; DNA has 鑲嵌成飾 step |
| Home — 8 testimonials carousel | `app/data/content-seed.json`, home wall, `/stories` | no | A3 closed; no name duplicates |
| `/imprint/article/dna-diamond` | `what-is-dna-diamond.html` | no | Public HTML ≈ home shell; no unique article body beyond home DNA blocks |
| `/imprint/about` — manifesto「樂意傾聽」+「碳化後毛髮銘印封存」+「高科技／高工藝長晶」+「4C高品質」 | `about.html` | **yes** | Soft brand story exists; legacy manifesto paragraphs not mirrored |
| `/imprint/about` — series strip (same as home) | series fragments | no | Series facts live on series pages |
| `/imprint/faq` — Q1–24 | `faq.html` + `app/data/content-seed.json` | no | Seed ports process/quality/pricing FAQ (產銷鏈、環保、75%、樣本、時程、雷射、保險等) |
| `/imprint/article/price` — intro「技術複雜…降低成本…60多台…可參觀實驗室…數百種珠寶…紅/藍/白>1ct」 | `partials/price-page-body.html` (via `price.html`) | **yes** | Tables OK; marketing intro facts missing on price surface (60+ lives on DNA, not price intro) |
| `/imprint/article/price` — ct tables / multi / shape adders | `partials/price-page-body.html` | no | Numbers align with legacy examples |
| `/imprint/contact` + `/imprint/article/contact` NAP | `contact.html` | no | A2: keep new NAP; legacy email Open Item only |
| `/imprint/contact` — slots「上午10am–12pm／下午1:30pm–6:30pm」 | `contact.html` | **yes** | Ops fact on legacy form; new form lacks slots — confirm still true before fold |
| `/imprint/testimon` — 8 quotes | `content-seed.json` | no | A3 closed |
| `/imprint/news` — posts (2026-03-18; 2023 pet expo; lab-grown explainer) | journal CMS / `journal.html` | **yes** | Route exists; 3 posts not in `content-seed.json` — confirm DB before inventing |
| `/imprint/member_policy` — return policy | `return-policy.html` | no | Substantive match |
| `/imprint/axbout` 鑽石4C — 0.2g/100分, IF–I3, D–Z + Fancy grades, EX–P cut | `diamond-4c.html` | **yes** | High-level 4C only; grade ladders / Fancy scale / EX–P missing |
| `/imprint/aybout` 培育鑽石 — HPHT+CVD history, aliases, FTC 2018「刪除自然」 | `lab-grown-diamond.html` | **yes** | CVD + physical equivalence present; HPHT + FTC + alias list missing |
| `/imprint/azbout` 比較 — 真鑽兩種、仿鑽(蘇聯鑽/莫桑)、優化鑽石、HPHT改色恆久 | `diamond-comparison.html` | **yes** | Natural/lab/DNA triad present; 仿鑽/優化/改色 missing |
| `/imprint/shop/18` First Love「迎接親愛寶貝…無限關愛」 | `fragments/series/first-love.html` | **yes** | Shop-specific lines absent (theme covered) |
| `/imprint/shop/8` Pet「永遠不離不棄…愛如家人」 | `fragments/series/pet.html` | **yes** | Exact blurb absent (theme covered) |
| `/imprint/shop/11` Love「結髮牽手…交換或融合」 | `fragments/series/love.html` | no | Fragment covers dual-hair / 結髮 |
| `/imprint/shop/19` Family「血緣交融…代代相傳」 | `fragments/series/family.html` | no | Covered |
| `/imprint/shop/20` Heirloom poem | `fragments/series/heirloom.html` | **yes** | Poem on home; **absent from heirloom fragment** |
| Shop pages —「DNA鑽石系列 需先支付50%訂金」 | `return-policy.html` / `terms.html` / series | **yes** | Deposit mentioned; **50%** figure absent |
| `/imprint/shop_list?search_cate1_id=3` jewelry SKUs | `jewelry/` | no | Commerce catalog; not copy-gap for this plan |
| Map short URLs `/4c` etc. (no alternate) | N/A | unfetchable | Recovered via axbout/aybout/azbout/faq/… — see Unfetchable table |

## missing=yes count

**13** rows marked `missing=yes`.

## Unfetchable list

- Redirect-map short paths that 404 with no content of their own: `/4c`, `/imprint/4c`, `/lab-grown`, `/compare`, `/faq`, `/stories`, `/journal`, `/engagement`, `/contact`, `/about`, `/price`, `/series` (root forms).  
- Content for those intents **was** recovered via real `/imprint/*` URLs above — not inventable blanks.  
- `/imprint/article/dna-diamond`: fetch OK but no unique body beyond home clone.

## Priority handoff for architect

1. **P0 DNA** `what-is-dna-diamond.html` — fold full **專業認證** authenticity paragraph (真品檢查／物化光／保證卡·GIA/IGI／真品保證); keep home pointer; full-page reword if gaining facts.  
2. **P0 Series** — `fragments/series/heirloom.html` poem; `first-love.html` + `pet.html` shop blurbs; Signature fold into `series.html` and/or `jewelry/engagement.html` (no new route).  
3. **P1 About** `about.html` — legacy manifesto (樂意傾聽 / 碳化銘印 / 高科技長晶).  
4. **P1 Knowledge** — `diamond-4c.html` grade ladders; `lab-grown-diamond.html` HPHT+FTC; `diamond-comparison.html` 仿鑽/優化/改色.  
5. **P1 Price** — fold 60艙/可參觀/降低成本/數百種 intro onto price body (tables already OK).  
6. **P2 Ops** — contact appointment slots only if still true; **50%** deposit only if still true; **do not** replace new NAP with legacy email.  
7. **P2 Journal** — seed 3 news posts only after DB/CMS confirm (Open Item until then).  
8. **Skip** — FAQ seed (ported); stories by name; return policy; home emotion/USP/無需漂洋過海/製作成飾品/Signature (already on home); jewelry SKU lists; photo gallery.

## Open items

- Concurrent home edits already closed several former home gaps — Phase 2 should not re-fold those.  
- Legacy `sales1@imprint-diamond.com` vs new LINE-first contact — A2 prefer new.  
- Journal posts not in static seed — confirm admin/DB before Phase 3.  
- Redirect map short paths outdated vs live CMS paths — cutover doc follow-up (out of this plan).  
- Ruflo AgentDB MCP unavailable this run; findings from public crawl + repo only.
