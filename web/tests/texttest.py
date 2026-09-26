"""Stage L's text and imported drawings: figures made of strokes.

Against the way each would fail:

- a beam that does not keep its speed: along a stroke it spends time in
  proportion to length, and between strokes an eighth of that, exactly;
- a traversal that misses its points or does not close: at each point's
  moment the figure is on that point, halfway along a segment it is halfway,
  and the lap ends where it began; with nothing to draw it is a dot, not a
  circle;
- a font that is not one: every glyph's points on its grid, every capital
  and digit present and each drawn differently, lower case drawn as capitals,
  anything unknown as a space, and a line of text filling the screen's width;
- a path reader that reads the specification loosely: relative and absolute,
  H and V, an implicit line after a move, numbers run together, arc flags run
  together, which way an arc sweeps, a cubic's midpoint, a smooth curve's
  reflection, Z closing - each against the drawing it has to be; and what it
  cannot read is refused with a reason;
- a panel that shows the wrong row or loses the picture: Text shows Words,
  Path shows SVG and says how many points; a path that cannot be read keeps
  the last drawing and says why; a file's paths are all drawn, and a script
  in it never runs;
- a generator that draws something else: every sample it draws, divided by
  the amplitude, lies on the compiled path, and it visits every point;
- a code that loses them: the words and the `d` come back exactly.
"""
import math, os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)

NOTE = "M 30 80 a 12 9 -20 1 1 0.1 0 M 42 78 L 42 20 C 50 30 62 34 58 52"

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()

    print("\n--- the beam's speed, and the traversal ---")
    walk = p.evaluate("""() => {
      // Two strokes a unit long, a unit apart: the travel is a unit too.
      const c = compilePath([[[0, 0], [1, 0]], [[1, 1], [0, 1]]]);
      // Back to the start from (0, 1) is a unit as well.
      const total = 1 + 1 / TRAVEL_SPEED + 1 + 1 / TRAVEL_SPEED;
      const want = [0, 1, 1 + 1 / TRAVEL_SPEED, 2 + 1 / TRAVEL_SPEED, total].map((w) => w / total);
      const at = (t) => figureAt('Path', t, 5, c);
      return {
        speed: TRAVEL_SPEED, at: c.at, want,
        onPoints: c.at.map((a, k) => { const p = at(a); return Math.hypot(p[0] - c.xy[2 * k], p[1] - c.xy[2 * k + 1]); }),
        half: at((c.at[0] + c.at[1]) / 2),
        wrap: [at(1), at(0), at(2.25), at(0.25)],
        nothing: [figureAt('Text', 0.3, 5, null), figureAt('Path', 0.3, 5, { xy: [], at: [] }), figureAt('Text', 0.3, 5)],
      };
    }""")
    print("    lap fractions %s" % [round(a, 4) for a in walk["at"]])
    check("the beam spends time by length along a stroke and an eighth of it between strokes",
          walk["speed"] == 8 and all(abs(a - w) < 1e-12 for a, w in zip(walk["at"], walk["want"])),
          "%s against %s" % (walk["at"], walk["want"]))
    check("at each point's moment it is on that point, and halfway along a segment it is halfway",
          max(walk["onPoints"]) < 1e-12 and abs(walk["half"][0] - 0.5) < 1e-12 and abs(walk["half"][1]) < 1e-12,
          "%s, %s" % (max(walk["onPoints"]), walk["half"]))
    check("the lap ends where it began, and a second lap is the first again",
          walk["wrap"][0] == walk["wrap"][1] and walk["wrap"][2] == walk["wrap"][3], str(walk["wrap"]))
    check("with nothing to draw it is a dot in the middle, not a circle",
          walk["nothing"] == [[0, 0], [0, 0], [0, 0]], str(walk["nothing"]))

    print("\n--- the font ---")
    font = p.evaluate("""() => {
      const keys = Object.keys(STROKE_FONT);
      const bad = keys.filter((k) => STROKE_FONT[k].split('|').some((part) => part && (part.length % 2
        || part.length < 4 || [...part].some((ch, i) => i % 2 === 0 ? !(ch >= '0' && ch <= '4') : !(ch >= '0' && ch <= '6')))));
      const need = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'.split('');
      const drawn = need.map((k) => STROKE_FONT[k]);
      const box = (strokes) => { let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
        for (const s of strokes) for (const [x, y] of s) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
        return [x0, x1, y0, y1]; };
      return {
        bad, missing: need.filter((k) => !(k in STROKE_FONT)), unique: new Set(drawn).size === drawn.length,
        lower: JSON.stringify(textStrokes('hello 42')) === JSON.stringify(textStrokes('HELLO 42')),
        unknown: JSON.stringify(textStrokes('H~H')) === JSON.stringify(textStrokes('H H')),
        hh: box(textStrokes('HH')), strokesHI: textStrokes('HI').length,
        long: textStrokes('X'.repeat(40)).length, max: TEXT_MAX,
        empty: textStrokes('').length,
      };
    }""")
    print("    %s" % font)
    check("every glyph's points are pairs on the four-by-six grid, and every capital and digit is there, each its own",
          font["bad"] == [] and font["missing"] == [] and font["unique"], "%s, %s" % (font["bad"], font["missing"]))
    check("lower case is drawn as capitals, and a character the font lacks as a space",
          font["lower"] and font["unknown"], "%s, %s" % (font["lower"], font["unknown"]))
    hh = font["hh"]
    check("a line of text fills the screen's width, centred, and stops at twenty-four characters",
          abs(hh[0] + 0.95) < 1e-12 and abs(hh[1] - 0.95) < 1e-12 and abs(hh[2] + hh[3]) < 1e-12
          and font["strokesHI"] == 6 and font["long"] == 24 * 2 and font["empty"] == 0,
          "HH spans %s; HI %d strokes; 40 Xs %d strokes" % (hh, font["strokesHI"], font["long"]))

    print("\n--- reading an SVG path ---")
    svg = p.evaluate("""() => {
      const J = (d) => JSON.stringify(svgStrokes(d));
      const out = {};
      out.relative = J('M0 0 L10 0 L10 10') === J('m0 0 l10 0 l0 10');
      out.hv = J('M0 0 L10 0 L10 10') === J('M0 0 H10 V10');
      out.implicit = J('M0 0 L10 0 L10 10') === J('M0 0 10 0 10 10');
      out.packed = J('M0,0L10-0L10,10') === J('M0 0 L10 0 L10 10') && J('M0 0L.5.5L1 0') === J('M0 0 L0.5 0.5 L1 0');
      // A relative v, and a relative move's further pairs being relative lines.
      // From y = 5: a relative v at y = 0 is the absolute one, and read the
      // same whichever it was taken for.
      out.relV = J('M0 5 l10 0 v10') === J('M0 5 L10 5 L10 15');
      out.implicitRel = J('m0 0 10 0 0 10') === J('M0 0 L10 0 L10 10');
      // Radii too small to reach are grown until they do: a radius of two
      // across a chord of ten is the same half circle as a radius of five.
      const small = svgStrokes('M0 0 A2 2 0 0 1 10 0')[0], five = svgStrokes('M0 0 A5 5 0 0 1 10 0')[0];
      out.grown = small.length === five.length
        ? Math.max(...small.map((p, k) => Math.hypot(p[0] - five[k][0], p[1] - five[k][1]))) : 99;
      out.closed = (() => { const s = svgStrokes('M0 0 L10 0 L10 10 Z')[0]; return JSON.stringify(s[0]) === JSON.stringify(s[s.length - 1]); })();
      // An arc with its flags run together: a half circle, every point as
      // far from the chord's middle as the ends are.
      const arc = svgStrokes('M0 0 A5 5 0 0110 0')[0], other = svgStrokes('M0 0 A5 5 0 0010 0')[0];
      const mx = (arc[0][0] + arc[arc.length - 1][0]) / 2, my = (arc[0][1] + arc[arc.length - 1][1]) / 2;
      const r = Math.hypot(arc[0][0] - mx, arc[0][1] - my);
      out.round = Math.max(...arc.map(([x, y]) => Math.abs(Math.hypot(x - mx, y - my) - r)));
      out.sweep = [arc[8][1], other[8][1]];
      // A cubic whose middle is (5, 7.5) in its own units: centred and scaled
      // by its box, that is (0, -0.7125).
      out.cubic = svgStrokes('M0 0 C0 10 10 10 10 0')[0][8];
      // And one whose control points are all off zero, every point of it:
      // the first had a control point at x = 0, so a wrong coefficient on it
      // multiplied nothing and the mutation pass saw it survive.
      out.cubicAll = svgStrokes('M1 2 C3 11 9 7 12 3')[0];
      // A smooth quadratic reflects its control point: the second hump is the
      // first upside down.
      const q = svgStrokes('M0 0 Q5 10 10 0 T20 0')[0];
      out.smooth = [q[8][1], q[24][1]];
      const refuse = (d) => { try { svgStrokes(d); return 'read'; } catch (e) { return e.message; } };
      out.errors = [refuse('M 1 2 X 3'), refuse('M0 0 A5 5 0 2 1 10 0'), refuse('M0 0 ' + 'L1 1 L0 0 '.repeat(3100))];
      out.note = svgStrokes(NOTE_D).length;
      return out;
    }""".replace("NOTE_D", repr(NOTE)))
    print("    %s" % svg)
    check("relative and absolute, H and V, a line implied after a move, and numbers run together all read the same",
          svg["relative"] and svg["hv"] and svg["implicit"] and svg["packed"],
          str([svg["relative"], svg["hv"], svg["implicit"], svg["packed"]]))
    check("Z closes a stroke where it began", svg["closed"], str(svg["closed"]))
    check("a relative v, and a relative move's further pairs, are relative lines",
          svg["relV"] and svg["implicitRel"], "%s, %s" % (svg["relV"], svg["implicitRel"]))
    check("radii too small to reach are grown until they do", svg["grown"] < 1e-9, "%.2e" % svg["grown"])
    raw = []
    for k in range(17):
        t = k / 16; u = 1 - t
        raw.append((u**3 * 1 + 3*u*u*t * 3 + 3*u*t*t * 9 + t**3 * 12, u**3 * 2 + 3*u*u*t * 11 + 3*u*t*t * 7 + t**3 * 3))
    x0 = min(p[0] for p in raw); x1 = max(p[0] for p in raw); y0 = min(p[1] for p in raw); y1 = max(p[1] for p in raw)
    sc = 1.9 / max(x1 - x0, y1 - y0); cx = (x0 + x1) / 2; cy = (y0 + y1) / 2
    want = [((x - cx) * sc, (cy - y) * sc) for x, y in raw]
    got = svg["cubicAll"]
    offc = max(math.hypot(a[0] - w[0], a[1] - w[1]) for a, w in zip(got, want)) if len(got) == 17 else 99
    check("a cubic with every control point off zero is the Bezier formula at every one of its points",
          offc < 1e-9, "%.2e" % offc)
    # The smooth quadratic's humps are held to their values, not only to being
    # opposite: without the reflection the second is flat, and re-centred on
    # its own box the two middles were still equal and opposite. With it, the
    # box is ten high and twenty wide, so each middle is 5 x 1.9 / 20 = 0.475.
    # A sweep of one runs clockwise on the screen, so from the left end to the
    # right it passes over the top: positive once y is turned the right way up.
    # Scaled to fit, the half circle's middle stands at exactly 0.475.
    check("an arc with its flags run together is a true half circle, and a sweep of one passes over the top",
          svg["round"] < 1e-9 and abs(svg["sweep"][0] - 0.475) < 1e-9 and abs(svg["sweep"][1] + 0.475) < 1e-9,
          "%.2e off round; middles %s" % (svg["round"], svg["sweep"]))
    check("a cubic's middle is where the formula puts it, and a smooth curve reflects its control point",
          abs(svg["cubic"][0]) < 1e-9 and abs(svg["cubic"][1] + 0.7125) < 1e-9
          and abs(svg["smooth"][0] + 0.475) < 1e-9 and abs(svg["smooth"][1] - 0.475) < 1e-9,
          "%s; %s" % (svg["cubic"], svg["smooth"]))
    check("and what it cannot read is refused with a reason: an unknown command, a flag that is not one, too many points",
          svg["errors"][0].startswith("no such command") and svg["errors"][1].startswith("expected an arc flag")
          and svg["errors"][2].startswith("too detailed") and svg["note"] == 2, str(svg["errors"]))

    print("\n--- on the page ---")
    page = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const out = {};
      el.genMode.value = 'figure'; el.genMode.dispatchEvent(new Event('change'));
      el.figure.value = 'Text'; el.figure.dispatchEvent(new Event('change'));
      out.text = { words: !el.figTextRow.hidden, svg: !el.figPathRow.hidden, note: !el.figPathNote.hidden,
                   label: [...el.figure.options].find((o) => o.value === 'Path').textContent };
      el.figText.value = 'SCOPE'; el.figText.dispatchEvent(new Event('input'));
      out.text.sent = JSON.stringify(genSettings().figPath) === JSON.stringify(compilePath(textStrokes('SCOPE')));
      el.figure.value = 'Path'; el.figure.dispatchEvent(new Event('change'));
      out.path = { words: !el.figTextRow.hidden, svg: !el.figPathRow.hidden };
      el.figPathD.value = NOTE_D; el.figPathD.dispatchEvent(new Event('change'));
      const good = JSON.stringify(genSettings().figPath);
      out.path.note = el.figPathNote.textContent;
      out.path.sent = good === JSON.stringify(compilePath(svgStrokes(NOTE_D)));
      el.figPathD.value = 'M 1 2 X'; el.figPathD.dispatchEvent(new Event('change'));
      out.path.kept = JSON.stringify(genSettings().figPath) === good;
      out.path.why = el.figPathNote.textContent;
      // A file, with two paths and a script that must never run.
      window.__ran = false;
      const svg = '<svg xmlns="http://www.w3.org/2000/svg"><script>window.__ran = true</script>'
        + '<path d="M0 0 L10 0 L10 10"/><rect width="5" height="5"/><path d="M20 20 L30 30"/></svg>';
      const dt = new DataTransfer();
      dt.items.add(new File([svg], 'two.svg', { type: 'image/svg+xml' }));
      el.figPathFile.files = dt.files;
      el.figPathFile.dispatchEvent(new Event('change'));
      await wait(200);
      out.file = { d: el.figPathD.value, ran: window.__ran,
                   sent: JSON.stringify(genSettings().figPath) === JSON.stringify(compilePath(svgStrokes('M0 0 L10 0 L10 10 M20 20 L30 30'))) };
      // What the generator draws: at ten laps a second, every sample on the path.
      el.figPathD.value = NOTE_D; el.figPathD.dispatchEvent(new Event('change'));
      el.figureRate.value = '10'; el.figureRate.dispatchEvent(new Event('input'));
      await wait(1200);
      const [l, r] = state.source.getLatestWindow(8820);
      out.drawn = { l: Array.from(l), r: Array.from(r), amp: genSettings().amp, path: genSettings().figPath };
      // A code, and back.
      el.figure.value = 'Text'; el.figure.dispatchEvent(new Event('change'));
      // A new generator, built from the panel, draws the same word: away to a
      // file and back to the tone.
      const rate = 44100, n = rate / 4, bytes = 44 + n * 2, buf = new ArrayBuffer(bytes), v = new DataView(buf);
      const str = (o, t) => { for (let i = 0; i < t.length; i++) v.setUint8(o + i, t.charCodeAt(i)); };
      str(0, 'RIFF'); v.setUint32(4, bytes - 8, true); str(8, 'WAVE'); str(12, 'fmt '); v.setUint32(16, 16, true);
      v.setUint16(20, 1, true); v.setUint16(22, 1, true); v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true);
      v.setUint16(32, 2, true); v.setUint16(34, 16, true); str(36, 'data'); v.setUint32(40, n * 2, true);
      await toFile(new File([buf], 'x.wav', { type: 'audio/wav' }));
      el.srcTone.click(); await wait(300);
      out.fresh = state.source.kind === 'tone'
        && JSON.stringify(genSettings().figPath) === JSON.stringify(compilePath(textStrokes('SCOPE')));
      const code = snapshot();
      out.code = [code.figText, code.figPath];
      restore({});
      out.bare = [el.figText.value, el.figPathD.value, figDrawing.path];
      restore(code);
      out.back = [el.figText.value, el.figPathD.value, JSON.stringify(genSettings().figPath) === JSON.stringify(compilePath(textStrokes('SCOPE')))];
      el.genMode.value = 'wave'; el.genMode.dispatchEvent(new Event('change'));
      return out;
    }""".replace("NOTE_D", repr(NOTE)))
    check("Text shows Words and nothing else, and the menu calls the other one SVG path",
          page["text"]["words"] and not page["text"]["svg"] and not page["text"]["note"]
          and page["text"]["label"] == "SVG path", str(page["text"]))
    check("typing a word sends its strokes to the generator", page["text"]["sent"], str(page["text"]["sent"]))
    check("Path shows SVG, sends the drawing, and says how many points it has",
          page["path"]["svg"] and not page["path"]["words"] and page["path"]["sent"]
          and page["path"]["note"].startswith("51 points"), page["path"]["note"])
    check("a path that cannot be read keeps the last drawing and says why",
          page["path"]["kept"] and page["path"]["why"] == "That path could not be read: no such command: X.",
          page["path"]["why"])
    check("a file's paths are all drawn, its other shapes left, and a script in it never runs",
          page["file"]["d"] == "M0 0 L10 0 L10 10 M20 20 L30 30" and page["file"]["sent"] and page["file"]["ran"] is False,
          str({k: page["file"][k] for k in ("d", "ran", "sent")}))

    d = page["drawn"]
    amp, xy = d["amp"], d["path"]["xy"]
    segs = [(xy[2 * k], xy[2 * k + 1], xy[2 * k + 2], xy[2 * k + 3]) for k in range(len(xy) // 2 - 1)]
    pts = [(x / amp, y / amp) for x, y in zip(d["l"], d["r"])]
    off = max(min(seg_dist(px, py, *s) for s in segs) for px, py in pts)
    visited = sum(1 for k in range(len(xy) // 2)
                  if min(math.hypot(px - xy[2 * k], py - xy[2 * k + 1]) for px, py in pts) < 0.02)
    check("every sample the generator draws lies on the path, and it visits every point of it",
          off < 1e-5 and visited == len(xy) // 2, "%.2e off the path; %d of %d points visited" % (off, visited, len(xy) // 2))
    check("a new generator, built from the panel, draws the same word", page["fresh"], str(page["fresh"]))
    check("a code carries the words and the d exactly, a code without them brings HELLO and no drawing, and it comes back",
          page["code"] == ["SCOPE", NOTE] and page["bare"] == ["HELLO", "", None]
          and page["back"] == ["SCOPE", NOTE, True], "%s / %s / %s" % (page["code"], page["bare"], page["back"]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
raise SystemExit(1 if fails else 0)
