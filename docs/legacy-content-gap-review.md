# Legacy content gap review (Critique Engine)

Date: 2026-08-07  
Final re-check: after coder legal fix landed  
Sources: [`legacy-content-gap-verify.md`](legacy-content-gap-verify.md), [`legacy-content-gap-matrix.md`](legacy-content-gap-matrix.md), [`legacy-content-fold-map.md`](legacy-content-fold-map.md)

## Verdict: **approve**

Invent blocker cleared. Terms/privacy are draft stubs with `noindex` (template meta + `config/routes.py`). M13 **50%** kept. Matrix folds M01–M05 / M07–M13 coherent. M06 journal Open Item OK. Soft「數百種珠寶」now on price intro.

---

## Re-check — terms / privacy (was blocker)

| File | Result | Evidence |
|------|--------|----------|
| `terms.html` | **pass** | `{% block extra_head %}` noindex; draft callout; inventable legal back to TODO; **50%** at 訂金與尾款 (L33–34) |
| `privacy.html` | **pass** | noindex meta; draft callout; 保存期限／權利／GA invent stripped to TODO; known ops (forms, Google login, session cookie) kept |
| `config/routes.py` | **pass** | `/privacy` + `/terms` → `robots='noindex, nofollow'` |

---

## Checklist

| # | Criterion | Result | Notes |
|---|-----------|--------|-------|
| 1 | No invented facts (M06 OK) | **pass** | Legal invent gone. M06 not seeded — OK. |
| 2 | UI/CSS unchanged | **pass** | Gap surfaces text/meta/seed; Signature uses existing `sov-*` patterns. |
| 3 | Coherent folded pages | **pass** | DNA / about / series / knowledge / fragments. |
| 4 | New NAP preferred | **pass** | Contact NAP/LINE; no legacy email. |
| 5 | No duplicate stories | **pass** | Legacy 8 unique; no name dups. |
| 6 | Matrix closure except M06 | **pass** | M01–M05, M07–M13 closed. |

---

## Soft / follow-ups (non-blocking)

| Item | Status |
|------|--------|
| M04「數百種珠寶」 | **Closed** — in `price-page-body.html` intro |
| M13 50% | On terms + return-policy + series |
| Bodies export mirrors | May lag templates — sync when convenient |
| Unrelated app/JS/auth tree diffs | Split from content-gap ship if committing |
| Terms/privacy publish | Needs counsel before removing `noindex` / TODOs |

---

## Matrix closure summary

| ID | Status |
|----|--------|
| M01–M05, M07–M13 | closed |
| M06 Journal 3 posts | Open Item — do not invent |

---

## Sign-off

Critique Engine blind pass: **approve** for Legacy Content Gap Fill plan scope.  
Path: `docs/legacy-content-gap-review.md`
