import sys
from playwright.sync_api import sync_playwright
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)                    # web/, which holds scope.html
SHOTS = os.path.join(HERE, "shots")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
os.makedirs(SHOTS, exist_ok=True)

import fixtures
STEMS = fixtures.ensure()
fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    p.evaluate("() => { setView('bench'); setBenchTab('play'); }"); p.wait_for_timeout(150)
    p.locator("#srcFile").click(no_wait_after=True); p.wait_for_timeout(150)
    p.locator("#fileInput").set_input_files(f"{STEMS}/test-fifth.wav")
    p.wait_for_timeout(2000)

    info = p.evaluate("""() => ({ kind: state.source.kind, rate: state.source.sampleRate,
                                  cap: state.source.capacity })""")
    print("\n--- the source under test ---")
    print("  %s at %d Hz, buffer holds %d samples (%.0f ms)"
          % (info["kind"], info["rate"], info["cap"], info["cap"] / info["rate"] * 1000))
    check("a real graph source is loaded", info["kind"] == "file" and info["cap"] == 32768)

    print("\n--- what capture asks for, at every timebase and trigger position ---")
    rows = p.evaluate("""() => {
      const src = state.source;
      const real = src.getLatestWindow.bind(src);
      let worst = 0;
      src.getLatestWindow = (n) => { if (n > worst) worst = n; return real(n); };
      const out = [];
      for (const lagOn of [false, true]) {
        state.lagOn = lagOn; state.lagAuto = false; state.lagMs = 40;
        for (let t = 0; t < TIMEBASE.length; t++) {
          for (const pos of [0, 0.5, 1]) {
            state.timebase = t; state.position = pos;
            worst = 0;
            const f = capture();
            let flat = 0;                       // leading samples that are exactly zero
            const c = f.channels[0];
            while (flat < c.length && c[flat] === 0) flat++;
            out.push({ lagOn, div: TIMEBASE[t], pos, ask: worst, cap: src.capacity,
                       over: worst - src.capacity, lag: +state.lagActual.toFixed(2),
                       starved: state.starved, flat,
                       finite: c.every(Number.isFinite) });
          }
        }
      }
      state.lagOn = false; state.timebase = 4; state.position = 0.1;
      return out;
    }""")

    over = [r for r in rows if r["over"] > 0]
    check("never asks for more than the buffer holds", over == [],
          "worst: %s" % (over[0] if over else ""))
    check("no flatline at the left edge", all(r["flat"] < 8 for r in rows),
          "worst %d samples" % max(r["flat"] for r in rows))
    check("no NaN anywhere", all(r["finite"] for r in rows))

    longest = [r for r in rows if r["div"] == 50 and r["lagOn"]]
    print("  at 50 ms/div with 40 ms of lag asked for:")
    for r in longest:
        print("    position %3d%%   asked %6d of %d   lag granted %.1f ms   starved %d"
              % (r["pos"] * 100, r["ask"], r["cap"], r["lag"], r["starved"]))
    mid = [r for r in rows if r["div"] == 2 and r["lagOn"]]
    check("granted in full when there is room",
          all(abs(r["lag"] - 40) < 0.01 for r in mid),
          "got %s" % [r["lag"] for r in mid])

    # This browser opens its AudioContext at 44.1 kHz, where a 500 ms window
    # and 40 ms of lag still fit in 32768 samples. At 48 kHz they do not, and
    # nor would they on a 96 kHz interface. Squeeze the buffer directly so the
    # order of give-way is tested as policy rather than left to the hardware.
    print("\n--- what gives way first, under a forced squeeze ---")
    squeeze = p.evaluate("""() => {
      const src = state.source;
      let fake = 32768;
      Object.defineProperty(src, 'capacity', { configurable: true, get: () => fake });
      const real = src.getLatestWindow.bind(src);
      let worst = 0;
      src.getLatestWindow = (n) => { if (n > worst) worst = n; return real(n); };

      state.lagOn = true; state.lagAuto = false; state.lagMs = 40;
      state.timebase = 8; state.position = 0.5;          // 50 ms/div = 500 ms
      const out = [];
      for (const cap of [32768, 26000, 24000, 20000]) {
        fake = cap; worst = 0;
        const f = capture();
        out.push({ cap, ask: worst, lag: +state.lagActual.toFixed(2),
                   starved: state.starved, len: f.length,
                   finite: f.channels[0].every(Number.isFinite) });
      }
      state.lagOn = false; state.timebase = 4; state.position = 0.1;
      delete src.capacity;
      return out;
    }""")
    for r in squeeze:
        print("    buffer %5d   asked %5d   window %5d   lag %5.1f ms   starved %5d"
              % (r["cap"], r["ask"], r["len"], r["lag"], r["starved"]))

    by = {r["cap"]: r for r in squeeze}
    check("the window is never shortened",
          all(r["len"] == squeeze[0]["len"] for r in squeeze),
          "lengths %s" % [r["len"] for r in squeeze])
    check("search headroom gives way first, keeping the lag",
          by[26000]["lag"] == 40 and by[26000]["ask"] <= 26000,
          "lag %.1f ms, asked %d" % (by[26000]["lag"], by[26000]["ask"]))
    check("the lag goes next, rather than starving the trigger",
          by[24000]["lag"] == 0 and by[24000]["ask"] <= 24000,
          "lag %.1f ms, asked %d" % (by[24000]["lag"], by[24000]["ask"]))
    check("a window longer than the buffer is reported, not hidden",
          by[20000]["starved"] > 0 and by[20000]["ask"] <= by[20000]["len"],
          "starved %d samples" % by[20000]["starved"])
    check("still no NaN under the squeeze", all(r["finite"] for r in squeeze))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("all capacity checks pass")
