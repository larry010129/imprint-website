"""Music bed for 外婆的項鍊 (33.03 s), built with numpy only (the /brag-slim way).

D major, about 69 BPM (bars of 3.5 s from the shop's entry at 13.1 s). Written under two voices, so it stays
sparse while anyone speaks and ducks 5 dB under each line (VO below, same times as index.html).
0-5.85 memory: Bm(add9) -> Gmaj7 pad, a few far-off piano notes.
5.85-13.1 the idea: Em7 -> G -> Asus4 held under 「很貴吧」, resolving to D as the shop opens.
13.1-27.1 shop and tracker: felt-piano arpeggio, soft bass; bells on the price (17.77) and 製作中 (26.45).
27.1-29.78 the necklace revealed: Gmaj7 -> Asus4 -> A, a rising melody between her words.
29.78-33.03 end card: Dmaj9, bell arpeggio on the mark, fade out.
"""

import wave
from pathlib import Path

import numpy as np

SR = 44100
DUR = 33.03
N = int(SR * DUR)
rng = np.random.default_rng(7)
BAR = 3.5
EIGHTH = BAR / 8
SHOP = 13.1
OUT = Path(__file__).resolve().parent.parent / "assets" / "audio" / "score.wav"


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lowpass(x, fc, order=2):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / (1 + (f / fc) ** order), len(x))


L = np.zeros(N)
R = np.zeros(N)
SL = np.zeros(N)  # reverb send
SRv = np.zeros(N)


def put(sig, t0, pan=0.0, send=0.3, gain=1.0):
    i = int(round(t0 * SR))
    if i >= N:
        return
    s = sig[: N - i] * gain
    gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    L[i : i + len(s)] += s * gl
    R[i : i + len(s)] += s * gr
    SL[i : i + len(s)] += s * gl * send
    SRv[i : i + len(s)] += s * gr * send


# ---------- instruments ----------
def piano(m, vel=0.6, dur=0.9):
    """Felt piano: slightly inharmonic partials, two detuned strings, soft hammer."""
    f = hz(m)
    n = int(SR * (dur + 1.6))
    t = np.arange(n) / SR
    base_tau = float(np.clip(1.8 * (440 / f) ** 0.35, 0.5, 3.0))
    s = np.zeros(n)
    bright = 0.6 + 0.6 * vel
    for h in range(1, 11):
        fh = f * h * np.sqrt(1 + 0.0004 * h * h)
        if fh > 9000:
            break
        amp = (1 / h ** (1.6 - 0.5 * bright)) * (1.0 if h == 1 else 0.8)
        tau = base_tau / (1 + 0.45 * (h - 1))
        for det in (-0.0006, 0.0006):
            s += amp * np.sin(2 * np.pi * fh * (1 + det) * t + rng.uniform(0, 6.28)) * np.exp(-t / tau)
    s /= 2
    hammer = lowpass(rng.normal(size=n), 1800) * np.exp(-t / 0.008) * 0.15
    env = np.minimum(1, t / 0.004) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.35))
    return lowpass((s + hammer) * env, 2200 + 3000 * vel) * vel * 0.32


def pad(midis, dur, attack=0.6, release=0.9):
    """String-like pad: detuned saws, darkened."""
    n = int(SR * (dur + release * 3))
    t = np.arange(n) / SR
    out = np.zeros(n)
    for m in midis:
        f = hz(m)
        for det in (-0.08, 0.0, 0.08):
            ff = f * 2 ** (det / 12)
            ph = rng.uniform(0, 6.28)
            for h in range(1, max(2, min(12, int(5000 / ff)))):
                out += np.sin(2 * np.pi * ff * h * t + ph * h) / h
    out /= 3 * len(midis)
    out = lowpass(out, 1300)
    env = np.minimum(1, t / attack) * np.where(t < dur, 1.0, np.exp(-(t - dur) / release))
    vib = 1 + 0.03 * np.sin(2 * np.pi * 4.8 * t)
    return out * env * vib * 0.38


def bass(m, dur):
    n = int(SR * (dur + 0.6))
    t = np.arange(n) / SR
    f = hz(m)
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)
    env = np.minimum(1, t / 0.03) * np.where(t < dur, np.exp(-t * 0.35), np.exp(-dur * 0.35) * np.exp(-(t - dur) / 0.2))
    return s * env * 0.34


def bell(m, vel=0.5):
    n = int(SR * 3.5)
    t = np.arange(n) / SR
    f = hz(m)
    s = np.zeros(n)
    for r, a, d in ((1, 1.0, 1.0), (2.0, 0.3, 0.6), (3.0, 0.12, 0.45), (4.07, 0.05, 0.3)):
        s += a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / (1.2 * d))
    return s * np.minimum(1, t / 0.002) * vel * 0.16


def shaker(vel):
    n = int(SR * 0.12)
    t = np.arange(n) / SR
    x = rng.normal(size=n)
    x = lowpass(x, 11000) - lowpass(x, 5000)
    return x * np.minimum(1, t / 0.01) * np.exp(-t / 0.03) * vel * 0.028


# ---------- harmony: (bass, pad, arpeggio) ----------
CH = {
    "Bmadd9": (35, [47, 54, 61, 62], [59, 61, 66, 74]),
    "Em7": (40, [52, 55, 59, 62], [52, 59, 62, 67]),
    "G": (43, [55, 59, 62, 67], [55, 62, 67, 71]),
    "Asus4": (45, [57, 62, 64, 69], [57, 64, 69, 74]),
    "A": (45, [57, 61, 64, 69], [57, 64, 69, 73]),
    "Dmaj7": (38, [50, 54, 57, 61], [62, 69, 73, 78]),
    "Bm7": (35, [54, 57, 59, 62], [59, 66, 69, 74]),
    "Gmaj7": (43, [55, 59, 62, 66], [55, 62, 66, 71]),
    "D/F#": (42, [54, 57, 61, 62], [54, 61, 66, 69]),
    "Dmaj9": (38, [50, 54, 57, 61, 64], [62, 69, 73, 76]),
}
PAYOFF = 27.1
END_CHORD = 29.78  # the end card
TIMELINE = [
    (0.0, "Bmadd9"),
    (3.0, "Gmaj7"),
    (5.85, "Em7"),
    (8.0, "G"),
    (10.0, "Asus4"),
    (SHOP, "Dmaj7"),
    (SHOP + BAR, "Bm7"),
    (SHOP + 2 * BAR, "Gmaj7"),
    (SHOP + 3 * BAR, "D/F#"),
    (SHOP + 3.5 * BAR, "Em7"),
    (SHOP + 3.75 * BAR, "Asus4"),
    (PAYOFF, "Gmaj7"),
    (28.4, "Asus4"),
    (29.2, "A"),
    (END_CHORD, "Dmaj9"),
]
# Dialogue (start, end) in seconds, matching the <audio> clips in index.html.
VO = [(0.35, 2.61), (2.9, 5.61), (6.0, 10.89), (11.15, 12.92), (13.3, 18.14), (20.85, 23.36), (23.45, 26.77), (27.3, 29.63)]


def chord_at(t):
    name = TIMELINE[0][1]
    for t0, c in TIMELINE:
        if t >= t0:
            name = c
    return name


# Pads, one per chord span; they open up with the shop and again on the reveal.
for k, (t0, name) in enumerate(TIMELINE):
    t1 = TIMELINE[k + 1][0] if k + 1 < len(TIMELINE) else DUR
    level = 0.5 if t0 < SHOP else (0.62 if t0 < PAYOFF else 0.9)
    put(pad(CH[name][1], t1 - t0 + 0.15, attack=1.2 if t0 < SHOP else 0.5), t0, send=0.55, gain=level)
    if t0 >= SHOP:
        put(bass(CH[name][0], t1 - t0), t0, send=0.05, gain=0.8)

# Memory and idea: a few far-off piano notes, never on top of a word's onset.
for t0, m, v in ((0.1, 74, 0.32), (2.75, 73, 0.28), (3.05, 71, 0.3), (5.75, 76, 0.3), (8.05, 74, 0.3), (11.0, 76, 0.34), (13.02, 81, 0.3)):
    put(piano(m, v, 1.4), t0, pan=0.25, send=0.6)
for k, m in enumerate((62, 66, 71)):  # a soft roll as she says 鑽石吧
    put(piano(m, 0.3, 1.6), 10.05 + 0.06 * k, pan=-0.2 + 0.2 * k, send=0.55)

# Piano arpeggio on eighths from the shop's entry until the reveal.
pattern = [0, 1, 2, 3, 2, 1, 2, 3]
t = SHOP
q = 0
while t < PAYOFF - 0.01:
    name = chord_at(t + 1e-3)
    arp = CH[name][2]
    ramp = 0.34 + 0.12 * min(1.0, (t - SHOP) / (PAYOFF - SHOP))
    accent = 1.12 if q % 4 == 0 else (0.88 if q % 2 else 1.0)
    put(piano(arp[pattern[q % 8]], ramp * accent, EIGHTH * 1.6), t, pan=-0.35 + 0.1 * (q % 8), send=0.35)
    t += EIGHTH
    q += 1

# In-key bells on two on-screen moments.
put(bell(83, 0.35), 17.79, pan=0.35, send=0.7)  # price appears (over Bm7: B5)
put(bell(90, 0.25), 17.89, pan=0.45, send=0.7)  # F#6
put(bell(81, 0.3), 26.47, pan=-0.3, send=0.7)  # 製作中 lands (over Asus4: A5)

# The reveal: melody in the gaps of her line, rising into the resolution.
for t0, m, d in ((27.15, 78, 0.9), (28.4, 81, 0.6), (29.2, 83, 0.5), (29.55, 85, 0.3), (END_CHORD, 86, 2.2)):
    put(piano(m, 0.6, d), t0, pan=0.1, send=0.5)

# Soft swell into the end card.
n = int(SR * 0.8)
tt = np.arange(n) / SR
swell = (lowpass(rng.normal(size=n), 6000) - lowpass(rng.normal(size=n), 900)) * (tt / 0.8) ** 2.5 * 0.05
put(swell, END_CHORD - 0.8, send=0.6)

# End card: rolled Dmaj9 on piano, bell arpeggio on the mark, then a few slowing notes.
for k, m in enumerate((50, 57, 62, 66, 69, 73, 76)):
    put(piano(m, 0.6, 2.4), END_CHORD + 0.035 * k, pan=-0.3 + 0.1 * k, send=0.5)
for k, m in enumerate((86, 90, 93, 97, 100)):
    put(bell(m, 0.32), END_CHORD + 0.3 + 0.09 * k, pan=-0.4 + 0.2 * k, send=0.75)
for k, m in enumerate((73, 69, 76, 74)):
    put(piano(m, 0.36 - 0.05 * k, 1.0), END_CHORD + 1.1 + 0.42 * k + 0.05 * k * k, pan=0.2, send=0.55)

# ---------- shared reverb ----------
irn = int(SR * 2.6)
ti = np.arange(irn) / SR


def make_ir():
    h = lowpass(rng.normal(size=irn) * np.exp(-ti / 0.75), 4500)
    h[: int(0.015 * SR)] *= np.linspace(0, 1, int(0.015 * SR))
    return h / np.sqrt((h ** 2).sum())


def conv(x, h):
    n = len(x) + len(h)
    m = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(h, m), m)[: len(x)]


rl = conv(SL, make_ir())  # two decorrelated tails for width
rr = conv(SRv, make_ir())

# ---------- mix ----------
mix = np.stack([L * 0.85 + rl * 0.55, R * 0.85 + rr * 0.55], 1)
for c in (0, 1):
    mix[:, c] = lowpass(mix[:, c], 12000)
    mix[:, c] -= lowpass(mix[:, c], 35)  # keep the sub clean
t = np.arange(N) / SR
fade = np.minimum(1, t / 0.6) * np.clip((DUR - t) / 1.8, 0, 1) ** 1.5
mix *= fade[:, None]
# Duck 5 dB under each spoken line, 0.15 s in and 0.4 s out.
duck = np.ones(N)
for a, b in VO:
    duck[int(max(0, a - 0.15) * SR) : int(b * SR)] = 10 ** (-5 / 20)
k = int(0.15 * SR)
duck = np.convolve(np.pad(duck, (k, k), mode="edge"), np.ones(k) / k, mode="same")[k:-k]
mix *= duck[:, None]
mix = np.tanh(mix * 1.3) / np.tanh(1.3)
mix = mix / np.abs(mix).max() * 0.85  # about -1.4 dBFS peak
pcm = (mix * 32767).astype(np.int16)
OUT.parent.mkdir(parents=True, exist_ok=True)
with wave.open(str(OUT), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("wrote", OUT, "peak", float(np.abs(mix).max()), "rms", float(np.sqrt((mix ** 2).mean())))
