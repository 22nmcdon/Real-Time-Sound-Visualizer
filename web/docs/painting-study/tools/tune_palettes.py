"""How Earth's and Night's inks were found: each started as a pigment picked
by eye (`palettes.py` before tuning), then moved in OKLCH - lightness within
0.12, chroma within 0.04, hue within 20 degrees, so each stays the pigment it
is named for - to clear DESIGN.md's bars (15 normal, 8 simulated, worst of all pairs)
with a margin of a twentieth while every ink keeps 3:1 contrast on its ground,
moving the inks as little as it can: past the margin, separation buys
nothing and drift costs, because a first search that maximised separation
alone drove every ink to its most saturated and the umber to grey. A seeded
hill climb; run it again and it lands on the same inks.

    python3 tune_palettes.py earth night
"""
import random, sys
import numpy as np
from colour import measure, hex_rgb, oklab, unlin

START = {
    "earth": ("#f0e7d6", {"a_main": "#33221a", "a_related": "#a4482a", "a_clash": "#2a4f80",
                          "b_main": "#6f7d45", "b_related": "#b98a2c", "b_clash": "#6e2a4a"}),
    "night": ("#151a24", {"a_main": "#ece3d0", "a_related": "#7fa8d6", "a_clash": "#e8734f",
                          "b_main": "#d8b04a", "b_related": "#5fb592", "b_clash": "#c06ab8"}),
}


# The umber is the earth palette's charcoal, and left free the search greys it.
FIXED = {"earth": ("a_main",), "night": ()}


def to_lch(h):
    L, a, b = oklab(hex_rgb(h)); return np.array([L, np.hypot(a, b), np.arctan2(b, a)])


def from_lch(lch):
    L, C, H = lch
    lab = np.array([L, C * np.cos(H), C * np.sin(H)])
    M2i = np.linalg.inv(np.array([[0.2104542553, 0.7936177850, -0.0040720468], [1.9779984951, -2.4285922050, 0.4505937099], [0.0259040371, 0.7827717662, -0.8086757660]]))
    M1i = np.linalg.inv(np.array([[0.4122214708, 0.5363325363, 0.0514459929], [0.2119034982, 0.6806995451, 0.1073969566], [0.0883024619, 0.2817188376, 0.6299787005]]))
    rgb_lin = M1i @ (M2i @ lab) ** 3
    if (rgb_lin < -1e-4).any() or (rgb_lin > 1 + 1e-4).any(): return None
    c = unlin(np.clip(rgb_lin, 0, 1))
    return "#" + "".join("%02x" % int(round(v * 255)) for v in c)


def drift(inks):
    return sum(np.linalg.norm(oklab(hex_rgb(v)) - oklab(hex_rgb(START_INKS[k]))) for k, v in inks.items())


def score(ground, inks):
    m = measure(inks, ground)
    if min(m["contrast"].values()) < 3: return -9, m
    return min(min(m["worst"]["normal"][0] / 15, m["simulated"][0] / 8), 1.05) - 0.15 * drift(inks), m


def tune(key, steps=12000):
    global START_INKS
    ground, inks = START[key]
    START_INKS = inks
    rnd = random.Random(1)
    base = {k: to_lch(v) for k, v in inks.items()}
    cur = dict(inks); best, _ = score(ground, cur)
    for _ in range(steps):
        k = rnd.choice([k for k in cur if k not in FIXED.get(key, ())]); lch = to_lch(cur[k])
        lch = lch + np.array([rnd.gauss(0, 0.02), rnd.gauss(0, 0.01), rnd.gauss(0, 0.05)])
        b = base[k]
        if abs(lch[0] - b[0]) > 0.12 or abs(lch[1] - b[1]) > 0.04 or lch[1] < 0: continue
        if abs((lch[2] - b[2] + np.pi) % (2 * np.pi) - np.pi) > np.radians(20): continue
        h = from_lch(lch)
        if h is None: continue
        trial = dict(cur, **{k: h}); s, _ = score(ground, trial)
        if s >= best: best, cur = s, trial
    return cur, best


if __name__ == "__main__":
    for key in sys.argv[1:] or START:
        inks, s = tune(key)
        m = measure(inks, START[key][0])
        print(key, round(s, 3), inks, m["worst"]["normal"], m["simulated"], round(drift(inks), 3))
