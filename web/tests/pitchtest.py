"""The pitch estimator: the readout, the tuner, the ratio, Autoset and the lag.

What would go wrong, and what is checked for it:

- the misreadings that replaced the crossing count: a registration with
  several bars full reading high, one with the 16' out wandering with the
  timebase, a loud top bar dragging the reading off. Each at four window
  lengths - the timebases from 1 to 10 ms/div;
- precision: a 4 kHz tone is eleven samples a period, where one dip alone
  read 0.4 per cent high;
- a pitch read from too little: a note needs two periods on screen, and a
  window with less says nothing rather than something;
- a pendulum at two hertz on a long timebase, which needs the second pass;
- noise named as a note;
- the readout, Autoset and the lag not using any of it;
- the cost, which is paid every frame the tuner is open.
"""
import os, sys, re
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)


READ = """([tone, n, rate]) => {
  const still = () => ({ shape: 'sine', rate: 0.2, depth: 0, phase: 0, held: 0, value: 0 });
  const core = makeGeneratorCore(rate, GEN_DESTS.length, [still(), still()]);
  core.set('mode', 'wave'); core.set('amp', 0.8);
  for (const k in tone) core.set(k, tone[k]);
  const L = new Float32Array(n), R = new Float32Array(n);
  core.block(L, R, n);
  const found = estimatePeriod(L, rate);
  return { hz: estimateFrequency(L, rate), aperiodicity: found && found.aperiodicity };
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
    read = lambda tone, n, rate=44100: p.evaluate(READ, [tone, n, rate])
    near = lambda got, want, tol: got is not None and abs(got - want) <= tol

    print("\n--- the registrations the crossing count misread ---")
    # At 441, 882, 2205 and 4410 samples: 1, 2, 5 and 10 ms/div at 44.1 kHz.
    windows = [441, 882, 2205, 4410]
    table = {}
    for reg in ("008888000", "888000000", "008000008", "000880000"):
        bars = [int(c) for c in reg]
        table[reg] = [read({"shape": "drawbars", "bars": bars, "freq": 220}, n)["hz"] for n in windows]
        print("    %s on a 220 Hz note: %s" % (reg, [None if h is None else round(h, 3) for h in table[reg]]))
    check("00 8888 000 reads 220 at every timebase - the crossing count read 430 to 534",
          all(near(h, 220, 0.01) for h in table["008888000"]), str(table["008888000"]))
    check("88 8000 000 reads 110, its sound's own period, the same at every timebase that holds two of it",
          all(near(h, 110, 0.01) for h in table["888000000"][1:]), str(table["888000000"]))
    check("and says nothing at 1 ms/div, which holds one of its periods, rather than something",
          table["888000000"][0] is None, str(table["888000000"][0]))
    check("00 8000 008, the 8' and a loud 1', reads 220 - not the 250.9 an early dip gave",
          all(near(h, 220, 0.01) for h in table["008000008"]), str(table["008000008"]))
    check("00 0880 000 has no 220 in it at all - 440 and 660 - and reads 220, the period they share",
          all(near(h, 220, 0.01) for h in table["000880000"]), str(table["000880000"]))

    print("\n--- every shape, and the range ---")
    shapes = {sh: read({"shape": sh, "freq": 220}, 4410)["hz"]
              for sh in ("sine", "square", "ramp", "triangle", "harmonic", "morph", "drawbars")}
    print("    %s" % {k: round(v, 3) for k, v in shapes.items()})
    check("every shape reads 220 to a hundredth of a hertz", all(near(v, 220, 0.01) for v in shapes.values()),
          str(shapes))
    rangebar = {}
    for rate in (44100, 96000):
        for f in (30, 100, 440, 1000, 4000):
            n = max(int(rate * 3 / f), 4096)
            rangebar[(rate, f)] = read({"shape": "sine", "freq": f}, n, rate)["hz"]
    worst = max(abs(v - f) / f for (r, f), v in rangebar.items())
    print("    worst error, 30 Hz to 4 kHz at 44.1 and 96 kHz: %.5f%%" % (worst * 100))
    check("30 Hz to 4 kHz, at 44.1 and 96 kHz, to a hundredth of a per cent - 4 kHz read 0.4 high from one dip",
          worst < 1e-4, "%.5f%% at worst" % (worst * 100))

    print("\n--- what it will and will not say ---")
    short = read({"shape": "sine", "freq": 220}, 441)["hz"]
    check("220 Hz in 441 samples - 1 ms/div, the default screen - reads 220", near(short, 220, 0.05), str(short))
    # A period just too long for the window: 230 samples against a range of
    # 220. A dip followed downhill to the end of the range read 200.5 - the
    # range's edge - rather than nothing.
    edge = read({"shape": "sine", "freq": 44100 / 230}, 441)["hz"]
    check("a period just longer than half the window says nothing, rather than the window's edge",
          edge is None, str(edge))
    # And one a little longer again, 245, which never dips under the
    # threshold: the deepest point is then the answer, and it is at the edge.
    deeper = read({"shape": "sine", "freq": 44100 / 245}, 441)["hz"]
    check("nor does one that never dips at all, whose deepest point is the edge",
          deeper is None, str(deeper))
    swing = read({"mode": "harmonograph", "swingRate": 2.1}, 88200)["hz"]
    check("a harmonograph at 2.1 Hz on a two-second window reads 2.1, through the second pass",
          near(swing, 2.1, 0.02), str(swing))
    noise = read({"shape": "noise"}, 8820)
    check("noise is not a note: no frequency, and aperiodicity over a half",
          noise["hz"] is None and noise["aperiodicity"] > 0.5, str(noise))
    # A tone under noise at half its level: noisy enough that no dip reaches
    # YIN's threshold, clean enough to trust. Seeded, so it is the same
    # noise every run. Summed rather than averaged over each lag, and taken
    # at the deepest point rather than the earliest nearly as deep, this
    # read 10.5 Hz and then 49.
    noisy = p.evaluate("""() => {
      const rate = 44100, n = 8820, x = new Float32Array(n);
      let seed = 12345;
      const rand = () => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; };
      for (let i = 0; i < n; i++) x[i] = Math.sin(2 * Math.PI * 147 * i / rate) + 0.5 * Math.sqrt(6) * (rand() - 0.5);
      const f = estimatePeriod(x, rate);
      return { hz: estimateFrequency(x, rate), aperiodicity: f.aperiodicity };
    }""")
    check("a 147 Hz tone under noise at half its level reads 147, with the noise in its aperiodicity",
          near(noisy["hz"], 147, 0.5) and 0.1 < noisy["aperiodicity"] < 0.35, str(noisy))
    chords = p.evaluate("""() => {
      const rate = 44100, n = 8820, a = new Float32Array(n), e = new Float32Array(n);
      for (let i = 0; i < n; i++) {
        const t = i / rate;
        a[i] = (Math.sin(2 * Math.PI * 260 * t) + Math.sin(2 * Math.PI * 325 * t) + Math.sin(2 * Math.PI * 390 * t)) / 3;
        e[i] = (Math.sin(2 * Math.PI * 261.63 * t) + Math.sin(2 * Math.PI * 329.63 * t) + Math.sin(2 * Math.PI * 392 * t)) / 3;
      }
      const j = estimatePeriod(a, rate), q = estimatePeriod(e, rate);
      return { just: j.hz, justAp: j.aperiodicity, equal: q.hz, equalAp: q.aperiodicity };
    }""")
    print("    %s" % chords)
    check("a just triad 4:5:6 on 260 Hz reads 65, its common period",
          near(chords["just"], 65, 0.01), str(chords["just"]))

    print("\n--- the page uses it ---")
    page = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const freqText = () => { const t = document.body.innerText; const i = t.indexOf('freq');
                               return t.slice(i + 5, i + 14).trim(); };
      el.dispYT.click();
      el.freq.value = '220'; el.freq.dispatchEvent(new Event('input'));
      el.shape.value = 'drawbars'; el.shape.dispatchEvent(new Event('change'));
      el.bars.value = '008888000'; el.bar0.dispatchEvent(new Event('input'));
      const readout = {};
      for (const tb of [3, 4, 5, 6]) {
        el.timebase.value = String(tb); el.timebase.dispatchEvent(new Event('input'));
        await wait(600);
        readout[tb] = freqText();
      }
      el.autoset.click(); await wait(100);
      const autoRich = state.timebase;
      el.shape.value = 'sine'; el.shape.dispatchEvent(new Event('change'));
      await wait(300);
      el.autoset.click(); await wait(100);
      const autoSine = state.timebase;
      return { readout, autoRich, autoSine };
    }""")
    print("    %s" % page)
    check("the readout says 220.0 Hz for 00 8888 000 at 1, 2, 5 and 10 ms/div",
          all(v.startswith("220.0 Hz") for v in page["readout"].values()), str(page["readout"]))
    check("and Autoset chooses the same timebase for it as for a sine at 220 - it used to see twice the pitch",
          page["autoRich"] == page["autoSine"], str((page["autoRich"], page["autoSine"])))

    lag = p.evaluate("""async () => {
      const rate = 44100, n = Math.round(LAG_PROBE_SECONDS * rate);
      const tone = new Float32Array(n), hiss = new Float32Array(n);
      for (let i = 0; i < n; i++) { tone[i] = Math.sin(2 * Math.PI * 147 * i / rate); hiss[i] = Math.random() * 2 - 1; }
      const t = estimatePeriod(tone, rate), h = estimatePeriod(hiss, rate);
      return { max: LAG_APERIODIC_MAX, tone: t.aperiodicity, hiss: h.aperiodicity };
    }""")
    check("the lag's gate lets a tone through and holds noise back, on the new scale",
          lag["tone"] < lag["max"] < lag["hiss"], str(lag))
    # Through the lag's own update, which is where the gate is: the numbers
    # above being right says nothing about whether it reads them.
    locked = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      midiPanic();
      const was = { on: state.lagOn, auto: state.lagAuto };
      state.lagOn = true; state.lagAuto = true;
      const frame = { rate: state.source.sampleRate };
      el.shape.value = 'noise'; el.shape.dispatchEvent(new Event('change'));
      await wait(400);
      lagLock = null;
      for (let i = 0; i < 5; i++) lagLockUpdate(frame);
      const hiss = lagLock;
      /* Noise alone reads outside the lag's range - above 5 kHz - and the
         range check turns it away before the gate is asked, so noise alone
         could not show the gate working. A tone at 147 Hz under noise as loud as itself is in
         range, and aperiodic: only the gate stands between it and a lock. */
      const real = state.source.getLatestWindow;
      state.source.getLatestWindow = (n) => {
        const x = new Float32Array(n);
        for (let i = 0; i < n; i++) x[i] = Math.sin(2 * Math.PI * 147 * i / frame.rate) + Math.sqrt(6) * (Math.random() - 0.5) * 1.0;
        return [x, x];
      };
      lagLock = null;
      for (let i = 0; i < 5; i++) lagLockUpdate(frame);
      const buried = lagLock;
      const buriedAp = estimatePeriod(state.source.getLatestWindow(8820)[0], frame.rate).aperiodicity;
      state.source.getLatestWindow = real;
      el.shape.value = 'sine'; el.shape.dispatchEvent(new Event('change'));
      el.freq.value = '147'; el.freq.dispatchEvent(new Event('input'));
      await wait(400);
      lagLockUpdate(frame);
      const tone = lagLock;
      state.lagOn = was.on; state.lagAuto = was.auto; lagLock = null;
      return { hiss, buried, buriedAp, tone, want: 0.25 / 147 };
    }""")
    print("    the automatic lag: on noise %s, on 147 Hz %s s (a quarter period is %.6f)"
          % (locked["hiss"], locked["tone"], locked["want"]))
    check("the automatic lag does not lock to noise, or to a tone buried in it, and locks to a clean one",
          locked["hiss"] is None and locked["buried"] is None and locked["buriedAp"] > 0.15
          and locked["tone"] is not None
          and abs(locked["tone"] - locked["want"]) < 1e-6, str(locked))

    print("\n--- what it costs ---")
    cost = p.evaluate("""() => {
      const rate = 44100, x = new Float32Array(16384);
      for (let i = 0; i < x.length; i++) x[i] = Math.sin(2 * Math.PI * 220 * i / rate);
      for (let i = 0; i < 5; i++) estimatePeriod(x, rate);
      const times = [];
      for (let i = 0; i < 20; i++) { const t0 = performance.now(); estimatePeriod(x, rate); times.push(performance.now() - t0); }
      times.sort((a, b) => a - b);
      return { median: times[10], worst: times[19] };
    }""")
    print("    the largest window, 16384 samples: median %.2f ms, worst %.2f ms" % (cost["median"], cost["worst"]))
    check("the largest window costs under ten milliseconds - it is paid each frame the tuner is open",
          cost["median"] < 10, str(cost))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the estimator reads the sound's period, whatever the wave does on the way round")
