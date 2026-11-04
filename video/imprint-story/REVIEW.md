# Review: 外婆的項鍊 (33 s story film with dialogue, Taiwan voices)

A daughter and her mother, after grandma has passed. Built from the 20 s shop demo (`../imprint-shop-demo`), which is unchanged.

## What it shows
| Time | Scene | Dialogue |
|------|-------|----------|
| 0–5.85 s | Grandma's framed photo and letter, slow push (site 故事 photo) | 女兒「媽，我好想外婆。」 媽媽「她以前總說，想一直陪著我們。」 |
| 5.85–13.1 s | Three generations of hands holding diamonds (site family-memorial photo) | 女兒「那就用外婆留下的頭髮，做成一顆鑽石吧。」 媽媽「鑽石？很貴吧。」 |
| 13.1–20.7 s | The live shop: 戒指 → 六爪單鑽戒 → 18K金 (NT$ 40,147 appears on 「算出來」) → 玫瑰金 → punch in on the price → 訂購 | 女兒「妳看，款式、規格都能選，價格馬上算出來。」 |
| 20.7–27.1 s | Order tracker (rebuilt, site's example order number); stages fill as she answers, 製作中 lands as she says it | 媽媽「那現在，做到哪裡了？」 女兒「鑑定完成了，已經在製作中。」 |
| 27.1–29.78 s | The opening shot again, pulled back: the finished necklace beside her photo | 媽媽「外婆，又回到我們身邊了。」 |
| 29.78–33.03 s | End card: mark, 銘印鑽石, 與天然鑽石成分一致，價格更親民 (answers 「很貴吧」), CTA | — |

## Creative calls
- Voices are BreezyVoice (MediaTek Research, Apache-2.0), a Taiwan Mandarin TTS run locally on the GPU (`music/breezy_voices.py`, BreezyVoice checkout and its Python 3.10 venv in the session scratchpad). Both roles clone the repo's own Taiwanese speaker prompt; the mother is shifted 2 semitones lower after synthesis (a lowered prompt garbled her words). Each line keeps the best of up to 3 seeds by Whisper read-back; all 8 read back as scripted (他/她 are homophones). Pauses over 0.5 s are shortened to 0.45 s.
- Earlier voices, for comparison: Kokoro (mainland accent) in `renders/imprint-story-30s.mp4`, Microsoft zh-TW neural (judged unnatural, not licensed for ads via edge-tts) in `renders/imprint-story-tw.mp4`.
- Re-timed to the BreezyVoice lines: 33 s.
- Subtitles are burned in with a speaker tag (女兒 / 媽媽), since both voices are female and Facebook autoplays muted.
- Score (`music/score.py`): D major, about 73 BPM, sparse until the shop opens, ducks 5 dB under every line, bells on the price and 製作中, resolves to Dmaj9 on the end card.

## Measured vs looked at
- `check` passes (one kept warning: `first_frame_empty`, frame 0 is grandma's photo, the intended thumbnail).
- Stills checked for every scene and every cut after the re-time.
- Audio measured, not heard: -16.4 LUFS integrated, -1.6 dBFS peak; voices at 1.25 volume, music 0.3 (ducked 5 dB under each line).

## Weakest points
- Both roles come from one speaker prompt, so mother and daughter share a timbre (the mother only lower); a 10-15 s clip of an older Taiwanese woman as her prompt would separate them.
- 33 s, over the 30 s asked for, because the lines run longer.
- 20.7–23.4 s: the tracker sits empty while the mother asks (a slow push keeps it moving).
