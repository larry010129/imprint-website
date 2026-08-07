# Legacy content gap verify (Phase 4)

Date: 2026-08-07  
Sources: [`legacy-content-gap-matrix.md`](legacy-content-gap-matrix.md), [`legacy-content-fold-map.md`](legacy-content-fold-map.md)  
Tester: Phase 4 spot-check + pytest. No invented copy.

## Verdict: **PASS** (with Open Items)

Core `missing=yes` folds (M01–M04, M07–M13 content) present as reworded equivalents. Open Items OK for journal / gated ops. Soft note on price「數百種」phrase.

---

## Matrix closure (M01–M13)

| ID | Fact | Result | Evidence |
|----|------|--------|----------|
| M01 | Signature overview | **pass** | `series.html` hero-lead + intro-body + Signature detail; engagement optional (no Signature — OK) |
| M02 | 專業認證 full block | **pass** | `what-is-dna-diamond.html`: 真品檢查／物化光／保證卡·GIA·IGI／為真品; home keeps pointer |
| M03 | About manifesto | **pass** | `about.html`: 樂意傾聽／碳化後毛髮銘印封存／高科技與高工藝／4C 高品質 |
| M04 | Price intro | **pass*** | `price-page-body.html`: 技術複雜／降低成本／60 多台／可參觀. *「數百種珠寶」phrase not found (see Soft notes) |
| M05 | Contact slots | **pass** | `contact.html`: 上午 10:00–12:00／下午 1:30–6:30 (+ form lead). NAP unchanged (no legacy email) |
| M06 | Journal 3 posts | **open** | Not in seed; matrix Open Item — no invent |
| M07 | 4C ladders | **pass** | `diamond-4c.html`: 0.2g／100分; IF–I3; D–Z + Fancy scale; EX–P |
| M08 | Lab-grown HPHT/FTC | **pass** | `lab-grown-diamond.html`: HPHT+CVD; aliases; FTC 2018 刪除「自然」 |
| M09 | Compare 仿鑽/優化 | **pass** | `diamond-comparison.html`: 蘇聯鑽／莫桑; 優化; HPHT 改色恆久 |
| M10 | First Love shop blurb | **pass** | `fragments/series/first-love.html`: 迎接親愛寶貝／無限關愛 |
| M11 | Pet shop blurb | **pass** | `fragments/series/pet.html`: 永遠不離不棄／愛如家人 |
| M12 | Heirloom poem fragment | **pass** | `fragments/series/heirloom.html`: 汩汩泉湧 |
| M13 | 50% 訂金 | **pass*** | Figure on `series.html` (×2). *Absent from `return-policy.html` / `terms.html` (matrix allowed series) |

\* Soft notes — not fail criteria for this plan.

---

## Grep / spot-check summary

Checked reworded presence of: 專業認證 authenticity, Signature｜專屬訂製, series shop blurbs, knowledge ladders (4C / lab-grown / compare), price intro, contact slots, 50% 訂金.  
Unfetchable short-path 404s: content recovered via real `/imprint/*` URLs per matrix — no invent required.

## pytest

```
python -m pytest tests/test_extensionless_urls.py -q
→ 27 passed, 2 warnings in ~27s (exit 0)
```

Routes still relevant; extensionless public URLs OK.

## Diff scope (CSS / redesign)

- **No** `.css` / `.scss` / `.less` files in `git diff` / untracked for this verify pass.
- Content-gap surfaces are templates / fragments / partials / bodies / seed / docs — text/meta focused.
- Working tree also has unrelated app/JS/auth changes outside this plan; not treated as CSS redesign.
- Some templates use existing class names + rare inline `style=` for spacing; no layout redesign observed in gap targets.

## Soft notes (non-blocking)

1. **M04** — legacy「數百種珠寶」+「紅/藍/白 >1ct」marketing line not literal on price intro; jewelry catalog lives under `/jewelry`. Tables already cover color/ct pricing.
2. **M13** — 50% lives on series overview, not return-policy/terms; acceptable per matrix `series` target.
3. **M01 optional** — `jewelry/engagement.html` has no Signature copy; primary `series.html` fold sufficient.

## Open Items (OK)

| Item | Status |
|------|--------|
| M06 Journal 3 legacy posts | Open until DB/CMS confirm — do not invent |
| Legacy `sales1@…` email | Prefer new NAP (A2) — skip |
| Redirect-map short paths 404 | Cutover doc follow-up — out of plan |
| Unfetchable short URLs | Recovered via alternate CMS paths |

## Handoff → reviewer

Verify doc ready. Blind pass next: no invented facts, UI/CSS unchanged, page coherent on folded files.  
Path: `docs/legacy-content-gap-verify.md`
