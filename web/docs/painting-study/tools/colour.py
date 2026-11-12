"""Colour measures for the study's palettes: the distance between inks in
OKLab, times a hundred, with colour vision deficiency simulated by Machado,
Oliveira and Fernandes (2009) at full severity, and WCAG contrast against the
ground.

The measure is not written down in the repository, but this one gives the
lane inks exactly the figures DESIGN.md quotes for them - worst all-pairs 16.1
with normal vision and 8.8 simulated (deuteranopia) - so it is taken to be
the one used, and the palettes are held to the same bars, 15 and 8.
`python3 colour.py` prints the lane inks' figures as that check. CIEDE2000
is kept beside it for anyone who wants the other scale."""
import itertools, math
import numpy as np


def hex_rgb(h):
    h = h.lstrip("#"); return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def lin(c):
    c = np.asarray(c, float); return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def unlin(c):
    c = np.clip(c, 0, 1); return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def lab(rgb):
    M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = M @ lin(rgb) / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def de2000(l1, l2):
    L1, a1, b1 = l1; L2, a2, b2 = l2
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2); Cb = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360; h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dL, dC = L2 - L1, C2p - C1p
    dh = 0 if C1p * C2p == 0 else (h2p - h1p if abs(h2p - h1p) <= 180 else h2p - h1p - 360 if h2p > h1p else h2p - h1p + 360)
    dH = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dh / 2))
    Lb, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    hb = h1p + h2p if C1p * C2p == 0 else ((h1p + h2p) / 2 if abs(h1p - h2p) <= 180 else (h1p + h2p + 360) / 2 if h1p + h2p < 360 else (h1p + h2p - 360) / 2)
    T = 1 - 0.17 * math.cos(math.radians(hb - 30)) + 0.24 * math.cos(math.radians(2 * hb)) + 0.32 * math.cos(math.radians(3 * hb + 6)) - 0.20 * math.cos(math.radians(4 * hb - 63))
    Sl = 1 + 0.015 * (Lb - 50) ** 2 / math.sqrt(20 + (Lb - 50) ** 2); Sc = 1 + 0.045 * Cbp; Sh = 1 + 0.015 * Cbp * T
    Rt = -2 * math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7)) * math.sin(math.radians(60 * math.exp(-((hb - 275) / 25) ** 2)))
    return math.sqrt((dL / Sl) ** 2 + (dC / Sc) ** 2 + (dH / Sh) ** 2 + Rt * (dC / Sc) * (dH / Sh))


# Machado et al. 2009, severity 1.0, applied to linear RGB.
CVD = {
    "protan": np.array([[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]]),
    "deutan": np.array([[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]]),
    "tritan": np.array([[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]]),
}


def simulate(rgb, kind): return unlin(CVD[kind] @ lin(rgb))


def luminance(rgb): return float(np.array([0.2126, 0.7152, 0.0722]) @ lin(rgb))


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True); return (la + 0.05) / (lb + 0.05)


def oklab(rgb):
    M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929], [0.2119034982, 0.6806995451, 0.1073969566], [0.0883024619, 0.2817188376, 0.6299787005]])
    M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468], [1.9779984951, -2.4285922050, 0.4505937099], [0.0259040371, 0.7827717662, -0.8086757660]])
    return M2 @ np.cbrt(M1 @ lin(rgb))


def dok(a, b): return float(np.linalg.norm(oklab(a) - oklab(b)) * 100)


def measure(inks, ground):
    """Worst all-pairs CIEDE2000 among the inks, normal and under each
    deficiency, and each ink's contrast on the ground."""
    rgbs = {k: hex_rgb(v) for k, v in inks.items()}
    out = {"worst": {}}
    for view in ("normal",) + tuple(CVD):
        f = (lambda c: c) if view == "normal" else (lambda c, v=view: simulate(c, v))
        worst = (1e9, None)
        for a, b in itertools.combinations(rgbs, 2):
            d = dok(f(rgbs[a]), f(rgbs[b]))
            worst = min(worst, (d, a + "/" + b))
        out["worst"][view] = (round(worst[0], 1), worst[1])
    out["simulated"] = min(out["worst"][v] for v in CVD)
    g = hex_rgb(ground)
    out["contrast"] = {k: round(contrast(c, g), 2) for k, c in rgbs.items()}
    out["ground"] = {k: round(dok(c, g), 1) for k, c in rgbs.items()}
    out["ground_simulated"] = {k: round(min(dok(simulate(c, v), simulate(g, v)) for v in CVD), 1) for k, c in rgbs.items()}
    return out


if __name__ == "__main__":
    lanes = {"ch1": "#241f1d", "ch2": "#5c6488", "ch3": "#4c4921", "ch4": "#6f9169", "ch5": "#72245e", "ch6": "#a6552d"}
    m = measure(lanes, "#faf6f0")
    print(m)
    assert m["worst"]["normal"][0] == 16.1 and m["simulated"][0] == 8.8, "not the measure DESIGN.md used"
