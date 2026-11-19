"""The play-band mockup's checks, in Chromium (web/docs/mockups/play-band/index.html).

Each check is fed a known-wrong case first or beside it (a null), and the null must be seen to fail,
as CLAUDE.md asks of every new assertion. The figures themselves (the envelope's law, its gestures,
Sustain here, the Envelope following) are the last mockup's, unchanged, and its own checks hold them
(../play-figures/checks/play_figures_checks.py).

- no console errors through every window, mode, hands state, way of sharing, count, end and chord;
- at the six windows, for Amp, Filter and Wave, one hand and two by notes with a chord held:
  * nothing between the band and the Expression row; Play does not scroll and the view's content is
    inside it; clear of the modulation row and the Picture; every knob and settings row one row;
  * every drawing wide: 1.5:1 to 7:1, the amp's at least 2:1, none under 120 px tall;
  * the subtab summaries fit; every value of the shown menus fits (Expression's four; Wave's Shape and
    Interval). Nulls: a figure area 2000 px tall scrolls; a figure area squeezed to 254 px makes a tower;
    the full menu names do not fit at 960x600;
- the band, in every state (Dyad, Mono, Poly; one hand; two by Key, Notes and Layer; every count from
  either end; a chord held or none; Learn waiting):
  * its content inside its one height. Nulls: a band 60 px tall cuts it; one 100 px tall squeezes the keys;
  * the split row's contents inside the row, nothing over its width. Null: testing's Notes row, the
    reading and the full end names put back, at 1100x860;
  * Key · Notes · Layer clear of the strip. Null: laid on the strip's top edge, as testing has it;
  * the line under the strip one sentence on one line. Null: testing's line, with the Chord window and
    Learn in it, at 960x600;
- the keys: 36 keys, 21 white, in every way of sharing, by notes too, and taller than testing's by half
  again. Null: testing's places drawing has no keys. By notes each held note's place drawn on its own
  key, the counted ones the counted hand's (null: a place drawn at testing's place positions is off its
  key), and the deal the instrument's (null: the other end's deal differs);
- nothing moves: every box on Play to half a pixel across all the states above, every Wave shape and
  the subtabs, at the six windows. Nulls: the band 6 px taller with two hands, as testing had it; the
  octave buttons taken out by notes, as testing does; a Wave band sized to its shape;
- Wave holds the Generator: its Shape, Glide, Interval and Level in Wave's header on one line no taller
  than the other views' (null: names over their controls make it taller), and none of them in the
  Expression row; Tuning in the dots at the header's end; the summary still the shape and its setting;
- a phone's width has no horizontal page scroll.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/play-band/checks/play_band_checks.py
"""
import os, sys, json
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import webfonts

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = "file://" + os.path.join(HERE, "index.html")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium")
fails, n = [], [0]

def check(ok, what):
    n[0] += 1
    print(("ok   " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)

def null(wrong_passes, what):
    """A null: the check, fed a known-wrong case, must fail."""
    check(not wrong_passes, "null: " + what)

SIZES = ["1660x1050", "1400x900", "1100x860", "1200x680", "1100x680", "960x600"]
COMPACT = {"1200x680", "1100x680", "960x600"}
TESTING_KEYS = {False: 44, True: 36}   # the strip's height on testing at 5597bd7, full and compact

def judge(m):
    fit = m["scroll"] <= 1 and m["viewOver"] <= 1
    nothing = m["gapBandToSettings"] <= 8 and m["between"] == 0
    clear = not m["coversModrow"] and not m["coversPicture"]
    one = all(r == 1 for r in m["knobRows"])
    wide = all(1.5 <= p["aspect"] <= 7 and p["h"] >= 120 and (p["what"] != "amp" or p["aspect"] >= 2) for p in m["plots"])
    fits = all(v["fits"] for v in m["labels"].values())
    menus = all(x["fits"] for x in m["menus"])
    return dict(fit=fit, nothing=nothing, clear=clear, one=one, wide=wide, fits=fits, menus=menus)

def band_ok(m):
    b = m["bandParts"]
    return dict(inside=m["bandOver"] <= 0, split=b["splitOverflow"] <= 0 and b["splitInside"], clear=b["kindsClearOfStrip"], line=b["hintFits"] and b["lineOneLine"])

# One state of the mockup, everything named, so no case inherits the last one's.
SET = """(o) => { const F = window.__figs, S = F.S;
  Object.assign(S, { size: "1400x900", sub: "amp", hands: 1, mode: "poly", kind: "key", count: 2, edge: "low", chord: "held", point: 60, base: 48, learning: false,
    menvOpen: false, flay: "auto", shape: "sine", editing: 0 }, o);
  S.linked.amp = true; S.linked.gen = true; S.linked.filter = true; S.note = null; F.render(); return F.measureNow(); }"""
BOX = "() => window.__figs.boxesNow()"

def same(a, b, keys=None):
    ks = [k for k in a if k in b and (keys is None or keys(k))]
    moved = [(k, a[k], b[k]) for k in ks if any(abs(x - y) > 0.5 for x, y in zip(a[k], b[k]))]
    missing = [k for k in a if k not in b and (keys is None or keys(k))]
    return (not moved and not missing), moved[:2] + [("missing", k) for k in missing[:2]], len(ks)

# Every state of the band, as (label, settings).
def band_states():
    out = [("Poly, one hand", {}), ("Dyad", {"mode": "dyad"}), ("Mono", {"mode": "mono"}), ("Poly, nothing held", {"chord": "none"}),
           ("two hands by key", {"hands": 2, "kind": "key"}), ("two hands by key, Learn waiting", {"hands": 2, "kind": "key", "learning": True}),
           ("two hands by key at G4", {"hands": 2, "kind": "key", "point": 67}), ("two hands layered", {"hands": 2, "kind": "layer"}),
           ("two hands by key, an octave up", {"hands": 2, "kind": "key", "base": 60})]
    for edge in ("low", "high"):
        for c in range(1, 7):
            for chord in ("held", "none"):
                out.append(("two hands by notes, %s %d, %s" % ("lowest" if edge == "low" else "highest", c, "a chord held" if chord == "held" else "nothing held"),
                            {"hands": 2, "kind": "notes", "edge": edge, "count": c, "chord": chord}))
    return out

results = {"rows": []}
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)
    p = b.new_page(viewport={"width": 1300, "height": 900})
    webfonts.route(p)
    errs = []
    p.on("pageerror", lambda e: errs.append(str(e)))
    p.on("console", lambda m: m.type == "error" and errs.append(m.text))
    p.goto(PAGE)
    p.wait_for_function("window.__ready === true", timeout=30000)
    faces = webfonts.settle(p)
    p.evaluate("() => window.__figs.render()")
    print("measured in " + ("the brand's webfonts (Jost, Playfair Display)" if faces else "FALLBACK faces: the webfonts did not load"))
    results["webfonts"] = faces
    STATES = band_states()

    # Every switch, a note held.
    for size in SIZES:
        for _, o in STATES:
            p.evaluate(SET, dict(o, size=size))
        for sub in ("amp", "filter", "wave"):
            p.evaluate(SET, {"size": size, "sub": sub, "hands": 2, "kind": "notes"})
    p.evaluate(SET, {"size": "1400x900", "menvOpen": True})
    p.evaluate("() => window.__figs.noteDown()"); p.wait_for_timeout(300)
    p.evaluate("() => window.__figs.noteUp()"); p.wait_for_timeout(300)
    check(not errs, "no console errors through every window, mode, hands state, way of sharing, count, end and chord, with a note held" + (": " + "; ".join(errs[:3]) if errs else ""))

    # ---- the fit ----
    for size in SIZES:
        for sub in ("amp", "filter", "wave"):
            for hands in (1, 2):
                m = p.evaluate(SET, {"size": size, "sub": sub, "hands": hands, "kind": "notes", "shape": "drawbars"})
                results["rows"].append(m)
                j = judge(m)
                tag = "%s, %s%s, %s" % (size, sub, " (%s)" % m["flayUsed"] if sub == "filter" else "", "two hands by notes" if hands == 2 else "one hand")
                check(j["nothing"] and j["fit"] and j["clear"] and j["one"],
                      tag + ": nothing between the band and Expression (%s px), no scroll (%s, view %s), clear of the rows under it, every row one row %s" % (m["gapBandToSettings"], m["scroll"], m["viewOver"], m["knobRows"]))
                check(j["wide"], tag + ": drawings wide and at least 120 px tall, %s" % ", ".join("%s %dx%d %.1f:1" % (q["what"], q["w"], q["h"], q["aspect"]) for q in m["plots"]))
                check(j["fits"] and j["menus"], tag + ": the summaries fit, and every value of the %d menus shown fits (tightest %s)" % (len(m["menus"]),
                      min(((x["room"] - x["widest"], x["menu"]) for x in m["menus"]), default=None)))
        m = p.evaluate(SET, {"size": size, "menvOpen": True})
        e = m["editor"]
        check(e["over"] <= 1 and not e["covers"] and all(2 <= q["aspect"] <= 7 and q["h"] >= 120 for q in e["plots"]),
              size + ": the Envelope's editor over the tabs, its content inside it, its drawing %s" % ["%dx%d" % (q["w"], q["h"]) for q in e["plots"]])
    p.evaluate(SET, {"size": "960x600", "hands": 2, "kind": "notes"})
    m = p.evaluate("() => { document.getElementById('figs').style.minHeight = '2000px'; return window.__figs.measureNow(); }")
    null(judge(m)["fit"], "a figure area 2000 px tall is seen to scroll (%s px)" % m["scroll"])
    p.evaluate(SET, {"size": "1660x1050"})
    m = p.evaluate("() => { const f = document.getElementById('figs'); f.style.width = '254px'; window.__figs.paint(); return window.__figs.measureNow(); }")
    null(judge(m)["wide"], "a figure area squeezed to 254 px is seen to make a tower %s" % [(q["w"], q["h"]) for q in m["plots"]])
    p.evaluate(SET, {"size": "960x600", "sub": "wave"})
    full = p.evaluate("() => window.__figs.measureNow().menus.filter((x) => !x.fullFits).map((x) => x.menu)")
    null(not full, "the full names, measured the same way, do not fit at 960x600 (%s)" % full)

    # ---- the band, in every state ----
    for size in SIZES:
        worst = {"inside": [], "split": [], "clear": [], "line": []}
        for label, o in STATES:
            m = p.evaluate(SET, dict(o, size=size))
            j = band_ok(m)
            for k in worst:
                if not j[k]:
                    worst[k].append(label)
        spare = p.evaluate(SET, {"size": size, "hands": 2, "kind": "notes", "edge": "high", "count": 6})["bandParts"]
        check(not worst["inside"], size + ": the band's content inside its one height in all %d states %s" % (len(STATES), worst["inside"] or ""))
        check(not worst["split"], size + ": the split row's contents inside it, nothing over its width, in every state (by notes %.1f px to spare) %s" % (-spare["splitOverflow"], worst["split"] or ""))
        check(not worst["clear"], size + ": Key · Notes · Layer clear of the strip in every state %s" % (worst["clear"] or ""))
        check(not worst["line"], size + ": the line under the strip one sentence on one line in every state %s" % (worst["line"] or ""))
    p.evaluate(SET, {"size": "960x600", "hands": 2, "kind": "notes"})
    # The keys take the band's spare height, so a band a little short squeezes them (the keys' check sees
    # that); one far too short cuts the left column, which cannot squeeze.
    over = p.evaluate("() => { document.getElementById('band').style.height = '60px'; return window.__figs.measureNow().bandOver; }")
    null(over <= 0, "a band 60 px tall is seen to cut its content (%.1f px over)" % over)
    p.evaluate(SET, {"size": "960x600", "hands": 2, "kind": "notes"})
    kh = p.evaluate("() => { document.getElementById('band').style.height = '100px'; return window.__figs.measureNow().bandParts.keysH; }")
    null(kh >= TESTING_KEYS[True] * 1.5, "a band 100 px tall is seen to squeeze the keys to %d px" % kh)
    p.evaluate(SET, {"size": "1100x860", "hands": 2, "kind": "notes"})
    m = p.evaluate("""() => { const o = document.getElementById('kindOwn'), s = document.createElement('span'); s.className = 'kb-read'; s.innerHTML = 'to the <b>lower</b> hand';
      o.insertBefore(s, document.getElementById('windowGo')); const e = document.querySelectorAll('#edgeSwitch button'); e[0].textContent = 'from the bottom'; e[1].textContent = 'from the top';
      e.forEach((x) => { x.style.width = 'auto'; }); return window.__figs.measureNow(); }""")
    null(band_ok(m)["split"], "testing's Notes row, the reading and the full end names put back, is seen not to fit at 1100x860 (%.1f px over)" % m["bandParts"]["splitOverflow"])
    p.evaluate(SET, {"size": "1400x900", "hands": 2, "kind": "notes"})
    m = p.evaluate("""() => { const k = document.getElementById('kindSwitch'), s = document.getElementById('strip'); s.style.position = 'relative'; s.appendChild(k);
      Object.assign(k.style, { position: 'absolute', left: '50%', top: '-11px', transform: 'translateX(-50%)' }); return window.__figs.measureNow(); }""")
    null(band_ok(m)["clear"], "Key · Notes · Layer laid on the strip's top edge, as testing has it, is seen over the strip")
    p.evaluate(SET, {"size": "960x600", "hands": 2, "kind": "notes"})
    m = p.evaluate("""() => { const h = document.getElementById('hint'); h.textContent = 'Lowest 2: the lower hand. Press a place for how many. learn from a key Chord window: 10 ms, in Settings'; return window.__figs.measureNow(); }""")
    null(band_ok(m)["line"], "testing's line, with Learn and the Chord window in it, is seen not to fit at 960x600 (%.1f px)" % m["bandParts"]["hintSpare"])

    # ---- the keys ----
    for size in SIZES:
        hs = set()
        for label, o in [("one hand", {}), ("by key", {"hands": 2, "kind": "key"}), ("by notes", {"hands": 2, "kind": "notes"}), ("layered", {"hands": 2, "kind": "layer"}), ("Dyad", {"mode": "dyad"})]:
            bp = p.evaluate(SET, dict(o, size=size))["bandParts"]
            hs.add((bp["keyCount"], bp["whiteCount"], bp["keysW"], bp["keysH"]))
        (kc, wc, kw, kh), = hs if len(hs) == 1 else [(0, 0, 0, 0)]
        want = TESTING_KEYS[size in COMPACT] * 1.5
        check(len(hs) == 1 and kc == 36 and wc == 21 and kh >= want,
              "%s: 36 keys, 21 white, %dx%d, in every way of sharing, by notes too; %.0f%% of testing's %d px tall" % (size, kw, kh, 100 * kh / TESTING_KEYS[size in COMPACT], TESTING_KEYS[size in COMPACT]))
    p.evaluate(SET, {"hands": 2, "kind": "notes"})
    bp = p.evaluate("""() => { const svg = document.getElementById('keys'); svg.innerHTML = '';
      for (let i = 0; i < 8; i++) { const r = document.createElementNS('http://www.w3.org/2000/svg', 'rect'); r.setAttribute('x', i * 70); r.setAttribute('width', 68); r.setAttribute('height', 60); r.setAttribute('class', 'k'); r.dataset.count = i + 1; svg.appendChild(r); }
      return window.__figs.measureNow().bandParts; }""")
    null(bp["keyCount"] == 36, "testing's places drawing, eight boxes and no keys, is seen to have %d keys" % bp["keyCount"])
    for edge in ("low", "high"):
        for c in range(1, 7):
            m = p.evaluate(SET, {"hands": 2, "kind": "notes", "edge": edge, "count": c})
            d = p.evaluate("() => window.__figs.dealt()")
            pl = m["bandParts"]["placed"]
            order = sorted(x["n"] for x in d) if edge == "low" else sorted((x["n"] for x in d), reverse=True)
            want_places = {order[i]: i + 1 for i in range(min(6, len(order)))}
            counted_hand = 0 if edge == "low" else 1
            deal_ok = all((x["hand"] == counted_hand) == (want_places.get(x["n"], 99) <= c) for x in d)
            check(all(q["onKey"] for q in pl) and {q["note"]: q["place"] for q in pl} == want_places and deal_ok,
                  "by notes, %s %d: places 1 to %d each on its own held key, the %d counted in the %s hand" % ("lowest" if edge == "low" else "highest", c, len(pl), c, "lower" if counted_hand == 0 else "upper"))
    p.evaluate(SET, {"hands": 2, "kind": "notes", "count": 3})
    pl = p.evaluate("""() => { const pw = document.getElementById('keys').clientWidth / 8;
      document.querySelectorAll('#keys [data-place] circle').forEach((c, i) => c.setAttribute('cx', i * pw + pw / 2)); return window.__figs.measureNow().bandParts.placed; }""")
    null(all(q["onKey"] for q in pl), "places drawn at testing's place positions are seen off their keys (%d of %d)" % (sum(not q["onKey"] for q in pl), len(pl)))
    lo = p.evaluate("() => { const F = window.__figs; F.S.edge = 'low'; return F.dealt().map((x) => x.hand); }")
    hi_ = p.evaluate("() => { const F = window.__figs; F.S.edge = 'high'; return F.dealt().map((x) => x.hand); }")
    null(lo == hi_, "counted from the other end, the deal differs (%s against %s)" % (lo, hi_))
    sp = p.evaluate(SET, {"hands": 2, "kind": "key", "point": 64})
    hands = p.evaluate("() => window.__figs.dealt().map((x) => [x.n, x.hand])")
    check(all((h == 1) == (n >= 64) for n, h in hands), "by key at E4, each held note under it the lower hand's and from it the upper's")

    # ---- nothing moves ----
    NOT_OWN = lambda k: not k.startswith("split own")
    for size in SIZES:
        p.evaluate(SET, {"size": size}); base = p.evaluate(BOX)
        moved_in = []
        for label, o in STATES[1:]:
            p.evaluate(SET, dict(o, size=size))
            ok, moved, nk = same(base, p.evaluate(BOX), NOT_OWN)
            if not ok:
                moved_in.append((label, moved))
        check(not moved_in, "%s: across all %d states of the band, every box on Play outside the split row's own controls (%d) where it was in Poly with one hand %s" % (size, len(STATES), nk, moved_in[:1] or ""))
        # Inside the split row by notes: every count from either end, a chord or none.
        p.evaluate(SET, {"size": size, "hands": 2, "kind": "notes"}); nb = p.evaluate(BOX)
        moved_in = []
        for label, o in STATES:
            if o.get("kind") != "notes":
                continue
            p.evaluate(SET, dict(o, size=size))
            ok, moved, nk = same(nb, p.evaluate(BOX))
            if not ok:
                moved_in.append((label, moved))
        check(not moved_in, "%s: by notes, every count from either end, a chord or none: all %d boxes, the split row's own too, where they were %s" % (size, nk, moved_in[:1] or ""))
        p.evaluate(SET, {"size": size, "hands": 2, "kind": "key"}); kb = p.evaluate(BOX)
        for label, o in [("Learn waiting", {"learning": True}), ("the split at G4", {"point": 67}), ("an octave up", {"base": 60}), ("nothing held", {"chord": "none"})]:
            p.evaluate(SET, dict(o, size=size, hands=2, kind="key"))
            ok, moved, nk = same(kb, p.evaluate(BOX))
            check(ok, "%s: by key, %s: all %d boxes where they were %s" % (size, label, nk, moved or ""))
        # Wave: every shape.
        shapes = p.evaluate("() => window.__figs.WAVE_SHAPES.map(([v]) => v)")
        p.evaluate(SET, {"size": size, "sub": "wave", "shape": "sine"}); wb = p.evaluate(BOX)
        moved_in, dims = [], set()
        for sh in shapes:
            m = p.evaluate(SET, {"size": size, "sub": "wave", "shape": sh})
            dims.add((m["plots"][0]["w"], m["plots"][0]["h"]))
            ok, moved, nk = same(wb, p.evaluate(BOX), lambda k: "knob g-" not in k)
            if not ok or m["viewOver"] > 1:
                moved_in.append((sh, moved))
        check(not moved_in and len(dims) == 1, "%s: Wave across all %d shapes: all %d boxes where they were with Sine, the cycle one size %s %s" % (size, len(shapes), nk, dims, moved_in[:1] or ""))
        # The subtabs: everything outside the view stays.
        p.evaluate(SET, {"size": size, "hands": 2, "kind": "notes"}); a = p.evaluate(BOX)
        for other in ("filter", "wave"):
            p.evaluate(SET, {"size": size, "sub": other, "hands": 2, "kind": "notes"})
            ok, moved, nk = same(a, p.evaluate(BOX), lambda k: not k.startswith("view"))
            check(ok, "%s: Amp to %s: all %d boxes outside the view where they were %s" % (size, other.capitalize(), nk, moved or ""))
    p.evaluate(SET, {}); a = p.evaluate(BOX)
    p.evaluate(SET, {"hands": 2})
    grown = p.evaluate("() => { const b = document.getElementById('band'); b.style.height = (parseFloat(b.style.height) + 6) + 'px'; return window.__figs.boxesNow(); }")
    ok, moved, _ = same(a, grown, NOT_OWN)
    null(ok, "the band 6 px taller with two hands, as testing had it, is seen to move %s" % (moved[0][0] if moved else "nothing"))
    p.evaluate(SET, {"hands": 2, "kind": "key"}); a = p.evaluate(BOX)
    p.evaluate(SET, {"hands": 2, "kind": "notes"})
    gone = p.evaluate("() => { document.getElementById('kbOct').style.display = 'none'; return window.__figs.boxesNow(); }")
    ok, moved, _ = same(a, gone, NOT_OWN)
    null(ok, "the octave buttons taken out by notes, as testing does, are seen to move %s" % (moved[0][0] if moved else "nothing"))
    p.evaluate(SET, {"size": "960x600", "sub": "wave", "shape": "sine"})
    p.evaluate("() => { const st = document.createElement('style'); st.id = 'nullBand'; st.textContent = '.wave-band { flex: 0 0 auto !important; height: auto !important; }'; document.head.appendChild(st); }")
    a = p.evaluate("() => { window.__figs.render(); return window.__figs.boxesNow(); }")
    b2 = p.evaluate("() => { window.__figs.S.shape = 'drawbars'; window.__figs.render(); return window.__figs.boxesNow(); }")
    ok, moved, _ = same(a, b2, lambda k: "knob g-" not in k)
    null(ok, "a Wave band sized to its shape is seen to move %s" % (moved[0][0] if moved else "nothing"))
    p.evaluate("() => document.getElementById('nullBand').remove()")

    # ---- Wave holds the Generator ----
    GEN = """() => { const sc = parseFloat(document.getElementById('stage').dataset.scale), h = document.querySelector('.fview:not([hidden]) .gen-head');
      const gf = [...h.querySelectorAll('.gf')], other = document.querySelector('.fview[data-view="amp"] .fhead');
      return { names: gf.map((g) => g.querySelector('.gl').textContent), tops: (() => { const t = gf.map((g) => { const q = g.getBoundingClientRect(); return (q.top + q.bottom) / 2 / sc; }); return Math.max(...t) - Math.min(...t) <= 1 ? 1 : 2; })(),
        h: h.getBoundingClientRect().height / sc, over: h.scrollWidth - h.clientWidth, dots: !!h.querySelector('[data-gen-dots]'), pill: !!h.querySelector('[data-link="gen"]'),
        inExpr: [...document.querySelectorAll('#setrow .fl')].map((x) => x.textContent), sum: document.querySelector('[data-sum="wave"]').textContent }; }"""
    for size in SIZES:
        p.evaluate(SET, {"size": size, "sub": "amp"})
        amp_head = p.evaluate("() => document.querySelector('.fview:not([hidden]) .fhead').getBoundingClientRect().height / parseFloat(document.getElementById('stage').dataset.scale)")
        p.evaluate(SET, {"size": size, "sub": "wave", "shape": "pulse", "hands": 2, "kind": "notes"})
        p.evaluate("() => { window.__figs.S.linked.gen = false; window.__figs.render(); }")
        g = p.evaluate(GEN)
        check(g["names"] == ["Shape", "Glide", "Interval", "Level"] and g["tops"] == 1 and g["over"] <= 0 and g["h"] <= amp_head + 4 and g["dots"] and g["pill"],
              "%s: Wave's header is the Generator, Shape, Glide, Interval and Level on one line, %.0f px tall (Amp's %.0f), nothing over, the pill and the dots at its end" % (size, g["h"], amp_head))
        check(g["inExpr"] == ["Pitch bend", "Mod wheel", "Pressure", "Velocity"], "%s: the row under the band is Expression's four alone %s" % (size, g["inExpr"]))
        check(g["sum"] == "pulse 25%", "%s: Wave's summary is the shape and its main setting (%r)" % (size, g["sum"]))
    p.evaluate(SET, {"size": "960x600", "sub": "wave"})
    g = p.evaluate("() => { document.querySelectorAll('.gen-head .gf').forEach((x) => { x.style.flexDirection = 'column'; x.style.alignItems = 'flex-start'; }); return (" + GEN + ")(); }")
    null(g["h"] <= 26, "the names over their controls are seen to make the header taller (%.0f px)" % g["h"])
    p.evaluate(SET, {"size": "1400x900", "sub": "wave"})
    p.click("[data-gen-dots]")
    tune = p.evaluate("() => { const m = document.getElementById('ctx'); return [!m.hidden, [...m.querySelectorAll('[data-tune]')].map((b) => b.textContent)]; }")
    check(tune[0] and tune[1] == ["Just", "Equal"], "Tuning is in the dots at the end of Wave's header")
    check(not p.evaluate("() => !!document.querySelector('#setrow [data-gen-dots], #setrow [data-tune]')"), "the Expression row has no Tuning")
    p.evaluate(SET, {"size": "1400x900", "sub": "wave", "shape": "drawbars"})
    bars = p.evaluate("""() => { const sc = parseFloat(document.getElementById('stage').dataset.scale), b = [...document.querySelectorAll('#waveBand input.vbar')];
      return { n: b.length, h: Math.min(...b.map((x) => x.getBoundingClientRect().height / sc)), tops: new Set(b.map((x) => Math.round(x.getBoundingClientRect().top))).size }; }""")
    check(bars["n"] == 9 and bars["h"] >= 48 and bars["tops"] == 1, "the nine drawbars in one row under the cycle, %.0f px tall" % bars["h"])

    # ---- a phone ----
    ph = b.new_page(viewport={"width": 390, "height": 800}); webfonts.route(ph); ph.goto(PAGE); ph.wait_for_function("window.__ready === true", timeout=30000)
    check(ph.evaluate("() => document.documentElement.scrollWidth <= innerWidth"), "a phone's width has no horizontal page scroll")
    ph.close()
    results["survey"] = p.evaluate("() => bandSurvey()")   # after the faces settled: at load it ran in a fallback face
    results["checks"] = n[0]; results["fails"] = fails
    with open(os.path.join(HERE, "checks", "results.json"), "w") as fh:
        json.dump(results, fh, indent=1, ensure_ascii=False)
print("%d checks, %d failed" % (n[0], len(fails)))
sys.exit(1 if fails else 0)
