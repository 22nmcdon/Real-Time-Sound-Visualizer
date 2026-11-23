"""Checks on the EQ-bands mockup (index.html), each against the failure it is
there for, each with its null, at 1400x900 and at 960x600 (90 per cent):

- the drag follows the pointer to every edge: for each band, from its point
  to 60 px past each edge of the plot, the point is where the pointer is,
  held to the band's own reach, at every step (null: the same drag with the
  points on the summed curve, today's way, which leaves the pointer; and a
  literal: the point's place before the drag);
- a point taken to an edge can be taken hold of again: what is under its
  centre is its own hit circle;
- a band switched off is out of the chain and its curve is gone, and the sum
  is the other four (null: the sum with it on differs);
- the chosen band's curve, and only it, is the one drawn stronger and washed;
- every point sits on its own band's curve at its frequency;
- each band is Web Audio's own BiquadFilterNode to 0.0001 dB (the cuts'
  Q given to the node in decibels, as pieces/eq.py does; null: the plain Q);
- nothing in the editor scrolls, and nothing moves - the strip, each cell, the
  plot and the foot - when a band is chosen, switched off, or the EQ is off;
- the five inks: contrast on paper and cream, and the all-pairs CIEDE2000
  separation with charcoal, normal and under simulated deuteranopia and
  protanopia (Machado 2009, full severity).

It writes checks/results.json and the same into index.html's checkResults
block, so the results travel with the page, and takes the screenshots.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/eq-bands/checks/eq_bands_checks.py
"""
import itertools, json, math, os, re, sys
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import webfonts

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(HERE, "index.html")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium")
checks = []


def check(name, ok, detail):
    checks.append({"name": name, "ok": bool(ok), "detail": detail})
    print(("ok   " if ok else "FAIL ") + name + " - " + detail)


# ---- colour: CIEDE2000, and Machado 2009's simulation at full severity ----
def srgb_lin(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lin_srgb(c):
    c = min(1, max(0, c))
    return 255 * (12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055)


def hex_rgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def lab(rgb):
    r, g, b = (srgb_lin(c) for c in rgb)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116
    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


def de2000(c1, c2):
    L1, a1, b1 = c1; L2, a2, b2 = c2
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    Cm = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)))
    a1p, a2p = a1 * (1 + G), a2 * (1 + G)
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1 = math.degrees(math.atan2(b1, a1p)) % 360
    h2 = math.degrees(math.atan2(b2, a2p)) % 360
    dL, dC = L2 - L1, C2p - C1p
    dh = 0 if C1p * C2p == 0 else (h2 - h1 if abs(h2 - h1) <= 180 else h2 - h1 - 360 if h2 > h1 else h2 - h1 + 360)
    dH = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dh / 2))
    Lm, Cmp = (L1 + L2) / 2, (C1p + C2p) / 2
    hm = h1 + h2 if C1p * C2p == 0 else ((h1 + h2) / 2 if abs(h1 - h2) <= 180 else (h1 + h2 + 360) / 2 if h1 + h2 < 360 else (h1 + h2 - 360) / 2)
    T = 1 - 0.17 * math.cos(math.radians(hm - 30)) + 0.24 * math.cos(math.radians(2 * hm)) + 0.32 * math.cos(math.radians(3 * hm + 6)) - 0.2 * math.cos(math.radians(4 * hm - 63))
    SL = 1 + 0.015 * (Lm - 50) ** 2 / math.sqrt(20 + (Lm - 50) ** 2)
    SC, SH = 1 + 0.045 * Cmp, 1 + 0.015 * Cmp * T
    RT = -2 * math.sqrt(Cmp ** 7 / (Cmp ** 7 + 25 ** 7)) * math.sin(math.radians(60 * math.exp(-((hm - 275) / 25) ** 2)))
    return math.sqrt((dL / SL) ** 2 + (dC / SC) ** 2 + (dH / SH) ** 2 + RT * (dC / SC) * (dH / SH))


MACHADO = {
    "deuteranopia": [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
    "protanopia": [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
}


def simulate(rgb, kind):
    m, l = MACHADO[kind], [srgb_lin(c) for c in rgb]
    return [lin_srgb(sum(m[i][j] * l[j] for j in range(3))) for i in range(3)]


def contrast(a, b):
    lum = lambda rgb: 0.2126 * srgb_lin(rgb[0]) + 0.7152 * srgb_lin(rgb[1]) + 0.0722 * srgb_lin(rgb[2])
    x, y = lum(a), lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


# ---- the page ----
def open_page(b, size):
    p = b.new_page(viewport={"width": 1500, "height": 1100})
    webfonts.route(p)
    errs = []
    p.on("pageerror", lambda e: errs.append(str(e)))
    p.goto("file://" + PAGE)
    p.wait_for_timeout(300)
    webfonts.settle(p)
    p.locator('#pgSize button[data-v="%s"]' % size).click()
    p.wait_for_timeout(200)
    return p, errs


def set_mode(p, place="own", start="shaped"):
    p.locator('#pgPlace button[data-v="%s"]' % place).click()
    p.locator('#pgStart button[data-v="%s"]' % start).click()
    p.wait_for_timeout(50)


GEO = """(k) => { const g = mock.geo(), box = document.getElementById('plot').getBoundingClientRect(), s = box.width / g.w;
  const ring = document.querySelector('.pt[data-band="' + k + '"] .ring').getBoundingClientRect();
  const b = mock.BANDS[k], hi = b.cut ? 20 * Math.log10(4) : b.kind === 'pk' ? 12 : 6, lo = b.cut ? 20 * Math.log10(0.5) : b.kind === 'pk' ? -16 : -8;
  return { s, pt: [ring.left + ring.width / 2, ring.top + ring.height / 2],
           x0: box.left + g.L * s, x1: box.left + (g.L + g.W) * s,
           y0: box.top + g.y(Math.min(12, hi)) * s, y1: box.top + g.y(Math.max(-16, lo)) * s,
           top: box.top + g.T * s, foot: box.top + (g.T + g.H) * s }; }"""


def drag_to_edge(p, k, edge, steps=40):
    """Press on band k's point and drag 60 px past an edge; at each step, how far the point is from the
    pointer held to the band's own reach. Returns the worst error (screen px), the worst against the
    point's place before the drag (the literal null), and the scale."""
    g = p.evaluate(GEO, k)
    sx, sy = g["pt"]
    tx, ty = {"right": (g["x1"] + 60, sy), "left": (g["x0"] - 60, sy), "top": (sx, g["top"] - 60), "foot": (sx, g["foot"] + 60)}[edge]
    p.mouse.move(sx, sy)
    p.mouse.down()
    worst = worst_null = 0
    for i in range(1, steps + 1):
        mx, my = sx + (tx - sx) * i / steps, sy + (ty - sy) * i / steps
        p.mouse.move(mx, my)
        now = p.evaluate(GEO, k)["pt"]
        want = (min(g["x1"], max(g["x0"], mx)), min(g["y1"], max(g["y0"], my)))
        worst = max(worst, math.hypot(now[0] - want[0], now[1] - want[1]))
        worst_null = max(worst_null, math.hypot(now[0] - sx, now[1] - sy))
    p.mouse.up()
    end = p.evaluate(GEO, k)["pt"]
    # Can it be taken hold of where it stopped? What is under its centre must be its own hit circle.
    grab = p.evaluate("([x, y, k]) => { const e = document.elementFromPoint(x, y); const pt = e && e.closest && e.closest('.pt'); return !!pt && pt.dataset.band === String(k); }",
                      [end[0], end[1], k])
    return worst, worst_null, grab, g["s"]


def boxes(p):
    return p.evaluate("""() => { const R = (n) => { const q = n.getBoundingClientRect(); return [q.left, q.top, q.width, q.height].map((v) => Math.round(v * 2) / 2); };
      const ed = document.getElementById('ed');
      return { strip: R(document.getElementById('strip')), cells: [...document.querySelectorAll('.cell')].map(R),
               vals: [...document.querySelectorAll('.cell .val')].map(R), lamps: [...document.querySelectorAll('.cell .lamp')].map(R),
               plot: R(document.getElementById('plot')), foot: R(document.getElementById('foot')), head: R(document.querySelector('.ed-head')),
               scrolls: ed.scrollHeight > ed.clientHeight + 0.5 || ed.scrollWidth > ed.clientWidth + 0.5,
               spill: [...ed.querySelectorAll('*')].filter((n) => { const q = n.getBoundingClientRect(), e = ed.getBoundingClientRect();
                         return n.getClientRects().length && !n.closest('svg') && (q.right > e.right + 0.5 || q.bottom > e.bottom + 0.5); }).length }; }""")


NODE = """async (cases) => { const out = [];
  for (const c of cases) { const ctx = new OfflineAudioContext(1, 128, 44100), f = ctx.createBiquadFilter();
    f.type = c.type; f.frequency.value = c.hz; f.gain.value = c.db; f.Q.value = c.q;
    const hz = new Float32Array(c.probes), mag = new Float32Array(hz.length), ph = new Float32Array(hz.length);
    f.getFrequencyResponse(hz, mag, ph); out.push(Array.from(mag, (m) => 20 * Math.log10(m))); }
  return out; }"""
PAGE_DB = """(cases) => cases.map((c) => { const S = mock.S, k = c.band, keep = JSON.parse(JSON.stringify(S.v));
  S.v.forEach((v, i) => { v.on = i === k; }); Object.assign(S.v[k], c.v); const co = mock.bandCoefs(k);
  const out = mock.respDb([co], c.probes); S.v.splice(0, 5, ...keep); return out; })"""


def run():
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=CHROME)
        for size in ("1400x900", "960x600"):
            p, errs = open_page(b, size)
            set_mode(p)
            # --- the drag follows the pointer to every edge ---
            worst, worst_null, grabs, scale = 0, 0, [], 1
            for k in range(5):
                for edge in ("right", "left", "top", "foot"):
                    set_mode(p, "own", "shaped")
                    w, wn, grab, scale = drag_to_edge(p, k, edge)
                    worst, worst_null = max(worst, w), max(worst_null, wn)
                    grabs.append(grab)
            check("%s: every point stays under the pointer to all four edges, held to its band's reach (20 drags, 40 steps each)" % size,
                  worst < 0.75, "worst %.2f screen px at a scale of %.2f" % (worst, scale))
            check("%s: null - the same check fails against the point's place before the drag" % size,
                  worst_null > 50, "%.0f px off" % worst_null)
            check("%s: a point taken to any edge can be taken hold of there (its own hit circle is under its centre)" % size,
                  all(grabs), "%d of %d" % (sum(grabs), len(grabs)))
            set_mode(p, "sum", "shaped")
            w_today, _, _, _ = drag_to_edge(p, 4, "right")
            check("%s: null - with the points on the summed curve (today), the High cut dragged right leaves the pointer" % size,
                  w_today > 5, "worst %.1f screen px" % w_today)
            set_mode(p, "own", "shaped")

            # --- every point on its own curve ---
            off = p.evaluate("""() => { const g = mock.geo(); let worst = 0; for (let k = 0; k < 5; k++) {
                const co = mock.bandCoefs(k), db = mock.respDb([co], [mock.S.v[k].hz])[0];
                worst = Math.max(worst, Math.abs(g.y(db) - mock.pointXY(k).y)); } return worst; }""")
            check("%s: every point sits on its own band's curve at its frequency" % size, off < 0.5, "worst %.3f px" % off)
            off_sum = p.evaluate("""() => { const g = mock.geo(), cas = mock.cascade(); let worst = 0; for (let k = 0; k < 5; k++) {
                worst = Math.max(worst, Math.abs(g.y(mock.respDb(cas, [mock.S.v[k].hz])[0]) - mock.pointXY(k).y)); } return worst; }""")
            check("%s: null - they are not on the summed curve" % size, off_sum > 5, "worst %.1f px off the sum" % off_sum)

            # --- the chosen band's curve is the one highlighted ---
            ok, null_ok = True, True
            for k in range(5):
                p.evaluate("(k) => mock.choose(k)", k)
                r = p.evaluate("""() => ({ chosen: [...document.querySelectorAll('.band-curve')].filter((c) => c.getAttribute('data-chosen') === '1').map((c) => Number(c.dataset.band)),
                    widths: [...document.querySelectorAll('.band-curve')].map((c) => Number(c.getAttribute('stroke-width'))),
                    fill: document.querySelector('.sel-fill').getAttribute('d').length, ink: document.querySelector('.sel-fill').getAttribute('fill'),
                    cell: [...document.querySelectorAll('.cell')].findIndex((c) => c.getAttribute('aria-selected') === 'true') })""")
                want_ink = p.evaluate("(k) => mock.BANDS[k].ink", k)
                ok &= r["chosen"] == [k] and r["widths"][k] == 2 and all(w < 2 for i, w in enumerate(r["widths"]) if i != k) \
                    and r["fill"] > 0 and want_ink in r["ink"] and r["cell"] == k
                null_ok &= r["chosen"] != [(k + 1) % 5]
            check("%s: the chosen band's curve, and only it, is drawn stronger and washed in its ink, and its cell is chosen" % size,
                  ok, "for each of the five")
            check("%s: null - for each band, the next band's curve is not the one highlighted" % size, null_ok, "five")

            # --- a band switched off: out of the chain, its curve gone ---
            res = []
            for k in range(5):
                set_mode(p, "own", "shaped")
                before = p.evaluate("() => [document.getElementById('sumPath').getAttribute('d'), mock.cascade().length]")
                p.locator('.cell[data-band="%d"] .lamp' % k).click()
                after = p.evaluate("""(k) => { const g = mock.geo(); const S = mock.S;
                  const others = [0,1,2,3,4].filter((i) => i !== k).map((i) => mock.bandCoefs(i)).filter(Boolean);
                  const fr = [30, 100, 300, 1000, 3000, 10000];
                  const want = mock.respDb(others, fr), got = mock.respDb(mock.cascade(), fr);
                  const ring = document.querySelector('.pt[data-band="' + k + '"] .ring');
                  return { d: document.querySelector('.band-curve[data-band="' + k + '"]').getAttribute('d'), sum: document.getElementById('sumPath').getAttribute('d'),
                    n: mock.cascade().length, diff: Math.max(...want.map((w, i) => Math.abs(w - got[i]))), on: S.v[k].on,
                    dash: ring.getAttribute('stroke-dasharray'), stroke: ring.getAttribute('stroke') }; }""", k)
                res.append((before, after))
            ok = all(a["d"] == "" and a["n"] == bf[1] - 1 and a["diff"] < 1e-9 and not a["on"] and a["dash"] and "unresolved" in a["stroke"] for bf, a in res)
            check("%s: a band switched off is out of the chain (the sum is the other four), its curve is gone and its point hollow and grey" % size,
                  ok, "for each of the five: " + ", ".join("%d to %d bands" % (bf[1], a["n"]) for bf, a in res))
            check("%s: null - switching each band off changes the summed curve" % size, all(bf[0] != a["sum"] for bf, a in res), "five")

            # --- nothing scrolls, nothing moves ---
            set_mode(p, "own", "shaped")
            base = boxes(p)
            states, moved, scroll = [], [], []
            for k in range(5):
                p.evaluate("(k) => mock.choose(k)", k); states.append(("chosen %d" % k, boxes(p)))
            for k in range(5):
                p.locator('.cell[data-band="%d"] .lamp' % k).click(); states.append(("off %d" % k, boxes(p)))
                p.locator('.cell[data-band="%d"] .lamp' % k).click()
            p.locator("#edOn").click(); states.append(("EQ off", boxes(p))); p.locator("#edOn").click()
            set_mode(p, "own", "flat"); states.append(("flat", boxes(p)))
            for name, bx in states:
                for key in ("strip", "cells", "vals", "lamps", "plot", "foot", "head"):
                    if bx[key] != base[key]:
                        moved.append(name + ":" + key)
                if bx["scrolls"] or bx["spill"]:
                    scroll.append(name)
            check("%s: nothing in the editor scrolls or spills, chosen, off, flat or with the EQ off (%d states)" % (size, len(states) + 1),
                  not base["scrolls"] and not base["spill"] and not scroll, ", ".join(scroll) or "none")
            check("%s: nothing moves - head, strip, cells, values, lamps, plot, foot - across them" % size, not moved, ", ".join(moved) or "to half a pixel")
            # Null: the check would see a reading sized to its words.
            p.evaluate("() => { document.querySelector('.cell .val').style.width = 'max-content'; document.querySelector('.cell .val').textContent = 'a much longer reading than that'; }")
            nb = boxes(p)
            check("%s: null - a reading sized to its words is seen to move" % size, nb["vals"] != base["vals"], "it moved")
            if errs:
                check("%s: no script errors" % size, False, "; ".join(errs))
            p.close()

        # --- the maths: Web Audio's own nodes ---
        p, _ = open_page(b, "1400x900")
        probes = [20, 50, 100, 160, 300, 700, 1000, 2000, 4000, 8000, 12000, 16000, 19000]
        cases, node = [], []
        kinds = ["highpass", "lowshelf", "peaking", "highshelf", "lowpass"]
        for k in range(5):
            for hz in (30, 160, 1000, 4000, 15000):
                if k in (0, 4):
                    for q in (0.5, 0.71, 1.4, 4):
                        cases.append({"band": k, "v": {"hz": hz, "q": q}, "probes": probes})
                        node.append({"type": kinds[k], "hz": hz, "db": 0, "q": 20 * math.log10(q), "probes": probes})
                else:
                    for db in (-16, -6, 3, 12):
                        for w in ((0.3, 1, 3) if k == 2 else (1,)):
                            cases.append({"band": k, "v": {"hz": hz, "db": db, "width": w}, "probes": probes})
                            node.append({"type": kinds[k], "hz": hz, "db": db, "q": (lambda p2: math.sqrt(p2) / (p2 - 1))(2 ** w) if k == 2 else 1, "probes": probes})
        mine, theirs = p.evaluate(PAGE_DB, cases), p.evaluate(NODE, node)
        worst = max(abs(a - b2) for m, t in zip(mine, theirs) for a, b2 in zip(m, t))
        check("each band is Web Audio's own BiquadFilterNode to 0.0001 dB (%d filters at %d frequencies, 44.1 kHz)" % (len(cases), len(probes)),
              worst < 1e-4, "worst %.1e dB" % worst)
        wrong = p.evaluate(NODE, [dict(n, q=c["v"]["q"]) if "q" in c["v"] else n for n, c in zip(node, cases)])
        werr = max(abs(a - b2) for m, t in zip(mine, wrong) for a, b2 in zip(m, t))
        check("null - the cuts against the node given the plain Q as its decibels", werr > 0.5, "%.2f dB off" % werr)
        p.close()
        b.close()

    # --- the inks ---
    tokens = dict(re.findall(r"(--[a-z0-9-]+):\s*(#[0-9a-f]{6})", open(PAGE).read().split("--pg-bg")[0]))
    inks = {"Low cut": tokens["--ch3"], "Low shelf": tokens["--ch6"], "Mid": tokens["--ch2"], "High shelf": tokens["--ch4"], "High cut": tokens["--ch5"]}
    lows = [min(contrast(hex_rgb(h), hex_rgb(tokens[g])) for g in ("--paper", "--cream")) for h in inks.values()]
    check("every band's ink clears 3:1 on paper and on cream", min(lows) >= 3, "lowest %.2f:1" % min(lows))
    allc = dict(inks, Sum=tokens["--charcoal"])
    pair = {}
    for kind in ("normal", "deuteranopia", "protanopia"):
        lab_of = {n: lab(hex_rgb(h) if kind == "normal" else simulate(hex_rgb(h), kind)) for n, h in allc.items()}
        pair[kind] = min((de2000(lab_of[a], lab_of[b2]), a, b2) for a, b2 in itertools.combinations(allc, 2))
    pairs = "All-pairs CIEDE2000 separation of the five inks and the sum's charcoal, measured by the checks: worst %.1f normal (%s and %s), %.1f simulated deuteranopia (%s and %s), %.1f protanopia (%s and %s)." % tuple(
        x for k in ("normal", "deuteranopia", "protanopia") for x in pair[k])
    check("the five inks and charcoal are told apart (CIEDE2000 all pairs, normal and two simulations)",
          pair["normal"][0] >= 15 and min(pair["deuteranopia"][0], pair["protanopia"][0]) >= 8, pairs)
    # Null: two inks next to each other in the range would fail it, as the two greens would.
    nul = de2000(lab(simulate(hex_rgb(tokens["--ch4"]), "deuteranopia")), lab(simulate(hex_rgb(tokens["--sage"]), "deuteranopia")))
    check("null - the brand's sage beside the lane sage fails the same bar", nul < 8, "%.1f" % nul)

    res = {"checks": checks, "pairs": pairs}
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.json"), "w") as f:
        json.dump(res, f, indent=1)
    s = open(PAGE).read()
    s = re.sub(r'(<script type="application/json" id="checkResults">).*?(</script>)', lambda m: m.group(1) + json.dumps(res).replace("</", "<\\/") + m.group(2), s, count=1, flags=re.S)
    open(PAGE, "w").write(s)
    bad = [c for c in checks if not c["ok"]]
    print("%d checks, %d failed" % (len(checks), len(bad)))
    return not bad


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
