"""Music + sfx for the Imprint Diamond brag video: 120 BPM, D major, one shared reverb."""
import numpy as np, wave
SR = 44100
DUR = 21.5
N = int(SR * DUR)
rng = np.random.default_rng(7)

def hz(m): return 440.0 * 2 ** ((m - 69) / 12)
def env_ad(n, a, rel_tau):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / rel_tau)
    return e
def lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    # one-pole low-pass via recursive filter (vectorised with lfilter-free loop in chunks)
    y = np.empty_like(x); s = 0.0
    for i in range(len(x)):
        s = (1 - a) * x[i] + a * s; y[i] = s
    return y
def lp_fast(x, fc):
    # FFT-domain smooth low-pass (zero-phase), plenty good for a mix bus
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / (1 + (f / fc) ** 4), len(x))

L = np.zeros(N); R = np.zeros(N)
WL = np.zeros(N); WR = np.zeros(N)   # reverb send

def add(sig, t0, pan=0.0, dry=1.0, send=0.35):
    i = int(t0 * SR)
    if i >= N: return
    s = sig[: N - i]
    gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    L[i:i + len(s)] += s * gl * dry; R[i:i + len(s)] += s * gr * dry
    WL[i:i + len(s)] += s * gl * send; WR[i:i + len(s)] += s * gr * send

def pad(midis, dur):
    n = int(SR * (dur + 1.2)); t = np.arange(n) / SR
    out = np.zeros(n)
    for m in midis:
        for det in (-0.07, 0.07):
            f = hz(m) * 2 ** (det / 12)
            ph = rng.uniform(0, 6.28)
            out += (np.sin(2 * np.pi * f * t + ph) + 0.35 * np.sin(4 * np.pi * f * t + ph) + 0.12 * np.sin(6 * np.pi * f * t + ph))
    e = np.minimum(1, t / 0.7) * np.where(t < dur, 1, np.exp(-(t - dur) / 0.35))
    return out * e / (len(midis) * 2) * 0.55

def pluck(m, vel=1.0, tau=0.55):
    n = int(SR * 2.5); t = np.arange(n) / SR; f = hz(m)
    s = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) * np.exp(-t * 6) + 0.1 * np.sin(6 * np.pi * f * t) * np.exp(-t * 9)
    return s * env_ad(n, 0.004, tau) * vel * 0.30

def bell(m, vel=1.0, tau=0.9):
    n = int(SR * 3.2); t = np.arange(n) / SR; f = hz(m)
    s = np.zeros(n)
    for r, a, d in ((1, 1.0, 1.0), (2.0, 0.28, 0.7), (3.01, 0.16, 0.5), (4.2, 0.07, 0.35)):
        s += a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / (tau * d))
    return s * np.minimum(1, t / 0.003) * vel * 0.22

# chords per 2s bar: (bass, pad notes, arpeggio notes)
CH = {
    "D": (38, [50, 57, 61, 66], [62, 66, 69, 73]),
    "Bm": (35, [47, 54, 57, 62], [59, 62, 66, 69]),
    "G": (43, [47, 55, 59, 62, 66], [55, 59, 62, 66]),
    "A": (45, [45, 52, 57, 61, 66], [57, 61, 64, 66]),
}
prog_ = ["D", "Bm", "G", "A", "D", "Bm", "G", "A", "D", "G", "D"]
for b, name in enumerate(prog_):
    bass, notes, arp = CH[name]
    t0 = b * 2.0
    dur = 2.0 if b < len(prog_) - 1 else 1.6
    add(pad(notes, dur), t0, 0.0, dry=0.9, send=0.5)
    bs = np.sin(2 * np.pi * hz(bass) * np.arange(int(SR * (dur + 0.4))) / SR)
    be = np.minimum(1, np.arange(len(bs)) / SR / 0.15) * np.where(np.arange(len(bs)) / SR < dur, 1, np.exp(-(np.arange(len(bs)) / SR - dur) / 0.2))
    add(bs * be * 0.34, t0, 0.0, send=0.1)
    # quarter-note arpeggio, gentle velocity shape
    order = [0, 1, 2, 3] if b % 2 == 0 else [0, 2, 1, 3]
    for k in range(4):
        tt = t0 + k * 0.5
        if tt < 0.9 or tt >= 3.0: continue            # let the hook breathe
        vel = [1.0, 0.65, 0.8, 0.6][k]
        add(pluck(arp[order[k]], vel), tt, pan=-0.35 + 0.23 * k, send=0.45)

# sparkle / chime hits, snapped to the 0.25s grid and in D major pentatonic
D6, E6, Fs6, A6, B6, D7 = 86, 88, 90, 93, 95, 98
def chime(t, m, v=1.0, pan=0.0): add(bell(m, v), t, pan, dry=0.8, send=0.7)
# scene 1: strand collapses into a diamond (flash at 1.5s) -- a glassy upward shimmer
for j, (dt, m) in enumerate(((0.0, 78), (0.08, 81), (0.16, 85), (0.24, 88), (0.32, 90), (0.4, 93))):
    chime(1.5 + dt, m, 0.5 + 0.08 * j, pan=-0.4 + 0.15 * j)
chime(1.5, 74, 0.9)
# scene 2 reveal
chime(3.5, 85, 0.7, -0.2); chime(3.95, 90, 0.55, 0.2)
# scene 3: calculator clicks (S3 starts at 5.7s): category, style, carat, 18K, gold, size
for k, (tt, m) in enumerate(((7.85, 81), (10.0, 83), (11.4, 85), (11.8, 88), (12.15, 90), (12.55, 93))):
    chime(tt, m, 0.55, -0.4 + 0.16 * k)
# price lands: glassy ascending shimmer
for j, m in enumerate((86, 90, 93, 95, 98)): chime(12.65 + 0.07 * j, m, 0.45 + 0.07 * j, -0.3 + 0.15 * j)
# engraving keystrokes, very soft
for j, tt in enumerate((13.6, 13.74, 13.88, 14.02, 14.16)): chime(tt, 95 + (j % 2) * 2, 0.22, 0.3)
# scene 4: six tiles ascending pentatonic
for k, m in enumerate((78, 81, 83, 85, 88, 90)): chime(15.75 + 0.28 * k, m, 0.5, -0.5 + 0.2 * k)
# scene 6: resolve
for k, m in enumerate((74, 78, 81, 85, 90)): chime(19.0 + 0.12 * k, m, 0.55, -0.4 + 0.2 * k)
chime(19.0, 62, 0.9); chime(19.3, 93, 0.5, 0.3)

# ---- HYPE layer: 120 BPM four-on-the-floor groove, pulsing bass, 16th lead, risers + impacts ----
BEAT = 0.5
G0, G1 = 3.0, 20.0          # groove on (S2 drop) / off

def _k():
    n = int(SR * 0.42); t = np.arange(n) / SR
    f = 46 + 130 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) * np.exp(-t * 7.5) + 0.25 * np.sin(2 * ph) * np.exp(-t * 20)) * np.minimum(1, t / 0.002)
KICK = _k()

def _hat():
    n = int(SR * 0.09); t = np.arange(n) / SR
    x = rng.normal(size=n); x = x - lp_fast(x, 5500)
    return x * np.exp(-t * 55)
HAT = _hat()

def _clap():
    n = int(SR * 0.3); t = np.arange(n) / SR
    x = rng.normal(size=n); x = lp_fast(x, 5500) - lp_fast(x, 900)
    e = sum(np.exp(-np.clip(t - d, 0, None) * 70) * (t >= d) for d in (0, 0.011, 0.023)) * 0.5 + np.exp(-t * 16) * 0.5
    return x * e
CLAP = _clap()

def bass_note(m, dur=0.22):
    n = int(SR * dur); t = np.arange(n) / SR; f = hz(m)
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)
    return s * np.minimum(1, t / 0.004) * np.exp(-t * 7) * 0.5

def lead_note(m, vel=1.0):
    n = int(SR * 0.4); t = np.arange(n) / SR; f = hz(m)
    s = sum(np.sin(2 * np.pi * f * h * t) / h for h in range(1, 7))
    return s * np.minimum(1, t / 0.002) * np.exp(-t * 11) * vel * 0.13

def riser(t0, dur, level=0.22):
    n = int(SR * dur); t = np.arange(n) / SR
    x = rng.normal(size=n)
    x = lp_fast(x, 9000) - lp_fast(x, 400 + 3500 * (t[-1] > 0))   # airy band
    e = (t / dur) ** 2.2
    tone = np.sin(2 * np.pi * np.cumsum(220 * 2 ** (3 * t / dur)) / SR) * 0.35
    add((x * 1.4 + tone) * e * level, t0, 0.0, dry=0.8, send=0.5)

def impact(t0, level=1.0):
    n = int(SR * 2.2); t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * np.cumsum(38 + 70 * np.exp(-t * 6)) / SR) * np.exp(-t * 2.2)
    cr = rng.normal(size=n); cr = cr - lp_fast(cr, 3500)
    cr = cr * np.exp(-t * 3.2) * 0.35
    add((boom * 0.9 + cr) * level * 0.5, t0, 0.0, dry=1.0, send=0.5)

# sidechain duck for the musical bus (applied before drums are added)
def duck_curve():
    t = np.arange(N) / SR
    ph = (t % BEAT) / BEAT
    d = 1 - 0.5 * np.exp(-ph * 9)
    on = (t >= G0) & (t < G1 + 0.3)
    return np.where(on, d, 1.0)
_duck = duck_curve()
L *= _duck; R *= _duck; WL *= _duck; WR *= _duck

# groove
bar0 = 0
for b, name in enumerate(prog_):
    t0 = b * 2.0
    bass_m = CH[name][0] + 12          # an octave up for audibility on small speakers
    arp = CH[name][2]
    for q in range(8):                 # 8th-note bass pulse, offbeat accent
        tt = t0 + q * 0.25
        if G0 <= tt < G1:
            add(bass_note(bass_m, 0.22) * (1.0 if q % 2 else 0.8), tt, 0.0, dry=1.0, send=0.05)
    for q in range(16):                # 16th lead pattern, up-down
        tt = t0 + q * 0.125
        if G0 + 2.0 <= tt < G1 and not (q % 4 == 3 and b % 2):
            i = [0, 1, 2, 3, 2, 1, 2, 3, 0, 1, 2, 3, 2, 1, 3, 2][q]
            add(lead_note(arp[i] + 12, 0.75 + 0.25 * (q % 4 == 0)), tt, pan=-0.4 + 0.8 * ((q % 8) / 7), dry=0.9, send=0.4)

kick_ts = [G0 + i * BEAT for i in range(int((G1 - G0) / BEAT))]
kick_ts += [18.5 + 0.0]  # extra weight on the outro hit
for tt in kick_ts: add(KICK * 0.95, tt, 0.0, dry=1.0, send=0.04)
for i in range(int((G1 - G0) / BEAT)):
    tt = G0 + i * BEAT
    add(HAT * 0.35, tt + 0.25, 0.25, dry=1.0, send=0.08)                 # offbeat open-ish hat
    if i % 2 == 1: add(CLAP * 0.55, tt, 0.0, dry=1.0, send=0.25)         # backbeat clap
    if i % 4 == 3: add(HAT * 0.18, tt + 0.375, -0.25, dry=1.0, send=0.05)

# build + drop moments
riser(1.6, 1.4, 0.26); impact(3.0, 1.0)                      # S1 -> S2 drop
for j in range(8): add(CLAP * (0.25 + 0.05 * j), 14.2 + j * (0.5 - 0.03 * j), 0.0, dry=1.0, send=0.2)   # snare-roll into collections
riser(14.4, 0.8, 0.2); impact(15.2, 0.55)
riser(17.0, 1.5, 0.3)
for j in range(12): add(CLAP * (0.2 + 0.04 * j), 17.0 + j * (0.125 + 0.0 * j) , 0.0, dry=1.0, send=0.2)
impact(18.5, 1.25)

# soft "air" whoosh under the flash (filtered noise, low level)
n = int(SR * 0.9); t = np.arange(n) / SR
nz = lp_fast(rng.normal(size=n), 2500); nz -= lp_fast(nz, 500)
w = nz * np.sin(np.pi * np.clip(t / 0.9, 0, 1)) ** 2 * 0.10
add(w, 1.05, 0.0, dry=0.6, send=0.5)

# reverb: shared algorithmic-ish IR from shaped noise
irn = int(SR * 2.6); ti = np.arange(irn) / SR
def ir():
    x = rng.normal(size=irn) * np.exp(-ti / 0.75)
    x = lp_fast(x, 4500)
    x[: int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))
    return x / np.sqrt((x ** 2).sum())
def conv(x, h):
    n = len(x) + len(h); m = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(h, m), m)[: len(x)]
rl = conv(WL, ir()); rr = conv(WR, ir())
mixL = L + rl * 0.75; mixR = R + rr * 0.75

# master
out = np.stack([mixL, mixR], 1)
out = np.stack([lp_fast(out[:, 0], 9000), lp_fast(out[:, 1], 9000)], 1)
t = np.arange(N) / SR
fade = np.minimum(1, t / 0.5) * np.minimum(1, (DUR - t) / 0.9)
out *= fade[:, None]
out = np.tanh(out * 1.9) / np.tanh(1.9)
out = out / np.abs(out).max() * 0.84
pcm = (out * 32767).astype(np.int16)
with wave.open(r"C:/Users/e1253/Documents/imprint-website/brag-output/work/audio.wav", "wb") as w_:
    w_.setnchannels(2); w_.setsampwidth(2); w_.setframerate(SR); w_.writeframes(pcm.tobytes())
print("peak", np.abs(out).max(), "rms", np.sqrt((out ** 2).mean()))
