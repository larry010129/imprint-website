# Legacy content fold map (architect)

Status: **matrix-merged (refresh)** — source [`docs/legacy-content-gap-matrix.md`](legacy-content-gap-matrix.md)  
`missing=yes` count: **13** (prior 19 obsolete; concurrent home folds closed several rows).

Constraints (locked): fold-first · no new route · keep UI/CSS · no invent · new NAP wins (A2) · no duplicate stories by name (A3) · full-page reword when file gains ≥1 missing fact · **專業認證** canonical on DNA page · **Signature overview** → `series.html` (home already has Signature — do not re-fold home) · architect does **not** edit templates.

Primary edit surface: `content/site/templates/` + `content/site/fragments/` (+ listed partials).  
`content/site/bodies/` = export mirrors — not primary.

---

## Skip — matrix `missing=no` (do not re-fold)

Per second researcher / current matrix. **Do not edit `index.html` for these:**

- Home emotion「我們樂意傾聽…」「照片無法滿足思念…」「一段思念…／天然 vs 摯愛」
- Home Heirloom poem (already on home hero + card)
- Home Signature blurb (already in series-lead)
- Home **無需漂洋過海** / **製作成飾品**
- DNA def / USP / First Love·Companion·Love·Family home blurbs
- FAQ seed · stories by name · return-policy substance (except 50% figure row) · price tables · NAP core · jewelry SKUs

---

## Confirmed rewrite scopes (`missing=yes` only) — M01–M13

| ID | Legacy fact (latest matrix) | Fold target | rewrite_scope | Phase |
|----|----------------------------|-------------|---------------|-------|
| M01 | Signature pointer for **overview** (series/engagement still lack; home already has it) | **Primary** `pages/series.html`; optional `pages/jewelry/engagement.html` if series copy insufficient | `full-page` | P2 |
| M02 | **專業認證** full authenticity paragraph (真品檢查／物化光／保證卡·GIA/IGI／絕對真品) | **Canonical** `pages/what-is-dna-diamond.html`; home may keep existing short pointer — **no home re-fold** | `full-page` DNA | P2 |
| M03 | About manifesto「樂意傾聽」+「碳化後毛髮銘印封存」+「高科技／高工藝長晶」+「4C高品質」 | `pages/about.html` | `full-page` | P3 |
| M04 | Price intro「技術複雜…降低成本…60多台…可參觀…數百種珠寶…」 | `partials/price-page-body.html` (via `price.html`) | `full-page` price surface | P3 |
| M05 | Contact slots「上午10am–12pm／下午1:30pm–6:30pm」 | `pages/contact.html` | `full-page` **only if ops still true**; NAP unchanged | P3 |
| M06 | Journal 3 legacy posts | journal CMS / seed | `seed-only` after DB confirm; else Open Item `none` | P3 gated |
| M07 | 4C grade ladders (0.2g/100分, IF–I3, D–Z+Fancy, EX–P) | `pages/diamond-4c.html` | `full-page` | P3 |
| M08 | Lab-grown HPHT+CVD history, aliases, FTC 2018 | `pages/lab-grown-diamond.html` | `full-page` | P3 |
| M09 | Compare 仿鑽(蘇聯鑽/莫桑)、優化、HPHT改色 | `pages/diamond-comparison.html` | `full-page` | P3 |
| M10 | Shop/18 First Love「迎接親愛寶貝…無限關愛」 | `fragments/series/first-love.html` | `full-page` | P2 |
| M11 | Shop/8 Pet「永遠不離不棄…愛如家人」 | `fragments/series/pet.html` | `full-page` | P2 |
| M12 | Shop/20 Heirloom poem (absent from **fragment**; home already has poem) | `fragments/series/heirloom.html` | `full-page` | P2 |
| M13 | Shop「需先支付**50%**訂金」 | `pages/return-policy.html` and/or `pages/terms.html` | `full-page` on file(s) that gain figure; confirm still true | P3 |

---

## Phase 2 file list (coder) — P0

| File | Matrix rows | Notes |
|------|-------------|-------|
| `content/site/templates/pages/what-is-dna-diamond.html` | **M02** | Full 專業認證 authenticity paragraph; reword whole DNA page |
| `content/site/templates/pages/series.html` | **M01** | Signature｜專屬訂製 overview fold; **no new route**, no sixth card UI |
| `content/site/fragments/series/first-love.html` | **M10** | Shop blurb lines |
| `content/site/fragments/series/pet.html` | **M11** | Shop blurb lines |
| `content/site/fragments/series/heirloom.html` | **M12** | 汩汩泉湧 poem (home already done — fragment only) |
| `content/site/templates/pages/jewelry/engagement.html` | **M01** optional | Only if Signature still thin after `series.html` |

**Phase 2 skip:** `pages/index.html` (home gaps closed) · `love.html` / `family.html` fragments · `cms_copy_slot_specs.py` unless series/DNA CMS defaults must change for M01/M02.

---

## Phase 3 file list (coder) — P1 + ops

| File | Matrix rows | Notes |
|------|-------------|-------|
| `content/site/templates/pages/about.html` | **M03** | Manifesto fold |
| `content/site/templates/pages/diamond-4c.html` | **M07** | Grade ladders |
| `content/site/templates/pages/lab-grown-diamond.html` | **M08** | HPHT + FTC + aliases |
| `content/site/templates/pages/diamond-comparison.html` | **M09** | 仿鑽 / 優化 / 改色 |
| `content/site/templates/pages/price.html` + `partials/price-page-body.html` | **M04** | Marketing intro only; tables OK |
| `content/site/templates/pages/contact.html` | **M05** | Slot labels only; **new NAP wins** |
| `content/site/templates/pages/return-policy.html` and/or `terms.html` | **M13** | 50% deposit figure |
| Journal CMS / seed (path after DB check) | **M06** | Open Item — **no invent** until confirmed |

**Phase 3 skip:** FAQ · stories/testimonials · jewelry SKU catalog · home emotion / 無需漂洋過海 / 製作成飾品 / home Signature.

---

## Coder rules

1. Fold only `missing=yes` rows above; skip closed home rows even if old fold-map said otherwise.  
2. Fact lands on file → reword entire user-facing Chinese on that file.  
3. No CSS/layout redesign; text/partial/seed only.  
4. Meta = Phase 4 if body changed and SEO stale.  
5. Ops (M05, M13): confirm still true before fold.  
6. Stories: zero duplicate names. Contact: no legacy email overwrite.

---

## Blind spots (peer)

- Home Signature closed ≠ overview closed — still do M01 on `series.html`.  
- Heirloom poem on home does **not** close M12 fragment.  
- Contact slots / 50% deposit are ops — wrong fold worse than skip.  
- Journal M06 stays Open Item until DB/CMS confirm.

---

## Hand-off

- Fold map: `docs/legacy-content-fold-map.md`  
- Matrix: `docs/legacy-content-gap-matrix.md` (13× missing=yes)  
- Next: coder Phase 2 → Phase 3  
- No template / plan edits by architect
