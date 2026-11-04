"""Dialogue for 外婆的項鍊, voiced with BreezyVoice (MediaTek Research, Apache-2.0), a Taiwan Mandarin TTS.

    BREEZY_DIR=<BreezyVoice checkout> <its python> music/breezy_voices.py [ids...]

BreezyVoice clones the voice of a speaker prompt; both roles use the repo's own Taiwanese prompt
(data/example.wav). A lowered prompt garbled the words, so the mother is spoken in the same voice and
then shifted 2 semitones lower afterwards (duration kept).
Sampling varies, so each line is generated with up to TAKES seeds; Whisper (medium, zh) transcribes
every take and the one closest to the script is kept. Each kept take is trimmed, given 60 ms of air at
both ends, normalised to -3 dB true peak (44.1 kHz mono) and has inner pauses over 0.5 s shortened to
0.45 s, into assets/voice/<id>.wav.
"""
import os
import subprocess
import sys
import tempfile

BREEZY = os.environ["BREEZY_DIR"]
sys.path.insert(0, BREEZY)
sys.path.insert(0, os.path.join(BREEZY, "third_party", "Matcha-TTS"))
os.chdir(BREEZY)

import librosa  # noqa: E402
import numpy as np  # noqa: E402
import opencc  # noqa: E402
import soundfile as sf  # noqa: E402
import torch  # noqa: E402
import torchaudio  # noqa: E402
import whisper  # noqa: E402
from g2pw import G2PWConverter  # noqa: E402

import single_inference as si  # noqa: E402

torch.set_num_threads(16)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets", "voice")
PROMPT = os.path.join(BREEZY, "data", "example.wav")
PROMPT_TEXT = "在密碼學中，加密是將明文資訊改變為難以讀取的密文內容，使之不可讀的方法。只有擁有解密方法的對象，經由解密過程，才能將密文還原為正常可讀的內容。"

LINES = [
    ("d1", "daughter", "媽，我好想外婆。"),
    ("m1", "mother", "她以前總說，想一直陪著我們。"),
    ("d2", "daughter", "那就用外婆留下的頭髮，做成一顆鑽石吧。"),
    ("m2", "mother", "鑽石？很貴吧。"),
    ("d3", "daughter", "妳看，款式、規格都能選，價格馬上算出來。"),
    ("m3", "mother", "那現在，做到哪裡了？"),
    ("d4", "daughter", "鑑定完成了，已經在製作中。"),
    ("m4", "mother", "外婆，又回到我們身邊了。"),
]
SEEDS = [1234, 7, 42, 2026, 99]
TAKES = 3
MOTHER_SEMITONES = -2

FILTER = (
    "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
    "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
    "adelay=60,apad=pad_dur=0.06,loudnorm=I=-18:TP=-3:LRA=11"
)


def distance(a, b):
    """Edit distance between two strings, punctuation ignored."""
    a = [c for c in a if c.isalnum()]
    b = [c for c in b if c.isalnum()]
    row = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev, row[0] = row[0], i
        for j, cb in enumerate(b, 1):
            prev, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, prev + (ca != cb))
    return row[-1]


def cap_pauses(path, longest=0.5, keep=0.45):
    """Shorten inner pauses over `longest` s to `keep` s (the model sometimes holds a second or more)."""
    x, sr = sf.read(path)
    hop = int(sr * 0.01)
    quiet = [20 * np.log10(np.sqrt(np.mean(x[i : i + hop] ** 2)) + 1e-9) < -42 for i in range(0, len(x) - hop, hop)]
    keepn, cuts, i = int(keep * sr), [], 0
    while i < len(quiet):
        j = i
        while j < len(quiet) and quiet[j]:
            j += 1
        if j > i and i > 0 and j < len(quiet) and (j - i) * hop > longest * sr:
            cuts.append((i * hop + keepn // 2, j * hop - keepn // 2))
        i = j + 1
    for a, b in reversed(cuts):
        x = np.concatenate([x[:a], x[b:]])
    sf.write(path, x, sr)


def lower(path, semitones):
    y, sr = librosa.load(path, sr=None)
    sf.write(path, librosa.effects.pitch_shift(y, sr=sr, n_steps=semitones), sr)


def main():
    only = set(sys.argv[1:])
    os.makedirs(OUT, exist_ok=True)
    cosyvoice = si.CustomCosyVoice("MediaTek-Research/BreezyVoice-300M")
    g2p = G2PWConverter()
    asr = whisper.load_model("medium", device="cuda" if torch.cuda.is_available() else "cpu")
    to_tw = opencc.OpenCC("s2twp")
    with tempfile.TemporaryDirectory() as tmp:
        for lid, who, text in LINES:
            if only and lid not in only:
                continue
            best = None
            for k, seed in enumerate(SEEDS[:TAKES]):
                torch.manual_seed(seed)
                take = os.path.join(tmp, f"{lid}-{k}.wav")
                si.single_inference(PROMPT, text, take, cosyvoice, g2p, PROMPT_TEXT)
                heard = to_tw.convert(asr.transcribe(take, language="zh")["text"])
                score = distance(heard, text)
                print(f"  {lid} seed {seed}: {heard} (off by {score})", flush=True)
                if best is None or score < best[0]:
                    best = (score, take, heard)
                if score == 0:
                    break
            raw = best[1]
            if who == "mother":
                lower(raw, MOTHER_SEMITONES)
            wav = os.path.join(OUT, f"{lid}.wav")
            subprocess.run(
                ["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", FILTER, "-ar", "44100", "-ac", "1", wav],
                check=True,
            )
            cap_pauses(wav)
            info = torchaudio.info(wav)
            print(f"{lid}\t{info.num_frames / info.sample_rate:.2f}s\t{who}\t{text}\theard: {best[2]}", flush=True)


if __name__ == "__main__":
    main()
