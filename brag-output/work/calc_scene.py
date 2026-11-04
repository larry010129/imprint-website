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

WP = [(0.0, 1560, 840), (1.9, 1035, 392), (2.4, 1035, 392), (3.6, 355, 392), (4.5, 355, 392),
      (5.4, 925, 400), (5.9, 925, 400), (6.25, 924, 568), (6.6, 924, 568), (6.95, 745, 656), (7.3, 745, 656),
      (7.8, 925, 770), (8.1, 925, 770), (8.6, 900, 880), (9.5, 900, 880)]
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
        chips = ["9K金", "14K金", "18K金", "鉑金 Pt950", "925銀"]; cw_ = [92, 104, 104, 156, 108]
        x = X
        for i, (cn, w2) in enumerate(zip(chips, cw_)):
            on = (i == 2) and t >= 6.1
            rrect(d, (x, 398, x + w2, 446), 24, fill=(MINT + (255,)) if on else (255, 255, 255, 255), outline=(MINT_DEEP if on else LINE) + (255,), width=2)
            d.text((x + w2 // 2, 422), cn, font=sans(22, 600), fill=UI + (255,), anchor="mm"); x += w2 + 12
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
            ("鑽石顏色", "白鑽", 0), ("戒圍", "#8" if t >= 6.85 else "-", 6.85), ("刻字", "LOVE" if t >= 8.4 else "-", 8.4)]
    for i, (k_, v, ts) in enumerate(rows):
        y = 312 + i * 50
        fl = 1 - ease_out(prog(t, ts, 0.5)) if ts else 0
        if fl > 0 and t >= ts: d.rounded_rectangle((20, y - 22, RW - 20, y + 22), 10, fill=MINT + (int(70 * fl),))
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

