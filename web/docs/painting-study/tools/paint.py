"""Paint a rendered phrase: the marks made from the sound (`marks`), a style
that says what each mark is drawn with, a layout that says where it lands,
and a rasteriser that lays the marks down in the order they were made - all
at once for Accumulate, frame by frame with the older ones fading for Fade.

A mark is a timed operation in canvas pixels (`Op`). The marks depend on the
sound, the style and the layout and never on the palette: a palette is only
a lookup from a mark's ink role to a colour at the very end, and the ink
density Scan would read (`State.density`) is kept beside the colour from the
same coverages, so it is the same under every palette by construction -
`study.py` checks that it is, to the bit, rather than trusting this comment.

Where randomness enters it is seeded, and it only chooses where within a
mark's reach a drop lands or which bristle runs dry first; how many drops,
how far, how wide, how dark, what ink, all come from the sound.
"""
import math
from dataclasses import dataclass, field
import numpy as np
from PIL import Image

from colour import hex_rgb, lin, unlin

# --- textures -----------------------------------------------------------------


def fbm(size, seed, octaves=6, base=4):
    rng = np.random.default_rng(seed)
    out = np.zeros((size, size), np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        n = base * 2 ** o
        g = rng.random((n, n)).astype(np.float32)
        img = Image.fromarray(g).resize((size, size), Image.BICUBIC)
        out += amp * np.asarray(img, np.float32); total += amp; amp *= 0.55
    out /= total
    return (out - out.min()) / (out.max() - out.min())


TEX = None


def textures():
    global TEX
    if TEX is None:
        TEX = {"edge": fbm(512, 11), "paper": fbm(1024, 12, octaves=7, base=16), "grain": fbm(512, 13, octaves=3, base=64)}
    return TEX


def sample(tex, xs, ys):
    n = tex.shape[0]
    return tex[np.asarray(ys, int) % n, np.asarray(xs, int) % n]


# --- the canvas -----------------------------------------------------------------


@dataclass
class Op:
    t: float
    kind: str
    p: dict
    role: str        # a_main ... b_clash: the ink, looked up in the palette at the end
    mode: str        # "glaze" (transparent, darkening) or "over" (opaque paint)


class State:
    """The canvas as coverage by role, for each of two modes, plus density.

    `glaze[role]` is accumulated optical density of that ink (it adds, as
    glazes of watercolour do); `over` is an ordered paint layer, kept as a
    premultiplied colour-index image so the palette can be applied after: a
    stack of (role weight) per pixel, each new coat covering what is under
    it by its alpha. Both fade by the same factor in Fade."""

    def __init__(self, w, h, roles):
        self.w, self.h = w, h
        self.roles = list(roles)
        self.glaze = np.zeros((len(roles), h, w), np.float32)
        # The paint layer: weight of each role and the total coverage.
        self.over = np.zeros((len(roles), h, w), np.float32)
        self.cover = np.zeros((h, w), np.float32)
        self.density = np.zeros((h, w), np.float32)

    def deposit(self, op, y0, x0, a):
        h, w = a.shape
        sl = (slice(y0, y0 + h), slice(x0, x0 + w))
        r = self.roles.index(op.role)
        if op.mode == "glaze":
            self.glaze[r][sl] += a
        else:
            keep = 1 - a
            self.over[:, sl[0], sl[1]] *= keep
            self.over[r][sl] += a
            self.cover[sl] = self.cover[sl] * keep + a
        d = np.clip(a, 0, 1)
        self.density[sl] = 1 - (1 - self.density[sl]) * (1 - d)

    def fade(self, k):
        self.glaze *= k; self.over *= k; self.cover *= k; self.density *= k

    def image(self, palette):
        """The colours, at last: glazes multiply the paper by each ink's
        transmittance on a light ground (softly saturating, so a pile of
        glazes deepens towards the darkest ink rather than past it into
        mud), and lay on as light over a dark one; the paint layer over that."""
        ground = lin(hex_rgb(palette["ground"]))
        inks = np.array([lin(hex_rgb(palette["inks"][r])) for r in self.roles])  # roles x 3
        tex = textures()["paper"]
        paper = 1 + 0.035 * (sample(tex, *np.meshgrid(np.arange(self.w), np.arange(self.h))) - 0.5)
        if not palette["dark"]:
            logk = np.log(np.maximum(inks, 1e-4) / ground)            # <= 0
            S = np.tensordot(self.glaze, logk, axes=(0, 0))            # h w 3
            M = 1.15 * np.abs(logk).max(axis=0)
            S = -M * np.tanh(-S / M)
            col = ground * np.exp(S)
        else:
            # Over a dark ground a glaze is light: each ink's coverage
            # brings its colour up from the ground, coverages combining as
            # screens do, so two glazes are brighter than one and never past white.
            col = np.broadcast_to(ground, (self.h, self.w, 3)).copy()
            for i in range(len(self.roles)):
                a = (1 - np.exp(-self.glaze[i]))[..., None]
                col = 1 - (1 - col) * (1 - a * np.clip((inks[i] - ground) / (1 - ground), 0, 1))
        col = col * paper[..., None]
        # The paint layer, its roles mixed by weight, over the glazes.
        wsum = self.over.sum(axis=0)
        mix = np.tensordot(self.over, inks, axes=(0, 0)) / np.maximum(wsum, 1e-6)[..., None]
        c = np.clip(self.cover, 0, 1)[..., None]
        col = col * (1 - c) + mix * c * (0.97 + 0.06 * (paper[..., None] - 1))
        return (np.clip(unlin(col), 0, 1) * 255 + 0.5).astype(np.uint8)


# --- the rasteriser -----------------------------------------------------------


def _box(st, cx, cy, rx, ry):
    x0, x1 = max(0, int(cx - rx - 2)), min(st.w, int(cx + rx + 3))
    y0, y1 = max(0, int(cy - ry - 2)), min(st.h, int(cy + ry + 3))
    if x1 <= x0 or y1 <= y0: return None
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    return x0, y0, xs, ys


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


def draw(st, op, s=1.0):
    """Lay one operation onto the state, at scale `s` (an animation's frame is smaller)."""
    p = op.p; k = op.kind
    tex = textures()
    if k == "dab":
        # A brush's footprint: an ellipse of fixed angle (a broad nib swept
        # along a path makes the calligraphic thick and thin), its alpha
        # across its width by a bristle profile that opens as the brush dries.
        cx, cy, a_, b_ = p["x"] * s, p["y"] * s, max(p["w"] * s / 2, 0.6), max(p["h"] * s / 2, 0.5)
        r = max(a_, b_)
        bx = _box(st, cx, cy, r, r)
        if bx is None: return
        x0, y0, xs, ys = bx
        ca, sa = math.cos(p["ang"]), math.sin(p["ang"])
        u = ((xs - cx) * ca + (ys - cy) * sa) / a_
        v = (-(xs - cx) * sa + (ys - cy) * ca) / b_
        d = u * u + v * v
        a = (1 - smooth(0.55, 1.0, d)) * p["a"]
        if p.get("dry", 0) > 0:
            prof = p["bristles"]
            idx = np.clip(((u + 1) / 2 * (len(prof) - 1)).astype(int), 0, len(prof) - 1)
            a *= smooth(p["dry"] - 0.12, p["dry"] + 0.12, prof[idx])
        if p.get("tooth", 0) > 0:
            a *= 1 - p["tooth"] * smooth(0.45, 0.75, sample(tex["paper"], xs / s, ys / s))
        st.deposit(op, y0, x0, a.astype(np.float32))
    elif k == "blob":
        # A soft round of pigment with a rough edge (the edge noise moves
        # the radius) and, for a wash, the darker rim where it dried.
        cx, cy, R = p["x"] * s, p["y"] * s, p["r"] * s
        bx = _box(st, cx, cy, R * 1.35, R * 1.35)
        if bx is None: return
        x0, y0, xs, ys = bx
        dx, dy = xs - cx, ys - cy
        d = np.sqrt(dx * dx + dy * dy) / max(R, 0.5)
        rough = p.get("rough", 0)
        if rough:
            n = sample(tex["edge"], xs / s * p.get("scale", 1) + p["seed"] * 97, ys / s * p.get("scale", 1) + p["seed"] * 61)
            d = d * (1 + rough * (n - 0.5) * 1.2)
        soft = p.get("soft", 0.3)
        a = 1 - smooth(1 - soft, 1.0, d)
        rim = p.get("rim", 0)
        if rim: a = a * (1 - rim + rim * (0.55 + 0.9 * np.exp(-((d - 0.93) / 0.09) ** 2)))
        if p.get("gran", 0) > 0:
            g = sample(tex["grain"], xs / s + p["seed"] * 13, ys / s + p["seed"] * 7)
            a = a * (1 - p["gran"] + p["gran"] * 2 * smooth(0.35, 0.75, g))
        st.deposit(op, y0, x0, (a * p["a"]).astype(np.float32))
    elif k == "line":
        # A straight band with round or flat ends (signed distance to a segment).
        x0_, y0_, x1_, y1_ = p["x0"] * s, p["y0"] * s, p["x1"] * s, p["y1"] * s
        hw = max(p["w"] * s / 2, 0.5)
        bx = _box(st, (x0_ + x1_) / 2, (y0_ + y1_) / 2, abs(x1_ - x0_) / 2 + hw, abs(y1_ - y0_) / 2 + hw)
        if bx is None: return
        X0, Y0, xs, ys = bx
        vx, vy = x1_ - x0_, y1_ - y0_
        L2 = max(vx * vx + vy * vy, 1e-6)
        t = ((xs - x0_) * vx + (ys - y0_) * vy) / L2
        tc = np.clip(t, 0, 1)
        d = np.hypot(xs - (x0_ + tc * vx), ys - (y0_ + tc * vy))
        a = 1 - smooth(hw - 0.8, hw + 0.8, d)
        if p.get("flat"): a *= ((t >= 0) & (t <= 1))
        st.deposit(op, Y0, X0, (a * p["a"]).astype(np.float32))
    elif k == "ring":
        # A circle: filled (w nought) or a ring of width w; optionally an arc
        # from angle a0 to a1.
        cx, cy, R = p["x"] * s, p["y"] * s, p["r"] * s
        w = p.get("w", 0) * s
        bx = _box(st, cx, cy, R + w + 1, R + w + 1)
        if bx is None: return
        x0, y0, xs, ys = bx
        d = np.hypot(xs - cx, ys - cy)
        if w > 0: a = 1 - smooth(w / 2 - 0.7, w / 2 + 0.7, np.abs(d - R))
        else: a = 1 - smooth(R - 0.9, R + 0.9, d)
        if "a0" in p:
            ang = np.arctan2(ys - cy, xs - cx)
            rel = (ang - p["a0"]) % (2 * math.pi)
            a *= rel <= ((p["a1"] - p["a0"]) % (2 * math.pi))
        st.deposit(op, y0, x0, (a * p["a"]).astype(np.float32))
    elif k == "poly":
        # A convex plane, by its corners in order.
        pts = np.array(p["pts"], np.float32) * s
        cx, cy = pts.mean(axis=0)
        r = np.abs(pts - [cx, cy]).max(axis=0)
        bx = _box(st, cx, cy, r[0] + 1, r[1] + 1)
        if bx is None: return
        x0, y0, xs, ys = bx
        inside = np.full(xs.shape, 1e9, np.float32)
        n = len(pts)
        area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
        sgn = 1 if area > 0 else -1
        for i in range(n):
            ax, ay = pts[i]; bx_, by = pts[(i + 1) % n]
            ex, ey = bx_ - ax, by - ay
            L = math.hypot(ex, ey) or 1
            dist = sgn * ((xs - ax) * ey - (ys - ay) * ex) / L * -1
            inside = np.minimum(inside, dist)
        a = smooth(-0.8, 0.8, inside)
        st.deposit(op, y0, x0, (a * p["a"]).astype(np.float32))
    elif k == "grain":
        # Dry grit: specks of the ink scattered over a round, as many as the
        # noise in the sound asks for.
        cx, cy, R = p["x"] * s, p["y"] * s, p["r"] * s
        bx = _box(st, cx, cy, R, R)
        if bx is None: return
        x0, y0, xs, ys = bx
        g = sample(tex["grain"], xs / s * 2.3 + p["seed"] * 31, ys / s * 2.3 + p["seed"] * 17)
        fall = 1 - smooth(0.4, 1.0, np.hypot(xs - cx, ys - cy) / max(R, 1))
        a = smooth(1 - p["density"] * 0.35, 1 - p["density"] * 0.35 + 0.04, g) * fall
        st.deposit(op, y0, x0, (a * p["a"]).astype(np.float32))


# --- where a mark lands ----------------------------------------------------------


TURN = 8.0   # seconds a Layered canvas takes to come round
WHEEL = 60.0  # seconds physical paint's wheel takes to turn once by time alone


class Layout:
    """`at(t, pitch)` in canvas pixels. Layered: round the canvas by time,
    one turn every eight seconds from the top, clockwise, so a phrase longer
    than that paints over its own beginning, and out from the centre by
    pitch, low notes inside. A held note is an arc at its pitch, a melody a
    line in and out across the turns. Scroll: across by time, up by pitch.

    A first version of Layered placed marks across by pitch and up by the
    sound's brightness. It was true and dull: brightness hardly moves in a
    held sound, so every phrase lay in one band and a held chord was a row of
    blobs (`painting-the-sound.md`, What the study found)."""

    def __init__(self, kind, a, w, h):
        self.kind, self.w, self.h = kind, w, h
        notes = [e["note"] for e in a["events"]]
        lo, hi = min(notes), max(notes)
        span = max(hi - lo, 14 if kind in ("layered", "wheel") else 24)
        mid = (lo + hi) / 2
        self.plo, self.phi = mid - span / 2 - 2, mid + span / 2 + 2
        self.T = a["length"]
        fr = a["frames"]
        # Brightness smoothed over 150 ms: the stroke follows the sound's
        # colour, not each frame's estimate of it.
        k = np.hanning(17); k /= k.sum()
        self.ft = fr["t"]
        self.bright = np.convolve(fr["bright"], k, mode="same")
        self.mx, self.my = 0.08 * w, 0.1 * h

    def bright_at(self, t): return float(np.interp(t, self.ft, self.bright))

    def at(self, t, pitch):
        w, h, mx, my = self.w, self.h, self.mx, self.my
        px = (pitch - self.plo) / (self.phi - self.plo)
        if self.kind == "scroll":
            x = mx + (w - 2 * mx) * t / self.T
            y = h - my - (h - 2 * my) * px
        elif self.kind == "wheel":
            # Physical paint's Layered: round the canvas by pitch class, one
            # turn an octave (so pitch spirals outward), turned slowly by
            # time, so a note played again lands where it was - into its own
            # wet paint after a moment, onto dry paint after a pause.
            m = min(w, h)
            th = -math.pi / 2 + 2 * math.pi * ((pitch % 12) / 12 + t / WHEEL)
            r = m * (0.1 + 0.34 * px)
            x, y = w / 2 + r * math.cos(th), h / 2 + r * math.sin(th)
        else:
            m = min(w, h)
            th = -math.pi / 2 + 2 * math.pi * t / TURN
            r = m * (0.12 + 0.32 * px)
            x, y = w / 2 + r * math.cos(th), h / 2 + r * math.sin(th)
        return float(x), float(y)


# --- the marks --------------------------------------------------------------------


@dataclass
class Ctx:
    a: dict
    lay: Layout
    style: str
    w: int
    h: int
    ops: list = field(default_factory=list)

    def f(self, name, t): return float(np.interp(t, self.a["frames"]["t"], self.a["frames"][name]))

    def role(self, e): return ("a_" if e["hand"] == 0 else "b_") + e["role"]

    def unit(self): return min(self.w, self.h) / 1000


def level_at(e, t): return float(np.interp(t, e["ts"], e["level"], left=0, right=0))


def phrases(events):
    """A hand's melody as chains of linked strikes: each strike (a chord's
    notes struck together are one) joined to the hand's next if it comes
    within 0.45 s, through its top note. A chain of one is a note or a chord
    struck alone."""
    chains = []
    for hand in (0, 1):
        evs = sorted([e for e in events if e["hand"] == hand], key=lambda e: e["t0"])
        strikes = []
        for e in evs:
            if strikes and e["t0"] - strikes[-1][0]["t0"] < 0.04: strikes[-1].append(e)
            else: strikes.append([e])
        chain = []
        for st in strikes:
            top = max(st, key=lambda e: e["note"])
            if chain and len(st) == 1 and st[0]["t0"] - chain[-1]["t0"] < 0.45: chain.append(top)
            else:
                if chain: chains.append(chain)
                chain = [top]
        if chain: chains.append(chain)
    return chains


def path_of(ctx, chain, dt=0.004):
    """The brush's path along a chain: at each moment the pitch of the note
    sounding, gliding to the next in the last third of the gap, placed by
    the layout and smoothed over 25 ms; with each moment's level (the
    louder of the note leaving and the note arriving, from the core)."""
    t0 = chain[0]["t0"]
    last = chain[-1]
    t1 = max(last["t1"], last["t0"] + 0.05)
    ts = np.arange(t0, t1, dt)
    pitch = np.empty_like(ts); lev = np.empty_like(ts); vel = np.empty_like(ts)
    starts = [e["t0"] for e in chain]
    for i, t in enumerate(ts):
        j = max(0, int(np.searchsorted(starts, t, side="right")) - 1)
        e = chain[j]
        pv = e["note"]
        if j + 1 < len(chain):
            nxt = chain[j + 1]
            g = smooth(0.67, 1.0, (t - e["t0"]) / max(nxt["t0"] - e["t0"], 1e-3))
            pv = pv + (nxt["note"] - pv) * g
        pitch[i] = pv
        lv = level_at(e, t)
        if j > 0: lv = max(lv, level_at(chain[j - 1], t))
        lev[i] = lv; vel[i] = e["vel"]
    pts = np.array([ctx.lay.at(t, pv) for t, pv in zip(ts, pitch)])
    k = np.hanning(13); k /= k.sum()
    if len(pts) > 13:
        pad = np.pad(pts, ((6, 6), (0, 0)), mode="edge")
        pts = np.stack([np.convolve(pad[:, c], k, mode="valid") for c in (0, 1)], axis=1)
    return ts, pts, lev, vel


def wobble(ctx, ts, pts, amount):
    """The sound's agitation moves the brush off its line: a hand that
    shakes as the spectrum is restless. Nought for a steady sound."""
    agit = np.array([ctx.f("agitation", t) for t in ts])
    n = len(ts)
    if n < 3: return pts
    d = np.gradient(pts, axis=0)
    nrm = np.stack([-d[:, 1], d[:, 0]], axis=1)
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-6)
    # A smooth noise along the path's length (not a sine: a regular wobble
    # reads as a machine's), the hand's tremor as wide as the sound is agitated.
    arc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    tex = textures()["edge"]
    row = int(abs(pts[0][0] * 7 + pts[0][1] * 13)) % tex.shape[0]
    off = (sample(tex, arc / ctx.unit() * 0.08, np.full(n, row)) - 0.5) * 2.4 * agit * amount * ctx.unit()
    return pts + nrm * off[:, None]


def bristles(rng, n=48):
    b = rng.random(n); b = np.convolve(b, np.ones(3) / 3, mode="same")
    return (b - b.min()) / (b.max() - b.min() + 1e-9)


def sweep(ctx, ts, pts, widths, alphas, role, mode, ang, aspect, dry=None, prof=None, tooth=0.0):
    """Dabs along a path, at a spacing set by the brush's thin side, laid
    between samples too, so the deposit per unit length does not depend on
    how fast the brush moved and a fast flick leaves no gaps."""
    carry = 0.0
    for i in range(1, len(ts)):
        w = float(widths[i])
        if w < 0.4 or alphas[i] <= 0.002: carry = 0.0; continue
        p0, p1 = pts[i - 1], pts[i]
        seg = float(np.hypot(*(p1 - p0)))
        step = max(0.8, w * aspect / 3)
        carry += seg
        if carry < step: continue
        n = int(carry // step); carry -= n * step
        for k in range(n):
            f = 1 - k / n if n > 1 else 1.0
            x, y = p0 + (p1 - p0) * f
            p = dict(x=float(x), y=float(y), w=w, h=max(w * aspect, 0.9), ang=ang, a=float(min(alphas[i], 0.9)), tooth=tooth)
            if dry is not None and dry[i] > 0: p.update(dry=float(dry[i]), bristles=prof)
            ctx.ops.append(Op(float(ts[i]), "dab", p, role, mode))


# --- (a) ink and wash ---------------------------------------------------------


def ink_and_wash(ctx, rng):
    a, u = ctx.a, ctx.unit()
    # Washes: every note held past its attack lays a broad, soft area of its
    # ink, a little more each 70 ms it is held at level, spreading as it is
    # held (radius with the square root of time, as a drop spreads on wet
    # paper), granulating where the sound is noisy.
    for n, e in enumerate(a["events"]):
        role = ctx.role(e)
        t = e["t0"] + max(0.08, e["rise"] * 0.5)
        while t < e["t1"]:
            lv = level_at(e, t)
            if lv > 0.08 * e["peak"] and lv > 0.02:
                held = t - e["t0"]
                x, y = ctx.lay.at(t, e["note"])
                r = u * (12 + 36 * min(1.0, math.sqrt(held / 3))) * (0.5 + 0.8 * lv)
                # Each coat thinner than the last, so a long hold deepens
                # towards the ink's own colour rather than past it to black.
                coat = (0.012 + 0.03 * lv) * (0.5 + 0.5 * math.exp(-held / 2))
                jx, jy = rng.normal(0, 0.05 * r), rng.normal(0, 0.05 * r)
                ctx.ops.append(Op(t, "blob", dict(x=x + jx, y=y + jy, r=r, a=coat, rough=0.7, soft=0.3, rim=0.3,
                                                  gran=0.2 + 0.6 * ctx.f("grain", t), seed=n * 7 + int(held * 10), scale=1.1),
                                  role, "glaze"))
            t += 0.03
    # Strokes: the melody's path with a broad brush at a fixed angle; the
    # louder the note (the core's own level) the wider, so a note tapers as
    # it fades; the brush dries along the stroke and is dipped again by a hard
    # strike, and a bright sound dries it faster (dry brush is a bright edge).
    for c, chain in enumerate(phrases(a["events"])):
        ts, pts, lev, vel = path_of(ctx, chain)
        pts = wobble(ctx, ts, pts, 14)
        role = ctx.role(chain[0])
        bright = np.array([ctx.f("bright", t) for t in ts])
        widths = u * (6 + 60 * np.power(np.clip(lev, 0, 1), 0.7))
        alive = lev > 0.015
        widths[~alive] = 0
        # Only the attack and early ring of a long note is a stroke; the rest is wash.
        since = np.array([t - max(e["t0"] for e in chain if e["t0"] <= t) for t in ts])
        widths *= np.where(since < 0.6, 1.0, 0.35 + 0.65 * np.exp(-(since - 0.6) / 0.6))
        load = np.ones(len(ts)); cur = 1.0
        last = -1
        for i, t in enumerate(ts):
            j = sum(1 for e in chain if e["t0"] <= t) - 1
            if j != last:
                cur = min(1.0, cur + 0.6 * chain[j]["vel"]); last = j
            cur -= 0.0016 * (1 + 0.8 * max(bright[i], 0))
            load[i] = max(cur, 0.0)
        dry = np.clip(0.75 - load, 0, 0.7)
        sweep(ctx, ts, pts, widths, 0.09 * (0.4 + 0.6 * load), role, "glaze", ang=-0.6, aspect=0.22, dry=dry,
              prof=bristles(rng), tooth=0.25)
    # Spatter: a few drops where a note was struck hard and fast; how many
    # and how far by the velocity and the sharpness of the core's attack.
    for n, e in enumerate(a["events"]):
        sharp = max(0.0, 1 - e["rise"] / 0.12)
        k = int(round(14 * e["vel"] ** 2 * sharp))
        x, y = ctx.lay.at(e["t0"], e["note"])
        for _ in range(k):
            ang = rng.uniform(0, 2 * math.pi); dist = u * rng.uniform(10, 80) * e["vel"]
            ctx.ops.append(Op(e["t0"] + 0.01, "blob", dict(x=x + dist * math.cos(ang), y=y + dist * math.sin(ang),
                                                         r=u * rng.uniform(1.2, 4.5) * e["vel"], a=0.5, soft=0.5, seed=n), ctx.role(e), "glaze"))
    # Grain: where the sound is noisy, a dry scumble of specks over the whole
    # register sounding.
    noisy(ctx, rng, "glaze", 0.35)


def noisy(ctx, rng, mode, alpha):
    a = ctx.a; fr = a["frames"]; u = ctx.unit()
    for i in range(0, len(fr["t"]), 10):
        g = fr["grain"][i]
        if g < 0.12 or fr["db"][i] < -45: continue
        t = fr["t"][i]
        sounding = [e for e in a["events"] if e["t0"] <= t <= e["t1"]]
        if not sounding: continue
        e = max(sounding, key=lambda e: level_at(e, t))
        x, y = ctx.lay.at(t, e["note"])
        ctx.ops.append(Op(t, "grain", dict(x=x + rng.normal(0, 30 * u), y=y + rng.normal(0, 30 * u), r=u * (40 + 80 * g),
                                           density=g, a=alpha, seed=i), ctx.role(e), mode))


# --- (b) gestural ------------------------------------------------------------------


def gestural(ctx, rng):
    a, u = ctx.a, ctx.unit()
    # Pools: a held note is paint poured and left to spread, opaque, growing
    # while it is held, its edge rippled; heavy pools drip.
    for n, e in enumerate(a["events"]):
        role = ctx.role(e)
        t = e["t0"] + max(0.1, e["rise"])
        poured = 0.0
        while t < e["t1"]:
            lv = level_at(e, t)
            if lv > 0.15 * e["peak"] and lv > 0.03:
                held = t - e["t0"]
                x, y = ctx.lay.at(t, e["note"])
                r = u * (8 + 38 * min(1.0, math.sqrt(held / 3))) * (0.5 + lv)
                ctx.ops.append(Op(t, "blob", dict(x=x, y=y, r=r, a=0.3, rough=0.8, soft=0.25, seed=n * 5 + int(held * 4), scale=2.2),
                                  role, "over"))
                poured += lv * 0.08
            t += 0.08
        # Drips run down from a pool the longer and louder it was held.
        drips = int(poured * 1.3)
        x, y = ctx.lay.at(e["t0"] + 0.5 * (e["t1"] - e["t0"]), e["note"])
        rr = u * (8 + 38 * min(1.0, math.sqrt((e["t1"] - e["t0"]) / 3))) * (0.5 + e["peak"])
        for d in range(drips):
            dx = rng.uniform(-0.7, 0.7) * rr
            ln = u * (20 + rng.pareto(1.6) * 50) * min(1.5, poured / 3 + 0.4)
            wdt = u * rng.uniform(1.5, 5)
            ts_ = e["t1"] + d * 0.05
            m = 24
            ys_ = y + rr * 0.25 + np.linspace(0, ln, m)
            xs_ = x + dx + np.cumsum(rng.normal(0, 0.25 * u, m))
            wd = wdt * (1 - 0.6 * np.linspace(0, 1, m))
            sweep(ctx, np.full(m, ts_), np.stack([xs_, ys_], 1), wd, np.full(m, 0.95), role, "over", ang=0.0, aspect=1.0)
            ctx.ops.append(Op(ts_, "blob", dict(x=float(xs_[-1]), y=float(ys_[-1]), r=wdt * 0.75, a=0.95, soft=0.2, seed=d), role, "over"))
    # Flung lines: the melody thrown as skeins of paint. The faster the hand
    # moves across the canvas the thinner and longer the line (a flick); a
    # slow move pours thick. At each strike the line overshoots in the
    # direction it was going, as far as the strike was hard.
    for c, chain in enumerate(phrases(a["events"])):
        ts, pts, lev, vel = path_of(ctx, chain, dt=0.003)
        pts = wobble(ctx, ts, pts, 30)
        role = ctx.role(chain[0])
        sp = np.linalg.norm(np.gradient(pts, axis=0), axis=1) / 0.003   # px per second
        thin = 1 / (1 + sp / (900 * u))
        widths = u * (3 + 40 * np.clip(lev, 0, 1) * thin)
        widths[lev < 0.02] = 0
        since = np.array([t - max(e["t0"] for e in chain if e["t0"] <= t) for t in ts])
        widths *= np.where(since < 0.8, 1.0, np.exp(-(since - 0.8) / 0.5))
        sweep(ctx, ts, pts, widths, np.full(len(ts), 0.55), role, "over", ang=0.0, aspect=1.0)
        for e in chain:
            i = int(np.clip(np.searchsorted(ts, e["t0"] + 0.02), 1, len(ts) - 1))
            d = pts[min(i + 6, len(pts) - 1)] - pts[max(i - 6, 0)]
            if np.linalg.norm(d) < 1e-3: d = np.array([1.0, -0.3])
            d = d / np.linalg.norm(d)
            reach = u * 180 * e["vel"] ** 1.5 * (0.4 + ctx.f("agitation", e["t0"]))
            m = 30
            curl = rng.uniform(-0.6, 0.6)
            p0 = pts[i]
            seg = []
            for k in range(m):
                f = k / (m - 1)
                rot = curl * f
                dd = np.array([d[0] * math.cos(rot) - d[1] * math.sin(rot), d[0] * math.sin(rot) + d[1] * math.cos(rot)])
                seg.append(p0 + dd * reach * f)
            seg = np.array(seg)
            wd = u * (1.2 + 7 * e["vel"]) * (1 - np.linspace(0, 1, m)) ** 1.3
            sweep(ctx, np.full(m, e["t0"] + 0.03), seg, wd, np.full(m, 0.8), role, "over", ang=0.0, aspect=1.0)
    # Spatter: a strike flings drops in a cone the way the hand was moving,
    # as many as velocity squared and the attack's sharpness ask, sizes
    # falling off as a power law, the hardest strikes the furthest.
    chains = phrases(a["events"])
    for n, e in enumerate(a["events"]):
        sharp = max(0.15, 1 - e["rise"] / 0.15)
        k = int(round(70 * e["vel"] ** 2 * sharp * (0.5 + ctx.f("agitation", e["t0"]))))
        x, y = ctx.lay.at(e["t0"], e["note"])
        heading = rng.uniform(0, 2 * math.pi)
        for ch in chains:
            if e in ch and len(ch) > 1:
                j = ch.index(e); o = ch[j + 1] if j + 1 < len(ch) else ch[j - 1]
                x2, y2 = ctx.lay.at(o["t0"], o["note"])
                heading = math.atan2(y2 - y, x2 - x) if j + 1 < len(ch) else math.atan2(y - y2, x - x2)
        for _ in range(k):
            ang = heading + rng.normal(0, 0.7)
            dist = u * (rng.pareto(2.5) + 0.2) * 70 * e["vel"]
            r = u * min(9, 0.8 + rng.pareto(3.0) * 2.2) * (0.5 + e["vel"])
            ctx.ops.append(Op(e["t0"] + 0.01, "blob", dict(x=x + dist * math.cos(ang), y=y + dist * math.sin(ang), r=r, a=0.95,
                                                         soft=0.25, rough=0.3, seed=n * 3 + _), ctx.role(e), "over"))
    noisy(ctx, rng, "over", 0.6)


# --- (c) geometric --------------------------------------------------------------------


def geometric(ctx, rng):
    a, u = ctx.a, ctx.unit()
    events = a["events"]
    # Planes: each chord struck (three notes or more, or two hands' notes
    # together) is a plane across the register it spans, as tall as it was
    # loud; level with the ground when consonant, tilted as far as it is tense.
    strikes = []
    for e in sorted(events, key=lambda e: e["t0"]):
        if strikes and e["t0"] - strikes[-1][0]["t0"] < 0.04: strikes[-1].append(e)
        else: strikes.append([e])
    for s_, st in enumerate(strikes):
        if len(st) < 3: continue
        t0 = st[0]["t0"]; t1 = max(e["t1"] for e in st)
        lo = min(st, key=lambda e: e["note"]); hi = max(st, key=lambda e: e["note"])
        x0, y0 = ctx.lay.at(t0, lo["note"]); x1, y1 = ctx.lay.at(t1 if ctx.lay.kind == "scroll" else t0, hi["note"])
        loud = max(e["peak"] for e in st)
        ten = max(e["tension"] for e in st)
        role = ("a_" if st[0]["hand"] == 0 else "b_") + ("clash" if ten > 0.42 else "related")
        if ctx.lay.kind == "layered" and ten <= 0.42:
            # Consonant: a band round the turn, between the chord's lowest and
            # highest notes, for as long as it sounded.
            m = min(ctx.w, ctx.h)
            r0 = m * (0.12 + 0.32 * (lo["note"] - ctx.lay.plo) / (ctx.lay.phi - ctx.lay.plo))
            r1 = m * (0.12 + 0.32 * (hi["note"] - ctx.lay.plo) / (ctx.lay.phi - ctx.lay.plo))
            a0 = -math.pi / 2 + 2 * math.pi * t0 / TURN
            a1 = -math.pi / 2 + 2 * math.pi * min(t1, t0 + TURN * 0.95) / TURN
            ctx.ops.append(Op(t0, "ring", dict(x=ctx.w / 2, y=ctx.h / 2, r=(r0 + r1) / 2, w=u * (16 + 40 * loud),
                                               a0=a0, a1=a1, a=0.45), role, "over"))
            for rr in (r0, r1):
                ctx.ops.append(Op(t0, "ring", dict(x=ctx.w / 2, y=ctx.h / 2, r=rr, w=1.4 * u, a0=a0, a1=a1, a=0.9),
                                  role[:2] + "main", "over"))
            continue
        if ctx.lay.kind == "layered":
            # Tense: a straight plane cutting across the turn, from where the
            # chord's low note was struck to where its high note let go, tilted
            # off that line by how tense it is.
            x1, y1 = ctx.lay.at(t1, hi["note"])
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if ctx.lay.kind == "scroll":
            hw, hh = abs(x1 - x0) / 2 + 10 * u, abs(y1 - y0) / 2 + u * 20 * loud
            tilt = ten * 0.5 * (1 if s_ % 2 else -1)
        else:
            hw, hh = math.hypot(x1 - x0, y1 - y0) / 2 + 20 * u, u * (25 + 60 * loud)
            tilt = math.atan2(y1 - y0, x1 - x0) + ten * 0.5 * (1 if s_ % 2 else -1)
        ca, sa = math.cos(tilt), math.sin(tilt)
        pts = [(cx + dx * ca - dy * sa, cy + dx * sa + dy * ca) for dx, dy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))]
        ctx.ops.append(Op(t0, "poly", dict(pts=pts, a=0.3), role, "over"))
    # Circles: a held note is a circle at its place, its radius growing with
    # the square root of how long it is held and with its level, drawn as
    # concentric discs as it grows, each ring a stage of the hold; the last
    # one ringed with a thin line in the hand's own ink.
    for n, e in enumerate(events):
        role = ctx.role(e)
        held = e["t1"] - e["t0"]
        if held < 0.35: continue
        x, y = ctx.lay.at(e["t0"] + min(held, 0.6), e["note"])
        R = u * (10 + 55 * math.sqrt(min(held, 9) / 9)) * (0.5 + e["peak"])
        hand = "a_" if e["hand"] == 0 else "b_"
        halo = hand + ("related" if e["role"] != "related" else "main")
        ctx.ops.append(Op(e["t0"] + 0.3, "ring", dict(x=x, y=y, r=R * 1.6, a=0.22), halo, "over"))
        ctx.ops.append(Op(e["t0"] + 0.35, "ring", dict(x=x, y=y, r=R, a=0.88), role, "over"))
        ctx.ops.append(Op(e["t0"] + held * 0.9, "ring", dict(x=x, y=y, r=R * 1.6, w=1.3 * u, a=0.9), hand + "main", "over"))
    # Lines and arcs: the melody from strike to strike - a step (two
    # semitones or less) an arc, a leap a straight line, as heavy as the
    # note was loud; calm playing keeps them thin, agitation thickens nothing
    # but tilts the arcs further.
    for c, chain in enumerate(phrases(events)):
        role = ctx.role(chain[0])
        for i in range(len(chain) - 1):
            e0, e1 = chain[i], chain[i + 1]
            x0, y0 = ctx.lay.at(e0["t0"], e0["note"]); x1, y1 = ctx.lay.at(e1["t0"], e1["note"])
            wdt = u * (1.2 + 9 * e1["peak"])
            if abs(e1["note"] - e0["note"]) <= 2:
                mx, my = (x0 + x1) / 2, (y0 + y1) / 2
                dx, dy = x1 - x0, y1 - y0
                L = math.hypot(dx, dy) or 1
                bulge = L * (0.35 + 0.5 * ctx.f("agitation", e1["t0"]))
                side = 1 if e1["note"] > e0["note"] else -1
                cx, cy = mx - dy / L * bulge * side, my + dx / L * bulge * side
                R = math.hypot(x0 - cx, y0 - cy)
                a0 = math.atan2(y0 - cy, x0 - cx); a1 = math.atan2(y1 - cy, x1 - cx)
                if ((a1 - a0) % (2 * math.pi)) > math.pi: a0, a1 = a1, a0
                ctx.ops.append(Op(e1["t0"], "ring", dict(x=cx, y=cy, r=R, w=wdt, a0=a0, a1=a1, a=0.9), role, "over"))
            else:
                ctx.ops.append(Op(e1["t0"], "line", dict(x0=x0, y0=y0, x1=x1, y1=y1, w=wdt, a=0.9, flat=True), role, "over"))
    # Points: a strike is a dot, as large as it was hard; a sharp hard one a
    # burst of short rays from it, as many as velocity and sharpness ask.
    for n, e in enumerate(events):
        x, y = ctx.lay.at(e["t0"], e["note"])
        sharp = max(0.0, 1 - e["rise"] / 0.12)
        ctx.ops.append(Op(e["t0"], "ring", dict(x=x, y=y, r=u * (2.5 + 9 * e["vel"]), a=0.95), ("a_" if e["hand"] == 0 else "b_") + "main", "over"))
        rays = int(round(10 * e["vel"] ** 2 * sharp))
        for k in range(rays):
            ang = 2 * math.pi * k / max(rays, 1) + rng.uniform(-0.15, 0.15)
            r0, r1 = u * (12 + 9 * e["vel"]), u * (22 + 60 * e["vel"] * rng.uniform(0.5, 1))
            ctx.ops.append(Op(e["t0"] + 0.01, "line", dict(x0=x + r0 * math.cos(ang), y0=y + r0 * math.sin(ang), x1=x + r1 * math.cos(ang),
                                                         y1=y + r1 * math.sin(ang), w=u * 1.4, a=0.9), ctx.role(e), "over"))
    # Grain: noise as a field of small squares, a checker of grit.
    fr = a["frames"]
    for i in range(0, len(fr["t"]), 12):
        g = fr["grain"][i]
        if g < 0.12 or fr["db"][i] < -45: continue
        t = fr["t"][i]
        sounding = [e for e in events if e["t0"] <= t <= e["t1"]]
        if not sounding: continue
        e = max(sounding, key=lambda e: level_at(e, t))
        x, y = ctx.lay.at(t, e["note"])
        for k in range(int(g * 12)):
            sx, sy = x + rng.normal(0, 45 * u), y + rng.normal(0, 45 * u)
            q = u * 3
            ctx.ops.append(Op(t, "poly", dict(pts=[(sx - q, sy - q), (sx + q, sy - q), (sx + q, sy + q), (sx - q, sy + q)], a=0.8), ctx.role(e), "over"))


STYLES = {"ink": ink_and_wash, "gesture": gestural, "geometry": geometric}
ROLES = ("a_main", "a_related", "a_clash", "b_main", "b_related", "b_clash")


def marks(a, style, layout, w, h, seed=0):
    ctx = Ctx(a, Layout(layout, a, w, h), style, w, h)
    rng = np.random.default_rng(seed + {"ink": 1, "gesture": 2, "geometry": 3}[style] * 1000 + (0 if layout == "layered" else 500))
    STYLES[style](ctx, rng)
    ctx.ops.sort(key=lambda o: o.t)
    return ctx.ops


def accumulate(ops, w, h, s=1.0):
    st = State(int(w * s), int(h * s), ROLES)
    for op in ops: draw(st, op, s)
    return st


def fade_frames(ops, w, h, s, fps, length, persistence):
    """Yield the state at each frame, every mark laid when it was made and
    everything older multiplied down so it is at a tenth after `persistence`
    seconds - a wash of the paper over the last frame, as the screen fades."""
    st = State(int(w * s), int(h * s), ROLES)
    k = 0.1 ** (1 / (persistence * fps))
    i = 0
    for f in range(int(length * fps)):
        t = (f + 1) / fps
        st.fade(k)
        while i < len(ops) and ops[i].t <= t:
            draw(st, ops[i], s); i += 1
        yield st
