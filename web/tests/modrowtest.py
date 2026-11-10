"""The modulation row (G5a of web/docs/the-face-second-pass.md): a card per
source across the window, each drawing its source; the drawn editors; and
Routings, with a switch per source and the fade.

What would go wrong, and what is checked for it:

- the row in the wrong place, or the old strip still in the screen's column:
  the row must run under both the screen's column and the tabs, from the
  screen's left to the tabs' right, over the Picture section, with Routings
  and its count in the right-hand corner. The null is the screen's column,
  which held the cards until G5a and runs under the screen only;
- a fourth card that is only a label: the Photocell's card must be there
  with the photocell off, and a routing made from it - a real drag onto a
  knob - must move the control. Its null is the same routing with the
  reticle in the dark, where it reads nought and moves nothing;
- a card or an editor that draws a picture of nothing in particular. Each
  drawing is read back off its canvas: the ink must be where its source's
  shape puts it and not where another shape would, and each dot must move
  as its source moves. An LFO's shape is checked an eighth of a cycle in,
  where a sine (0.71) and a square (1) differ - a quarter-cycle point would
  pass either;
- the Envelope's curve following the wrong envelope: following Play it must
  move with Play's attack and not with its own, and the other way round
  with its own, each with its null;
- the photocell's crop being a picture of somewhere else: the inked pixels
  of the trace around the reticle must be inked in the crop, and the same
  pixels a crop-width away must not all be (the null);
- a silence that loses the routing or silences nothing: switched off, the
  routing must stop moving its control, stay in the setup and come back
  when switched on; the instrument behind the page must be told the routings
  heard. And Routings must list by source and by destination;
- the fade not working from its new home: chosen there, the fade must be the
  page's, and Settings must no longer hold it.

Parallel: everything is read off values and pixels at a moment; the dots'
movement is asked of a few hundred milliseconds and any change passes.
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)
def null(name, red, detail=""):
    """A check's null: the same comparison fed a value it must reject."""
    check("null: " + name, red, detail)

# The darkest pixel down one column of a canvas, in CSS pixels, and how dark
# it is: where a drawing's ink is at that x. Lines of the paper's own ink
# (the midline, the floor) are light; the strokes are the darkest thing.
INK = """window.__inkAt = (canvas, xCss) => {
  const dpr = window.devicePixelRatio || 1, g = canvas.getContext('2d');
  const x = Math.min(canvas.width - 1, Math.max(0, Math.round(xCss * dpr)));
  const d = g.getImageData(x, 0, 1, canvas.height).data;
  let best = -1, dark = -1;
  for (let y = 0; y < canvas.height; y++) {
    const a = d[y * 4 + 3] / 255, lum = (d[y * 4] + d[y * 4 + 1] + d[y * 4 + 2]) / 3;
    const v = a * (255 - lum);
    if (v > dark) { dark = v; best = y; }
  }
  return { y: best / dpr, dark };
};
window.__pixel = (canvas, xCss, yCss) => {
  const dpr = window.devicePixelRatio || 1;
  return Array.from(canvas.getContext('2d').getImageData(Math.round(xCss * dpr), Math.round(yCss * dpr), 1, 1).data);
};
true"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append(str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(1200)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.locator("#trace").click(position={"x": 5, "y": 5}); p.wait_for_timeout(500)
    p.evaluate("() => { setView('bench'); setBenchTab('play'); setDisplay('xy'); }")
    p.evaluate(INK)
    p.wait_for_timeout(400)

    print("\n--- the row ---")
    row = p.evaluate("""() => {
      const box = (e) => e.getBoundingClientRect();
      const r = box(el.modRow), side = box(el.benchSide), main = box(document.querySelector('.bench-main'));
      // Routings and its line under it, as a block in the corner.
      const routes = box(el.routingsButton.parentElement), bar = box(el.pictureBar);
      const wrap = el.modRow.querySelector('.wrap'), inner = box(wrap).right - parseFloat(getComputedStyle(wrap).paddingRight);
      const lastCard = Math.max(...[...el.modStrip.querySelectorAll('.mod-card')].map((c) => box(c).right));
      return { cards: [...el.modStrip.querySelectorAll('.mod-card')].map((c) => c.dataset.source),
               photoOn: photo.on,
               underBoth: r.top >= side.bottom - 1 && r.top >= main.bottom - 1, overBar: r.bottom <= bar.top + 1,
               spans: r.left <= side.left && r.right >= main.right,
               inColumn: !!el.modStrip.closest('#benchSide'),
               cornerGap: Math.round(inner - routes.right), pastCards: routes.left > lastCard, count: el.routingsCount.textContent,
               columnSpans: side.left <= side.left && side.right >= main.right };
    }""")
    print("    %s" % row)
    check("four cards, LFO 1, LFO 2, the Envelope and the Photocell, the Photocell's with the photocell off",
          row["cards"] == ["lfo1", "lfo2", "env.note", "photo.1"] and row["photoOn"] is False, str(row["cards"]))
    null("F4's three would not do", ["lfo1", "lfo2", "env.note"] != row["cards"])
    check("the row runs under the screen and the tabs, from the screen's left to the tabs' right, over the Picture section",
          row["underBoth"] and row["spans"] and row["overBar"] and not row["inColumn"], str(row))
    null("the screen's column, where the cards were, does not span the tabs", row["columnSpans"] is False)
    check("Routings is in the right-hand corner, past the cards, with its count",
          abs(row["cornerGap"]) <= 2 and row["pastCards"] and row["count"] == "· 0", str(row))
    counted = p.evaluate("""async () => { state.modRoutings = []; touchRoutings(); addRouting('lfo1', 'view.rotate'); addRouting('lfo2', 'gen.freq');
      await new Promise((r) => setTimeout(r, 400)); const c = el.routingsCount.textContent; state.modRoutings = []; touchRoutings();
      await new Promise((r) => setTimeout(r, 400)); return [c, el.routingsCount.textContent]; }""")
    check("its count follows the routings", counted == ["· 2", "· 0"], str(counted))

    print("\n--- each card draws its source, with a dot that moves ---")
    lfo = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      // Through its Rate, as a hand turns it, so the instrument behind the page
      // runs it at 2 Hz too: the phase the card draws is the instrument's.
      const rate = (v) => { const r = document.getElementById('lfoRate0'); r.value = String(v); r.dispatchEvent(new Event('input', { bubbles: true })); };
      lfos[0].shape = 'sine'; rate(200);
      await wait(300);
      const canvas = el.modStrip.querySelector('[data-source="lfo1"] canvas');
      const a = canvas._drawn.dot.slice();
      const under = __pixel(canvas, a[0], a[1]), corner = __pixel(canvas, 1, 1);
      await wait(260);
      const b = canvas._drawn.dot.slice();
      // Drawn now, beside the phase it was drawn from: the dot's x is the
      // LFO's phase across the first of the two cycles.
      paintModLive();
      const at = { x: canvas._drawn.dot[0], want: (lfos[0].phase % TWO_PI) / TWO_PI * canvas._drawn.w / 2 };
      // A sixteenth of a cycle in, the first cycle being the left half: the
      // card is 36 px tall, and there a sine (0.38) and a square (1) are nine
      // pixels apart where at an eighth they were four.
      const x = canvas._drawn.w / 32, h = canvas._drawn.h;
      const ink = __inkAt(canvas, x);
      const mid = h / 2, amp = h / 2 - 3;
      rate(20);
      // The null's shape is the ramp, which a sixteenth in is near its foot.
      return { a, b, at, under, corner, ink: ink.y, sine: mid - Math.sin(Math.PI / 8) * amp, ramp: mid - (2 / 16 - 1) * amp };
    }""")
    print("    %s" % lfo)
    check("LFO 1's card: its dot is drawn where it says, in the dark ink", lfo["under"][3] > 200 and sum(lfo["under"][:3]) / 3 < 110, str(lfo["under"]))
    null("the card's corner, away from the dot and the wave, is not that ink", lfo["corner"][3] < 50, str(lfo["corner"]))
    # Across, not only up and down: a dot held at one x still rises and falls
    # with the wave's value, and passed this check until it asked for the x
    # (the mutation pass).
    check("and the dot moves across as the LFO runs, at the LFO's phase", abs(lfo["a"][0] - lfo["b"][0]) > 20
          and abs(lfo["at"]["x"] - lfo["at"]["want"]) < 1.5, "%s then %s; %s" % (lfo["a"], lfo["b"], lfo["at"]))
    check("the wave drawn is a sine: a sixteenth of a cycle in, the ink is at 0.38 of its height",
          abs(lfo["ink"] - lfo["sine"]) < 2.5, "ink at %.1f, sine %.1f" % (lfo["ink"], lfo["sine"]))
    null("a ramp's height there is somewhere else", abs(lfo["ink"] - lfo["ramp"]) > 8, "ramp %.1f" % lfo["ramp"])

    env = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      el.menvOwn.checked = true; el.menvOwn.dispatchEvent(new Event('change'));
      for (const [id, v] of [['menvAtk', 900], ['menvDec', 300], ['menvSus', 50], ['menvRel', 900]]) setControl(id, v);
      setScreenKeys(true); await wait(200);
      const canvas = el.modStrip.querySelector('[data-source="env.note"] canvas');
      const idle = canvas._drawn.dot.slice(), idleStage = canvas._drawn.stage;
      midiNoteOn(60, 100); await wait(250);
      const early = canvas._drawn.dot.slice(), earlyStage = canvas._drawn.stage;
      await wait(350);
      const later = canvas._drawn.dot.slice();
      midiNoteOff(60); midiPanic(); setScreenKeys(false); await wait(1300);
      el.menvOwn.checked = false; el.menvOwn.dispatchEvent(new Event('change'));
      return { idle, idleStage, early, earlyStage, later };
    }""")
    print("    %s" % env)
    check("the Envelope's card: its dot rests at the start with nothing played", env["idleStage"] == "idle", str(env))
    check("and climbs the attack as a note is held, moving on", env["earlyStage"] == "attack" and env["later"][0] > env["early"][0]
          and env["later"][1] < env["early"][1], str(env))
    null("the resting dot is not where the attack took it", env["early"] != env["idle"])

    photo = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      // Found afresh each time: the cards are built again as sources come and go.
      const canvas = () => el.modStrip.querySelector('[data-source="photo.1"] canvas');
      const off = canvas()._drawn.dot.slice(), offValue = canvas()._drawn.value;
      el.photoButton.click(); await wait(1500);
      const on = canvas()._drawn.dot.slice();
      return { off, offValue, on, value: canvas()._drawn.value, photo: photo.value, reading: el.modStrip.querySelector('[data-source="photo.1"] .reading').textContent };
    }""")
    print("    %s" % photo)
    check("the Photocell's card: off, it draws nought; on the figure, its dot is at its reading",
          photo["offValue"] == 0 and photo["value"] > 0.1 and abs(photo["value"] - photo["photo"]) < 0.05 and photo["on"][1] < photo["off"][1] - 3,
          str(photo))
    null("on, the dot is not where it was off", photo["on"] != photo["off"])

    print("\n--- the Photocell, routable from its card ---")
    # A real drag of the card onto the Plane's Turn, with the photocell off:
    # the drag switches it on, and the routing moves the screen's rotation.
    # The Plane open, so its Turn is on show whether or not the Plane is on.
    p.evaluate("() => { el.photoButton.click(); state.modRoutings = []; touchRoutings(); setBenchTab('space'); openFx('plane', true); }")
    p.wait_for_timeout(300)
    card = p.locator('.mod-card[data-source="photo.1"]').bounding_box()
    knob = p.locator('[data-mod-dest="view.rotate"] .knob-face').first.bounding_box()
    p.mouse.move(card["x"] + card["width"] / 2, card["y"] + card["height"] / 2); p.mouse.down()
    p.mouse.move(card["x"] + 40, card["y"] - 40, steps=4)
    p.mouse.move(knob["x"] + knob["width"] / 2, knob["y"] + knob["height"] / 2, steps=8); p.mouse.up()
    p.wait_for_timeout(1500)
    routed = p.evaluate("""() => ({ on: photo.on, routes: state.modRoutings.map((r) => r.sourceId + '>' + r.destId),
      value: photo.value, turn: state.rotateMod })""")
    p.evaluate("() => movePhoto(0.02, 0.02)"); p.wait_for_timeout(2200)
    dark = p.evaluate("() => ({ value: photo.value, turn: state.rotateMod })")
    print("    %s; in the dark %s" % (routed, dark))
    check("dragged off with the photocell off, it is switched on and routed onto the Turn",
          routed["on"] and routed["routes"] == ["photo.1>view.rotate"], str(routed))
    check("and on the figure it turns the screen", routed["value"] > 0.1 and abs(routed["turn"]) > 0.01, str(routed))
    null("in the dark it reads nought and turns nothing", dark["value"] < 0.02 and abs(dark["turn"]) < 0.005, str(dark))
    offered = p.evaluate("""() => { el.photoButton.click(); state.modRoutings = []; touchRoutings();
      const opener = document.querySelector('.mod-open[data-dest="vcf.cut"]') || document.querySelector('.mod-open');
      const dest = opener.dataset.dest; openModEditor(dest, opener);
      const adds = [...document.querySelectorAll('.over [data-add]')].map((b) => b.dataset.add); closeOverlay();
      return { dest, adds, on: photo.on }; }""")
    check("a control's own list offers the four cards, the Photocell's while it is off",
          offered["adds"] == ["lfo1", "lfo2", "env.note", "photo.1"] and offered["on"] is False, str(offered))
    p.evaluate("() => setBenchTab('play')")

    print("\n--- the editors, drawn ---")
    p.locator('.mod-card[data-source="lfo1"]').click(); p.wait_for_timeout(300)
    wave = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const canvas = document.getElementById('srcDraw');
      // An eighth of a cycle in, where a sine is 0.71 and the LFO's square 0.9 (its height).
      const read = () => { paintModLive(); const d = canvas._drawn, x = d.w / 16, mid = d.h / 2, amp = d.h / 2 - 4;
        return { ink: __inkAt(canvas, x).y, sine: mid - Math.SQRT1_2 * amp, square: mid - 0.9 * amp, shape: d.shape, dot: d.dot.slice() }; };
      const sine = read();
      const shape = document.getElementById('lfoShape0'); shape.value = 'square'; shape.dispatchEvent(new Event('change'));
      await wait(100);
      const square = read();
      shape.value = 'sine'; shape.dispatchEvent(new Event('change'));
      return { open: !el.modEditor.hidden, sine, square, over: el.modEditor.getBoundingClientRect().left >= el.traceSheet.getBoundingClientRect().right,
               coversTabs: el.modEditor.getBoundingClientRect().top <= el.benchRail.getBoundingClientRect().top + 1 };
    }""")
    print("    %s" % wave)
    check("LFO 1's editor draws its wave large: a sine an eighth of a cycle in at 0.71", wave["open"] and wave["sine"]["shape"] == "sine"
          and abs(wave["sine"]["ink"] - wave["sine"]["sine"]) < 3, str(wave["sine"]))
    check("and with Square chosen, at its height, 0.9", wave["square"]["shape"] == "square" and abs(wave["square"]["ink"] - wave["square"]["square"]) < 3,
          str(wave["square"]))
    null("the square is not drawn at the sine's height", abs(wave["square"]["ink"] - wave["square"]["sine"]) > 4)
    check("the editor is over the tabs, their cards too, and beside the screen", wave["over"] and wave["coversTabs"], str(wave))
    p.locator('.mod-card[data-source="lfo1"]').click(); p.wait_for_timeout(200)
    check("pressing the card again puts it away", p.evaluate("() => el.modEditor.hidden && editingSource === null"))

    p.locator('.mod-card[data-source="env.note"]').click(); p.wait_for_timeout(300)
    curve = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const canvas = el.menvCurve;
      const attackX = () => { paintModLive(); return canvas._drawn.corners[1][0]; };
      const out = {};
      el.menvFollow.click(); await wait(50);
      setControl('envAttack', 0); setControl('menvAtk', 0); const a0 = attackX();
      setControl('envAttack', 200); const a1 = attackX();
      setControl('menvAtk', 2000); const a2 = attackX();
      out.follows = { own: canvas._drawn.own, play: a1 - a0, its: a2 - a1, grey: canvas._drawn.ink };
      el.menvItsOwn.click(); await wait(50);
      setControl('menvAtk', 0); const b0 = attackX();
      setControl('menvAtk', 2000); const b1 = attackX();
      setControl('envAttack', 0); const b2 = attackX();
      out.own = { own: canvas._drawn.own, its: b1 - b0, play: b2 - b1, ink: canvas._drawn.ink, checked: el.menvOwn.checked };
      el.menvFollow.click(); setControl('envAttack', 8); setControl('menvAtk', 10);
      return out;
    }""")
    print("    %s" % curve)
    check("following Play, the Envelope's curve is Play's: Play's attack moves its corner", curve["follows"]["own"] is False
          and curve["follows"]["play"] > 5, str(curve["follows"]))
    null("and its own attack does not", abs(curve["follows"]["its"]) < 0.5, str(curve["follows"]))
    check("pressed Its own, the curve is its own: its attack moves the corner", curve["own"]["own"] is True and curve["own"]["checked"] is True
          and curve["own"]["its"] > 5, str(curve["own"]))
    null("and Play's does not", abs(curve["own"]["play"]) < 0.5, str(curve["own"]))
    check("greyed following Play and in its ink with its own", curve["follows"]["grey"] != curve["own"]["ink"],
          "%s / %s" % (curve["follows"]["grey"], curve["own"]["ink"]))

    p.locator('.mod-card[data-source="photo.1"]').click(); p.wait_for_timeout(300)
    seen = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const off = { crop: !!document.getElementById('photoCrop'), on: photo.on, inEditor: el.photoButton.closest('#modEditor') !== null,
                    shown: !!el.photoButton.offsetParent };
      el.photoButton.click(); await wait(4400);
      const crop = document.getElementById('photoCrop');
      paintModLive();
      const d = crop._drawn, dpr = window.devicePixelRatio || 1;
      const trace = el.trace.getContext('2d').getImageData(0, 0, el.trace.width, el.trace.height);
      const cropImg = crop.getContext('2d').getImageData(0, 0, crop.width, crop.height);
      const tw = el.trace.width, cw = crop.width, ch = crop.height;
      const inkAt = (img, w, x, y) => { const k = (y * w + x) * 4; return img.data[k + 1] < 185; };
      // Each inked trace pixel inside the crop's window, outside the reticle's ring and cross.
      const count = (shift) => { let n = 0, hit = 0;
        for (let i = 2; i < cw - 2; i += 2) for (let j = 2; j < ch - 2; j += 2) {
          const ox = i - cw / 2, oy = j - ch / 2; if (Math.hypot(ox, oy) < cw * 0.24) continue;
          if (Math.abs(ox) < 2 * dpr || Math.abs(oy) < 2 * dpr) continue;
          const tx = Math.floor(d.from[0] + shift + (i + 0.5) / cw * d.from[2]), ty = Math.floor(d.from[1] + (j + 0.5) / ch * d.from[2]);
          if (tx < 0 || ty < 0 || tx >= tw || ty >= el.trace.height) continue;
          if (!inkAt(trace, tw, tx, ty)) continue;
          n++;
          // The crop is scaled up, so a stroke's edge can fall a pixel either side.
          let near = false;
          for (let a = -2; a <= 2 && !near; a++) for (let c = -2; c <= 2 && !near; c++) {
            const x = i + a, y = j + c; if (x >= 0 && y >= 0 && x < cw && y < ch && inkAt(cropImg, cw, x, y)) near = true; }
          if (near) hit++;
        }
        return [n, hit]; };
      const here = count(0), there = count(d.from[2]);
      /* And the window is the reticle's, as the reticle is placed on the
         screen (placeReticle): a crop that compared well with the trace but
         was cut from somewhere else passed the comparison above until the
         mutation pass, since the comparison reads the window the crop says. */
      const ret = el.photoReticle.getBoundingClientRect(), tr = el.trace.getBoundingClientRect();
      const centre = [((ret.left + ret.width / 2) - tr.left) * d.scale, ((ret.top + ret.height / 2) - tr.top) * d.scale];
      const window_ = [d.from[0] + d.from[2] / 2, d.from[1] + d.from[2] / 2];
      const graph = document.getElementById('photoGraph');
      const g = graph._drawn;
      const midInk = __inkAt(graph, g.w / 2);
      const out = { off, here, there, centre, window_, span: g.span, points: g.points, value: g.value, photo: photo.value,
                    now: document.getElementById('photoNow').textContent, midY: midInk.y, floor: g.h - 6 };
      el.photoButton.click(); await wait(4400); paintModLive();
      // Found afresh: the editor is built again as its source comes and goes.
      const after = document.getElementById('photoGraph');
      out.offMid = __inkAt(after, after._drawn.w / 2).y; out.offNow = document.getElementById('photoNow').textContent;
      return out;
    }""")
    print("    %s" % seen)
    check("the Photocell's editor holds its switch, and its drawings", seen["off"]["crop"] and seen["off"]["inEditor"] and seen["off"]["shown"],
          str(seen["off"]))
    check("its crop is the screen around the reticle: the trace's inked pixels there are inked in the crop",
          seen["here"][0] >= 20 and seen["here"][1] >= 0.9 * seen["here"][0], str(seen["here"]))
    null("the trace a crop's width to the right is not what the crop shows", seen["there"][0] == 0 or seen["there"][1] < 0.6 * seen["there"][0],
         str(seen["there"]))
    check("and it is cut around the reticle as the screen places it", abs(seen["centre"][0] - seen["window_"][0]) < 3
          and abs(seen["centre"][1] - seen["window_"][1]) < 3, "%s / %s" % (seen["centre"], seen["window_"]))
    check("its graph is the last four seconds, ending at its reading, which it says",
          3500 <= seen["span"] <= 4100 and seen["points"] > 60 and abs(seen["value"] - seen["photo"]) < 0.01 and seen["value"] > 0.1
          and seen["now"] == "%.2f" % seen["value"], str(seen))
    check("two seconds back it was reading the figure, above nought", seen["midY"] < seen["floor"] - 5, str(seen))
    null("switched off for four seconds, the same place on the graph is at nought, and it says off",
         abs(seen["offMid"] - seen["floor"]) < 2 and seen["offNow"] == "off", str(seen))
    p.locator("#modEditorClose").click(); p.wait_for_timeout(200)

    print("\n--- Routings ---")
    p.evaluate("""() => { state.modRoutings = []; touchRoutings();
      addRouting('lfo1', 'view.rotate'); addRouting('lfo1', 'gen.freq'); addRouting('lfo2', 'view.rotate'); }""")
    p.wait_for_timeout(300)
    p.locator("#routingsButton").click(); p.wait_for_timeout(300)
    by_source = p.evaluate("""() => [...el.routingsList.querySelectorAll('.route-group')].map((g) =>
      [g.dataset.source, [...g.querySelectorAll('.mod-edit')].map((r) => r.dataset.dest)])""")
    p.locator("#routingsByDest").click(); p.wait_for_timeout(200)
    by_dest = p.evaluate("""() => [...el.routingsList.querySelectorAll('.route-group')].map((g) =>
      [g.dataset.dest, [...g.querySelectorAll('.mod-edit')].map((r) => r.dataset.source)])""")
    print("    by source %s\n    by destination %s" % (by_source, by_dest))
    check("by source: the four cards, each with its routings",
          by_source == [["lfo1", ["view.rotate", "gen.freq"]], ["lfo2", ["view.rotate"]], ["env.note", []], ["photo.1", []]], str(by_source))
    check("by destination: each control with every source on it",
          by_dest == [["view.rotate", ["lfo1", "lfo2"]], ["gen.freq", ["lfo1"]]], str(by_dest))
    null("the two lists are not the same list", [x[1] for x in by_source[:2]] != [x[1] for x in by_dest])
    p.locator("#routingsBySource").click(); p.wait_for_timeout(200)

    # The silence: LFO 2 alone on the Turn, at full rate and depth, so the Turn moves by it alone.
    p.evaluate("""() => { state.modRoutings = state.modRoutings.filter((r) => r.sourceId !== 'lfo1'); touchRoutings();
      lfos[1].rate = 3; lfos[1].free = 3; state.modRoutings[0].amount = 0.5; touchRoutings(); }""")
    p.wait_for_timeout(400)
    TURNS = """async () => { const out = []; for (let i = 0; i < 12; i++) { out.push(state.rotateMod);
      await new Promise((r) => setTimeout(r, 50)); } return Math.max(...out.map(Math.abs)); }"""
    heard = p.evaluate(TURNS)
    code = p.evaluate("() => snapshot().mod")
    p.locator('[data-silence="lfo2"]').click(); p.wait_for_timeout(500)
    quiet = p.evaluate(TURNS)
    held = p.evaluate("""() => ({ heard: state.modRoutings.length, kept: routingsKept().map((r) => r.sourceId + '>' + r.destId + '@' + r.amount),
      code: snapshot().mod, told: hostSync.routings, switch: document.querySelector('[data-silence="lfo2"]').getAttribute('aria-checked'),
      card: el.modStrip.querySelector('[data-source="lfo2"]').dataset.silent !== undefined, count: el.routingsCount.textContent })""")
    p.locator('[data-silence="lfo2"]').click(); p.wait_for_timeout(500)
    back = p.evaluate(TURNS)
    after = p.evaluate("() => state.modRoutings.map((r) => r.sourceId + '>' + r.destId + '@' + r.amount)")
    print("    turning %.3f; silenced %.4f %s; back %.3f %s" % (heard, quiet, held, back, after))
    check("LFO 2 on the Turn moves it", heard > 0.05, "%.3f" % heard)
    check("switched off in Routings, the Turn is still", quiet < 0.002, "%.4f" % quiet)
    check("and the routing is kept: in the setup as it was, counted, its card marked silent, the switch off",
          held["heard"] == 0 and held["kept"] == ["lfo2>view.rotate@0.5"] and held["code"] == code and held["switch"] == "false"
          and held["card"] and held["count"] == "· 1", str(held))
    check("the instrument behind the page is told the routings heard, which are none", held["told"] == "", repr(held["told"]))
    check("switched on, it is back as it was and moving the Turn", after == ["lfo2>view.rotate@0.5"] and back > 0.05, "%s %.3f" % (after, back))
    null("silenced, the Turn did not move as it moves heard", quiet < heard / 10)
    forgot = p.evaluate("""() => { silenceSource('lfo2', true); const before = held.size; restore(decodeSetup(encodeSetup(snapshot())));
      return { before, after: held.size, heard: state.modRoutings.map((r) => r.sourceId) }; }""")
    check("a silence is forgotten when a setup is put back, and the setup's routings are heard",
          forgot == {"before": 1, "after": 0, "heard": ["lfo2"]}, str(forgot))
    patched = p.evaluate("""() => { silenceSource('lfo2', true); addRouting('lfo2', 'gen.freq');
      return { silenced: held.has('lfo2'), heard: state.modRoutings.map((r) => r.sourceId + '>' + r.destId) }; }""")
    check("patching a silenced source switches it back on", patched == {"silenced": False, "heard": ["lfo2>view.rotate", "lfo2>gen.freq"]},
          str(patched))

    print("\n--- the fade, in Routings ---")
    fade = p.evaluate("""() => ({ inRoutings: !!el.fadeMode.closest('#routingsPanel'), inSettings: !!el.fadeMode.closest('#menuPanel'),
      home: homeOf(el.fadeGroup) })""")
    p.select_option("#fadeMode", "both"); p.wait_for_timeout(200)
    chosen = p.evaluate("() => fade.mode")
    p.locator("#routingsClose").click(); p.wait_for_timeout(200)
    shown = p.evaluate("() => { showControl('fadeRestart'); return { open: !el.routingsPanel.hidden, seen: !!el.fadeRestart.offsetParent }; }")
    p.select_option("#fadeMode", "off"); p.wait_for_timeout(150)
    print("    %s; chosen %s; shown %s" % (fade, chosen, shown))
    check("the fade is in Routings and not in Settings", fade == {"inRoutings": True, "inSettings": False, "home": "routings"}, str(fade))
    check("chosen there, it is the page's fade", chosen == "both", chosen)
    check("and showing one of its controls opens Routings", shown == {"open": True, "seen": True}, str(shown))
    p.keyboard.press("Escape"); p.wait_for_timeout(200)
    check("Esc closes Routings", p.evaluate("() => el.routingsPanel.hidden && !routingsOpen"))

    print("\n--- chips, on the compact face and under 900 tall ---")
    chips = {}
    for w, h in ((1400, 900), (1400, 860), (1200, 680)):
        p.set_viewport_size({"width": w, "height": h}); p.wait_for_timeout(350)
        chips[(w, h)] = p.evaluate("""() => { const c = el.modStrip.querySelector('[data-source="lfo1"]'), cv = c.querySelector('canvas');
          return { chips: document.body.dataset.chips !== undefined, compact: document.body.dataset.compact !== undefined,
                   height: Math.round(el.modRow.getBoundingClientRect().height), drawing: [cv.clientWidth, cv.clientHeight] }; }""")
    print("    %s" % chips)
    check("at 1400x900 cards, each with its drawing", not chips[(1400, 900)]["chips"] and chips[(1400, 900)]["drawing"][1] == 36,
          str(chips[(1400, 900)]))
    check("under 900 tall, chips, each still with a small drawing of its shape, the row under 40 px",
          chips[(1400, 860)]["chips"] and not chips[(1400, 860)]["compact"] and chips[(1400, 860)]["drawing"] == [44, 16]
          and chips[(1400, 860)]["height"] <= 40 and chips[(1200, 680)]["chips"], str(chips))
    null("the cards' row is taller than the chips'", chips[(1400, 900)]["height"] > 2 * chips[(1400, 860)]["height"])

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the row, its drawings and Routings hold")
