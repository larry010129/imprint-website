"""Music bed for the 20 s shop demo, built with numpy only (the /brag-slim way).

D major, 100 BPM, bars of 2.4 s from the shop's entry at 2.6 s.
0-2.6 hook: pad + bell motif, G(add9) -> Asus4 -> A, resolving to D as the shop opens.
2.6-14.6 the shop: felt-piano arpeggio, soft bass, pad; a light shaker from 7.4 s.
14.6-17.0 value beat: rising melody F#5 A5 B5 C#6, string swell into the end card.
17.0-20 end card: Dmaj9, bell arpeggio on the mark, fade out by 20 s.
Bells on the price reveal (8.12 s) and the current tracker stage (13.1 s), in key.
"""

import wave
from pathlib import Path

import numpy as np

SR = 44100
DUR = 20.0
N = int(SR * DUR)
rng = np.random.default_rng(7)
BAR = 2.4
EIGHTH = BAR / 8
SHOP = 2.6
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


# ---------- harmony: (start, bass, pad, arpeggio) ----------
CH = {
    "Gadd9": (43, [55, 59, 62, 69], [55, 62, 67, 69]),
    "Asus4": (45, [57, 62, 64, 69], [57, 64, 69, 74]),
    "A": (45, [57, 61, 64, 69], [57, 64, 69, 73]),
    "Dmaj7": (38, [50, 54, 57, 61], [62, 69, 73, 78]),
    "Bm7": (35, [54, 57, 59, 62], [59, 66, 69, 74]),
    "Gmaj7": (43, [55, 59, 62, 66], [55, 62, 66, 71]),
    "D/F#": (42, [54, 57, 61, 62], [54, 61, 66, 69]),
    "Dmaj9": (38, [50, 54, 57, 61, 64], [62, 69, 73, 76]),
}
TIMELINE = [
    (0.0, "Gadd9"),
    (1.4, "Asus4"),
    (2.0, "A"),
    (SHOP, "Dmaj7"),
    (SHOP + BAR, "Bm7"),
    (SHOP + 2 * BAR, "Gmaj7"),
    (SHOP + 3 * BAR, "Asus4"),
    (SHOP + 3.5 * BAR, "A"),
    (SHOP + 4 * BAR, "D/F#"),
    (SHOP + 5 * BAR, "Gmaj7"),
    (SHOP + 5.5 * BAR, "Asus4"),
    (SHOP + 5.75 * BAR, "A"),
    (SHOP + 6 * BAR, "Dmaj9"),
]
END_CHORD = SHOP + 6 * BAR  # 17.0 s, the end card's mark


def chord_at(t):
    name = TIMELINE[0][1]
    for t0, c in TIMELINE:
        if t >= t0:
            name = c
    return name


# Pads, one per chord span; louder from the value beat on.
for k, (t0, name) in enumerate(TIMELINE):
    t1 = TIMELINE[k + 1][0] if k + 1 < len(TIMELINE) else DUR
    level = 0.55 if t0 < SHOP else (0.7 if t0 < 14.6 else 1.0)
    put(pad(CH[name][1], t1 - t0 + 0.15, attack=0.5 if t0 else 1.0), t0, send=0.5, gain=level)
    if t0 >= SHOP:
        put(bass(CH[name][0], t1 - t0), t0, send=0.05, gain=0.9)

# Hook: bell motif over the pad (D A F# E, in the key the shop resolves to).
for dt, m, p in ((0.25, 74, -0.3), (0.7, 81, 0.2), (1.15, 78, -0.1), (1.75, 76, 0.25)):
    put(bell(m, 0.42), dt, pan=p, send=0.65)

# Piano arpeggio on eighths from the shop's entry until the end chord.
pattern = [0, 1, 2, 3, 2, 1, 2, 3]
t = SHOP
q = 0
while t < END_CHORD - 0.01:
    name = chord_at(t + 1e-3)
    arp = CH[name][2]
    ramp = 0.38 + 0.22 * min(1.0, (t - SHOP) / (14.6 - SHOP))
    accent = 1.12 if q % 4 == 0 else (0.88 if q % 2 else 1.0)
    put(piano(arp[pattern[q % 8]], ramp * accent, EIGHTH * 1.6), t, pan=-0.35 + 0.1 * (q % 8), send=0.35)
    t += EIGHTH
    q += 1

# Light shaker pulse under the configure and tracker beats.
t = SHOP + 2 * BAR
q = 0
while t < END_CHORD - 0.3:
    put(shaker(1.0 if q % 2 else 0.55), t, pan=0.3, send=0.1)
    t += EIGHTH
    q += 1

# In-key bells on two on-screen moments.
put(bell(83, 0.35), 8.14, pan=0.35, send=0.7)  # price appears (over Gmaj7: B5)
put(bell(90, 0.25), 8.24, pan=0.45, send=0.7)  # F#6
put(bell(81, 0.3), 13.12, pan=-0.3, send=0.7)  # 製作中 lands (over D/F#: A5)

# Value beat melody, rising into the resolution.
for t0, m, d in ((14.6, 78, 0.55), (15.2, 81, 0.55), (15.8, 83, 0.55), (16.4, 85, 0.55), (END_CHORD, 86, 2.2)):
    put(piano(m, 0.72, d), t0, pan=0.1, send=0.45)

# Soft swell into the end card.
n = int(SR * 0.8)
tt = np.arange(n) / SR
swell = (lowpass(rng.normal(size=n), 6000) - lowpass(rng.normal(size=n), 900)) * (tt / 0.8) ** 2.5 * 0.05
put(swell, END_CHORD - 0.8, send=0.6)

# End card: rolled Dmaj9 on piano, bell arpeggio on the mark, then a few slowing notes.
for k, m in enumerate((50, 57, 62, 66, 69, 73, 76)):
    put(piano(m, 0.6, 2.4), END_CHORD + 0.035 * k, pan=-0.3 + 0.1 * k, send=0.5)
for k, m in enumerate((86, 90, 93, 97, 100)):
    put(bell(m, 0.32), 17.25 + 0.09 * k, pan=-0.4 + 0.2 * k, send=0.75)
for k, m in enumerate((73, 69, 76, 74)):
    put(piano(m, 0.38 - 0.05 * k, 1.0), 18.2 + 0.42 * k + 0.05 * k * k, pan=0.2, send=0.55)

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
fade = np.minimum(1, t / 0.4) * np.clip((DUR - t) / 1.6, 0, 1) ** 1.5
mix *= fade[:, None]
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
