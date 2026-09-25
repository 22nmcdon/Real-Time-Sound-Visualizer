"""The rack as something you build: lanes in and out one at a time.

What would go wrong, and what is checked for it:

- Lanes opening a file picker, or changing the screen, when there is nothing
  in the rack yet - and not saying that the screen has not changed;
- added files replacing the ones already in, or going in out of order;
- a lane's remove button taking out the wrong lane. The file removed is the
  MIDDLE one of three, with the generator in front of them, so an index that
  forgot to skip the generator, or counted from the end, takes out another;
- the remove button offered where it cannot work: on the last lane, or on a
  band split whose lanes are one file through a crossover;
- Play along building a rack the boxes cannot see, so the live input could
  not be taken out of it or the generator added beside it;
- two builds in flight, and the one that finishes last winning rather than
  the one asked for last; or a build finishing after another source was
  chosen and taking the screen back;
- Lanes forgetting the rack when you come back to it;
- files dropped on a rack replacing it rather than joining it.

The files are made here, in the page: short WAVs of known length, each with
its own name, so a lane is identified by the file it came from and never by
where it happens to sit. The microphone is an oscillator, as contracttest's is.
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

SETUP = """() => {
  // A mono 16-bit WAV of a sine, a quarter of a second, named.
  window.__wav = (name, hz) => {
    const rate = 44100, n = rate / 4, bytes = 44 + n * 2;
    const b = new ArrayBuffer(bytes), v = new DataView(b);
    const str = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
    str(0, 'RIFF'); v.setUint32(4, bytes - 8, true); str(8, 'WAVE'); str(12, 'fmt ');
    v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
    v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true);
    v.setUint16(34, 16, true); str(36, 'data'); v.setUint32(40, n * 2, true);
    for (let i = 0; i < n; i++) v.setInt16(44 + i * 2, Math.round(12000 * Math.sin(2 * Math.PI * hz * i / rate)), true);
    return new File([b], name + '.wav', { type: 'audio/wav' });
  };
  // The microphone, as an oscillator.
  const ctx = new AudioContext();
  const osc = ctx.createOscillator(), dest = ctx.createMediaStreamDestination();
  osc.connect(dest); osc.start();
  navigator.mediaDevices.getUserMedia = () => Promise.resolve(dest.stream);
  if (!navigator.mediaDevices.enumerateDevices) navigator.mediaDevices.enumerateDevices = () => Promise.resolve([]);
  liveStreams.clear();
  window.__names = () => state.source.lanes ? state.source.lanes.map((l) => l.name) : null;
  window.__removable = () => Array.from(el.laneList.querySelectorAll('[data-act="remove"]'))
    .map((b) => Number(b.dataset.lane));
  window.__wait = (ms) => new Promise((r) => setTimeout(r, ms));
}"""

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
    p.wait_for_timeout(200)
    p.evaluate(SETUP)
    p.evaluate("() => { setView('bench'); setBenchTab('play'); }"); p.wait_for_timeout(150)

    print("\n--- Lanes, with nothing in the rack ---")
    empty = p.evaluate("""async () => {
      let picked = 0;
      const real = el.rackInput.click.bind(el.rackInput);
      el.rackInput.click = () => { picked++; };
      el.srcRack.click();
      await __wait(300);
      const out = { picked, kind: state.source.kind, rows: !el.rackRows.hidden,
                    switch: el.srcRack.getAttribute('aria-checked'), label: el.srcRack.textContent,
                    note: el.rackNote.textContent,
                    // Nothing loaded yet, so no lanes to list.
                    sectionOff: el.laneGroup.offsetHeight === 0 };
      el.rackInput.click = real;
      return out;
    }""")
    print("    %s" % empty)
    check("Lanes opens no file picker and leaves the screen alone",
          empty["picked"] == 0 and empty["kind"] == "tone" and empty["rows"]
          and empty["switch"] == "true" and empty["label"] == "Lanes", str(empty))
    check("and says the screen is still showing the generator",
          "Nothing in the rack yet" in empty["note"] and "generator" in empty["note"], empty["note"])

    print("\n--- lanes in, in order ---")
    order = p.evaluate("""async () => {
      el.rackSynth.checked = true; await setRackSynth(true);
      await addRackFiles([__wav('one', 220), __wav('two', 330)]);
      const two = __names();
      await addRackFiles([__wav('three', 440)]);
      const three = __names();
      el.rackLive.checked = true; await setRackLive(true);
      showControl('laneList');          // its tab, which is Picture
      const section = el.laneGroup.offsetHeight > 0 && el.laneList.offsetHeight > 0;
      setBenchTab('play');
      return { two, three, all: __names(), budget: el.rackBudget.textContent, removable: __removable(),
               section };
    }""")
    print("    %s" % order)
    check("files are added beside the ones already in, not instead",
          order["two"] == ["Generator", "one", "two"] and order["three"] == ["Generator", "one", "two", "three"],
          str(order))
    check("and the rack comes in one order: the generator, the files, then you",
          order["all"] == ["Generator", "one", "two", "three", "You"] and "5 of 6" in order["budget"], str(order))
    check("the lanes have a section of their own, showing while there is a rack",
          order["section"] and empty["sectionOff"], str({"with": order["section"], "without": empty["sectionOff"]}))
    check("every lane can be taken out while there is more than one",
          order["removable"] == [0, 1, 2, 3, 4], str(order["removable"]))

    print("\n--- lanes out, the one asked for ---")
    out = p.evaluate("""async () => {
      const steps = {};
      // The middle file, with the generator in front of it.
      el.laneList.querySelector('[data-act="remove"][data-lane="2"]').click();
      await __wait(900);
      steps.file = { names: __names(), files: rackFiles.map((f) => f.name) };
      // The generator, by its button: the box follows.
      el.laneList.querySelector('[data-act="remove"][data-lane="0"]').click();
      await __wait(900);
      steps.generator = { names: __names(), box: el.rackSynth.checked, state: state.rackSynth };
      // And you.
      const you = __names().indexOf('You');
      el.laneList.querySelector('[data-act="remove"][data-lane="' + you + '"]').click();
      await __wait(900);
      steps.live = { names: __names(), box: el.rackLive.checked };
      // Down to one: no button on it.
      el.laneList.querySelector('[data-act="remove"][data-lane="1"]').click();
      await __wait(900);
      steps.last = { names: __names(), removable: __removable() };
      return steps;
    }""")
    print("    %s" % out)
    check("removing the middle file takes out that file and no other",
          out["file"]["names"] == ["Generator", "one", "three", "You"]
          and out["file"]["files"] == ["one.wav", "three.wav"], str(out["file"]))
    check("removing the generator's lane unticks its box",
          out["generator"]["names"] == ["one", "three", "You"] and not out["generator"]["box"]
          and not out["generator"]["state"], str(out["generator"]))
    check("and removing yours unticks the live input",
          out["live"]["names"] == ["one", "three"] and not out["live"]["box"], str(out["live"]))
    check("the last lane has no remove button: a rack of nothing is not a source",
          out["last"]["names"] == ["one"] and out["last"]["removable"] == [], str(out["last"]))

    print("\n--- Lanes remembers ---")
    back = p.evaluate("""async () => {
      el.srcTone.click(); await __wait(300);
      const away = state.source.kind;
      el.srcRack.click(); await __wait(900);
      return { away, kind: state.source.kind, names: __names() };
    }""")
    print("    %s" % back)
    check("coming back to Lanes brings the rack back as it was",
          back["away"] == "tone" and back["kind"] == "rack" and back["names"] == ["one"], str(back))

    print("\n--- Play along is a membership ---")
    along = p.evaluate("""async () => {
      await toPlayAlong(__wav('track', 110));
      const made = { names: __names(), box: el.rackLive.checked, files: rackFiles.map((f) => f.name),
                     align: state.alignMs, suggested: state.source.suggestedAlignMs,
                     mark: el.sourceMark.textContent.trim().toLowerCase() };
      el.rackSynth.checked = true; await setRackSynth(true);
      made.withGen = __names();
      const you = __names().indexOf('You');
      el.laneList.querySelector('[data-act="remove"][data-lane="' + you + '"]').click();
      await __wait(900);
      made.withoutYou = { names: __names(), box: el.rackLive.checked };
      return made;
    }""")
    print("    %s" % along)
    check("Play along is the track as the one file and the live input ticked",
          along["names"] == ["track", "You"] and along["box"] and along["files"] == ["track.wav"]
          and along["mark"] == "play along" and along["align"] == along["suggested"], str(along))
    check("so the generator goes in beside it, and you can be taken out of it",
          along["withGen"] == ["Generator", "track", "You"]
          and along["withoutYou"]["names"] == ["Generator", "track"] and not along["withoutYou"]["box"],
          str(along))

    print("\n--- a band split's lanes are not separable ---")
    bands = p.evaluate("""async () => {
      await toBands(__wav('whole', 220));
      await __wait(300);
      return { lanes: __names().length, removable: __removable() };
    }""")
    print("    %s" % bands)
    check("a band split offers no remove buttons", bands["lanes"] >= 2 and bands["removable"] == [], str(bands))

    print("\n--- builds in flight ---")
    race = p.evaluate("""async () => {
      el.rackSynth.checked = false; state.rackSynth = false;
      el.rackLive.checked = false; state.rackLive = false;
      // Asked for one after the other, without waiting: the second is what
      // was asked for last, whichever finishes last.
      const slow = toRack([__wav('a', 220), __wav('b', 330), __wav('c', 440), __wav('d', 550)]);
      const quick = toRack([__wav('e', 660)]);
      await Promise.all([slow, quick]);
      await __wait(300);
      const last = __names();
      // And a build still going when another source is chosen does not take
      // the screen back.
      const late = toRack([__wav('f', 220), __wav('g', 330)]);
      toTone();
      await late; await __wait(300);
      return { last, after: state.source.kind };
    }""")
    print("    %s" % race)
    check("of two builds in flight, the one asked for last is the one loaded",
          race["last"] == ["e"], str(race["last"]))
    check("and one still going when the tone is chosen does not replace it",
          race["after"] == "tone", race["after"])

    print("\n--- files dropped on a rack join it ---")
    drop = p.evaluate("""async () => {
      await toRack([__wav('kept', 220)]);
      await __wait(200);
      const dt = new DataTransfer();
      dt.items.add(__wav('dropped', 330));
      document.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true, cancelable: true }));
      await __wait(1200);
      const onRack = __names();
      // Onto anything else, several files are a new rack of just them.
      el.srcTone.click(); await __wait(300);
      const dt2 = new DataTransfer();
      dt2.items.add(__wav('x', 220)); dt2.items.add(__wav('y', 330));
      document.dispatchEvent(new DragEvent('drop', { dataTransfer: dt2, bubbles: true, cancelable: true }));
      await __wait(1200);
      return { onRack, fresh: __names() };
    }""")
    print("    %s" % drop)
    check("a file dropped on a rack goes in beside what is there",
          drop["onRack"] == ["kept", "dropped"], str(drop["onRack"]))
    check("and files dropped on the tone make a rack of just them",
          drop["fresh"] == ["x", "y"], str(drop["fresh"]))

    print("\n--- the Bench, with a rack in it ---")
    # The rack Stage D is for - the generator and the live input - used to
    # scroll the Bench by 52 px at this size: a Pause and a Position with
    # nothing to play, an Alignment with nothing to align, and a label pushed
    # onto a second line by the lane count. Width too: the X-Y menus ran 119 px
    # into the next column with any rack at all.
    fit = p.evaluate("""async () => {
      el.srcTone.click(); await __wait(200);
      rackFiles = null;
      el.rackSynth.checked = true; state.rackSynth = false; await setRackSynth(true);
      el.rackLive.checked = true; state.rackLive = false; await setRackLive(true);
      showSource('rack'); setView('bench'); await __wait(900);
      // The worst tab, since the Bench became tabs: a rack's rows land on
      // Play (what is in it) and Picture (its lanes).
      // Which tab was worst, for the message: a failure that says only
      // "over by 3" leaves the reader to go and find it.
      let overAt = '';
      const over = () => {
        let worst = -Infinity;
        for (const [tab] of BENCH_TABS) {
          setBenchTab(tab);
          const by = el.benchBody.scrollHeight - el.benchBody.clientHeight;
          if (by > worst) { worst = by; overAt = tab; }
        }
        setBenchTab('play');
        return worst;
      };
      const wide = () => ['srcRack', 'laneList'].flatMap((id) => {
        showControl(id);
        const group = el[id].closest('.menu-group'), right = group.getBoundingClientRect().right;
        return Array.from(group.querySelectorAll('input, select, button, .reading'))
          .filter((c) => c.getBoundingClientRect().width > 0)
          .map((c) => [c.id || c.className, Math.round(c.getBoundingClientRect().right - right)])
          .filter(([, by]) => by > 1);
      });
      const two = { lanes: state.source.lanes.length, over: over(), wide: wide(),
                    transport: !el.fileRows.hidden, align: !el.alignRow.hidden,
                    mark: el.sourceMark.textContent.trim().toLowerCase() };
      await addRackFiles([1, 2, 3, 4].map((i) => __wav('f' + i, 200 + i * 60)));
      await __wait(900);
      const six = { lanes: state.source.lanes.length, over: over(), at: overAt, wide: wide(),
                    transport: !el.fileRows.hidden, align: !el.alignRow.hidden };
      setView('scope');
      return { two, six };
    }""")
    print("    %s" % fit)
    check("the generator and the live input fit the Bench without scrolling",
          fit["two"]["lanes"] == 2 and fit["two"]["over"] <= 0, str(fit["two"]))
    check("with no transport and no alignment, since there is nothing to play or align",
          not fit["two"]["transport"] and not fit["two"]["align"], str(fit["two"]))
    check("and the heading calls it lanes, not a play-along with nothing to play along to",
          fit["two"]["mark"] == "lanes", fit["two"]["mark"])
    check("and they come back once there is a file",
          fit["six"]["transport"] and fit["six"]["align"], str(fit["six"]))
    # The known limit the rack builder left - a rack of files scrolled the
    # Bench by 50 to 190 px - is what the tabs were for.
    check("and a rack of six fits the Bench on every tab, since the Bench became tabs",
          fit["six"]["lanes"] == 6 and fit["six"]["over"] <= 0, str(fit["six"]))
    check("nothing in the rack's sections runs out of its column, with two lanes or six",
          fit["two"]["wide"] == [] and fit["six"]["lanes"] == 6 and fit["six"]["wide"] == [], str(fit))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("a rack is built a lane at a time, and taken apart the same way")
