"""Imprint Diamond brag video: every frame is a pure function of time (PIL + numpy), piped to ffmpeg."""
import math, subprocess, sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

W, H, FPS = 1920, 1080, 30
DUR = 21.5
ROOT = r"C:/Users/e1253/Documents/imprint-website/public/images"
OUT = r"C:/Users/e1253/Documents/imprint-website/brag-output"
FONT = "C:/Windows/Fonts/NotoSerifTC-VF.ttf"
SANS = "C:/Windows/Fonts/NotoSansTC-VF.ttf"

CREAM = (251, 247, 242)
INK = (43, 35, 32)
MUTED = (112, 98, 90)
MINT = (142, 237, 240)
MINT_DEEP = (82, 196, 200)
MINT_TEXT = (30, 150, 155)
DARK = (51, 45, 42)
GOLD = (150, 112, 78)

# scene boundaries (seconds)
SC = [0.0, 3.0, 5.7, 15.2, 18.5, 21.5]

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(p): return 1 - (1 - clamp(p)) ** 3
def ease_io(p):
    p = clamp(p); return p * p * (3 - 2 * p)
def prog(t, t0, d): return clamp((t - t0) / d)
def lerp(a, b, k): return a + (b - a) * k
def mix(c1, c2, k): return tuple(int(round(lerp(a, b, k))) for a, b in zip(c1, c2))

_fonts = {}
def font(size, wght=600, sans=False):
    key = (size, wght, sans)
    if key not in _fonts:
        f = ImageFont.truetype(SANS if sans else FONT, size)
        f.set_variation_by_axes([wght])
        _fonts[key] = f
    return _fonts[key]

_tl = {}
def text_layer(txt, size, wght, color, sans=False, track=0):
    key = (txt, size, wght, color, sans, track)
    if key in _tl: return _tl[key]
    f = font(size, wght, sans)
    widths = [f.getlength(c) + track for c in txt] if track else [f.getlength(txt)]
    w = int(sum(widths)) + size
    h = int(size * 1.6)
    im = Image.new("RGBA", (w, h), color + (0,))
    d = ImageDraw.Draw(im)
    if track:
        x = size // 2
        for c, cw in zip(txt, widths):
            d.text((x, size * 0.2), c, font=f, fill=color + (255,)); x += cw
        tw = sum(widths)
    else:
        d.text((size // 2, size * 0.2), txt, font=f, fill=color + (255,)); tw = widths[0]
    _tl[key] = (im, tw)
    return _tl[key]

def put(base, layer, x, y, op=1.0):
    """alpha-paste RGBA layer at (x,y) with opacity"""
    if op <= 0: return
    if op < 1:
        a = layer.getchannel("A").point(lambda v: int(v * op))
        layer = layer.copy(); layer.putalpha(a)
    base.paste(layer, (int(x), int(y)), layer)

def say(base, txt, cx, cy, size, wght, color, op=1.0, dy=0, anchor="c", sans=False, track=0):
    """draw text centered at cx (anchor c) or left at cx (anchor l)"""
    im, tw = text_layer(txt, size, wght, color, sans, track)
    x = cx - tw / 2 - size // 2 if anchor == "c" else cx - size // 2
    y = cy - size * 0.2 - size * 0.62 + dy
    put(base, im, x, y, op)

def reveal(base, t, t0, txt, cx, cy, size, wght, color, anchor="c", sans=False, track=0, d=0.55, rise=26):
    p = ease_out(prog(t, t0, d))
    if p > 0: say(base, txt, cx, cy, size, wght, color, op=p, dy=(1 - p) * rise, anchor=anchor, sans=sans, track=track)

# ---------- backgrounds ----------
yy, xx = np.mgrid[0:H, 0:W]
rr = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H * 0.45) / (H / 2)) ** 2)
_c = np.clip(rr / 1.25, 0, 1)[..., None]
_BGC = (np.array([255, 252, 248]) * (1 - _c) + np.array([243, 236, 228]) * _c).astype(np.uint8)
_c2 = np.clip(rr / 1.3, 0, 1)[..., None]
_BGD = (np.array([70, 61, 56]) * (1 - _c2) + np.array([38, 33, 31]) * _c2).astype(np.uint8)

def bg_cream(): return Image.fromarray(_BGC)
def bg_dark(): return Image.fromarray(_BGD)

# ---------- images ----------
_im = {}
def load(path, bgfill=None):
    if path not in _im:
        im = Image.open(os.path.join(ROOT, path))
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            base = Image.new("RGBA", im.size, (bgfill or (244, 241, 236)) + (255,))
            base.alpha_composite(im); im = base
        _im[path] = im.convert("RGB")
    return _im[path]

def cover(im, w, h, cx=0.5, cy=0.5, zoom=1.0):
    s = max(w / im.width, h / im.height) * zoom
    nw, nh = int(im.width * s) + 1, int(im.height * s) + 1
    r = im.resize((nw, nh), Image.LANCZOS)
    x = int(clamp(cx * nw - w / 2, 0, nw - w)); y = int(clamp(cy * nh - h / 2, 0, nh - h))
    return r.crop((x, y, x + w, y + h))

def rmask(w, h, r):
    m = Image.new("L", (w * 2, h * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * 2 - 1, h * 2 - 1), r * 2, fill=255)
    return m.resize((w, h), Image.LANCZOS)

_sh = {}
def shadow(w, h, r, blur=28, op=70):
    k = (w, h, r)
    if k not in _sh:
        pad = blur * 3
        m = Image.new("L", (w + pad * 2, h + pad * 2), 0)
        ImageDraw.Draw(m).rounded_rectangle((pad, pad, pad + w, pad + h), r, fill=op)
        m = m.filter(ImageFilter.GaussianBlur(blur))
        im = Image.new("RGBA", m.size, (60, 40, 30, 0)); im.putalpha(m)
        _sh[k] = (im, pad)
    return _sh[k]

def card(base, img, x, y, op=1.0, r=26, lift=True):
    w, h = img.size
    if lift:
        s, pad = shadow(w, h, r)
        put(base, s, x - pad, y - pad + 14, op)
    layer = img.convert("RGBA"); layer.putalpha(rmask(w, h, r))
    put(base, layer, x, y, op)

# ---------- diamond ----------
def diamond(S, phase, glow=0.0, op=1.0, light=False):
    """brilliant-cut diamond, S = girdle width in px. returns RGBA with margins"""
    k = 2
    pad = int(S * 0.35)
    cw, ch = int(S + pad * 2), int(S * 0.9 + pad * 2)
    im = Image.new("RGBA", (cw * k, ch * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ox, oy = cw / 2, pad + S * 0.32
    def P(x, y): return ((ox + x * S) * k, (oy + y * S) * k)
    T = [(-.30, -.30), (-.10, -.30), (.10, -.30), (.30, -.30)]
    G = [(-.5, 0), (-.25, 0), (0, 0), (.25, 0), (.5, 0)]
    tip = (0, .52)
    facets = [(G[0], T[0], G[1]), (T[0], T[1], G[1]), (G[1], T[1], G[2]), (T[1], T[2], G[2]),
              (G[2], T[2], G[3]), (T[2], T[3], G[3]), (G[3], T[3], G[4]),
              (G[0], G[1], tip), (G[1], G[2], tip), (G[2], G[3], tip), (G[3], G[4], tip)]
    hi = (255, 255, 255)
    for i, f in enumerate(facets):
        s = 0.5 + 0.5 * math.sin(phase * 2.2 + i * 1.3)
        base = MINT if i % 2 == 0 else (205, 246, 247)
        if i >= 7: base = mix(MINT_DEEP, MINT, 0.35 + 0.15 * (i % 2))
        col = mix(base, hi, 0.25 + 0.55 * s * (0.4 + glow))
        d.polygon([P(*p) for p in f], fill=col + (255,))
    line = (255, 255, 255, 235)
    for f in facets: d.line([P(*p) for p in f] + [P(*f[0])], fill=line, width=2 * k, joint="curve")
    outline = [G[0], T[0], T[3], G[4], tip, G[0]]
    d.line([P(*p) for p in outline], fill=(255, 255, 255, 255), width=3 * k, joint="curve")
    im = im.resize((cw, ch), Image.LANCZOS)
    if op < 1:
        im.putalpha(im.getchannel("A").point(lambda v: int(v * op)))
    return im, (ox, oy)

def star(base, cx, cy, r, op):
    """4-point sparkle"""
    if op <= 0 or r < 1: return
    n = int(r * 2.6)
    im = Image.new("RGBA", (n * 2, n * 2), (255, 255, 255, 0))
    d = ImageDraw.Draw(im)
    c = n
    for ang in (0, 90):
        a = math.radians(ang)
        dx, dy = math.cos(a), math.sin(a)
        px, py = -dy, dx
        w = r * 0.09
        d.polygon([(c + dx * r, c + dy * r), (c + px * w, c + py * w), (c - dx * r, c - dy * r), (c - px * w, c - py * w)], fill=(255, 255, 255, 255))
    glow = Image.new("L", (n * 2, n * 2), 0)
    ImageDraw.Draw(glow).ellipse((c - r * .22, c - r * .22, c + r * .22, c + r * .22), fill=140)
    glow = glow.filter(ImageFilter.GaussianBlur(r * .12))
    im.alpha_composite(Image.merge("RGBA", (Image.new("L", im.size, 255),) * 3 + (glow,)))
    put(base, im, cx - n, cy - n, op)

_gl = None
def glow_layer(R, color, strength):
    global _gl
    if _gl is None:
        g = np.mgrid[-450:450, -450:450]
        _gl = np.clip(1 - np.sqrt(g[0] ** 2 + g[1] ** 2) / 450, 0, 1) ** 2.2
    a = (_gl * 255 * clamp(strength)).astype(np.uint8)
    im = Image.new("RGBA", (900, 900), color + (0,)); im.putalpha(Image.fromarray(a))
    s = int(R * 2)
    return im.resize((s, s), Image.BILINEAR)

def draw_diamond_mark(base, cx, cy, S, t, op=1.0, glow=0.0, phase0=0.0):
    im, (ox, oy) = diamond(S, t * 1.4 + phase0, glow, op)
    put(base, im, cx - ox, cy - oy)

# ---------- scene 1: hook ----------
STRAND_C = (960, 470)
def strand_pts(k, n=120):
    pts = []
    for i in range(n + 1):
        s = i / n
        x = 250 + 1420 * s
        y = 470 + 105 * math.sin(2 * math.pi * 1.15 * s + 0.4 + k * 0.18) * (0.55 + 0.45 * math.sin(math.pi * s)) + (k - 1) * 9 * math.sin(3 * s + k)
        pts.append((x, y))
    return pts

def scene1(t):
    f = bg_cream()
    # hair lock: a ribbon of fine strands that drifts, then is drawn into one point
    draw_p = ease_io(prog(t, 0.05, 1.0))
    coll = ease_io(prog(t, 1.05, 0.45))
    if coll < 1:
        reg = (150, 250, 1770, 760)
        k2 = 2
        L = Image.new("RGBA", ((reg[2] - reg[0]) * k2, (reg[3] - reg[1]) * k2), (0, 0, 0, 0))
        d = ImageDraw.Draw(L)
        NST = 22
        for k in range(NST):
            u = (k - (NST - 1) / 2) / ((NST - 1) / 2)          # -1..1 across the lock
            ph = k * 0.37
            n = 90; m = max(2, int(n * clamp(draw_p * 1.08 - 0.012 * k)))
            pp = []
            for i in range(m + 1):
                sx = i / n
                x = 240 + 1440 * sx
                spread = (30 + 26 * math.sin(2 * math.pi * 0.8 * sx + 0.6)) * (0.35 + 0.65 * math.sin(math.pi * min(1, sx * 1.02)) ** 0.7)
                y = 480 + 95 * math.sin(2 * math.pi * 1.1 * sx + 0.4 + 0.5 * t) + u * spread + 7 * math.sin(9 * sx + ph + 1.6 * t) * abs(u)
                x2 = lerp(x, STRAND_C[0], coll); y2 = lerp(y, STRAND_C[1], coll)
                pp.append(((x2 - reg[0]) * k2, (y2 - reg[1]) * k2))
            tone = (math.sin(k * 1.7) + 1) / 2
            col = mix((92, 64, 46), (186, 144, 98), tone)
            al = int((150 + 90 * tone) * (1 - coll))
            d.line(pp, fill=col + (al,), width=max(1, int((2.2 + 1.2 * (1 - abs(u))) * k2 * (1 - 0.5 * coll))), joint="curve")
        L = L.resize((reg[2] - reg[0], reg[3] - reg[1]), Image.LANCZOS)
        put(f, L, reg[0], reg[1])
        gl = ease_in = coll * (1 - coll) * 4
        if gl > 0.01: put(f, glow_layer(260, (255, 214, 150), gl * 0.8), STRAND_C[0] - 260, STRAND_C[1] - 260)
    # flash + real logo
    fl = math.exp(-((t - 1.5) / 0.22) ** 2)
    if t > 1.2:
        sc = lerp(0.55, 1.0, ease_out(prog(t, 1.35, 0.7)))
        op = ease_out(prog(t, 1.35, 0.25))
        put(f, glow_layer(380 * sc, MINT, 0.55 * op + fl * 0.5), 960 - 380 * sc, 450 - 380 * sc)
        sz = int(300 * sc)
        lg = Image.open(OUT + "/work/logo.png").convert("RGB").resize((sz, sz), Image.LANCZOS)
        LG = lg.convert("RGBA"); LG.putalpha(rmask(sz, sz, int(sz * 0.2)))
        put(f, LG, 960 - sz // 2, 440 - sz // 2, op)
        if fl > 0.02: put(f, glow_layer(520, (255, 255, 255), fl * 0.85), 960 - 520, 450 - 520)
        for (dx, dy, t0, r) in ((-190, -90, 1.6, 54), (200, -50, 1.75, 40), (150, 140, 1.9, 34), (-170, 100, 2.05, 26)):
            q = prog(t, t0, 0.5)
            star(f, 960 + dx * sc, 440 + dy * sc, r * math.sin(math.pi * q), 1.0)
    # headline
    f1, w1 = "一縷髮絲，", None
    fo = font(92, 600)
    wa = fo.getlength("一縷髮絲，"); wb = fo.getlength("一顆鑽石。")
    x0 = 960 - (wa + wb) / 2
    reveal(f, t, 0.35, "一縷髮絲，", x0, 800, 92, 600, INK, anchor="l")
    reveal(f, t, 1.6, "一顆鑽石。", x0 + wa, 800, 92, 600, MINT_TEXT, anchor="l")
    return f

# ---------- scene 2: reveal ----------
def scene2(t):
    im = load("hero/imprint-diamond-family-portrait-jewelry.jpg")
    z = 1.04 + 0.08 * (t / 3.5)
    f = cover(im, W, H, cx=0.74, cy=0.5, zoom=z)
    # cream wash from the left
    wash = np.clip(1 - (np.arange(W) / (W * 0.66)), 0, 1) ** 0.9
    a = (np.tile(wash, (H, 1)) * 238).astype(np.uint8)
    L = Image.new("RGBA", (W, H), CREAM + (0,)); L.putalpha(Image.fromarray(a))
    f = f.convert("RGBA"); f.alpha_composite(L); f = f.convert("RGB")
    reveal(f, t, 0.4, "IMPRINT DIAMOND", 150, 360, 30, 500, MINT_TEXT, anchor="l", sans=True, track=8)
    reveal(f, t, 0.55, "銘印鑽石", 150, 500, 170, 700, INK, anchor="l", d=0.7)
    ln = ease_out(prog(t, 0.8, 0.6))
    ImageDraw.Draw(f).rectangle((156, 596, 156 + 120 * ln, 600), fill=MINT_DEEP)
    reveal(f, t, 0.95, "台灣在地 DNA 紀念鑽石", 150, 690, 54, 500, INK, anchor="l")
    return f

# ---------- scene 3: the calculator in use ----------
CALC = os.path.join(OUT, "work", "calc")
_ci = {}
def cimg(name, bg=(255, 255, 255)):
    if name not in _ci:
        im = Image.open(os.path.join(CALC, name))
        if im.mode == "RGBA":
            b = Image.new("RGBA", im.size, bg + (255,)); b.alpha_composite(im); im = b
        _ci[name] = im.convert("RGB")
    return _ci[name]

UI = (23, 35, 31)
LINE = (224, 217, 207)
PX, PY = 200, 230
RX, RY, RW, RH = 1230, 230, 490, 740
def sans(s, w=500): return font(s, w, True)

def rrect(d, box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)

def fit(im, w, h, pad=0):
    s = min((w - pad * 2) / im.width, (h - pad * 2) / im.height)
    r = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    c = Image.new("RGB", (w, h), (255, 255, 255)); c.paste(r, ((w - r.width) // 2, (h - r.height) // 2))
    return c

def tile(L, x, y, w, h, img, name, hl=0.0, op=1.0):
    card_ = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(card_)
    rrect(d, (0, 0, w - 1, h - 1), 18, fill=(255, 255, 255, 255), outline=mix(LINE, MINT_DEEP, hl) + (255,), width=2 + int(2 * hl))
    ph = fit(img, w - 8, h - 74).convert("RGBA"); ph.putalpha(rmask(w - 8, h - 74, 14))
    card_.alpha_composite(ph, (4, 4))
    d.text((w // 2, h - 38), name, font=sans(28, 600), fill=UI + (255,), anchor="mm")
    if hl > 0:
        glow = Image.new("RGBA", (w, h), MINT + (0,)); glow.putalpha(rmask(w, h, 18).point(lambda v: int(v * 0.18 * hl))); card_.alpha_composite(glow)
    if op < 1: card_.putalpha(card_.getchannel("A").point(lambda v: int(v * op)))
    L.alpha_composite(card_, (x, y))

def cursor(f, x, y):
    k = 3
    im = Image.new("RGBA", (60 * k, 70 * k), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = [(8, 6), (8, 44), (18, 35), (25, 50), (32, 47), (25, 33), (38, 33)]
    d.polygon([((a + 2) * k, (b + 3) * k) for a, b in pts], fill=(0, 0, 0, 70))
    d.polygon([(a * k, b * k) for a, b in pts], fill=(255, 255, 255, 255))
    d.line([(a * k, b * k) for a, b in pts + [pts[0]]], fill=(30, 26, 24, 255), width=2 * k, joint="curve")
    im = im.resize((60, 70), Image.LANCZOS)
    put(f, im, x - 8, y - 6)

def ripple(f, x, y, q):
    if q <= 0 or q >= 1: return
    r = 14 + 46 * q
    L = Image.new("RGBA", (140, 140), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    d.ellipse((70 - r, 70 - r, 70 + r, 70 + r), outline=MINT_DEEP + (int(230 * (1 - q)),), width=5)
    put(f, L, x - 70, y - 70)

WP = [(0.0, 1560, 840), (1.9, 1035, 400), (2.4, 1035, 400), (3.6, 355, 400), (4.5, 355, 400),
      (5.4, 925, 452), (5.75, 925, 452), (6.1, 894, 652), (6.2, 894, 652), (6.45, 750, 714), (6.55, 750, 714),
      (6.85, 925, 814), (7.0, 925, 814), (7.7, 1000, 918), (9.5, 1000, 918)]
CLICKS = [2.15, 4.3, 5.7, 6.1, 6.45, 6.85, 7.7]

def cur_pos(t):
    for (t0, x0, y0), (t1, x1, y1) in zip(WP, WP[1:]):
        if t0 <= t <= t1:
            k = ease_io((t - t0) / (t1 - t0)) if t1 > t0 else 1
            return lerp(x0, x1, k), lerp(y0, y1, k)
    return WP[-1][1], WP[-1][2]

CATS = [("紀念鑽石", "cat_diamond.webp"), ("項墜", "cat_pendant.webp"), ("戒指", "cat_ring.webp"),
        ("耳環", "cat_earring.webp"), ("手鍊", "cat_bracelet.webp"), ("鏈條", "cat_chain.webp")]
STYLES = [("六爪單鑽戒", "ring_white.png"), ("花環", "style1.webp"), ("相遇之光", "style2.webp"),
          ("V字六爪戒", "style3.webp"), ("Weave", "style4.webp"), ("晶采", "style5.webp")]

def stage_op(t, a, b):
    return min(ease_io(prog(t, a, 0.25)), 1 - ease_io(prog(t, b - 0.25, 0.25)))

def scene3(t):
    f = bg_cream()
    reveal(f, t, 0.15, "六大 DNA 紀念鑽石系列線上試算", 960, 86, 48, 600, INK, d=0.5, rise=18)
    step = 0 if t < 2.7 else (1 if t < 5.0 else 2)
    labels = ["選品項", "選款式", "配置下單"]
    dr = ImageDraw.Draw(f)
    for i, lb in enumerate(labels):
        x0 = 200 + i * 520; w = 480
        a = ease_io(prog(t, 0.5, 0.4)) if i == 0 else (ease_io(prog(t, 2.7, 0.35)) if i == 1 else ease_io(prog(t, 5.0, 0.35)))
        dr.rectangle((x0, 150, x0 + w, 154), fill=(222, 216, 208))
        dr.rectangle((x0, 150, x0 + w * a, 154), fill=MINT_DEEP)
        c = INK if i <= step else (150, 140, 132)
        put(f, text_layer(lb, 24, 600, c, True)[0], x0 - 12, 161)
    L = Image.new("RGBA", (990, 780), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    selA = ease_io(prog(t, 2.15, 0.3))
    selB = ease_io(prog(t, 4.3, 0.3))
    if t < 2.9:
        op = stage_op(t, 0.3, 2.9) if t > 0.3 else 0
        d.text((0, 6), "選擇品項", font=sans(26, 600), fill=UI + (255,))
        for i, (nm, im) in enumerate(CATS):
            p = ease_out(prog(t, 0.4 + i * 0.12, 0.4))
            x = (i % 3) * 340; y = 56 + (i // 3) * 350
            tile(L, x, y + int((1 - p) * 24), 310, 320, cimg(im), nm, hl=selA if i == 2 else 0, op=p)
        L.putalpha(L.getchannel("A").point(lambda v: int(v * op)))
    elif t < 5.15:
        op = stage_op(t, 2.7, 5.15)
        d.text((0, 6), "← 返回品項", font=sans(22, 500), fill=(110, 100, 94, 255))
        d.text((170, 4), "戒指", font=sans(30, 700), fill=UI + (255,))
        for i, (nm, im) in enumerate(STYLES):
            p = ease_out(prog(t, 3.0 + i * 0.1, 0.4))
            x = (i % 3) * 340; y = 56 + (i // 3) * 350
            tile(L, x, y + int((1 - p) * 24), 310, 320, cimg(im), nm, hl=selB if i == 0 else 0, op=p)
        L.putalpha(L.getchannel("A").point(lambda v: int(v * op)))
    else:
        op = ease_io(prog(t, 5.0, 0.3))
        d.text((0, 6), "← 更換款式", font=sans(22, 500), fill=(110, 100, 94, 255))
        pv = Image.new("RGBA", (420, 420), (0, 0, 0, 0)); pd = ImageDraw.Draw(pv)
        rrect(pd, (0, 0, 419, 419), 22, fill=(255, 255, 255, 255), outline=LINE + (255,), width=2)
        k = ease_io(prog(t, 6.45, 0.45))
        im = Image.blend(cimg("ring_white.png"), cimg("ring_yellow.png"), k)
        ph = fit(im, 404, 404).convert("RGBA"); ph.putalpha(rmask(404, 404, 18)); pv.alpha_composite(ph, (8, 8))
        L.alpha_composite(pv, (0, 56))
        X = 460
        d.text((X, 62), "戒指 R-024", font=sans(20, 500), fill=(110, 100, 94, 255))
        d.text((X, 92), "六爪單鑽戒", font=font(46, 700), fill=INK + (255,))
        def label(txt, y): d.text((X, y), txt, font=sans(21, 600), fill=(90, 82, 76, 255))
        def box(y, txt, filled, clickp):
            rrect(d, (X, y, X + 530, y + 56), 12, fill=(255, 255, 255, 255), outline=mix(LINE, MINT_DEEP, clickp) + (255,), width=2)
            d.text((X + 20, y + 28), txt, font=sans(24, 500), fill=(UI if filled else (150, 142, 135)) + (255,), anchor="lm")
            d.polygon([(X + 490, y + 24), (X + 506, y + 24), (X + 498, y + 34)], fill=(120, 110, 104, 255))
        label("選擇克拉數", 168)
        c1 = t >= 5.7
        box(194, "0.1 ct" if c1 else "選擇克拉", c1, ease_out(prog(t, 5.65, 0.3)) * (1 - ease_io(prog(t, 6.2, 0.3))))
        label("選擇鑽石顏色", 272)
        rrect(d, (X, 298, X + 150, 346), 24, fill=(238, 252, 252, 255), outline=MINT_DEEP + (255,), width=2)
        d.ellipse((X + 14, 310, X + 38, 334), fill=(236, 248, 250, 255), outline=(150, 190, 196, 255), width=2)
        d.text((X + 50, 322), "白鑽", font=sans(24, 600), fill=UI + (255,), anchor="lm")
        label("選擇材質", 372)
        chips = ["9K金", "14K金", "18K金", "鉑金 Pt950", "925銀"]; cw_ = [80, 92, 92, 130, 92]
        x = X
        for i, (cn, w2) in enumerate(zip(chips, cw_)):
            on = (i == 2) and t >= 6.1
            rrect(d, (x, 398, x + w2, 446), 24, fill=(MINT + (255,)) if on else (255, 255, 255, 255), outline=(MINT_DEEP if on else LINE) + (255,), width=2)
            d.text((x + w2 // 2, 422), cn, font=sans(20, 600), fill=UI + (255,), anchor="mm"); x += w2 + 8
        dots = [("白金", (226, 228, 232)), ("黃金", (232, 196, 108)), ("玫瑰金", (230, 164, 150))]
        da = ease_out(prog(t, 6.15, 0.3))
        for i, (dn, dc) in enumerate(dots):
            cx_ = X + 26 + i * 64; cy_ = 484
            on = (i == 1 and t >= 6.45) or (i == 0 and t < 6.45)
            if da > 0:
                col = mix((255, 255, 255), dc, da)
                d.ellipse((cx_ - 22, cy_ - 22, cx_ + 22, cy_ + 22), fill=col + (255,), outline=(MINT_DEEP if on else LINE) + (255,), width=4 if on else 2)
        label("選擇國際戒圍", 530)
        c2 = t >= 6.85
        box(556, "國際戒圍 #8" if c2 else "請選擇國際戒圍", c2, ease_out(prog(t, 6.8, 0.3)) * (1 - ease_io(prog(t, 7.3, 0.3))))
        label("戒圈刻字", 634)
        rrect(d, (X, 660, X + 530, 716), 12, fill=(255, 255, 255, 255), outline=mix(LINE, MINT_DEEP, ease_io(prog(t, 7.7, 0.2))) + (255,), width=2)
        txt = "LOVE"; n = int(clamp((t - 7.9) / 0.14, 0, 5))
        if n == 0: d.text((X + 20, 688), "e.g. LOVE / 2024 / initials", font=sans(22, 400), fill=(170, 162, 155, 255), anchor="lm")
        d.text((X + 20, 688), txt[:min(n, 4)], font=sans(28, 700), fill=UI + (255,), anchor="lm")
        if n >= 5:
            hw = d.textlength(txt, font=sans(28, 700))
            hi = Image.open(os.path.join(CALC, "double-heart.png")).convert("RGBA"); hi.thumbnail((40, 30))
            L.alpha_composite(hi, (X + 26 + int(hw), 688 - hi.height // 2))
        cnt = 0 if n == 0 else (min(n, 4) + (2 if n >= 5 else 0))
        d.text((X + 530, 734), f"{cnt} / 12", font=sans(20, 500), fill=(120, 110, 104, 255), anchor="rm")
        L.putalpha(L.getchannel("A").point(lambda v: int(v * op)))
    f.paste(L, (PX, PY), L)
    pl = ease_out(prog(t, 0.3, 0.5))
    P = Image.new("RGBA", (RW, RH), (0, 0, 0, 0)); d = ImageDraw.Draw(P)
    rrect(d, (0, 0, RW - 1, RH - 1), 22, fill=(255, 255, 255, 255), outline=LINE + (255,), width=2)
    d.text((32, 40), "試算總價", font=sans(24, 600), fill=(100, 92, 86, 255), anchor="lm")
    priced = t >= 6.9
    val = int(40312 * ease_out(prog(t, 6.9, 0.8)))
    d.text((32, 128), "NT$", font=sans(30, 600), fill=(100, 92, 86, 255), anchor="lm")
    d.text((110, 124), f"{val:,}" if priced else "—", font=font(78, 700), fill=(INK if priced else (170, 162, 155)) + (255,), anchor="lm")
    d.text((32, 194), "預估參考，非最終報價" if priced else "選擇規格後顯示估價", font=sans(20, 400), fill=(130, 120, 113, 255), anchor="lm")
    d.line((32, 228, RW - 32, 228), fill=LINE + (255,), width=2)
    d.text((32, 262), "價格明細", font=sans(21, 600), fill=(100, 92, 86, 255), anchor="lm")
    rows = [("品項", "戒指" if t >= 2.15 else "-", 2.15), ("款式", "六爪單鑽戒" if t >= 4.3 else "-", 4.3),
            ("金屬材質", "18K黃金" if t >= 6.45 else "-", 6.45), ("克拉", "0.1 ct" if t >= 5.7 else "-", 5.7),
            ("鑽石顏色", "白鑽", 0), ("鑽石價格", "NT$ 24,000" if t >= 6.9 else "-", 6.9), ("金工價格", "NT$ 16,312" if t >= 6.9 else "-", 6.9)]
    for i, (k_, v, ts) in enumerate(rows):
        y = 312 + i * 50
        fl = 1 - ease_out(prog(t, ts, 0.5)) if ts else 0
        if fl > 0 and t >= ts: d.rounded_rectangle((20, y - 22, RW - 20, y + 22), 10, fill=mix((255, 255, 255), MINT, 0.45 * fl) + (255,))
        d.text((32, y), k_, font=sans(22, 500), fill=(110, 100, 94, 255), anchor="lm")
        d.text((RW - 32, y), v, font=sans(24, 700), fill=UI + (255,), anchor="rm")
    rrect(d, (32, 668, RW - 32, 716), 12, fill=MINT_DEEP + (255,))
    d.text((RW // 2, 692), "訂購", font=sans(26, 700), fill=(255, 255, 255, 255), anchor="mm")
    P.putalpha(P.getchannel("A").point(lambda v: int(v * pl)))
    s, pad = shadow(RW, RH, 22); put(f, s, RX - pad, RY - pad + 14, pl)
    f.paste(P, (RX, RY), P)
    for ct in CLICKS: ripple(f, *cur_pos(ct), prog(t, ct, 0.45))
    if t > 0.3:
        cx_, cy_ = cur_pos(t); cursor(f, cx_, cy_)
    return f


# ---------- scene 4: six collections ----------
TILES = [
    ("First Love", "滿月鑽石", "hero/imprint-diamond-newborn-baby-necklace.jpg", 0.74, 0),
    ("Companion", "寵物鑽石", "hero/imprint-diamond-pet-memorial-cat.jpg", 0.6, 0),
    ("Love", "結髮鑽石", "hero/imprint-diamond-wedding-couple-ring.jpg", 0.45, 0),
    ("Family", "全家福鑽石", "hero/imprint-diamond-family-portrait-jewelry.jpg", 0.64, 0),
    ("Heirloom", "生命鑽石", "hero/imprint-diamond-heirloom-memorial.jpg", 0.48, 0),
    ("Signature", "真我鑽石", OUT + "/work/signature.jpg", 0.36, 0),
]
def tile_img(i, w, h, t, t0):
    eng, name, path, cx, _ = TILES[i]
    k = 1.06 - 0.06 * ease_out(prog(t, t0, 1.6))
    if path:
        im = cover(load(path), w, h, cx, 0.5, k)
    else:
        ar = np.linspace(0, 1, w)[None, :, None] * 0.6 + np.linspace(0, 1, h)[:, None, None] * 0.4
        a = np.array(MINT) * (1 - ar) + np.array(MINT_DEEP) * ar
        im = Image.fromarray(a.astype(np.uint8))
        draw_diamond_mark(im, w * 0.5, h * 0.40, 150, t, 1.0, 0.2)
        if False: pass
    # label gradient
    g = np.linspace(0, 1, h)[:, None]
    ga = (np.clip((g - 0.52) / 0.48, 0, 1) ** 1.3 * 190).astype(np.uint8)
    ga = np.tile(ga, (1, w))
    L = Image.new("RGBA", (w, h), (36, 28, 24, 0)); L.putalpha(Image.fromarray(ga))
    im = im.convert("RGBA"); im.alpha_composite(L); im = im.convert("RGB")
    d = ImageDraw.Draw(im)
    d.text((32, h - 116), eng.upper(), font=font(20, 500, True), fill=(235, 250, 250))
    d.text((32, h - 88), name, font=font(46, 700), fill=(255, 255, 255))
    return im

def scene4(t):
    f = bg_cream()
    reveal(f, t, 0.3, "每一種羈絆，都有屬於它的光", 960, 118, 56, 600, INK)
    tw, th, gx, gy = 560, 330, 34, 34
    x0 = (W - (3 * tw + 2 * gx)) // 2
    y0 = 200
    for i in range(6):
        t0 = 0.5 + i * 0.28
        p = ease_out(prog(t, t0, 0.6))
        if p <= 0: continue
        x = x0 + (i % 3) * (tw + gx); y = y0 + (i // 3) * (th + gy) + (1 - p) * 36
        card(f, tile_img(i, tw, th, t, t0), x, y, op=p, r=22)
    return f

# ---------- scene 6: outro ----------
def scene6(t):
    f = bg_dark()
    p = ease_out(prog(t, 0.4, 0.8))
    if p > 0:
        put(f, glow_layer(520, MINT_DEEP, 0.26 * p), 960 - 520, 330 - 520)
        sz = int(300 * (0.9 + 0.1 * p))
        lg = Image.open(OUT + "/work/logo.png").convert("RGB").resize((sz, sz), Image.LANCZOS)
        L = lg.convert("RGBA"); L.putalpha(rmask(sz, sz, int(sz * 0.2)))
        put(f, L, 960 - sz // 2, 310 - sz // 2, p)
    reveal(f, t, 0.9, "把最深的情感，銘印成永恆", 960, 610, 84, 600, (251, 247, 242))
    reveal(f, t, 1.5, "銘印鑽石  ·  IMPRINT DIAMOND", 960, 725, 34, 500, MINT, sans=True, track=5)
    reveal(f, t, 1.9, "預約制一對一顧問  ｜  imprint-diamond.com", 960, 840, 34, 400, (228, 220, 212), sans=True, track=2)
    return f

SCENES = [scene1, scene2, scene3, scene4, scene6]
DIP = [(CREAM, CREAM), (CREAM, CREAM), (CREAM, CREAM), (CREAM, DARK), (DARK, (30, 26, 24))]
NS = len(SCENES)

def render(T):
    i = next((j for j in range(NS) if T < SC[j + 1]), NS - 1)
    t = T - SC[i]
    f = SCENES[i](t)
    dur = SC[i + 1] - SC[i]
    fo = 0.35 if i == NS - 1 else 0.3
    a_in = ease_io(prog(t, 0, 0.3)) if i > 0 else 1.0
    a_out = 1 - ease_io(prog(t, dur - fo, fo))
    k = min(a_in, a_out)
    if k < 1:
        c = DIP[i][0] if a_in < a_out else DIP[i][1]
        f = Image.blend(Image.new("RGB", f.size, c), f, k)
    return f

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "stills":
        os.makedirs(OUT + "/work/stills", exist_ok=True)
        for T in [float(x) for x in sys.argv[2:]]:
            render(T).save(f"{OUT}/work/stills/t{T:05.2f}.png")
    else:
        poster_T = float(sys.argv[2])
        ff = sys.argv[3]
        n = int(DUR * FPS)
        p = subprocess.Popen([ff, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                              OUT + "/work/silent.mp4"], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        for i in range(n):
            fr = render(poster_T) if i == 0 else render(i / FPS)
            if i == 0: fr.convert("RGB").save(OUT + "/brag.jpg", quality=95)
            p.stdin.write(fr.tobytes())
            if i % 60 == 0: print("frame", i, flush=True)
        p.stdin.close(); p.wait()
