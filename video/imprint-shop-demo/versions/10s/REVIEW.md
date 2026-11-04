# Review: 10 s shop demo (銘印鑽石)

## What it shows
| Time | Scene | Source |
|------|-------|--------|
| 0–1.55 s | 01 選品項: whole calculator page, camera moves to the tiles, click 戒指 | live screenshot, imprint-diamond.com/shop/calculator/ |
| 1.55–3.0 s | 02 選款式: click 六爪單鑽戒 | live screenshot |
| 3.0–6.15 s | 03 配置: click 18K金 (price appears), click 18K玫瑰金 (ring turns rose), punch in on NT$ 40,147 = 鑽石 24,000 + 金工 16,147, click 訂購 | three live screenshots of the same screen |
| 6.15–7.6 s | 04 查詢訂製進度: the 訂購 fill carries into the order tracker; five stages fill up to 製作中 | rebuilt (see below) |
| 7.6–10 s | End card: mark, 銘印鑽石 / IMPRINT DIAMOND, 把最深的情感，銘印成永恆, 線上試算 · imprint-diamond.com | brand mark from favicon.svg |

## Creative calls
- Traditional Chinese throughout, matching the site. Prices and labels are the live site's values captured 2026-11-01.
- The tracker is rebuilt at 2.5x from the member order view (`history_order_rows.html`, `member-app.css`) with the real stage labels and colours from `app/orders.py`. The order number is the site's own example (`IMP-20260714-0001`, the placeholder on /track-order); no customer data. No dates are shown because none would be real.
- Fonts: Noto Sans TC / Noto Serif TC (the site's pair), as variable woff2 in `assets/fonts/`.
- No music: the brief did not ask for sound, and the film is under 15 s.

## Measured vs looked at
- `check` passes. Looked at the beat sheet, all five seams and the phone sheet.
- Kept warnings: `line_unread` on the step sub-lines (each step has 1.2–2.1 s in a 10 s film; the titles are 2–3 characters and read in time); the end card lines hold about 1.8 s against a 2 s guideline; `first_frame_empty` (frame 0 is the real catalog page, which is the intended thumbnail).

## Weakest shot
- t=6.05–6.3 s · the empty dark step card sits over the full mint flood for about 0.25 s → fade the card out with the flood and back in with 04.
- t=0.0–0.3 s · the full calculator page is small on a phone → start already pushed in on the tiles if this is cut for social.
