"""Which controls reach the sound, measured (the picture reach audit, Part B).

Scan and the three reads take in the light as drawn on the 64 by 64 grid, so a
control that only changes how the figure is drawn - the zoom, the timebase, the
turn, the beam - can change the sound. This measures it rather than guessing,
for every control on the face, in two passes:

1. The browser. The page opened as a player opens it, the worklet running, and
   every message the page posts to the instrument caught on its way
   (MessagePort.prototype.postMessage, as braintest.py catches them). On each
   figure, each control is moved to two other values, one at a time, and what
   it sent is kept - the plugin's editor sends the same - along with the setup
   code the page would save after it. A control that sends nothing and leaves
   the code as it was cannot reach the instrument: it is look-only by
   construction, and is recorded so.
2. The core. For each control and value that sent anything or changed the
   code, the instrument rendered offline (core/tests/tools/render_cpp.cpp)
   from the figure's code, the messages handed over before the first note (and
   again loaded from the code the change left, where that differs), a chord
   held 4.5 seconds, against the figure rendered without them. The held part,
   1.5 to 4.5 s, is compared: the difference's RMS against the sound's, in dB,
   and the spectrum's distance (honestytest's fifth-octave band shares, window
   against window, a mean). The engine is deterministic, so the base rendered
   twice is the same to the bit - the null every reading stands on - and a
   control that cannot reach the sound reads exactly nothing.

The figures: a Settled preset (Tine piano), a Breathing one (Slow pad) and a
two-hands split (Bass under the pad), each at Scan 60 and Picture 80, each in
X-Y and in Y-T.

    CHROME=/opt/pw-browsers/chromium python3 web/tools/reach_audit.py
    python3 web/tools/reach_audit.py --measure    # the core pass again, from the browser's record
    python3 web/tools/reach_audit.py --write      # the table again, from both records

Writes web/docs/what-reaches-the-sound.json (every reading, not kept in the
repository: --write needs a measure in the same checkout first) and the table in
web/docs/what-reaches-the-sound.md between its markers; the prose around the
table is the doc's own. reachtest.py holds the info lines to the table.
"""
import json, math, os, subprocess, sys, hashlib, threading
from concurrent.futures import ThreadPoolExecutor
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
CORE = os.path.join(ROOT, "core")
BUILD = os.path.join(CORE, "build", "audit")
WORK = os.path.join(BUILD, "reach")
PAGE = "file://" + os.path.join(ROOT, "web", "scope.html")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
BROWSED = os.path.join(BUILD, "reach-browsed.json")
OUT_JSON = os.path.join(ROOT, "web", "docs", "what-reaches-the-sound.json")
DOC = os.path.join(ROOT, "web", "docs", "what-reaches-the-sound.md")
RATE = 44100

FIGURES = [
    ("settled-xy", "Tine piano", "xy"), ("settled-yt", "Tine piano", "yt"),
    ("breathing-xy", "Slow pad", "xy"), ("breathing-yt", "Slow pad", "yt"),
    ("split-xy", "Bass under the pad", "xy"), ("split-yt", "Bass under the pad", "yt"),
]

# Not moved, with why: each leaves the page, needs a device, or is not a
# setting at all, and none is a view of the figure.
SKIP = {
    "presetPrev": "loads another sound", "presetNext": "loads another sound", "preset": "opens the browser",
    "presetBrowse": "opens the browser", "presetNew": "loads the base", "presetLoad": "loads a sound",
    "presetSave": "saves", "presetSaveHead": "saves", "presetSaveOpen": "opens saving", "presetDelete": "deletes a saved sound",
    "presetCopy": "copies the code", "presetPaste": "loads a code", "presetClose": "closes the browser",
    "presetName": "a saved sound's name", "presetCode": "a code to paste", "benchSearch": "a search box",
    "undoButton": "a step back", "redoButton": "a step on", "midiConnect": "asks for MIDI devices",
    "srcTone": "the source: an input needs a device", "srcMic": "needs a microphone", "micWhole": "needs a microphone",
    "micBands": "needs a microphone", "kindMic": "needs an input", "kindLine": "needs an input", "device": "needs a device",
    "midiOut": "a MIDI port", "midiOutCh": "a MIDI port's channel",
    "keysOpen": "the on-screen keys", "keysDown": "the on-screen keys", "keysUp": "the on-screen keys",
    "keysPedal": "the on-screen keys' pedal", "keysClose": "the on-screen keys", "keysLatch": "the on-screen keys",
    "helpButton": "the help sheet", "helpClose": "the help sheet", "helpFirst": "the help sheet",
    "tabScreen": "the help sheet", "tabTrigger": "the help sheet", "tabMeasure": "the help sheet",
    "tabSignal": "the help sheet", "tabKeys": "the help sheet",
    "routingsClear": "clears every routing", "routingsAllOff": "silences every routing",
    "tempoTap": "taps a tempo over real seconds", "midiSplitLearn": "waits for a key",
    "saveReference": "stores a reference trace", "clearReference": "clears the reference",
}

BROWSE = r"""async ([name, display, skip]) => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  if (!window.__reach) {
    window.__reach = [];
    const real = MessagePort.prototype.postMessage;
    MessagePort.prototype.postMessage = function (m, ...rest) {
      if (m && m.op && m.op !== 'midi') window.__reach.push(JSON.parse(JSON.stringify(m)));
      return real.call(this, m, ...rest);
    };
  }
  const sent = () => { const s = window.__reach.slice(); window.__reach.length = 0; return s; };
  // The figure: the preset, then Scan 60 and Picture 80 as a hand turns them, and the display.
  applyPreset('b:' + name);
  window.setControl('oscScan', 60);
  window.setControl('pictureAmount', 80);
  document.getElementById(display === 'xy' ? 'dispXY' : 'dispYT').click();
  await wait(400);
  const base = encodeSetup(snapshot());
  // Anything posted while nothing is touched is not any control's.
  sent(); await wait(300);
  const idle = sent();
  const back = async () => {
    if (encodeSetup(snapshot()) !== base) { loadCode(base); await wait(60); }
    if (typeof setEnlarged === 'function') setEnlarged(false);
    await wait(30); sent();
  };
  const homeOf = (e) => { const h = e.closest('[data-home]'); return h ? h.dataset.home : ''; };
  const sectionOf = (e) => { const s = e.closest('[data-fx], section[id], details[id], [data-section]');
    return s ? (s.dataset.fx || s.id || s.dataset.section) : ''; };
  const out = [];
  const take = async (id, value, move) => {
    sent();
    move();
    await wait(60);
    const msgs = sent();
    const code = encodeSetup(snapshot());
    return { value: String(value), msgs, code: code === base ? null : code };
  };
  /* Found again by id for each control: the lanes' rows and the trigger's
     source are made afresh when the lanes change, so an element held from
     the start can be one no longer on the page, whose click reaches nothing. */
  const ids = Array.from(document.querySelectorAll('input[id], select[id], button[id]'), (x) => x.id);
  // A control the page's `el` has not got (the LFO's, made later) is moved the same way, by id.
  const setControl = (id, value) => {
    const c = document.getElementById(id);
    c.value = String(value);
    c.dispatchEvent(new Event(c.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true }));
  };
  for (const id of ids) {
    const e = document.getElementById(id);
    if (!e) { out.push({ id, kind: '?', home: '', section: '', base: null, values: [], error: 'not on the page by now' }); continue; }
    const kind = e.tagName.toLowerCase() + (e.type ? ':' + e.type : '');
    const row = { id, kind, home: homeOf(e), section: sectionOf(e), base: null, values: [] };
    out.push(row);
    if (skip.includes(id)) { row.skipped = true; continue; }
    try {
      if (kind === 'input:range') {
        const min = Number(e.min), max = Number(e.max), step = Number(e.step) || 1, now = Number(e.value);
        row.base = String(now);
        const snap = (v) => Math.round((min + v * (max - min) - min) / step) * step + min;
        let vs = [snap(0.25), snap(0.8)].map((v) => (v === now ? snap(0.55) : v));
        if (vs[0] === vs[1]) vs = [vs[0], snap(0.05) === vs[0] ? max : snap(0.05)];
        for (const v of vs) {
          row.values.push(await take(id, v, () => setControl(id, v)));
          setControl(id, now); await back();
        }
      } else if (e.tagName === 'SELECT') {
        const now = e.value; row.base = now;
        const others = Array.from(e.options).map((o) => o.value).filter((v) => v !== now).slice(0, 2);
        for (const v of others) {
          row.values.push(await take(id, v, () => setControl(id, v)));
          setControl(id, now); await back();
        }
      } else if (kind === 'input:checkbox') {
        row.base = String(e.checked);
        row.values.push(await take(id, !e.checked, () => e.click()));
        e.click(); await back();
      } else if (e.tagName === 'BUTTON' && e.getAttribute('role') === 'radio') {
        const group = Array.from(e.parentElement.querySelectorAll(':scope > button[role=radio]'));
        const on = group.find((b) => b.getAttribute('aria-checked') === 'true');
        row.base = on ? on.id : '';
        row.group = group.map((b) => b.id);
        if (e === on) { row.values.push({ value: 'already on', msgs: [], code: null, idle: true }); continue; }
        row.values.push(await take(id, 'on', () => e.click()));
        if (on) on.click();
        await back();
      } else if (e.tagName === 'BUTTON' && e.hasAttribute('aria-pressed')) {
        row.base = e.getAttribute('aria-pressed');
        row.values.push(await take(id, 'pressed', () => e.click()));
        if (e.getAttribute('aria-pressed') !== row.base) e.click();
        await back();
      } else if (e.tagName === 'BUTTON') {
        row.base = 'action';
        row.values.push(await take(id, 'pressed', () => e.click()));
        await back();
        // A panel it opened, closed again, so the next control is found as it was.
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
        await wait(20); sent();
      }
    } catch (error) { row.error = String(error && error.message || error); await back(); }
  }
  return { base, idle, controls: out, words: CONTROL_WORDS, host: HOST_PARAMS };
}"""


def browse():
    from playwright.sync_api import sync_playwright
    record = {}
    with sync_playwright() as pw:
        for tag, name, display in FIGURES:
            b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
            p = b.new_page(viewport={"width": 1400, "height": 900})
            errors = []
            p.on("pageerror", lambda e: errors.append(str(e)))
            p.on("dialog", lambda d: d.dismiss())
            p.goto(PAGE); p.wait_for_timeout(1500)
            if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
            p.locator("#trace").click(position={"x": 5, "y": 5})
            p.wait_for_timeout(1500)
            r = p.evaluate(BROWSE, [name, display, list(SKIP)])
            r["errors"] = errors
            record[tag] = r
            moved = sum(1 for c in r["controls"] if c["values"])
            print("browsed %-13s %d controls, %d moved, idle messages %d, page errors %d"
                  % (tag, len(r["controls"]), moved, len(r["idle"]), len(errors)))
            b.close()
    os.makedirs(BUILD, exist_ok=True)
    with open(BROWSED, "w") as f: json.dump(record, f)


# --- the core ----------------------------------------------------------------------------

def tool(name):
    os.makedirs(BUILD, exist_ok=True)
    exe = os.path.join(BUILD, name)
    subprocess.run(["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-I", os.path.join(CORE, "include"),
                    os.path.join(CORE, "tests", "tools", name + ".cpp"), "-o", exe], check=True)
    return exe


def as_commands(msgs):
    out = []
    for m in msgs:
        op = m.get("op")
        if op == "slider": out.append(["slider", m["id"], str(m["value"])])
        elif op == "control":
            v = m.get("value")
            out.append(["control", m["id"], v if isinstance(v, bool) else ("" if v is None else str(v))])
        elif op == "click": out.append(["click", m["id"]])
        elif op == "setup": out.append(["setup", m["code"]])
        elif op == "routings": out.append(["routings", m["text"]])
        elif op == "fade": out.append(["fade", m["json"] if isinstance(m["json"], str) else json.dumps(m["json"])])
        else: out.append(["unknown", op])
    return out


def chord(tag):
    return [36, 43, 64, 67] if tag.startswith("split") else [48, 55, 60, 64]


# View controls that act only behind a switch of their own, measured with it
# on - in the base and the change alike - since off they read nought by
# construction and "look-only" would be a claim about the switch.
CONTEXT = {
    "filterType": [["control", "filterOn", True]], "filterCutoff": [["control", "filterOn", True]],
    "filterRes": [["control", "filterOn", True]], "seeDry": [["control", "filterOn", True]],
    "hearWet": [["control", "filterOn", True]], "hearDry": [["control", "filterOn", True]],
    "lag": [["control", "lagOn", True]], "lagMix": [["control", "lagOn", True]], "lagManual": [["control", "lagOn", True]],
    "acCorner": [["control", "ch1Ac", True], ["control", "ch2Ac", True]],
    "measurePost": [["slider", "rotate", "30"]], "measurePre": [["slider", "rotate", "30"]],
}
# And one that acts at a moment: Clear wipes a grid that is empty before the first note.
AT = {"clearButton": 2.0}


def render(exe, tag, code, commands, context=(), at=None):
    """The figure's code made, any context, the commands handed over (before the
    first note, or at `at` seconds), a chord held: the heard pair."""
    lines = [["make", RATE, code]] + list(context) + ([] if at else commands) + [["to", 0.1]]
    lines += [["midi", 0x90, n, 100] for n in chord(tag)]
    raw = os.path.join(WORK, hashlib.sha1(json.dumps([lines, commands, at]).encode()).hexdigest()[:16])
    part = "%s.%d.%d.part" % (raw, os.getpid(), threading.get_ident())
    lines += [["record", "heard", part]]
    lines += ([["to", at]] + commands if at else []) + [["to", 4.5]]
    if not os.path.exists(raw + ".f32"):
        # Written aside and moved into place, so two jobs on the same script never read half a file.
        with open(part + ".txt", "w") as f: f.write("\n".join(json.dumps(l) for l in lines) + "\n")
        out = subprocess.run([exe, part + ".txt"], check=True, capture_output=True, text=True).stdout
        os.remove(part + ".txt")
        if any(l.startswith("no ") for l in out.split("\n")) or "unknown" in out:
            raise RuntimeError("render_cpp refused: " + out[:300])
        os.replace(part, raw + ".f32")
    return np.fromfile(raw + ".f32", dtype="<f4").reshape(-1, 2).astype(np.float64)


def bands(x):
    n = len(x)
    w = x * (0.5 - 0.5 * np.cos(2 * np.pi * np.arange(n) / (n - 1)))
    spec = np.fft.rfft(w)
    p = (spec.real ** 2 + spec.imag ** 2)[1:n // 2]
    f = np.arange(1, n // 2) * 44100 / n
    keep = f >= 40
    idx = np.minimum(47, np.floor(np.log2(f[keep] / 40) * 5)).astype(int)
    b = np.zeros(48)
    np.add.at(b, idx, p[keep])
    tot = b.sum()
    return np.sqrt(b / tot) if tot > 0 else b


def compare(a, b):
    """The held part, 1.5 to 4.5 s (the record starts at 0.1): None when the two are the same to the bit."""
    sl = slice(int(1.4 * RATE), int(4.4 * RATE))
    x, y = a[sl], b[sl]
    if np.array_equal(x, y): return None
    rms = lambda v: math.sqrt(float(np.mean(v ** 2)))
    d = rms(x - y) / rms(x) if rms(x) > 0 else math.inf
    n = 4096
    ds = [float(np.sqrt(np.sum((bands(x[i:i + n, 0]) - bands(y[i:i + n, 0])) ** 2))) for i in range(0, len(x) - n + 1, n // 2)]
    level = 20 * math.log10(rms(y) / rms(x)) if rms(x) > 0 and rms(y) > 0 else 0.0
    return {"diffDb": 20 * math.log10(d) if d > 0 else -999, "spectral": sum(ds) / len(ds), "levelDb": level}


def measure():
    record = json.load(open(BROWSED))
    exe = tool("render_cpp")
    os.makedirs(WORK, exist_ok=True)
    jobs = []
    for tag, r in record.items():
        for c in r["controls"]:
            for v in c["values"]:
                if v["msgs"]: jobs.append((tag, c["id"], v["value"], "live", as_commands(v["msgs"]), r["base"]))
                if v["code"]: jobs.append((tag, c["id"], v["value"], "loaded", [], v["code"]))
    bases = {tag: render(exe, tag, r["base"], []) for tag, r in record.items()}
    # The null under every reading: the base twice, from nothing cached.
    again = {}
    for tag, r in record.items():
        lines_tag = tag
        raw = os.path.join(WORK, "null-" + tag)
        lines = [["make", RATE, r["base"]], ["to", 0.1]] + [["midi", 0x90, n, 100] for n in chord(lines_tag)] \
            + [["record", "heard", raw + ".f32"], ["to", 4.5]]
        with open(raw + ".txt", "w") as f: f.write("\n".join(json.dumps(l) for l in lines) + "\n")
        subprocess.run([exe, raw + ".txt"], check=True, capture_output=True)
        again[tag] = compare(bases[tag], np.fromfile(raw + ".f32", dtype="<f4").reshape(-1, 2).astype(np.float64))
    print("null, each figure's base rendered twice:", again)

    def one(job):
        tag, cid, value, how, cmds, code = job
        try:
            ctx, at = CONTEXT.get(cid, []), AT.get(cid)
            base = render(exe, tag, record[tag]["base"], [], ctx) if ctx else bases[tag]
            return job, compare(base, render(exe, tag, code, cmds, ctx, at)), None
        except Exception as error:   # a refused message is recorded, not fatal
            return job, None, str(error)[:200]
    readings = []
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
        for k, (job, got, err) in enumerate(pool.map(one, jobs)):
            tag, cid, value, how, cmds, code = job
            readings.append({"figure": tag, "id": cid, "value": value, "how": how, "reading": got, "error": err})
            if k % 200 == 0: print("  %d of %d" % (k, len(jobs)))
    with open(OUT_JSON, "w") as f:
        json.dump({"null": again, "readings": readings}, f, indent=0)
    print("measured", len(readings), "renders")


# --- the table ------------------------------------------------------------------------------

# By design: what the player tunes the sound with. Everything here is placed
# by its home and section, and the view's own - the screen, the scope's
# tools, the look - are named, since they are the suspects.
VIEW = {
    # Scope & measure and the screen's toolbar.
    "level", "position", "holdoff", "timebase", "zoom", "xyX", "xyY", "filterOn", "filterType", "filterCutoff",
    "filterRes", "ch1On", "ch1Ac", "ch1Scale", "ch1Offset", "ch2On", "ch2Ac", "ch2Scale", "ch2Offset", "midSide",
    "lagOn", "lag", "lagMix", "acCorner", "readoutsOn", "cursorsOn", "midiTruth", "midiFollow",
    "edgeRising", "edgeFalling", "trigSource0", "trigSource1", "layStack", "layOver", "seeDry", "seeWet",
    "hearDry", "hearWet", "lagAuto", "lagManual", "measurePre", "measurePost", "measureButton", "measureClose",
    "run", "modeAuto", "modeNormal", "modeSingle", "autoset", "clearButton",
    "dispYT", "dispXY", "dispSpect", "enlargeButton", "pictureOnly", "handsBoth", "handsA", "handsB", "enlargeTrail",
    # The look, in the Picture's Advanced and This window.
    "beamLevel", "bInk", "traceWidth", "graticuleOn", "beamXY", "beamYT", "beamGoni", "inkAccent", "inkCh1",
    "inkCh2", "inkCh3", "inkCh4", "inkCh5", "goniOn", "spectrumOn", "harmonicsOn", "tunerOn", "spectroSpan",
    "loopButton", "panesButton", "panesClose", "sizeAuto", "size90", "size100", "size125", "infoLineOn",
    # The Plane's Turn is the screen's rotation.
    "rotate",
    # A split's third and fourth lanes, which the page has and the instrument does not.
    "ch3On", "ch3Ac", "ch3Scale", "ch3Offset", "ch4On", "ch4Ac", "ch4Scale", "ch4Offset",
}
# Why a row reads nought where nought is not the whole story.
NOTES = {
    "ch3Scale": "refused: the instrument has no such slider, so the page's lane 3 and Scan's part ways",
    "ch3Offset": "refused: the instrument has no such slider", "ch4Scale": "refused: the instrument has no such slider",
    "ch4Offset": "refused: the instrument has no such slider",
    "midiFollow": "sends nothing when a note moves the page's timebase (measured with a note held): the instrument's stays",
    "autoset": "sends only Run; the timebase, full scales and level it picks stay the page's (measured with a note held)",
    "hearWet": "measured with the trace filter on: the generator's sound is the same to the bit; a live input was not played",
    "lagMix": "measured with Lag X-Y on: the same to the bit; a live input was not played",
    "clearButton": "pressed two seconds into the chord",
}
# Panels and menus that open and close: nothing but the face.
FACE = {"performButton", "performClose", "menuButton", "menuClose", "pictureMore", "pictureClose", "routingsButton",
        "routingsClose", "modEditorClose", "routingsBySource", "routingsByDest", "benchTab-play", "benchTab-ink",
        "benchTab-space", "infoMore", "photoPlace", "midiStripDown", "midiStripUp", "midiWindowGo", "fadeEditA",
        "fadeEditB", "editHandA", "editHandB", "srcDetail-add", "monitorLive"}


def summarise():
    record = json.load(open(BROWSED))
    measured = json.load(open(OUT_JSON))
    any_tag = next(iter(record))
    # The words as the doc has them now, not as the page had them when it was browsed.
    sys.path.insert(0, HERE)
    import write_words
    words = write_words.parse(open(write_words.DOC, encoding="utf-8").read())
    host = record[any_tag]["host"]
    rows = {}
    for tag, r in record.items():
        for c in r["controls"]:
            row = rows.setdefault(c["id"], {"id": c["id"], "kind": c["kind"], "home": c["home"], "section": c["section"],
                                            "skipped": c.get("skipped", False), "sent": False, "coded": False,
                                            "readings": [], "errors": []})
            for v in c["values"]:
                if v["msgs"]: row["sent"] = True
                if v["code"]: row["coded"] = True
            if c.get("error"): row["errors"].append(c["error"])
            if c.get("group"): row["group"] = c["group"]
            row["alwaysOn"] = row.get("alwaysOn", True) and bool(c["values"]) and all(v.get("idle") for v in c["values"])
    for m in measured["readings"]:
        if m["error"]: rows[m["id"]]["errors"].append(m["error"])
        if m["reading"]: rows[m["id"]]["readings"].append(m)
    # A radio button on in every figure was never itself moved: choosing it is
    # the change back from its group's others, so it reads as they do.
    for cid, row in rows.items():
        if row.get("group") and row.get("alwaysOn") and not row["readings"]:
            for other in row["group"]:
                if other != cid and other in rows: row["readings"] += rows[other]["readings"]
            row["inherits"] = [o for o in row["group"] if o != cid]
    out = []
    for cid, row in rows.items():
        live = [m for m in row["readings"] if m["how"] == "live"]
        loaded = [m for m in row["readings"] if m["how"] == "loaded"]
        most = max(row["readings"], key=lambda m: m["reading"]["spectral"], default=None)
        figs = sorted(set(m["figure"] for m in row["readings"]))
        if row["skipped"]: cls = "not moved"
        elif not row["readings"]:
            cls = "look-only" if (cid in VIEW or cid in FACE) else ("idle here" if row["sent"] or row["coded"] else "face only")
        elif cid in VIEW: cls = "REACHES THE SOUND THROUGH THE PICTURE"
        else: cls = "sound by design"
        line = words.get(cid, [None, None])
        out.append({**{k: row[k] for k in ("id", "kind", "home", "section", "sent", "coded")},
                    "class": cls, "figures": figs, "live": bool(live), "loaded": bool(loaded),
                    "most": most and {"figure": most["figure"], "value": most["value"], **most["reading"]},
                    "host": cid in host, "name": line[0], "line": line[1], "skip": SKIP.get(cid),
                    "errors": sorted(set(row["errors"]))[:2], "inherits": row.get("inherits"),
                    "note": NOTES.get(cid)})
    return out, measured["null"]


def size(m, r=None):
    tail = ""
    if r and r.get("inherits"): tail += "; on in every figure, so measured as the change back from " + ", ".join(r["inherits"])
    if r and r.get("note"): tail += "; " + r["note"]
    if not m: return "nought (the same to the bit)" + tail
    return size_of(m) + tail


def size_of(m):
    return "%.3f spectrum, %s dB difference (%s at %s)" % (m["spectral"], ("%.0f" % m["diffDb"]).replace("-", "&minus;"),
                                                           m["figure"], m["value"])


def write_doc(rows, null):
    order = {"REACHES THE SOUND THROUGH THE PICTURE": 0, "sound by design": 1, "idle here": 2, "look-only": 3,
             "face only": 4, "not moved": 5}
    rows.sort(key=lambda r: (order[r["class"]], r["home"] or "~", r["id"]))
    with open(os.path.join(ROOT, "web", "docs", "what-reaches-the-sound.table.json"), "w") as f:
        json.dump([{k: r[k] for k in ("id", "class", "host", "figures", "most")} for r in rows], f, indent=0)
    lines = ["| id | control | home | class | measured change (most, held part) | figures | info line now | right? |",
             "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        claim = (r["line"] or "").replace("|", "/")
        lines.append("| `%s`%s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["id"], " (host)" if r["host"] else "", r["name"] or "", (r["home"] or "-") + ("/" + r["section"] if r["section"] else ""),
            r["class"] if r["class"] != "not moved" else "not moved: " + (r["skip"] or ""),
            size(r["most"], r) if r["class"] not in ("not moved",) else "-",
            ", ".join(f.replace("-", " ") for f in r["figures"]) or "-", claim, "{{right:%s}}" % r["id"]))
    text = open(DOC).read()
    start, end = "<!-- table: written by web/tools/reach_audit.py -->", "<!-- end of table -->"
    a, b = text.index(start) + len(start), text.index(end)
    rights = json.load(open(os.path.join(ROOT, "web", "docs", "what-reaches-the-sound.rights.json")))
    body = "\n".join(lines)
    for r in rows: body = body.replace("{{right:%s}}" % r["id"], rights.get(r["id"], ""))
    counts = {}
    for r in rows: counts[r["class"]] = counts.get(r["class"], 0) + 1
    head = "\n\n%d controls. %s. The null: each figure's base rendered twice, %s.\n\n" % (
        len(rows), "; ".join("%s %d" % (k, v) for k, v in sorted(counts.items(), key=lambda kv: order[kv[0]])),
        "the same to the bit on all six" if all(v is None for v in null.values()) else "NOT the same: " + json.dumps(null))
    with open(DOC, "w") as f: f.write(text[:a] + head + body + "\n\n" + text[b:])
    print(head.strip())


if __name__ == "__main__":
    if "--measure" not in sys.argv and "--write" not in sys.argv: browse()
    if "--write" not in sys.argv: measure()
    rows, null = summarise()
    if os.path.exists(DOC): write_doc(rows, null)
    else:
        for r in rows:
            if r["class"] in ("REACHES THE SOUND THROUGH THE PICTURE", "sound by design"):
                print("%-40s %-16s %s" % (r["class"][:40], r["id"], size(r["most"])))
