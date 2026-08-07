# Legacy imprint-diamond.com → new site URL map

Cutover checklist for hosting/DNS 301s. New host: `https://www.imprintdiamond.com` (extensionless paths).

Legacy origin audited: `https://www.imprint-diamond.com` (homepage also at `/imprint/index`).

## Core

| Legacy path (examples) | New path | Notes |
|------------------------|----------|--------|
| `/`, `/imprint`, `/imprint/`, `/imprint/index` | `/` | Homepage |
| `/imprint/index.html` | `/` | If served as static file |

## DNA / series / commerce

| Legacy intent | New path |
|---------------|----------|
| DNA / 什麼是 DNA 鑽石 | `/what-is-dna-diamond` |
| 價格 / 價目 | `/price` |
| 黃金牌價 | `/gold-price` |
| 線上試算 / 訂製 | `/shop/calculator/` |
| First Love / 滿月／寶寶 | `/series/first-love/` |
| Companion / 寵物 | `/series/pet/` |
| Love / 結髮 | `/series/love/` |
| Family / 全家福 | `/series/family/` |
| Heirloom / 生命／骨灰 | `/series/heirloom/` |
| 五大系列總覽 | `/series` |
| 時尚珠寶總覽 | `/jewelry/` |
| 求婚戒指／結髮飾品入口 | `/jewelry/engagement/` |
| 戒指分類 | `/jewelry/rings/` |

## Knowledge / about

| Legacy intent | New path |
|---------------|----------|
| 鑽石 4C | `/diamond-4c` |
| 什麼是培育鑽石 / lab-grown | `/lab-grown-diamond` |
| 鑽石比較（天然 vs 培育） | `/diamond-comparison` |
| FAQ / 常見問題 | `/faq` |
| 品牌故事 / about | `/about` |
| 客戶見證 / testimonials | `/stories` |
| 品牌日誌 / journal | `/journal` |
| 聯絡我們 | `/contact` |
| 退換貨 | `/return-policy` |

## Suggested 301 rules (hosting)

Implement on the **legacy** host (or edge) when DNS moves:

```
# Exact / prefix examples — adjust to actual legacy CMS paths.
/imprint/index          → https://www.imprintdiamond.com/
/imprint/               → https://www.imprintdiamond.com/
/4c                     → https://www.imprintdiamond.com/diamond-4c
/imprint/4c             → https://www.imprintdiamond.com/diamond-4c
/lab-grown              → https://www.imprintdiamond.com/lab-grown-diamond
/compare                → https://www.imprintdiamond.com/diamond-comparison
/faq                    → https://www.imprintdiamond.com/faq
/stories                → https://www.imprintdiamond.com/stories
/journal                → https://www.imprintdiamond.com/journal
/engagement             → https://www.imprintdiamond.com/jewelry/engagement/
/求婚                   → https://www.imprintdiamond.com/jewelry/engagement/
```

New site already 301s `*.html` → extensionless (see `tests/test_extensionless_urls.py`). Do **not** invent Person authors or stronger uniqueness claims in redirect landing copy.

## Sitemap / llms

After cutover, confirm `sitemap.xml` and `llms.txt` on the new host include:

- `/diamond-4c`
- `/lab-grown-diamond`
- `/diamond-comparison`
- `/jewelry/engagement/`
