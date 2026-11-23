"""The release switch (22 Nov): what the stable site holds back from the first
release for testers, decided in one place (RELEASE, the top of the page's
script). Paint is the one held back: the stable site has no Paint, and a setup
that names screenDraws: paint is drawn and heard on the trace there, while the
setup keeps saying paint, so the same code still paints on testing.

The page is served over http as Pages serves it, at the root (/web/scope.html,
the stable site) and under /testing/ (/testing/web/scope.html), from one
directory: the same file, told apart only by where it is. Each leg also opens
it from the disk, as every other suite does, which must show Paint.

What would go wrong, and what is checked for it, each with its null:

- the root showing Paint: the display switch's Paint button not rendered, and
  the switch's rendered buttons Y-T, X-Y and Spect. The null is the testing
  site and the file, where the button is rendered;
- a paint code painting at the root: a code made with screenDraws: paint,
  pasted into the browser's field and loaded with Paste, leaves the screen on
  the trace, the painting's canvas hidden, the instrument's own state (its
  scopeState code) on trace and its strokes not arriving. The null is the same
  code on testing, which paints by every one of those readings;
- the root rewriting the code: the setup the page saves after that load still
  says paint, so the code goes on painting on testing. The null is a code made
  with trace, which says trace - the reading is not a constant;
- something on the face still saying Paint at the root: every text the page
  can show - its text, the cheat sheet included, and its aria-labels and
  titles - is searched for paint or brush, and every one found must be inside
  something held back and not rendered; the info line's words for every
  control but Paint's own (CONTROL_WORDS) say neither; the line the
  Persistence knob says is the stable one; and the search finds nothing for
  paint. The nulls: the button let back out of its mark (data-paint-only
  taken off) is found, and the testing site's words do say Paint;
- the override: ?site=testing at the root shows Paint and ?site=stable on the
  file holds it back, so either can be looked at from anywhere.

Parallel: nothing is timed; the waits are for the instrument to start and its
strokes to arrive, and every reading is a value.
"""
import os, sys, threading, functools, re
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)                    # web/, which holds scope.html
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
ARGS = ["--autoplay-policy=no-user-gesture-required"]

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def null(name, red, detail=""):
    check("null: " + name, red, detail)

# /web/... and /testing/web/... are both web/, as Pages lays the two sites out.
class Site(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def translate_path(self, path):
        path = re.sub(r"^/testing(?=/)", "", path)
        path = re.sub(r"^/web(?=/)", "", path)
        return super().translate_path(path)
server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Site, directory=ART))
threading.Thread(target=server.serve_forever, daemon=True).start()
ROOT = "http://127.0.0.1:%d/web/scope.html" % server.server_address[1]
TESTING = "http://127.0.0.1:%d/testing/web/scope.html" % server.server_address[1]
FILE = "file://%s/scope.html" % ART

bad = []
def open_page(b, url):
    p = b.new_page(viewport={"width": 1400, "height": 900})
    p.on("pageerror", lambda e: bad.append(url + ": " + str(e)))
    p.goto(url); p.wait_for_timeout(2000)
    p.keyboard.press("Escape"); p.wait_for_timeout(200)
    return p

SWITCH = """() => ({ release: RELEASE, paintShown: !!el.drawPaint.offsetParent,
  buttons: Array.from(el.dispYT.parentElement.querySelectorAll('button')).filter((b) => b.offsetParent).map((b) => b.textContent.trim()) })"""

# A code that paints, made on the page from what is loaded: only screenDraws differs from it.
PAINT_CODE = """(draws) => encodeSetup(Object.assign({}, decodeSetup(encodeSetup(snapshot())), { screenDraws: draws, oscScan: 60 }))"""

# Load by the browser's field and Paste, the way a tester would, then read the face, the saved setup and the instrument.
LOAD = """async (code) => {
  el.presetCode.value = code; el.presetPaste.click();
  await new Promise((r) => setTimeout(r, 600));
  midiNoteOn(57, 100);
  await new Promise((r) => setTimeout(r, 600));
  const before = paintView.since;
  await new Promise((r) => setTimeout(r, 600));
  const core = decodeSetup((await scopeHost.call('scopeState')).code);
  // A code leaves out what is at its default, and trace is screenDraws' default.
  const field = (setup) => setup.screenDraws === undefined ? DEFAULTS.screenDraws : setup.screenDraws;
  return { draws: state.draws, kept: field(decodeSetup(encodeSetup(snapshot()))), snap: snapshot().screenDraws,
           canvas: !!(paintView.canvas && !paintView.canvas.hidden && paintView.canvas.offsetParent),
           bodyPaint: document.body.hasAttribute('data-paint'),
           core: field(core), strokes: paintView.since > before };
}"""

# Every text the page can show that says paint or brush, and whether something held back and unrendered holds it.
SAYS = """() => {
  const said = /paint|brush/i, out = [];
  const held = (node) => { for (let n = node; n && n.nodeType === 1; n = n.parentElement)
    if (n.hasAttribute('data-paint-only') && getComputedStyle(n).display === 'none') return true; return false; };
  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let t = walk.nextNode(); t; t = walk.nextNode()) {
    const host = t.parentElement;
    if (!host || /^(SCRIPT|STYLE|TEMPLATE)$/.test(host.tagName)) continue;
    if (said.test(t.textContent) && !held(host)) out.push(host.tagName + '#' + host.id + ': ' + t.textContent.trim().slice(0, 60));
  }
  for (const n of document.body.querySelectorAll('[aria-label], [title]')) {
    const words = (n.getAttribute('aria-label') || '') + ' ' + (n.getAttribute('title') || '');
    // The painting's own canvas: never shown while Paint is held (it is drawn only in Paint).
    if (n === paintView.canvas && n.hidden) continue;
    if (said.test(words) && !held(n)) out.push(n.tagName + '#' + n.id + ' label: ' + words.trim().slice(0, 60));
  }
  return out;
}"""
WORDS = """() => Object.entries(CONTROL_WORDS).filter(([k, v]) => k !== 'drawPaint' && /paint|brush/i.test(v.join(' '))).map(([k]) => k)"""
PERSISTENCE_LINE = """() => { sayInfo(el.scanMemory); return el.infoText.textContent; }"""
SEARCH = """() => searchFor('paint').map((r) => r.label)"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=ARGS)

    # --- the root, the stable site ---
    p = open_page(b, ROOT)
    s = p.evaluate(SWITCH)
    check("the root is the stable site and holds Paint back", s["release"] == {"stable": True, "paint": False}, str(s["release"]))
    check("the root's display switch has no Paint: Y-T, X-Y and Spect", not s["paintShown"] and s["buttons"] == ["Y–T", "X–Y", "Spect"],
          str(s))
    paint_code = p.evaluate(PAINT_CODE, "paint")
    trace_code = p.evaluate(PAINT_CODE, "trace")
    got = p.evaluate(LOAD, paint_code)
    check("a paint code at the root lands on the trace: the screen, the canvas and the body say trace",
          got["draws"] == "trace" and not got["canvas"] and not got["bodyPaint"], str(got))
    check("and the instrument hears trace: its own state says trace and it serves no strokes",
          got["core"] == "trace" and not got["strokes"], str(got))
    check("and the setup the page keeps still says paint, so the code still paints on testing", got["kept"] == "paint" and got["snap"] == "paint", str(got))
    got_t = p.evaluate(LOAD, trace_code)
    null("a trace code's setup says trace: the kept field is read, not a constant", got_t["kept"] == "trace" and got_t["snap"] == "trace", str(got_t))
    p.evaluate(LOAD, paint_code)
    p.evaluate("() => { const d = document.getElementById('helpDialog'); if (d && !d.open) d.showModal(); }")
    says = p.evaluate(SAYS)
    check("nothing the root can show says paint or brush, cheat sheet included, but what is held back", says == [], str(says[:6]))
    words = p.evaluate(WORDS)
    check("the root's info line words say neither, for every control but Paint's own", words == [], str(words))
    line = p.evaluate(PERSISTENCE_LINE)
    check("the Persistence knob says the stable line", line.startswith("How long a stroke takes to fade to half.") and "Paint" not in line, line)
    found = p.evaluate(SEARCH)
    check("the search finds nothing for paint at the root", found == [], str(found))
    # The null for SAYS: let the button out of its mark and it is found.
    p.evaluate("() => el.drawPaint.removeAttribute('data-paint-only')")
    says_null = p.evaluate(SAYS)
    null("the Paint button let out of its mark is found by the same search", any("drawPaint" in x for x in says_null), str(says_null[:3]))
    p.close()

    # --- the testing site, and the file ---
    for name, url in (("testing", TESTING), ("the file", FILE)):
        p = open_page(b, url)
        s = p.evaluate(SWITCH)
        null("%s shows Paint in the display switch" % name, s["release"]["paint"] and s["paintShown"] and s["buttons"][-1] == "Paint", str(s))
        got = p.evaluate(LOAD, paint_code)
        null("%s paints the root's code: the screen, the canvas, the instrument and its strokes" % name,
             got["draws"] == "paint" and got["canvas"] and got["bodyPaint"] and got["core"] == "paint" and got["strokes"], str(got))
        words = p.evaluate(WORDS)
        null("%s's words do say Paint (the words check can see it)" % name, len(words) >= 3, str(words))
        p.close()

    # --- the override ---
    p = open_page(b, ROOT + "?site=testing")
    s = p.evaluate(SWITCH)
    check("?site=testing at the root shows Paint", s["release"]["paint"] and s["paintShown"], str(s))
    p.close()
    p = open_page(b, FILE + "?site=stable")
    s = p.evaluate(SWITCH)
    check("?site=stable on the file holds Paint back", not s["release"]["paint"] and not s["paintShown"], str(s))
    p.close()

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

server.shutdown()
print()
print("%d failed" % len(fails) if fails else "all passed")
sys.exit(1 if fails else 0)
