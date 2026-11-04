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
