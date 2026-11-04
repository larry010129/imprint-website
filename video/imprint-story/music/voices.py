"""Dialogue for 外婆的項鍊, voiced with Microsoft's Taiwan Mandarin (zh-TW) neural voices.

    python music/voices.py [ids...]   # writes assets/voice/<id>.wav and prints each line's length

Needs `pip install edge-tts numpy soundfile` and ffmpeg. edge-tts uses Edge's free read-aloud service, which is not
licensed for commercial ads: for the published film, render the same voices and settings through an
Azure Speech resource instead (they sound the same).

Daughter: zh-TW-HsiaoChenNeural. Mother: zh-TW-HsiaoYuNeural, slower and a little lower.
Each file is trimmed of leading and trailing silence, given 60 ms of air at both ends and normalised
to -3 dB true peak; inner pauses over 0.4 s are shortened to 0.35 s.
"""
import asyncio
import os
import subprocess
import sys
import tempfile

import edge_tts
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets", "voice")

# (voice, rate, pitch)
DAUGHTER = ("zh-TW-HsiaoChenNeural", "+0%", "+0Hz")
MOTHER = ("zh-TW-HsiaoYuNeural", "-4%", "-6Hz")

LINES = [
    ("d1", DAUGHTER, "媽，我好想外婆。"),
    ("m1", MOTHER, "她以前總說，想一直陪著我們。"),
    ("d2", DAUGHTER, "那就用外婆留下的頭髮，做成一顆鑽石吧。"),
    ("m2", MOTHER, "鑽石？很貴吧。"),
    ("d3", DAUGHTER, "妳看，款式、規格都能選，價格馬上算出來。"),
    ("m3", MOTHER, "那現在，做到哪裡了？"),
    ("d4", DAUGHTER, "鑑定完成了，已經在製作中。"),
    ("m4", MOTHER, "外婆，又回到我們身邊了。"),
]

# Trim silence at both ends, pad 60 ms, normalise to -3 dB true peak, 44.1 kHz mono.
FILTER = (
    "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
    "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
    "adelay=60,apad=pad_dur=0.06,loudnorm=I=-18:TP=-3:LRA=11"
)


def cap_pauses(path, longest=0.4, keep=0.35):
    """Shorten inner pauses over `longest` s to `keep` s (HsiaoYu holds a full second after 「鑽石？」)."""
    x, sr = sf.read(path)
    hop = int(sr * 0.01)
    rms = np.array([np.sqrt(np.mean(x[i : i + hop] ** 2)) for i in range(0, len(x) - hop, hop)])
    quiet = 20 * np.log10(rms + 1e-9) < -42
    keepn, cuts, i = int(keep * sr), [], 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j < len(quiet) and quiet[j]:
                j += 1
            if i > 0 and j < len(quiet) and (j - i) * hop > longest * sr:
                cuts.append((i * hop + keepn // 2, j * hop - keepn // 2))
            i = j
        else:
            i += 1
    for a, b in reversed(cuts):
        x = np.concatenate([x[:a], x[b:]])
    sf.write(path, x, sr)


def duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout)


async def main():
    os.makedirs(OUT, exist_ok=True)
    only = set(sys.argv[1:])
    for lid, (voice, rate, pitch), text in LINES:
        if only and lid not in only:
            continue
        with tempfile.TemporaryDirectory() as tmp:
            mp3 = os.path.join(tmp, "take.mp3")
            await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(mp3)
            wav = os.path.join(OUT, f"{lid}.wav")
            subprocess.run(
                ["ffmpeg", "-v", "error", "-y", "-i", mp3, "-af", FILTER, "-ar", "44100", "-ac", "1", wav],
                check=True,
            )
            cap_pauses(wav)
        print(f"{lid}\t{duration(wav):.2f}s\t{voice}\t{text}")


if __name__ == "__main__":
    asyncio.run(main())
