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

# Roundness as the ratio of the principal axes, from the 2x2 covariance.
# Not min/max radius: the capture window holds a fractional number of cycles,
# so the sample mean sits a couple of percent off centre, and an extreme
# statistic reads that as eccentricity that is not there. Covariance
# eigenvalues are averages and barely move. 1.0 is a circle.
SHAPE = """() => {
  const f = capture();
  const x = f.channels[0], y = f.channels[1], n = x.length;
  let mx=0, my=0;
  for (let i=0;i<n;i++){ mx+=x[i]; my+=y[i]; }
  mx/=n; my/=n;
  let sxy=0, sxx=0, syy=0;
  for (let i=0;i<n;i++){
    const a=x[i]-mx, b=y[i]-my;
    sxy+=a*b; sxx+=a*a; syy+=b*b;
  }
  sxy/=n; sxx/=n; syy/=n;
  const tr = sxx + syy, det = sxx*syy - sxy*sxy;
  const disc = Math.sqrt(Math.max(0, tr*tr/4 - det));
  const hi = tr/2 + disc, lo = tr/2 - disc;
  return {
    corr: sxy/Math.sqrt(sxx*syy || 1e-30),
    round: hi > 0 ? Math.sqrt(Math.max(0, lo)/hi) : 0,
    finite: x.every(Number.isFinite) && y.every(Number.isFinite),
    lag: state.lagActual,
  };
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text) if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    print("\n--- boot ---")
    check("no errors on boot", not bad, "; ".join(bad[:3]))

    # ---- the request never exceeds what the source holds --------------------
    print("\n--- capacity, by watching what capture actually asks for ---")
    over = p.evaluate("""() => {
      const src = state.source;
      const real = src.getLatestWindow.bind(src);
      let worst = 0;
      src.getLatestWindow = (n) => { if (n > worst) worst = n; return real(n); };
      const rows = [];
      const wasT = state.timebase, wasOn = state.lagOn, wasAuto = state.lagAuto;
      state.lagOn = true; state.lagAuto = false; state.lagMs = 40;
      for (let t = 0; t < TIMEBASE.length; t++) {
        for (const pos of [0, 0.5, 1]) {
          state.timebase = t; state.position = pos;
          worst = 0; capture();
          rows.push({ t: TIMEBASE[t], pos, ask: worst, cap: src.capacity });
        }
      }
      state.timebase = wasT; state.position = 0.1;
      state.lagOn = wasOn; state.lagAuto = wasAuto;
      return rows.filter(r => r.ask > r.cap);
    }""")
    check("tone source: never over-asks", over == [], str(over[:2]))

    # ---- the null test: a sine, quarter-period lag, is a circle -------------
    print("\n--- lag X-Y on a 440 Hz sine ---")
    p.evaluate("""() => {
      el.shape.value = 'sine'; el.shape.dispatchEvent(new Event('change'));
      el.freq.value = '440'; el.freq.dispatchEvent(new Event('input'));
      el.interval.value = '0'; el.interval.dispatchEvent(new Event('change'));
      el.phase.value = '0'; el.phase.dispatchEvent(new Event('input'));
      setDisplay('xy');
      state.timebase = 3; state.position = 0.1;
    }""")
    p.wait_for_timeout(300)

    off = p.evaluate(SHAPE)
    check("lag off: the two lanes are one signal, so a diagonal",
          abs(off["corr"]) > 0.99 and off["round"] < 0.05,
          "corr %.4f  roundness %.4f" % (off["corr"], off["round"]))

    p.evaluate("""() => {
      el.lagOn.checked = true; el.lagOn.dispatchEvent(new Event('change'));
      setLagAuto(false);
      state.lagMs = 0.25 / 440 * 1000;      // an exact quarter period
    }""")
    p.wait_for_timeout(300)
    on = p.evaluate(SHAPE)
    check("quarter-period lag: a circle", abs(on["corr"]) < 0.05 and on["round"] > 0.97,
          "corr %.4f  roundness %.4f  tau %.4f ms" % (on["corr"], on["round"], on["lag"]))
    check("all samples finite", on["finite"])

    # ---- fractional delay earns its keep at 5 kHz ---------------------------
    print("\n--- fractional delay at 4 kHz (quarter period = 2.76 samples) ---")
    p.evaluate("""() => {
      el.freq.value = '4000'; el.freq.dispatchEvent(new Event('input'));
      state.lagMs = 0.25 / 4000 * 1000;
    }""")
    p.wait_for_timeout(400)
    fine = p.evaluate(SHAPE)
    # The same figure, but with the delay rounded to whole samples.
    coarse = p.evaluate("""() => {
      const f = capture();
      const rate = f.rate;
      const tau = Math.round(0.25 / 4000 * rate);      // whole samples
      const src = state.source.getLatestWindow(f.channels[0].length + tau);
      const x = src[0].subarray(tau), y = src[0].subarray(0, src[0].length - tau);
      const n = Math.min(x.length, y.length);
      let mx=0,my=0; for(let i=0;i<n;i++){mx+=x[i];my+=y[i];} mx/=n; my/=n;
      let sxy=0,sxx=0,syy=0;
      for(let i=0;i<n;i++){ const a=x[i]-mx,b=y[i]-my; sxy+=a*b; sxx+=a*a; syy+=b*b; }
      sxy/=n; sxx/=n; syy/=n;
      const tr=sxx+syy, det=sxx*syy-sxy*sxy;
      const disc=Math.sqrt(Math.max(0,tr*tr/4-det));
      return Math.sqrt(Math.max(0,tr/2-disc)/(tr/2+disc));
    }""")
    check("interpolated is rounder than whole-sample", fine["round"] > coarse + 0.05,
          "interpolated %.3f  vs  rounded %.3f" % (fine["round"], coarse))

    slider = p.evaluate("""() => {
      el.freq.value = '440'; el.freq.dispatchEvent(new Event('input'));
      el.lag.value = '6'; el.lag.dispatchEvent(new Event('input'));   // 0.6 ms
      return state.lagMs;
    }""")
    p.wait_for_timeout(300)
    viaSlider = p.evaluate(SHAPE)
    # 0.6 ms is the nearest tenth to a quarter period at 440 Hz (0.568 ms),
    # so the figure is a slightly tilted ellipse rather than a true circle.
    check("the slider drives it too", abs(slider - 0.6) < 1e-9 and viaSlider["round"] > 0.90,
          "%.1f ms  roundness %.4f" % (slider, viaSlider["round"]))

    # ---- the slow lock ------------------------------------------------------
    print("\n--- the automatic lag locks slowly and gates on periodicity ---")
    p.evaluate("""() => {
      el.freq.value = '440'; el.freq.dispatchEvent(new Event('input'));
      setLagAuto(true);
    }""")
    p.wait_for_timeout(2500)
    locked = p.evaluate("() => ({ lock: lagLock, want: 0.25/440 })")
    check("locks onto a quarter period", locked["lock"] is not None
          and abs(locked["lock"] - locked["want"]) / locked["want"] < 0.15,
          "locked %.6f s, wanted %.6f s" % (locked["lock"] or 0, locked["want"]))

    moved = p.evaluate("""() => {
      const before = lagLock;
      el.freq.value = '660'; el.freq.dispatchEvent(new Event('input'));
      return before;
    }""")
    p.wait_for_timeout(400)
    soon = p.evaluate("() => lagLock")
    p.wait_for_timeout(3000)
    later = p.evaluate("() => lagLock")
    step = abs(soon - moved) / moved
    check("a new note does not snap the lag", step < 0.35, "moved %.1f%% in 400 ms" % (step * 100))
    check("but it does get there", abs(later - 0.25 / 660) / (0.25 / 660) < 0.2,
          "after 3.4 s: %.6f s, wanted %.6f s" % (later, 0.25 / 660))

    # ---- noise is not periodic, so the lock must refuse it ------------------
    # The lock reads its own block from the source, so noise has to be fed in
    # there rather than through the frame.
    noisy = p.evaluate("""() => {
      lagLock = null;
      const src = state.source;
      const real = src.getLatestWindow.bind(src);
      src.getLatestWindow = (n) => {
        const x = new Float32Array(n);
        for (let i = 0; i < n; i++) x[i] = Math.random() * 2 - 1;
        return [x, x];
      };
      for (let i = 0; i < 20; i++) lagLockUpdate({ channels: [new Float32Array(8)], rate: 44100 });
      const got = lagLock;
      src.getLatestWindow = real;
      return got;
    }""")
    check("noise does not produce a lock", noisy is None, "lock = %s" % noisy)

    # The bug the square-wave screenshot found: at 2 ms/div the displayed
    # window holds 2.2 periods of a 110 Hz note, which is two crossings and no
    # evidence of anything. The lock must not depend on the timebase.
    print("\n--- the lock does not depend on the timebase ---")
    p.evaluate("""() => {
      lagLock = null;
      el.shape.value = 'square'; el.shape.dispatchEvent(new Event('change'));
      el.freq.value = '110'; el.freq.dispatchEvent(new Event('input'));
      state.timebase = 4;                     // 2 ms/div: a 20 ms window
      setLagAuto(true);
    }""")
    p.wait_for_timeout(3000)
    lowNote = p.evaluate("""() => ({
      lock: lagLock, want: 0.25 / 110,
      windowPeriods: +(windowMs() / 1000 * 110).toFixed(2),
    })""")
    check("a 110 Hz square locks at 2 ms/div",
          lowNote["lock"] is not None
          and abs(lowNote["lock"] - lowNote["want"]) / lowNote["want"] < 0.15,
          "window holds %.2f periods; locked %s, wanted %.6f"
          % (lowNote["windowPeriods"], ("%.6f" % lowNote["lock"]) if lowNote["lock"] else None,
             lowNote["want"]))
    p.evaluate("""() => {
      el.shape.value = 'sine'; el.shape.dispatchEvent(new Event('change'));
      el.freq.value = '440'; el.freq.dispatchEvent(new Event('input'));
      state.timebase = 3;
    }""")

    # ---- the two switches cannot both be on ---------------------------------
    print("\n--- mid/side and lag are exclusive ---")
    excl = p.evaluate("""() => {
      el.lagOn.checked = true; el.lagOn.dispatchEvent(new Event('change'));
      el.midSide.checked = true; el.midSide.dispatchEvent(new Event('change'));
      const a = { lag: state.lagOn, ms: state.midSide, box: el.lagOn.checked };
      el.lagOn.checked = true; el.lagOn.dispatchEvent(new Event('change'));
      const b = { lag: state.lagOn, ms: state.midSide, box: el.midSide.checked };
      return { a, b };
    }""")
    check("mid/side turns lag off, on the page too",
          not excl["a"]["lag"] and excl["a"]["ms"] and not excl["a"]["box"], str(excl["a"]))
    check("and the other way round",
          excl["b"]["lag"] and not excl["b"]["ms"] and not excl["b"]["box"], str(excl["b"]))

    # ---- preset round trip --------------------------------------------------
    print("\n--- the setup survives a round trip ---")
    trip = p.evaluate("""() => {
      el.lagOn.checked = true; el.lagOn.dispatchEvent(new Event('change'));
      setLagAuto(false);
      el.lag.value = '123'; el.lag.dispatchEvent(new Event('input'));
      const before = snapshot();
      const code = encodeSetup(before);
      restore(decodeSetup(code));
      const after = snapshot();
      const differ = Object.keys(before).filter(k => before[k] !== after[k]);
      return { differ, lagMs: after.lagMs, lagOn: after.lagOn, lagAuto: after.lagAuto };
    }""")
    check("snapshot survives encode/decode/restore", trip["differ"] == [], str(trip["differ"]))
    check("the lag values come back", trip["lagMs"] == 12.3 and trip["lagOn"] and not trip["lagAuto"],
          str(trip))

    # `.switch` sets overflow:hidden, so a switch that a flex row has squeezed
    # below its content width silently swallows a button rather than wrapping.
    # That is how the Set button shipped invisible; it is cheap to assert for
    # every switch on the page rather than only the one that was caught.
    print("\n--- no switch clips its own buttons ---")
    p.evaluate("""() => {
      el.lagOn.checked = true; el.lagOn.dispatchEvent(new Event('change'));
      el.menuButton.click();
    }""")
    p.wait_for_timeout(300)
    clipped = p.evaluate("""() => {
      const bad = [];
      for (const sw of document.querySelectorAll('.switch')) {
        if (sw.getBoundingClientRect().width === 0) continue;   // in a hidden panel
        let need = 0;
        for (const btn of sw.children) need += btn.getBoundingClientRect().width;
        const have = sw.getBoundingClientRect().width;
        if (need - have > 1) bad.push({
          label: sw.getAttribute('aria-label'),
          have: Math.round(have), need: Math.round(need),
        });
      }
      return bad;
    }""")
    check("every visible switch fits its buttons", clipped == [], str(clipped))
    p.evaluate("() => el.menuButton.click()")

    print("\n--- errors seen at any point ---")
    check("no page errors across the run", not bad, "; ".join(bad[:4]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("all lag checks pass")
