# Review: 20 s shop demo (銘印鑽石)

The 10 s version's source is in `versions/10s/`, its render in `renders/imprint-shop-demo-10s.mp4`.

## What it shows
| Time | Scene | Source |
|------|-------|--------|
| 0–2.6 s | Hook: 為最愛的人，訂製一顆真鑽石 over the 滿月 and 寵物 photos; the second photo pushes into the shop | site photography, public/images/hero |
| 2.6–4.9 s | 01 選品項: whole calculator page, camera to the tiles, click 戒指 | live screenshot, imprint-diamond.com/shop/calculator/ |
| 4.9–7.05 s | 02 選款式: click 六爪單鑽戒 | live screenshot |
| 7.05–11.85 s | 03 配置: 18K金 (price appears), 18K玫瑰金 (ring turns rose), punch in on NT$ 40,147 = 鑽石 24,000 + 金工 16,147, click 訂購 | three live screenshots of one screen |
| 11.85–14.3 s | 04 查詢訂製進度: the 訂購 fill carries into the tracker; five stages fill to 製作中 | rebuilt (see below) |
| 14.3–16.9 s | 與天然鑽石成分一致，價格更親民。從培育到鑲嵌，台灣在地完成 over the 全家福 jewelry photo | claims as worded on the lab-grown-diamond and price pages |
| 16.9–20 s | Dark floods over the photo: mark, 銘印鑽石 / IMPRINT DIAMOND, 把最深的情感，銘印成永恆, 線上試算 · imprint-diamond.com | brand mark from favicon.svg |

## Creative calls
- Traditional Chinese, matching the site. Prices and labels are the live site's values captured 2026-11-01.
- The tracker is rebuilt at 2.5x from the member order view (`history_order_rows.html`, `member-app.css`) with the stage labels and colours from `app/orders.py`. The order number is the site's own example from /track-order; no customer data, no dates.
- Sound: a click on each of the five cursor clicks, a whoosh into the shop and through 訂購, and a music bed written for this cut in code (`music/score.py`, the /brag-slim way, numpy only): D major, 100 BPM, pad and bells under the hook, felt-piano arpeggio from the shop's entry at 2.6 s, in-key bells on the price reveal (8.12 s) and 製作中 (13.1 s), a rising melody over the value beat resolving to Dmaj9 on the mark at 17 s, fading out by 20 s. Re-run `python music/score.py` after retiming.
- The renderer pulls the whole mix down when any clip peaks over full scale: clicks above about 1.3 volume push the music down with them.

## Measured vs looked at
- `check` passes. Looked at the beat sheet and every seam.
- Rendered audio measured, not heard (`renders/imprint-shop-demo-20s-music.mp4`): -14.8 LUFS integrated, true peak -1.7 dBTP, no clipping; clicks still register as onsets at 4.72, 6.86, 8.05, 8.96, 11.36 s (the on-screen presses). The score's loudness envelope and spectrogram were checked: quiet hook, opens at 2.6 s, builds to 17 s, fades by 19.7 s.
- Kept warnings: `first_frame_empty` (frame 0 is the newborn photo, a good thumbnail); `line_unread` on 從培育到鑲嵌 (on screen about 1.9 s).

## Weakest shot
- 4.9–6.85 s · the cursor rests on 六爪單鑽戒 for about 0.8 s before clicking → move the click earlier if the pace feels slow.
- The score is synthesised, so it will sound plainer than a produced track; swap `assets/audio/score.wav` for a Suno or catalog track later and keep the same volume.
