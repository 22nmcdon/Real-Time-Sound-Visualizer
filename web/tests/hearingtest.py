"""What the sound says, as sources (Stage J1).

Each source against a fixture whose answer is known, and each written against
the way it would fail:

- a pitch that reads the wrong octave, or goes to middle C when the note
  stops: a 440 Hz and a 110 Hz sine, two octaves apart, read 0.375 and -0.625,
  and silence after the 110 leaves -0.625 standing;
- a pitch that ignores the key a player is holding: a held A4 over a 110 Hz
  input reads A4;
- a brightness or a band that measures the level rather than where the energy
  is: 200 Hz and 4 kHz sines at one level read low and high, and a 60 Hz and a
  2 kHz sine each fill their own band and leave the other three empty;
- a width that cannot tell mono from opposite from unrelated;
- a flux that is high on a held tone, or never rises on a new one;
- a step: every value is slew-limited or followed, and an octave-and-a-half
  jump in pitch is measured frame by frame against the limit;
- a loop that is not bounded: on the generator these hear its own output and
  must take the picture's reach and the loop's total, and a switch of source
  must change that without anyone touching a routing.
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

C4 = 261.6256
PITCH = lambda hz: max(-1, min(1, math.log2(hz / C4) / 2))
BRIGHT = lambda hz: max(0, min(1, math.log2(hz / 100) / math.log2(80)))

STUB = """
  window.__midi = { port: null };
  navigator.requestMIDIAccess = function () {
    const port = { id: "stub", name: "Stub Keyboard", onmidimessage: null };
    window.__midi.port = port;
    return Promise.resolve({ inputs: new Map([["stub", port]]), outputs: new Map(), onstatechange: null });
  };
  window.__send = (bytes) => window.__midi.port.onmidimessage({ data: Uint8Array.from(bytes) });
  window.__wait = (ms) => new Promise((r) => setTimeout(r, ms));
  /* A microphone the test plays: oscillator A on the left, and on the right
     A again, A upside down, or a second oscillator C - chosen by gains. */
  window.__mic = async () => {
    const ctx = new AudioContext();
    const merge = ctx.createChannelMerger(2), dest = ctx.createMediaStreamDestination();
    const a = ctx.createOscillator(), c = ctx.createOscillator();
    const gl = ctx.createGain(), rs = ctx.createGain(), ri = ctx.createGain(), rc = ctx.createGain();
    a.connect(gl); gl.connect(merge, 0, 0);
    a.connect(rs); rs.connect(merge, 0, 1);
    a.connect(ri); ri.connect(merge, 0, 1);
    c.connect(rc); rc.connect(merge, 0, 1);
    merge.connect(dest); a.start(); c.start();
    window.__osc = { ctx, a, c, gl, rs, ri, rc };
    __play(220, 'same', 0.8);
    navigator.mediaDevices.getUserMedia = () => Promise.resolve(dest.stream);
    el.srcMic.click(); await __wait(1200);
  };
  window.__play = (hz, right, level) => {
    const o = window.__osc, t = o.ctx.currentTime;
    o.a.frequency.setValueAtTime(hz, t); o.c.frequency.setValueAtTime(hz * 1.5, t);
    o.gl.gain.setValueAtTime(level, t);
    o.rs.gain.setValueAtTime(right === 'same' ? level : 0, t);
    o.ri.gain.setValueAtTime(right === 'inverted' ? -level : 0, t);
    o.rc.gain.setValueAtTime(right === 'other' ? level : 0, t);
  };
  window.__read = () => ({ pitch: hearing.pitch, bright: hearing.bright, bands: hearing.bands.slice(),
                           width: hearing.width, flux: hearing.flux, cost: hearing.cost });
"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.add_init_script(STUB)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()

    def at(hz, right="same", level=0.8, settle=900):
        return p.evaluate("async ([hz, right, level, settle]) => { __play(hz, right, level); "
                          "await __wait(settle); return __read(); }", [hz, right, level, settle])

    print("\n--- registered ---")
    reg = p.evaluate("""() => {
      const ids = [...MOD_SOURCES.values()].filter((s) => s.family === 'hearing').map((s) => s.id);
      setView('bench'); setBenchTab('sources');
      const fam = el.srcGrid.querySelector('[data-family="hearing"]');
      return { ids, chips: fam ? fam.querySelectorAll('.mod-chip').length : 0 };
    }""")
    check("eight sources that hear, in a family of their own on the Sources tab",
          len(reg["ids"]) == 8 and reg["chips"] == 8, str(reg))

    p.evaluate("() => __mic()")
    print("\n--- pitch ---")
    hi = at(440, settle=1200)
    lo = at(110, settle=1200)
    print("    440 Hz reads %.4f (want %.4f), 110 Hz reads %.4f (want %.4f)"
          % (hi["pitch"], PITCH(440), lo["pitch"], PITCH(110)))
    check("440 Hz and 110 Hz read their octaves from middle C, a tenth of a semitone either way",
          abs(hi["pitch"] - PITCH(440)) < 0.005 and abs(lo["pitch"] - PITCH(110)) < 0.005,
          "%.4f, %.4f" % (hi["pitch"], lo["pitch"]))
    quiet = at(110, level=0, settle=700)
    # The width too: silence correlates to nothing, and a width that went to
    # nought whenever the player stopped would be a source that lied.
    check("and silence after the 110 leaves it standing, rather than sending it to middle C, and the width too",
          abs(quiet["pitch"] - PITCH(110)) < 0.005 and quiet["width"] > 0.98,
          "%.4f, width %.3f" % (quiet["pitch"], quiet["width"]))
    p.evaluate("() => midiConnect()"); p.wait_for_timeout(200)
    held = p.evaluate("""async () => {
      __play(110, 'same', 0.8); await __wait(600);
      __send([0x90, 69, 100]); await __wait(700);
      const on = hearing.pitch;
      __send([0x80, 69, 0]); await __wait(700);
      return { on, off: hearing.pitch };
    }""")
    check("a held A4 over a 110 Hz input reads A4, and letting go gives the input back",
          abs(held["on"] - PITCH(440)) < 0.005 and abs(held["off"] - PITCH(110)) < 0.005, str(held))

    print("\n--- brightness and the bands ---")
    dull, keen = at(200), at(4000)
    print("    200 Hz %.3f (want %.3f), 4 kHz %.3f (want %.3f)" % (dull["bright"], BRIGHT(200),
                                                                   keen["bright"], BRIGHT(4000)))
    check("brightness puts a 200 Hz sine low and a 4 kHz one high, at one level, where the centroid says",
          abs(dull["bright"] - BRIGHT(200)) < 0.03 and abs(keen["bright"] - BRIGHT(4000)) < 0.03,
          "%.3f, %.3f" % (dull["bright"], keen["bright"]))
    low, mid = at(60, settle=1200), at(2000, settle=1200)
    print("    60 Hz bands %s; 2 kHz bands %s" % (["%.3f" % v for v in low["bands"]],
                                                   ["%.3f" % v for v in mid["bands"]]))
    empty = lambda bands, i: all(v < 0.05 for j, v in enumerate(bands) if j != i)
    check("a full-scale-ish 60 Hz sine fills the low band at its level, 0.8, and leaves the other three empty",
          abs(low["bands"][0] - 0.8) < 0.04 and empty(low["bands"], 0), str(low["bands"]))
    check("and a 2 kHz one fills the high-mid band instead", abs(mid["bands"][2] - 0.8) < 0.04
          and empty(mid["bands"], 2), str(mid["bands"]))

    print("\n--- width ---")
    same, inv, other = at(220, "same"), at(220, "inverted"), at(220, "other")
    print("    same %.3f, inverted %.3f, a fifth apart %.3f" % (same["width"], inv["width"], other["width"]))
    check("width reads one for mono, minus one for a channel upside down, and near nought for a fifth apart",
          same["width"] > 0.98 and inv["width"] < -0.98 and abs(other["width"]) < 0.1,
          "%.3f, %.3f, %.3f" % (same["width"], inv["width"], other["width"]))

    print("\n--- flux ---")
    steady = at(330, settle=1500)
    struck = p.evaluate("""async () => {
      // A note struck four times a second: on for 120 ms, off for 130.
      let peak = 0, on = false;
      const t0 = performance.now();
      const timer = setInterval(() => { on = !on; __play(330, 'same', on ? 0.8 : 0); }, 125);
      while (performance.now() - t0 < 1500) { await __wait(16); peak = Math.max(peak, hearing.flux); }
      clearInterval(timer); __play(330, 'same', 0.8);
      return peak;
    }""")
    stopped = p.evaluate("""async () => {
      __play(330, 'same', 0.8); await __wait(1200);
      // Released over 80 ms, as a note ends. Cut off in one sample it is a
      // click, which is broadband and a real rise; this checks the release.
      let peak = 0;
      const o = __osc, t = o.ctx.currentTime;
      for (const g of [o.gl, o.rs]) { g.gain.setValueAtTime(0.8, t); g.gain.linearRampToValueAtTime(0, t + 0.08); }
      const t0 = performance.now();
      while (performance.now() - t0 < 400) { await __wait(10); peak = Math.max(peak, hearing.flux); }
      __play(330, 'same', 0.8); await __wait(600);
      return peak;
    }""")
    print("    held tone %.3f; struck four times a second, peak %.3f; stopped, peak %.3f"
          % (steady["flux"], struck, stopped))
    # Rising energy only: a note ending is not a new event, and a flux that
    # rose on releases would throw an echo or a hit at every lift of a key.
    check("and a note stopping does not raise it: only rising energy counts", stopped < 0.1, "%.3f" % stopped)
    check("flux is near nought on a held tone and rises on struck ones",
          steady["flux"] < 0.05 and struck > 0.3, "%.3f, %.3f" % (steady["flux"], struck))

    print("\n--- continuity ---")
    glide = p.evaluate("""async () => {
      __play(110, 'same', 0.8); await __wait(1200);
      const trace = [];
      __play(880, 'same', 0.8);
      const t0 = performance.now();
      await new Promise((done) => {
        const tick = (t) => { trace.push([t, hearing.pitch]); if (t - t0 < 900) requestAnimationFrame(tick); else done(); };
        requestAnimationFrame(tick);
      });
      let steepest = 0;
      for (let i = 1; i < trace.length; i++) {
        const dt = (trace[i][0] - trace[i - 1][0]) / 1000;
        if (dt > 0) steepest = Math.max(steepest, Math.abs(trace[i][1] - trace[i - 1][1]) / dt);
      }
      return { steepest, end: trace[trace.length - 1][1], frames: trace.length };
    }""")
    print("    110 to 880 Hz: steepest %.2f a second, limit 4; ends at %.4f (want %.4f)"
          % (glide["steepest"], glide["end"], PITCH(880)))
    # A frame's timestamp and the page's own elapsed can differ by a frame's
    # jitter, so the limit is held to a tenth over.
    check("a jump of an octave and a half is a glide inside the slew limit, not a step, and arrives",
          glide["steepest"] <= 4.4 and abs(glide["end"] - PITCH(880)) < 0.005 and glide["frames"] > 20,
          str(glide))

    cost = p.evaluate("""async () => { let worst = 0, sum = 0, n = 0;
      for (let i = 0; i < 60; i++) { await __wait(16); worst = Math.max(worst, hearing.cost); sum += hearing.cost; n++; }
      return { mean: sum / n, worst }; }""")
    print("    cost a frame: mean %.2f ms, worst %.2f ms" % (cost["mean"], cost["worst"]))
    check("and all of it costs under two milliseconds a frame on average", cost["mean"] < 2, str(cost))

    print("\n--- the loop ---")
    loop = p.evaluate("""async () => {
      const src = MOD_SOURCES.get('hear.bright');
      state.modRoutings = [{ sourceId: 'hear.bright', destId: 'gen.fm', amount: 1 }]; touchRoutings();
      await __wait(200);
      if (modDirty) compileRoutes();
      const mic = { loop: src.fromPicture, amount: routingAmount(src, 1),
                    total: genRoutes.some((r) => r.loopTotal) };
      // Switched with the routing left alone: the page has to notice.
      el.srcTone.click(); await __wait(600);
      if (modDirty) compileRoutes();
      const tone = { loop: src.fromPicture, amount: routingAmount(src, 1),
                     total: genRoutes.some((r) => r.loopTotal) };
      state.modRoutings = []; touchRoutings();
      return { mic, tone };
    }""")
    print("    %s" % loop)
    check("hearing a microphone they are ordinary sources, at full reach and routed directly",
          loop["mic"] == {"loop": False, "amount": 1, "total": False}, str(loop["mic"]))
    check("hearing the generator they are a loop: the picture's reach, and into the one bounded total",
          loop["tone"] == {"loop": True, "amount": 0.5, "total": True}, str(loop["tone"]))

    # Now on the tone. An amount asked for on a microphone, 0.6, must survive a
    # visit to the generator: applied at the loop's reach there, shown at it,
    # and 0.6 again back on the microphone. Clamped in storage, it came back
    # as 0.5 and the preset that asked for 0.6 was quietly a different one.
    kept = p.evaluate("""async () => {
      state.modRoutings = [{ sourceId: 'hear.bright', destId: 'gen.fm', amount: 0.6 }]; touchRoutings();
      await __wait(300);
      const src = MOD_SOURCES.get('hear.bright'), r = state.modRoutings[0];
      const tone = { stored: r.amount, applied: routingAmount(src, r.amount),
                     shown: /value="50"/.test(depthRowHTML(r, 'x', 'ch1', 'x')) };
      await __mic(); await __wait(400);
      const mic = { stored: state.modRoutings[0].amount, applied: routingAmount(src, state.modRoutings[0].amount) };
      state.modRoutings = []; touchRoutings();
      return { tone, mic };
    }""")
    print("    %s" % kept)
    check("an amount of 0.6 is applied and shown at the loop's 0.5 on the generator, and is 0.6 again on a microphone",
          kept["tone"] == {"stored": 0.6, "applied": 0.5, "shown": True}
          and kept["mic"] == {"stored": 0.6, "applied": 0.6}, str(kept))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
raise SystemExit(1 if fails else 0)
