"""The page in WebKit (22 Nov, the first release for testers): every other
suite runs Chromium, and testers on a Mac will often open the site in
Safari. Playwright's WebKit cannot be fetched here (the environment's network
refuses its download hosts, web/README.md); WebKitGTK, the plugin's web view
on Linux, is installed, and is Safari's engine - WebKit and JavaScriptCore,
its Web Audio and its AudioWorklet - without Safari's shell or the Mac's
audio. webkit_page.py drives it under xvfb-run; this reads what it answers.

The site is served over http as Pages serves it: the root (the stable site,
Paint held back) at 1400x900 and 1100x680, and /testing/ at 1400x900, where
Paint is pressed too. Autoplay is refused, as Safari refuses it, so the sound
starts only on a real press.

What would go wrong, and what is checked for it, each with its null:

- the engine not being WebKit after all: its user agent names AppleWebKit and
  not Chrome;
- errors unseen: no error, unhandled rejection, console.error or warn from
  the page's first script to the last step. The null: a console.error made
  on purpose at the start is caught by the same net;
- the sound not starting, or starting on its own: before any press the
  instrument is not running; after one real click on the title (which plays
  nothing) the AudioWorklet runs the compiled core - the host's `running`,
  which is the worklet's ready and the context running, not the main-thread
  stand-in - with no fault. The null is the reading before the click;
- the sound not reaching the screen: a dyad played, and the picture's lanes
  carry it and the trace has more ink. The null is the same readings before
  the note, where the lanes are silent;
- the layout not fitting: no tab of the Bench scrolls and the page has no
  scroll either way, on each of the three tabs; Scope & measure, the preset
  browser and Settings each open, and Scope & measure and Settings do not
  scroll. The null: the same measure with a tall block put in the Bench finds
  it over - one that will not shrink, since the Bench is a flex box and a plain
  3000 px block was squeezed to fit it and read nought, the first try;
- Paint in WebKit (testing only): pressed, it paints on the graphics card or
  draws the map plain, and says which, with no error.

Parallel: the waits are for the page and its sound, and no reading is a time.
"""
import functools, json, os, re, shutil, subprocess, sys, tempfile, threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
PY = os.environ.get("WEBKIT_PYTHON", "/usr/bin/python3.12")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def null(name, red, detail=""):
    check("null: " + name, red, detail)

# A check that cannot run is not a pass: say what is missing and fail.
have = shutil.which("xvfb-run") and os.path.exists(PY) and subprocess.run(
    [PY, "-c", "import gi; gi.require_version('WebKit2', '4.1'); from gi.repository import WebKit2"],
    capture_output=True).returncode == 0
if not have:
    check("WebKitGTK 4.1, its GObject bindings for %s and xvfb-run are here" % PY, False,
          "install libwebkit2gtk-4.1, gir1.2-webkit2-4.1, python3-gi and xvfb, or set WEBKIT_PYTHON")
    sys.exit(1)

class Site(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def translate_path(self, path):
        return super().translate_path(re.sub(r"^/web(?=/)", "", re.sub(r"^/testing(?=/)", "", path)))
server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Site, directory=ART))
threading.Thread(target=server.serve_forever, daemon=True).start()
PORT = server.server_address[1]

COMMON = r"""
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const ink = () => { const c = document.getElementById('trace'), k = document.createElement('canvas'); k.width = c.width; k.height = c.height;
  const g = k.getContext('2d'); g.drawImage(c, 0, 0); const d = g.getImageData(0, 0, k.width, k.height).data;
  let n = 0; for (let i = 0; i < d.length; i += 4) if (Math.abs(d[i] - d[0]) + Math.abs(d[i + 1] - d[1]) + Math.abs(d[i + 2] - d[2]) > 60) n++; return n; };
const peak = () => { const lanes = state.source.getLatestWindow(Math.round(state.source.sampleRate / 4)); let p = 0;
  for (const l of lanes) for (let i = 0; i < l.length; i++) p = Math.max(p, Math.abs(l[i])); return p; };
const sound = () => ({ running: !!scopeHost.running, fault: state.source.fault || el.genFault.textContent || '', peak: peak(), ink: ink() });
const over = () => ({ page: Math.max(document.documentElement.scrollWidth - innerWidth, document.documentElement.scrollHeight - innerHeight),
  bench: el.benchBody.scrollHeight - el.benchBody.clientHeight });
"""

def steps(paint, shot):
    out = [
        ["js", COMMON + """const t = document.querySelector('.sheet-title').getBoundingClientRect();
          const before = sound(); console.error('webkittest: the null'); const caught = __errs.slice(); __errs.length = 0;
          return { ua: navigator.userAgent, release: RELEASE, before, caught, title: [t.x + t.width / 2, t.y + t.height / 2] };"""],
        ["click", None],   # the title's middle, filled in from the first step's answer
        ["js", COMMON + "await wait(2500); return sound();"],
        ["js", COMMON + "midiNoteOn(57, 100); midiNoteOn(64, 100); await wait(1500); return sound();"],
        ["js", COMMON + """const tabs = {}; for (const tab of ['play', 'ink', 'space', 'play']) { setBenchTab(tab); await wait(400); tabs[tab] = over(); }
          const tall = document.createElement('div'); tall.style.cssText = 'flex: 0 0 3000px; min-height: 3000px; width: 100%'; el.benchBody.appendChild(tall); await wait(100);
          const crowded = over(); tall.remove(); return { tabs, crowded };"""],
        ["js", COMMON + """el.measureButton.click(); await wait(500);
          const measure = { open: !el.measurePanel.hidden, over: el.measurePanel.scrollHeight - el.measurePanel.clientHeight, page: over().page };
          el.measureButton.click(); await wait(300);
          el.preset.click(); await wait(800); const presets = { open: el.presetDialog.open }; el.presetClose.click(); await wait(300);
          const panel = document.getElementById('menuPanel'); el.menuButton.click(); await wait(500);
          const settings = { open: !panel.hidden, over: panel.scrollHeight - panel.clientHeight }; el.menuButton.click(); await wait(300);
          return { measure, presets, settings };"""],
    ]
    if paint:
        out.append(["js", COMMON + "el.drawPaint.click(); await wait(1500); return { draws: state.draws, mode: paintView.mode };"])
    if shot:
        out.append(["shot", shot])
    out.append(["js", "return __errs.slice();"])
    return out

def drive(url, w, h, paint=False, shot=None):
    with tempfile.TemporaryDirectory() as tmp:
        # The title's place is known only once the page is laid out: a first run asks, the second clicks there.
        first = run_steps(url, w, h, steps(paint, shot)[:1], tmp)
        plan = steps(paint, shot)
        plan[1] = ["click", first[0]["title"]]
        return run_steps(url, w, h, plan, tmp)

def run_steps(url, w, h, plan, tmp):
    path = os.path.join(tmp, "steps.json")
    with open(path, "w") as f: json.dump(plan, f)
    done = subprocess.run(["xvfb-run", "-a", "-s", "-screen 0 1920x1200x24", PY, os.path.join(HERE, "webkit_page.py"), url, str(w), str(h), path],
                          capture_output=True, text=True, timeout=400)
    line = next((l for l in done.stdout.split("\n") if l.startswith("RESULT ")), None)
    if line is None:
        raise SystemExit("webkit_page.py answered nothing:\n" + done.stdout[-2000:] + done.stderr[-2000:])
    return json.loads(line[len("RESULT "):])

SHOTS = os.environ.get("WEBKIT_SHOTS")
for site, path, w, h, paint in (("the root", "/web/scope.html", 1400, 900, False), ("the root", "/web/scope.html", 1100, 680, False),
                                ("testing", "/testing/web/scope.html", 1400, 900, True)):
    label = "%s at %dx%d" % (site, w, h)
    print("\n--- %s, in WebKit ---" % label)
    shot = os.path.join(SHOTS, "webkit-%s-%dx%d.png" % (site.replace(" ", ""), w, h)) if SHOTS else None
    r = drive("http://127.0.0.1:%d%s" % (PORT, path), w, h, paint, shot)
    first, pressed, played, fit, panels = r[0], r[2], r[3], r[4], r[5]
    errs = r[-1]
    if label.endswith("1400x900") and site == "the root":
        check("the engine is WebKit, not Chromium", "AppleWebKit" in first["ua"] and "Chrome" not in first["ua"], first["ua"])
    check("%s: no error, rejection, console.error or warn" % label, errs == [], "; ".join(map(str, errs[:4])))
    null("%s: a console.error made on purpose is caught" % label, any("the null" in e for e in first["caught"]), str(first["caught"]))
    null("%s: before any press the instrument is not running" % label, not first["before"]["running"], str(first["before"]))
    check("%s: one real click starts the AudioWorklet's core, with no fault" % label,
          pressed["running"] and not pressed["fault"], str(pressed))
    null("%s: before a note the lanes are silent" % label, pressed["peak"] < 1e-6, "%.2e" % pressed["peak"])
    check("%s: a dyad reaches the lanes and the trace" % label, played["peak"] > 0.1 and played["ink"] > pressed["ink"] * 1.05,
          "peak %.3f, ink %d against %d" % (played["peak"], played["ink"], pressed["ink"]))
    bad = {t: v for t, v in fit["tabs"].items() if v["bench"] > 0 or v["page"] > 0}
    check("%s: no tab scrolls, and the page does not" % label, not bad, str(fit["tabs"]))
    null("%s: a tall block in the Bench is found over" % label, fit["crowded"]["bench"] > 0 or fit["crowded"]["page"] > 0, str(fit["crowded"]))
    check("%s: Scope & measure, the browser and Settings open, and neither panel scrolls" % label,
          panels["measure"]["open"] and panels["measure"]["over"] <= 0 and panels["measure"]["page"] <= 0
          and panels["presets"]["open"] and panels["settings"]["open"] and panels["settings"]["over"] <= 0, str(panels))
    if paint:
        p = r[6]
        check("%s: Paint pressed paints, and says how" % label, p["draws"] == "paint" and p["mode"] in ("gpu", "plain"), str(p))

server.shutdown()
print()
print("%d failed" % len(fails) if fails else "all passed")
sys.exit(1 if fails else 0)
