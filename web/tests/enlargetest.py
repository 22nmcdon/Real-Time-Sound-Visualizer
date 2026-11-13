"""Enlarge (G4 of web/docs/the-face-second-pass.md): the screen on its own,
filling the window, and the header kept to one row.

What would go wrong, and what is checked for it:

- the button doing nothing, or Esc leaving the screen enlarged, or Esc taking
  the screen back when a panel over it was what it should have closed: the
  button is pressed with the mouse and Esc with the keyboard, and the frame,
  the sheet's parent and the sheet's size are read. The null is the face
  before the press, where the sheet is in its column and the frame not drawn;
- Picture only hiding nothing, or something it should not: the reticle, the
  loop overlay, the hand's mark, the verdict and the panes are read as
  elements, and what is drawn into the trace - the graticule, its labels, the
  trigger's marks - as ink on the canvas away from the trace, on a screen
  that is cleared every frame so only this frame's ruling is there. Each with
  its null: Picture only off, where all of it is back;
- hiding them changing the sound. On the site's instrument, which draws and
  reads its own grid in the core from the lanes it plays, nothing the face
  shows reaches what is heard unless the face sends it: so Picture only,
  Enlarge and Which hands are pressed by hand with every message to the
  instrument counted, and must send none. The null is a knob turned the same
  way, which sends one. (Until stage 5's step 3, 13 Nov, this was read on
  the page's own brain, ?brain=js, where the grid the page drew was the one
  Scan read: the grid compared to the bit with Picture only on and off and
  with Which hands on one hand and on both, and Scan's table to the drift
  of a settled path, with a step of zoom as the null. On the default page
  that grid is the face's own copy, fed from the instrument's lanes, which
  nothing heard reads; comparing it would pass and say nothing about the
  sound, so it went.);
- the Trail touching the grid, or not shortening what is seen: a figure is
  drawn and taken off the screen, and the canvas's deep ink and the grid's
  light are read ten frames apart at As heard, Half and Short, and on the
  face with Half chosen. The grid's fade a frame is the Persistence's at all
  of them; the canvas's is the grid's at As heard and on the face, its square
  at Half, Short's or faster at Short. The nulls: the grid's fade is not
  Half's, and Half's canvas does not fade as the grid does. On the default
  page since stage 5's step 3 (13 Nov): the grid is the page's own, fed from
  the instrument's lanes, the face's reference for the Persistence and what
  its read bars and photocell show - no longer what Scan reads, which is the
  instrument's own and which the Trail cannot reach (the message count above);
- opening or closing wiping that grid's light, as any resize does: light left
  by a figure taken off the screen goes on fading at the Persistence across
  both. The null is Clear, which wipes it;
- Which hands drawing the wrong figure, or both: a split with each hand's
  figure in its ink, and each ink counted on the canvas at Both, A and B; and
  sending the instrument nothing as it is pressed;
- the panes not where the design puts them: beside the enlarged screen with
  Picture only off, and nowhere on the face or with Picture only on;
- Enlarge at the plugin's minimum window (960x600 at Auto's 90): the screen
  and the panes inside the window, nothing scrolling;
- a step in undo, or anything remembered: every press made with the real
  mouse and keys, which undo counts as a hand, and the history read after.
  The null is a key press on a knob, which is a step;
- the header on two rows before any sound has started, at 1920x1080, 1400x900
  and the plugin's minimum, with the line that says "press anything to hear
  it" under the title. The null is the same header made to wrap.

Serial: the Trail and the light kept are read over real frames of fading.
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

def open_page(b, w, h, query=""):
    p = b.new_page(viewport={"width": w, "height": h})
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html{query}"); p.wait_for_timeout(1500)
    # Closed by code, not a click: a press is what starts the sound, and the
    # header is read before any.
    p.evaluate("() => { const d = document.getElementById('helpDialog'); if (d && d.open) d.close(); }")
    p.wait_for_timeout(150)
    return p

# Where the screen is and how big, and whether the frame is drawn.
WHERE = """() => { const r = el.traceSheet.getBoundingClientRect();
  return { on: enlarge.on, attr: document.body.dataset.enlarged !== undefined, parent: el.traceSheet.parentElement.id,
           frame: getComputedStyle(el.screenFrame).display, w: Math.round(r.width), h: Math.round(r.height),
           pressed: el.enlargeButton.getAttribute('aria-pressed') }; }"""

# Whether each overlay element is on show: laid out, and not display: none.
SHOWN = """() => { const seen = (n) => !!n && n.getClientRects().length > 0 && getComputedStyle(n).display !== 'none';
  return { reticle: seen(el.photoReticle), loop: seen(el.loopOverlay), mark: seen(document.getElementById('bendMark')),
           verdict: seen(el.verdict), panes: seen(el.aside) }; }"""

# Ink on the canvas away from the trace: pixels off the paper, outside a band
# round the trace (the middle row in Y-T, a disc at the centre in X-Y, where
# a beam at nought amplitude sits).
INK_OFF_TRACE = """() => {
  const c = el.trace, ctx = c.getContext('2d'), k = c.width / c.clientWidth;
  const d = ctx.getImageData(0, 0, c.width, c.height).data;
  const paper = getComputedStyle(document.documentElement).getPropertyValue('--paper').trim();
  const n = parseInt(paper.slice(1), 16), pr = (n >> 16) & 255, pg = (n >> 8) & 255, pb = n & 255;
  const cx = (plot.x + plot.w / 2) * k, cy = (plot.y + plot.h / 2) * k, keep = 8 * k;
  const yt = state.display === 'yt';
  // Y-T's lanes at rest: the middle of each band when stacked, of the plot when overlaid.
  const bands = yt && stacked() ? laneCount() : 1;
  const rests = Array.from({ length: bands }, (_, i) => (plot.y + (i + 0.5) * plot.h / bands) * k);
  let inked = 0;
  for (let y = 0; y < c.height; y++) for (let x = 0; x < c.width; x++) {
    if (yt ? rests.some((r) => Math.abs(y - r) < keep) : Math.hypot(x - cx, y - cy) < keep) continue;
    const i = (y * c.width + x) * 4;
    if (Math.abs(d[i] - pr) + Math.abs(d[i + 1] - pg) + Math.abs(d[i + 2] - pb) > 24) inked++;
  }
  return inked;
}"""

bad = []
with sync_playwright() as pw:
    # Without the autoplay switch the rest of the suite runs with: with it, the
    # sound starts as the page opens and the line never says to press anything.
    quiet = pw.chromium.launch(executable_path=CHROME)
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])

    print("\n--- the header is one row before any sound ---")
    ROW = """() => { const r = (e) => e.getBoundingClientRect();
      const items = Array.from(document.querySelector('.head').children).filter((e) => r(e).height > 0);
      const mids = items.map((e) => r(e).top + r(e).height / 2);
      return { spread: Math.round(Math.max(...mids) - Math.min(...mids)), credit: el.credit.textContent,
               shown: el.credit.offsetWidth > 0, help: Math.round(r(el.helpButton).top), settings: Math.round(r(el.menuButton).top),
               title: Math.round(r(document.querySelector('.sheet-title')).top) }; }"""
    for w, h in ((1920, 1080), (1400, 900), (960, 600)):
        p = open_page(quiet, w, h)
        row = p.evaluate(ROW)
        waiting = "press anything" in row["credit"]
        # On the compact face (960x600) the line is hidden on purpose and the status says it instead.
        check("at %dx%d, before a sound, the header is one row%s" % (w, h, ", the line under the title on show" if row["shown"] else ""),
              waiting and row["spread"] <= 12 and (row["shown"] or (w, h) == (960, 600)), str(row))
        if (w, h) == (1920, 1080):
            # The null: the same header allowed to wrap, with something wide in it, is two rows.
            wrapped = p.evaluate("""(read) => { const head = document.querySelector('.head'), s = document.createElement('span');
              s.style.cssText = 'display:inline-block;width:1700px;height:10px'; head.style.flexWrap = 'wrap'; head.appendChild(s);
              const r = (0, eval)('(' + read + ')')(); s.remove(); head.style.flexWrap = ''; return r; }""", ROW)
            null("the same header made to wrap is two rows", wrapped["spread"] > 12, str(wrapped))
        p.close()
    quiet.close()

    print("\n--- Enlarge opens, and Esc brings it back ---")
    p = open_page(b, 1400, 900)
    def is_big(r):
        return (r["on"] and r["attr"] and r["parent"] == "panes" and r["frame"] != "none"
                and r["w"] > 1300 and r["h"] > 780 and r["pressed"] == "true")
    face = p.evaluate(WHERE)
    null("on the face, before the press, the same check fails: the screen in its column, the frame not drawn",
         not is_big(face), str(face))
    p.locator("#enlargeButton").click(); p.wait_for_timeout(300)
    big = p.evaluate(WHERE)
    check("the button fills the window with the screen", is_big(big), str(big))
    # A panel over the screen is closed by the first Esc, and the screen by the next.
    p.locator("#measureButton").click(); p.wait_for_timeout(200)
    p.keyboard.press("Escape"); p.wait_for_timeout(200)
    one = p.evaluate("() => ({ panel: !el.measurePanel.hidden, on: enlarge.on })")
    p.keyboard.press("Escape"); p.wait_for_timeout(300)
    two = p.evaluate(WHERE)
    check("Esc with Scope & measure open closes the panel and stays enlarged", one == {"panel": False, "on": True}, str(one))
    check("and the next Esc brings the face back, the screen in its column", not two["on"] and not two["attr"]
          and two["parent"] == "benchScope" and two["frame"] == "none" and two["pressed"] == "false", str(two))
    p.locator("#enlargeButton").click(); p.wait_for_timeout(250)
    p.locator("#enlargeButton").click(); p.wait_for_timeout(250)
    again = p.evaluate(WHERE)
    check("and the button pressed again does the same", not again["on"] and again["parent"] == "benchScope", str(again))

    print("\n--- Picture only ---")
    # Everything that can be over the trace, put there: the photocell's
    # reticle, the loop overlay, the hand's mark, the verdict, and a pane.
    # The setup first, since a setup carries the photocell's switch.
    p.evaluate("""() => { hostQuietly(() => restore({ display: 'xy', persistence: 0 })); hostSendSetup();
      setPhoto(true); setLoopOverlay(true); el.goniOn.checked = true; el.goniOn.dispatchEvent(new Event('change'));
      const a = document.getElementById('amp'); a.value = '0'; a.dispatchEvent(new Event('input', { bubbles: true })); }""")
    p.locator("#enlargeButton").click(); p.wait_for_timeout(300)
    p.evaluate("() => bendMarkAt([200, 200])")
    p.wait_for_timeout(500)
    bare = p.evaluate(SHOWN); bare_ink = p.evaluate(INK_OFF_TRACE)
    p.locator("#pictureOnly").click(); p.wait_for_timeout(500)
    p.evaluate("() => bendMarkAt([200, 200])")
    full = p.evaluate(SHOWN); full_ink = p.evaluate(INK_OFF_TRACE)
    check("Picture only is on as Enlarge opens, and hides the reticle, the loop, the hand's mark, the verdict and the panes",
          not any(bare.values()), str(bare))
    null("with it off every one of them is on show", all(full.values()), str(full))
    check("and nothing is drawn into the X-Y screen but the trace: no graticule, no edge, no axis names",
          bare_ink == 0, "%d pixels" % bare_ink)
    null("with it off the ruling and the names are there", full_ink > 2000, "%d pixels" % full_ink)
    # Y-T, with the trigger's level and mark and the time and amplitude labels.
    p.evaluate("() => { setDisplay('yt'); }"); p.wait_for_timeout(400)
    yt_full = p.evaluate(INK_OFF_TRACE)
    p.locator("#pictureOnly").click(); p.wait_for_timeout(400)
    yt_bare = p.evaluate(INK_OFF_TRACE)
    check("nor into the Y-T screen: no graticule, labels, or trigger mark", yt_bare == 0, "%d pixels" % yt_bare)
    null("with it off they are there", yt_full > 2000, "%d pixels" % yt_full)
    p.keyboard.press("Escape"); p.wait_for_timeout(300)
    onface = p.evaluate(SHOWN)
    check("and on the face, the overlays are its own again, and the panes are not shown",
          onface["reticle"] and onface["loop"] and onface["verdict"] and not onface["panes"], str(onface))
    p.evaluate("() => { setPhoto(false); setLoopOverlay(false); bendMarkAt(null); }")

    print("\n--- the panes, beside the enlarged screen ---")
    PANES = """() => { const s = el.traceSheet.getBoundingClientRect(), a = el.aside.getBoundingClientRect();
      const doc = document.scrollingElement;
      return { shown: a.width > 0 && getComputedStyle(el.aside).display !== 'none', beside: a.left >= s.right - 1,
               inside: s.left >= 0 && s.top >= 0 && a.right <= innerWidth + 1 && a.bottom <= innerHeight + 1 && s.bottom <= innerHeight + 1,
               scrolls: doc.scrollHeight > innerHeight + 1 || doc.scrollWidth > innerWidth + 1, w: Math.round(s.width), h: Math.round(s.height) }; }"""
    for w, h in ((1400, 900), (960, 600)):
        p.set_viewport_size({"width": w, "height": h}); p.wait_for_timeout(400)
        if (w, h) == (960, 600):
            zoom = p.evaluate("() => pageZoom")
            check("the plugin's minimum window is at Auto's 90", zoom == 0.9, str(zoom))
        p.locator("#enlargeButton").click(); p.wait_for_timeout(300)
        p.locator("#pictureOnly").click(); p.wait_for_timeout(300)
        panes = p.evaluate(PANES)
        p.locator("#pictureOnly").click(); p.wait_for_timeout(300)
        hidden = p.evaluate(PANES)
        check("at %dx%d, Picture only off, the panes are beside the enlarged screen, all of it inside the window and nothing scrolling" % (w, h),
              panes["shown"] and panes["beside"] and panes["inside"] and not panes["scrolls"] and panes["w"] > 400, str(panes))
        check("at %dx%d, with Picture only on, they are not shown and the screen is inside the window" % (w, h),
              not hidden["shown"] and hidden["inside"] and not hidden["scrolls"], str(hidden))
        p.keyboard.press("Escape"); p.wait_for_timeout(300)
    p.set_viewport_size({"width": 1400, "height": 900}); p.wait_for_timeout(300)

    print("\n--- not a step in undo, and not remembered ---")
    p.evaluate("() => { undoHistory.undo = []; undoHistory.redo = []; undoRebase(); paintUndo(); }")
    p.wait_for_timeout(600)
    stored = p.evaluate("() => Object.keys(localStorage).sort()")
    p.locator("#enlargeButton").click(); p.wait_for_timeout(200)
    p.locator("#pictureOnly").click(); p.wait_for_timeout(200)
    p.locator("#enlargeTrail").select_option("half"); p.wait_for_timeout(200)
    p.locator("#pictureOnly").click(); p.wait_for_timeout(200)
    p.keyboard.press("Escape"); p.wait_for_timeout(900)
    after = p.evaluate("() => ({ undo: undoHistory.undo.length, keys: Object.keys(localStorage).sort() })")
    check("Enlarge, Picture only, the Trail and Esc, by hand, are no step in undo", after["undo"] == 0, str(after))
    check("and leave nothing in the browser's storage", after["keys"] == stored, "%s -> %s" % (stored, after["keys"]))
    p.evaluate("() => { showControl('freq'); el.freq.focus(); }")
    p.keyboard.press("ArrowUp"); p.wait_for_timeout(900)
    null("a knob turned by a key is a step, so the history is being kept",
         p.evaluate("() => undoHistory.undo.length") == 1, str(p.evaluate("() => undoHistory.undo.length")))
    p.close()

    # --- what is heard: nothing the face only shows reaches the instrument --
    print("\n--- hiding sends the instrument nothing ---")
    p = open_page(b, 1400, 900)
    # Every message the face sends the instrument, counted: the host's calls
    # (sliders, setups, menus, switches, clicks, routings, the fade) and MIDI.
    # The state read back is a question, not a message, and is not counted.
    p.evaluate("""() => {
      window.__sent = [];
      const call = scopeHost.call, midi = scopeHost.midi;
      scopeHost.call = function (name, ...a) { if (name !== 'scopeState' && name !== 'scopeHost') __sent.push(name + ' ' + a[0]); return call.apply(this, [name, ...a]); };
      scopeHost.midi = function (bytes, at) { __sent.push('midi ' + Array.from(bytes).join(',')); return midi.apply(this, [bytes, at]); };
    }""")
    SENT = "() => __sent.splice(0)"
    p.evaluate("() => { midiPanic(); el.midiMono.click(); midiNoteOn(57, 127); }"); p.wait_for_timeout(800)
    p.evaluate(SENT)
    p.locator("#enlargeButton").click(); p.wait_for_timeout(300)
    p.locator("#pictureOnly").click(); p.wait_for_timeout(300)
    p.locator("#pictureOnly").click(); p.wait_for_timeout(300)
    p.locator("#enlargeTrail").select_option("short"); p.wait_for_timeout(200)
    p.locator("#enlargeTrail").select_option("heard"); p.wait_for_timeout(200)
    p.keyboard.press("Escape"); p.wait_for_timeout(300)
    hid = p.evaluate(SENT)
    check("Enlarge, Picture only and the Trail, pressed by hand, send the instrument nothing", hid == [], str(hid))
    p.evaluate("() => { showControl('freq'); el.freq.focus(); }")
    p.keyboard.press("ArrowUp"); p.wait_for_timeout(300)
    turned = p.evaluate(SENT)
    null("a knob turned by a key sends it something, so the count is being kept", len(turned) > 0, str(turned[:3]))

    print("\n--- the Trail fades the screen and not the grid ---")
    # Long (0.04 a frame), read over about ten frames from the moment the
    # figure is taken off the screen: both lanes offset fifty full scales, so
    # from the next frame nothing is drawn or laid into the grid at all, and
    # both fade untouched. (Sending the beam to the middle with the level was
    # the first way; the figure shrinking there inked part of what was read,
    # and the canvas read about 0.008 a frame slow.) The canvas is read where
    # the figure had inked it deeply, so its fade is measured above the
    # eight-bit floor a long fade stalls at (washtest.py), and away from the
    # edge of the square; the graticule is off, so on the face nothing but
    # the figure is in the plot. Eight bits fade a little slower than the
    # arithmetic - a step of 0.04 of a pixel's distance from the paper is
    # rounded, and at 0.04 a frame that reads as 0.965 where the grid's is
    # 0.96 - so the canvas is held to its fade within 0.008, and Half to
    # its square within 0.012, which still leaves the two 0.02 apart.
    TRAIL = """async ([trail, enlarged]) => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setEnlarged(enlarged); await wait(400);
      midiPanic();
      hostQuietly(() => restore({ shape: 'sine', freq: 220, interval: 7, just: false, display: 'xy',
                                   persistence: 0.04, pictureAmount: 0, oscScan: 0, graticule: false })); hostSendSetup();
      el.midiMono.click(); midiNoteOn(57, 127);   // held, as above
      enlarge.trail = trail; enlarge.pictureOnly = true; paintEnlarge();
      const amp = document.getElementById('amp');
      amp.value = '55'; amp.dispatchEvent(new Event('input', { bubbles: true }));
      wipeScreen = true; await wait(1500);
      const c = el.trace, ctx = c.getContext('2d'), k = c.width / c.clientWidth;
      const x0 = Math.round(plot.x * k), y0 = Math.round(plot.y * k), w = Math.round(plot.w * k), h = Math.round(plot.h * k);
      const paper = getComputedStyle(document.documentElement).getPropertyValue('--paper').trim();
      const n = parseInt(paper.slice(1), 16), pr = (n >> 16) & 255, pg = (n >> 8) & 255, pb = n & 255;
      const off = (d, i) => Math.max(0, pr - d[i]) + Math.max(0, pg - d[i + 1]) + Math.max(0, pb - d[i + 2]);
      const light = () => { let sum = 0; for (const v of phosphor.grid) sum += v; return sum; };
      // Read before the next frame, which is the first drawn with the figure off the screen.
      for (const ch of state.channels) ch.offset = 50;
      const d0 = ctx.getImageData(x0, y0, w, h).data, c0 = phosphor.frames, g0 = light();
      const deep = [], edge = Math.round(5 * k);
      for (let y = edge; y < h - edge; y++) for (let x = edge; x < w - edge; x++) {
        const i = (y * w + x) * 4;
        if (off(d0, i) > 150) deep.push(i);
      }
      await wait(160);
      const d1 = ctx.getImageData(x0, y0, w, h).data, c1 = phosphor.frames, g1 = light();
      let s0 = 0, s1 = 0;
      for (const i of deep) { s0 += off(d0, i); s1 += off(d1, i); }
      for (const ch of state.channels) ch.offset = 0;
      enlarge.trail = 'heard'; paintEnlarge(); setEnlarged(false);
      const fades = c1 - c0;
      return { fades, deep: deep.length, grid: Math.pow(g1 / g0, 1 / fades), canvas: Math.pow(s1 / s0, 1 / fades) };
    }"""
    got = {t: p.evaluate(TRAIL, [t, True]) for t in ("heard", "half", "short")}
    got["face"] = p.evaluate(TRAIL, ["half", False])
    for t, r in got.items():
        print("    %-6s %d fades over %d deep pixels: the grid keeps %.4f a frame, the canvas %.4f"
              % (t, r["fades"], r["deep"], r["grid"], r["canvas"]))
    for t in ("heard", "half", "short"):
        check("at %s the grid fades by the Persistence, 0.96 a frame" % t, abs(got[t]["grid"] - 0.96) < 0.001, "%.4f" % got[t]["grid"])
    null("the grid's fade is not what Half does to the canvas, 0.9216", abs(got["half"]["grid"] - 0.9216) > 0.01, "%.4f" % got["half"]["grid"])
    check("As heard, the canvas fades as the grid does", abs(got["heard"]["canvas"] - got["heard"]["grid"]) < 0.008
          and got["heard"]["deep"] > 300, "%.4f against %.4f" % (got["heard"]["canvas"], got["heard"]["grid"]))
    check("Half fades it by the square, 0.9216 a frame: half the half-life", abs(got["half"]["canvas"] - 0.9216) < 0.012,
          "%.4f" % got["half"]["canvas"])
    null("Half's canvas does not fade as the grid does", abs(got["half"]["canvas"] - got["half"]["grid"]) > 0.02,
         "%.4f against %.4f" % (got["half"]["canvas"], got["half"]["grid"]))
    check("Short fades it at the Persistence menu's Short or faster: 0.7 a frame at most", got["short"]["canvas"] < 0.75,
          "%.4f" % got["short"]["canvas"])
    # And the Trail is Enlarge's alone: Half chosen, read on the face, which fades as heard.
    check("on the face a Trail chosen does nothing: the canvas fades as the grid does",
          abs(got["face"]["canvas"] - got["face"]["grid"]) < 0.008 and abs(got["face"]["grid"] - 0.96) < 0.003,
          "%.4f against %.4f" % (got["face"]["canvas"], got["face"]["grid"]))

    print("\n--- opening and closing keep the grid's light ---")
    # Opening resizes the canvas, and a resized canvas is wiped. The grid is
    # not: a figure taken off the screen leaves light that only fades, and
    # across Enlarge opening and then closing it goes on fading at the
    # Persistence. The null is Clear, which does wipe it.
    KEEP = """async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      setEnlarged(false);
      hostQuietly(() => restore({ shape: 'sine', freq: 220, interval: 7, just: false, display: 'xy',
                                   persistence: 0.04, pictureAmount: 0, oscScan: 0 })); hostSendSetup();
      await wait(1500);
      const light = () => { let sum = 0; for (const v of phosphor.grid) sum += v; return sum; };
      for (const ch of state.channels) ch.offset = 50;
      await wait(100);
      const out = [];
      for (const step of [() => setEnlarged(true), () => setEnlarged(false), () => { wipeScreen = true; }]) {
        const s0 = light(), f0 = phosphor.frames;
        step(); await wait(300);
        out.push({ kept: light() / s0, fades: phosphor.frames - f0, sheet: el.traceSheet.parentElement.id });
      }
      for (const ch of state.channels) ch.offset = 0;
      return out;
    }"""
    kept = p.evaluate(KEEP)
    for (name, r) in zip(("opening", "closing"), kept[:2]):
        want = 0.96 ** r["fades"]
        check("%s Enlarge, the light goes on fading at the Persistence: %.3f kept over %d frames, where %.3f is" % (name, r["kept"], r["fades"], want),
              abs(r["kept"] - want) < 0.02 and r["kept"] > 0.05, str(r))
    null("Clear wipes it", kept[2]["kept"] < 1e-6, str(kept[2]))

    print("\n--- Which hands ---")
    SPLIT = """async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      hostQuietly(() => restore({ shape: 'sine', display: 'xy', persistence: 0, pictureAmount: 0, oscScan: 0, beam: 'off' })); hostSendSetup();
      /* Poly by its button, which the instrument hears (setMidiMode, the
         page's call this used on ?brain=js, it does not: it stayed in the
         Mono clicked above and drew no upper hand). The split at the
         default's 60. The two hands' levels and temperament were set on the
         page's own generator; they never reached the instrument, and the
         inks below need neither. */
      midiPanic(); setScreenKeys(true); el.midiPoly.click();
      el.midiLayers.value = 'split'; el.midiLayers.dispatchEvent(new Event('change'));
      for (const n of [48, 55, 72, 79]) midiNoteOn(n, 100);
      await wait(1500);
      // Whether each hand draws its own figure: the instrument's reading (each
      // layer's picture), where it was the page's own layerPictures.live.
      const layers = state.source.layerPictures;
      return { figures: (sourceFigures() || []).length, live: !!(layers && layers.live), inks: [figureInk(0, 0), figureInk(1, 2)] };
    }"""
    split = p.evaluate(SPLIT)
    check("a split draws a figure for each hand, in two inks", split["figures"] == 2 and split["live"]
          and split["inks"][0] != split["inks"][1], str(split))
    offered_face = p.evaluate("() => !el.handsField.hidden")
    p.locator("#enlargeButton").click(); p.wait_for_timeout(600)
    offered = p.evaluate("() => !el.handsField.hidden")
    check("Which hands is offered in Enlarge while there are two figures, and not on the face", offered and not offered_face,
          "%s / %s" % (offered, offered_face))
    INKS = """(inks) => {
      const c = el.trace, ctx = c.getContext('2d'), d = ctx.getImageData(0, 0, c.width, c.height).data;
      const rgb = inks.map((name) => { const n = parseInt(ink[name].slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; });
      const count = rgb.map(() => 0);
      for (let i = 0; i < d.length; i += 4) rgb.forEach(([r, g, b], k) => {
        if (Math.abs(d[i] - r) + Math.abs(d[i + 1] - g) + Math.abs(d[i + 2] - b) < 30) count[k]++; });
      return count;
    }"""
    counts = {}
    for hands in ("handsBoth", "handsA", "handsB"):
        p.locator("#" + hands).click(); p.wait_for_timeout(400)
        counts[hands] = p.evaluate(INKS, split["inks"])
    print("    pixels of A's ink and B's: %s" % counts)
    check("A draws A's figure and none of B's", counts["handsA"][0] > 200 and counts["handsA"][1] < 10, str(counts["handsA"]))
    check("B draws B's figure and none of A's", counts["handsB"][1] > 200 and counts["handsB"][0] < 10, str(counts["handsB"]))
    null("Both draws both", counts["handsBoth"][0] > 200 and counts["handsBoth"][1] > 200, str(counts["handsBoth"]))
    # And what Scan reads is both, whichever is drawn: on the site's
    # instrument, Which hands sends it nothing. (On ?brain=js until 13 Nov the
    # page's grid and each hand's were compared to the bit with B alone drawn
    # and with both, a step of zoom the null; see the top.)
    p.evaluate(SENT)
    for hands in ("handsA", "handsB", "handsBoth"):
        p.locator("#" + hands).click(); p.wait_for_timeout(200)
    picked = p.evaluate(SENT)
    check("Which hands, pressed through A, B and Both, sends the instrument nothing", picked == [], str(picked))
    p.close()

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails))
sys.exit(1 if fails else 0)
