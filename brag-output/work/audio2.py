"""Version 2 soundtrack: 128 BPM, A major / F# minor. Supersaw stabs, sub bass, punchy drums, risers.
Built entirely with numpy so it needs nothing but the machine's own Python."""
import numpy as np, wave
SR = 44100
DUR = 21.5
N = int(SR * DUR)
rng = np.random.default_rng(11)
BEAT = 60 / 128
DROP = 3.0
def tb(k): return DROP + k * BEAT

def hz(m): return 440.0 * 2 ** ((m - 69) / 12)
def lp_fast(x, fc, order=4):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / (1 + (f / fc) ** order), len(x))

L = np.zeros(N); R = np.zeros(N)           # music bus (ducked)
WL = np.zeros(N); WR = np.zeros(N)         # reverb send (ducked)
DL = np.zeros(N); DR = np.zeros(N)         # drums / fx bus (not ducked)

def put(buf_l, buf_r, sig, t0, pan, send_l=None, send=0.0):
    i = int(t0 * SR)
    if i >= N or i < 0: return
    s = sig[: N - i]
    gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf_l[i:i + len(s)] += s * gl; buf_r[i:i + len(s)] += s * gr
    if send:
        WL[i:i + len(s)] += s * gl * send; WR[i:i + len(s)] += s * gr * send

def mus(sig, t0, pan=0.0, send=0.3): put(L, R, sig, t0, pan, send=send)
def drm(sig, t0, pan=0.0, send=0.05): put(DL, DR, sig, t0, pan, send=send)

# ---------- instruments ----------
def saw(f, n, dets=(-0.18, -0.07, 0, 0.07, 0.18), hmax=14):
    t = np.arange(n) / SR; out = np.zeros(n)
    for d in dets:
        ff = f * 2 ** (d / 12); ph = rng.uniform(0, 6.28)
        H = max(1, min(hmax, int(9000 / ff)))
        for h in range(1, H + 1): out += np.sin(2 * np.pi * ff * h * t + ph * h) / h
    return out / len(dets)

def stab(midis, dur=0.28, vel=1.0):
    n = int(SR * (dur + 0.25)); t = np.arange(n) / SR
    s = sum(saw(hz(m), n) for m in midis) / len(midis)
    env = np.minimum(1, t / 0.004) * np.where(t < dur, 1, np.exp(-(t - dur) / 0.06)) * np.exp(-t * 3.5)
    s = lp_fast(s * env, 2600 + 2500 * vel, 2)
    return s * 0.55 * vel

def pad(midis, dur):
    n = int(SR * (dur + 1.0)); t = np.arange(n) / SR; out = np.zeros(n)
    for m in midis:
        for det in (-0.09, 0.09):
            out += np.sin(2 * np.pi * hz(m) * 2 ** (det / 12) * t + rng.uniform(0, 6.28)) + 0.3 * np.sin(4 * np.pi * hz(m) * t)
    e = np.minimum(1, t / 0.5) * np.where(t < dur, 1, np.exp(-(t - dur) / 0.3))
    return out * e / (2 * len(midis)) * 0.5

def pluck(m, vel=1.0, tau=0.14):
    n = int(SR * 0.45); t = np.arange(n) / SR
    s = saw(hz(m), n, dets=(-0.05, 0.05), hmax=10)
    cut = 1200 + 5500 * np.exp(-t * 14)           # filter-envelope: bright attack, mellow body
    out = np.zeros(n); chunk = 512
    # cheap time-varying low-pass: blend between dark and bright versions
    dark = lp_fast(s, 1100, 2); bright = s
    k = np.exp(-t * 14)
    out = dark * (1 - k) + bright * k
    return out * np.minimum(1, t / 0.002) * np.exp(-t / tau) * vel * 0.34

def bass(m, dur=0.2, vel=1.0):
    n = int(SR * (dur + 0.1)); t = np.arange(n) / SR; f = hz(m)
    s = np.sin(2 * np.pi * f * t) + 0.45 * np.sin(4 * np.pi * f * t) * np.exp(-t * 8) + 0.2 * np.sin(6 * np.pi * f * t) * np.exp(-t * 12)
    e = np.minimum(1, t / 0.004) * np.where(t < dur, 1, np.exp(-(t - dur) / 0.04))
    return s * e * vel * 0.75

def bell(m, vel=1.0, tau=0.9):
    n = int(SR * 3.0); t = np.arange(n) / SR; f = hz(m); s = np.zeros(n)
    for r, a, d in ((1, 1.0, 1.0), (2.0, 0.28, 0.7), (3.01, 0.16, 0.5), (4.2, 0.07, 0.35)):
        s += a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / (tau * d))
    return s * np.minimum(1, t / 0.003) * vel * 0.2

def kick():
    n = int(SR * 0.4); t = np.arange(n) / SR
    ph = 2 * np.pi * np.cumsum(44 + 150 * np.exp(-t * 32)) / SR
    return (np.sin(ph) * np.exp(-t * 8) + 0.3 * np.sin(2 * ph) * np.exp(-t * 22)) * np.minimum(1, t / 0.0015)
def noise_hit(n_s, hp, lpf, tau):
    n = int(SR * n_s); t = np.arange(n) / SR; x = rng.normal(size=n)
    x = lp_fast(x, lpf, 2) - lp_fast(x, hp, 2)
    return x * np.exp(-t / tau)
KICK = kick()
HAT = noise_hit(0.08, 6000, 15000, 0.012)
OPEN = noise_hit(0.3, 6000, 15000, 0.07)
SNARE = noise_hit(0.3, 1500, 9000, 0.07) * 1.0 + np.sin(2 * np.pi * 190 * np.arange(int(SR * 0.3)) / SR) * np.exp(-np.arange(int(SR * 0.3)) / SR / 0.05) * 0.6
def clap():
    n = int(SR * 0.3); t = np.arange(n) / SR; x = rng.normal(size=n); x = lp_fast(x, 5500, 2) - lp_fast(x, 1000, 2)
    e = sum(np.exp(-np.clip(t - d, 0, None) * 80) * (t >= d) for d in (0, 0.011, 0.022)) * 0.5 + np.exp(-t * 14) * 0.5
    return x * e
CLAP = clap()

def riser(t0, dur, level):
    n = int(SR * dur); t = np.arange(n) / SR; x = rng.normal(size=n)
    x = lp_fast(x, 12000, 2) - lp_fast(x, 500, 2)
    tone = saw(220, n, (0,), 6) * 0 + np.sin(2 * np.pi * np.cumsum(260 * 2 ** (3.2 * t / dur)) / SR)
    e = (t / dur) ** 2.4
    drm((x * 1.5 + tone * 0.4) * e * level, t0, 0.0, send=0.35)

def impact(t0, level=1.0):
    n = int(SR * 2.4); t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * np.cumsum(36 + 80 * np.exp(-t * 7)) / SR) * np.exp(-t * 2.0)
    cr = rng.normal(size=n); cr = lp_fast(cr, 15000, 2) - lp_fast(cr, 3500, 2); cr *= np.exp(-t * 2.6) * 0.5
    drm((boom + cr) * level * 0.7, t0, 0.0, send=0.5)

def snare_roll(t0, t1, level=0.5):
    t = t0; step = 0.25 * BEAT * 2
    while t < t1 - 0.02:
        k = (t - t0) / (t1 - t0)
        drm(SNARE * level * (0.4 + 0.8 * k), t, 0.0, send=0.15)
        step = BEAT * 0.5 * (1 - 0.7 * k) + BEAT * 0.12
        t += step

# ---------- harmony ----------
# chord per bar, starting at the drop: F#m  D  A  E
CH = {"F#m": dict(root=30, pad=[54, 57, 61, 66], st=[61, 66, 69, 73], arp=[66, 69, 73, 78]),
      "D":   dict(root=26, pad=[50, 54, 57, 62], st=[62, 66, 69, 74], arp=[62, 66, 69, 74]),
      "A":   dict(root=33, pad=[57, 61, 64, 69], st=[61, 64, 69, 73], arp=[69, 73, 76, 81]),
      "E":   dict(root=28, pad=[56, 59, 64, 68], st=[59, 64, 68, 71], arp=[64, 68, 71, 76])}
PROG = ["F#m", "D", "A", "E"]
NB = 10   # bars of groove (3.0 -> 21.75)

def bar_t(b): return tb(4 * b)
GROOVE_END = tb(33)          # final hit lands on beat 33 (~18.47s)

# --- intro 0..3s: pad + soft pluck arp, riser, snare roll into the drop
mus(pad(CH["F#m"]["pad"], 3.0), 0.0, send=0.5)
for q in range(16):
    tt = 0.85 + q * BEAT / 2
    if tt < DROP - 0.1:
        m = CH["F#m"]["arp"][[0, 1, 2, 3, 2, 1][q % 6]]
        mus(pluck(m, 0.6 + 0.04 * q, 0.18), tt, pan=-0.4 + 0.15 * (q % 6), send=0.5)
riser(1.5, 1.5, 0.25)
snare_roll(2.2, DROP, 0.45)
impact(DROP, 1.0)

# --- groove
kick_beats = [k for k in range(0, 34) if not (28 <= k < 29 and False)]
for k in range(0, 33):
    t = tb(k)
    if t >= GROOVE_END: break
    drm(KICK * 1.0, t, 0.0, send=0.03)
    if k % 4 in (1, 3):
        drm(CLAP * 0.55, t, 0.0, send=0.22); drm(SNARE * 0.35, t, 0.0, send=0.1)
    drm(OPEN * 0.16, t + BEAT / 2, 0.2, send=0.08)
    drm(HAT * 0.20, t + BEAT / 4, -0.2, send=0.03); drm(HAT * 0.20, t + 3 * BEAT / 4, 0.25, send=0.03)
    if k >= 8: drm(HAT * 0.12, t, -0.1, send=0.03)

for b in range(0, 9):
    t0 = bar_t(b); name = PROG[b % 4]; c = CH[name]
    if t0 >= GROOVE_END: break
    mus(pad(c["pad"], 4 * BEAT), t0, send=0.5)
    # bass: root on 1, syncopated octave pops
    for pos, off, v in ((0, 0, 1.0), (1.5, 0, 0.8), (2, 0, 0.95), (3, 12, 0.7), (3.5, 0, 0.8)):
        tt = t0 + pos * BEAT
        if tt < GROOVE_END: mus(bass(c["root"] + 12 + off, 0.2, v), tt, 0.0, send=0.02)
    # supersaw stabs on 16ths: x . . x . . x . | . . x . . x . .
    for p in (0, 3, 6, 10, 13):
        tt = t0 + p * BEAT / 4
        if tt < GROOVE_END - 0.1: mus(stab(c["st"], 0.2, 0.95 if p in (0, 6) else 0.75), tt, pan=0.0, send=0.3)
    # 16th pluck arp joins from bar 2
    if b >= 2:
        for q in range(16):
            tt = t0 + q * BEAT / 4
            if tt < GROOVE_END - 0.1 and q % 4 != 0:
                i = [0, 1, 2, 3, 2, 1, 2, 3, 0, 1, 2, 3, 2, 1, 3, 2][q]
                mus(pluck(c["arp"][i] + 12, 0.55 + 0.25 * (q % 2 == 0), 0.12), tt, pan=-0.5 + (q / 15), send=0.35)

# builds + hits (calculator -> collections at 15.19 = beat 26; outro at beat 33)
snare_roll(tb(22), tb(26), 0.45); riser(tb(22), tb(26) - tb(22), 0.22); impact(tb(26), 0.6)
riser(tb(27), tb(33) - tb(27), 0.3); snare_roll(tb(29), tb(33), 0.55)
impact(GROOVE_END, 1.25)
drm(KICK * 1.1, GROOVE_END, 0.0)
# outro: A major chord ring + bell, kick-led tail
mus(pad(CH["A"]["pad"], 3.4), GROOVE_END, send=0.6)
mus(stab(CH["A"]["st"] + [81], 0.9, 1.0), GROOVE_END, send=0.5)
for k in range(33, 38):
    if tb(k) < 20.4: drm(KICK * 0.9, tb(k), 0.0)
for k in (34, 36):
    drm(CLAP * 0.5, tb(k) + 0.0, 0.0, send=0.2)

# ---------- chimes synced to on-screen actions (all diatonic to A major) ----------
def chime(t, m, v=1.0, pan=0.0): mus(bell(m, v), t, pan, send=0.7)
for j, (dt, m) in enumerate(((0.0, 78), (0.08, 81), (0.16, 85), (0.24, 88), (0.32, 90), (0.4, 93))):
    chime(1.5 + dt, m, 0.5 + 0.08 * j, -0.4 + 0.15 * j)
chime(3.5, 85, 0.6, -0.2); chime(3.95, 90, 0.5, 0.2)
for k, (tt, m) in enumerate(((7.85, 81), (10.0, 83), (11.4, 85), (11.8, 88), (12.15, 90), (12.55, 93))):
    chime(tt, m, 0.55, -0.4 + 0.16 * k)
for j, m in enumerate((86, 90, 93, 95, 98)): chime(12.65 + 0.07 * j, m, 0.45 + 0.07 * j, -0.3 + 0.15 * j)
for j, tt in enumerate((13.6, 13.74, 13.88, 14.02, 14.16)): chime(tt, 95 + (j % 2) * 2, 0.22, 0.3)
for k, m in enumerate((78, 81, 83, 85, 88, 90)): chime(15.75 + 0.28 * k, m, 0.5, -0.5 + 0.2 * k)
for k, m in enumerate((74, 78, 81, 85, 90)): chime(19.0 + 0.12 * k, m, 0.55, -0.4 + 0.2 * k)
chime(19.0, 62, 0.9); chime(19.3, 93, 0.5, 0.3)

# ---------- sidechain: duck the music bus on every kick ----------
t = np.arange(N) / SR
duck = np.ones(N)
for k in range(0, 34):
    tk = tb(k)
    if tk >= GROOVE_END + 2.0: break
    i = int(tk * SR); n = int(SR * BEAT)
    seg = 1 - 0.62 * np.exp(-np.arange(min(n, N - i)) / SR / 0.11)
    duck[i:i + len(seg)] = np.minimum(duck[i:i + len(seg)], seg)
L *= duck; R *= duck; WL *= duck; WR *= duck

# ---------- shared reverb ----------
irn = int(SR * 2.2); ti = np.arange(irn) / SR
def ir():
    x = rng.normal(size=irn) * np.exp(-ti / 0.6); x = lp_fast(x, 5500, 2)
    x[: int(0.01 * SR)] *= np.linspace(0, 1, int(0.01 * SR)); return x / np.sqrt((x ** 2).sum())
def conv(x, h):
    n = len(x) + len(h); m = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(h, m), m)[: len(x)]
rl = conv(WL, ir()); rr = conv(WR, ir())

# ---------- mix ----------
mixL = L * 0.9 + DL * 1.0 + rl * 0.7
mixR = R * 0.9 + DR * 1.0 + rr * 0.7
out = np.stack([mixL, mixR], 1)
out = np.stack([lp_fast(out[:, 0], 14000, 2), lp_fast(out[:, 1], 14000, 2)], 1)
# gentle high-pass to keep sub clean
for c in (0, 1): out[:, c] -= lp_fast(out[:, c], 28, 2)
fade = np.minimum(1, t / 0.15) * np.minimum(1, (DUR - t) / 0.9)
out *= fade[:, None]
out = np.tanh(out * 1.6) / np.tanh(1.6)
out = out / np.abs(out).max() * 0.9
pcm = (out * 32767).astype(np.int16)
with wave.open(r"C:/Users/e1253/Documents/imprint-website/brag-output/work/audio2.wav", "wb") as w_:
    w_.setnchannels(2); w_.setsampwidth(2); w_.setframerate(SR); w_.writeframes(pcm.tobytes())
print("peak", np.abs(out).max(), "rms", np.sqrt((out ** 2).mean()))
