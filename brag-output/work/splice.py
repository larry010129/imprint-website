s = open('build.py', encoding='utf8').read()
a = s.index("# ---------- scene 3: process ----------"); b = s.index("# ---------- scene 4")
s = s[:a] + open('calc_scene.py', encoding='utf8').read() + "\n" + s[b:]
a = s.index("# ---------- scene 5: what you get ----------"); b = s.index("# ---------- scene 6")
s = s[:a] + s[b:]
s = s.replace("SC = [0.0, 3.0, 6.5, 11.0, 15.5, 18.5, 21.5]", "SC = [0.0, 3.0, 5.7, 15.2, 18.5, 21.5]")
a = s.index("SCENES = ["); b = s.index('if __name__')
s = s[:a] + '''SCENES = [scene1, scene2, scene3, scene4, scene6]
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

''' + s[b:]
s = s.replace('reveal(f, t, 0.45, "IMPRINT DIAMOND"', 'reveal(f, t, 0.4, "IMPRINT DIAMOND"').replace('reveal(f, t, 0.7, "銘印鑽石", 150', 'reveal(f, t, 0.55, "銘印鑽石", 150').replace('reveal(f, t, 1.2, "台灣在地', 'reveal(f, t, 0.95, "台灣在地').replace('prog(t, 1.0, 0.7))\n    ImageDraw', 'prog(t, 0.8, 0.6))\n    ImageDraw')
s = s.replace('t0 = 0.65 + i * 0.5', 't0 = 0.5 + i * 0.28')
open('build.py', 'w', encoding='utf8').write(s)
