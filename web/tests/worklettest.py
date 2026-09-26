"""The generator in the audio thread: the module, and what happens when it runs.

The generator was arithmetic into a ring buffer and nothing else - the one
source in this page with no audio graph behind it, and therefore the one that
could not be heard, filtered, rotated or monitored. Stage C built all of that
and had nothing to point it at. This is the generator getting an output.

Three things are checked, and the first is the one that catches the mistakes.

THE MODULE RUNS. It is built by stringifying a list of functions, which goes
wrong by leaving one out or by the core reaching for a name that exists only
on the main thread. Neither is a parse error, so `node --check` sees nothing
and the browser reports a worklet that failed to construct. `workletharness.mjs`
evaluates the text against the three globals a worklet actually gets and drives
every mode and every shape, so a missing name is a `ReferenceError` with the
name in it.

IT IS SERVED FROM SOMEWHERE THE BROWSER WILL FETCH. A Blob URL is the obvious
answer and it does not work: from `file://` the origin is opaque, the URL comes
out `blob:null/...`, and `addModule` refuses it. A data URL loads. Both are
tried here rather than assumed, because a page that only worked when served
would be a page most people meet broken.

ONE LOOP, IN ONE PLACE. While the worklet is producing, the main thread must
not be running the same loop - two copies of a stateful generator drift, and
two paths stepping the same oscillator run every rate at double, which this
page has shipped once already. `lfoDriver` names the one that may, both
advance paths check it, and the check throws.
"""
import json, os, subprocess, sys, tempfile
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)


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

    print("\n--- the module, run in Node against a worklet's globals ---")
    built = p.evaluate("""() => ({
      text: generatorModuleSource(), slots: GEN_DESTS.length, echoSlot: ECHO_SLOT,
    })""")
    module_path = os.path.join(tempfile.gettempdir(), "generator-module.js")
    with open(module_path, "w", encoding="utf-8") as f:
        f.write(built["text"])
    print("    %d bytes of module, %d slots"
          % (len(built["text"]), built["slots"]))
    run = subprocess.run(
        [sys.executable and "node", os.path.join(HERE, "workletharness.mjs"),
         module_path, str(built["slots"]), str(built["echoSlot"])],
        capture_output=True, text=True)
    try:
        report = json.loads(run.stdout or "{}")
    except ValueError:
        report = {"ok": False, "error": (run.stdout or run.stderr)[:200]}
    check("it evaluates and registers a processor",
          report.get("ok") and report.get("name") == "generator",
          report.get("error", str(report.get("name"))))

    if report.get("ok"):
        for mode, got in report["modes"].items():
            print("    %-13s peak %.3f, mean square %.5f"
                  % (mode, got["worst"], got["energy"]))
        check("every mode produces finite samples inside full scale",
              all(m["finite"] and m["worst"] <= 1.0 for m in report["modes"].values()),
              str({k: round(v["worst"], 3) for k, v in report["modes"].items()}))
        # Silence would satisfy "finite and inside full scale", which is the
        # sort of check that passes whatever the code does.
        check("and none of them is silence",
              all(m["energy"] > 1e-6 for m in report["modes"].values()),
              str({k: round(v["energy"], 5) for k, v in report["modes"].items()}))
        check("every waveform shape works, band-limited ones included",
              all(sh["finite"] and sh["worst"] > 0.01
                  for sh in report["shapes"].values()),
              str({k: round(v["worst"], 3) for k, v in report["shapes"].items()}))
        # Each of these is a table lookup of its own, and the model lookup is
        # the one that was missing from the module: `MODEL_BY_NAME` is a Map,
        # which `JSON.stringify` turns into `{}`.
        prints = [m["print"] for m in report["models"].values()]
        check("every solid draws, which is the lookup that was missing",
              all(m["finite"] and m["worst"] > 0.01
                  for m in report["models"].values()),
              str({k: round(v["worst"], 3) for k, v in report["models"].items()}))
        # And draws a DIFFERENT solid. `wire.set` keeps what it has when the
        # name is not found, so an empty lookup gives three cubes that are all
        # finite, all loud, and all the same - which is what the missing
        # `MODEL_BY_NAME` did and what the check above could not see.
        check("and each one is a different solid, not the cube three times",
              len(set(prints)) == len(prints), str(prints))
        check("and every figure",
              all(f["finite"] and f["worst"] > 0.01
                  for f in report["figures"].values()),
              str({k: round(v["worst"], 3) for k, v in report["figures"].items()}))
        check("and it posts its samples back rather than only playing them",
              report["posted"] > 0, str(report["posted"]))
        q = report["quantised"]
        check("the quantiser runs in the worklet: 225 Hz to A3, 220 exactly, and left alone when off",
              abs(q["on"] - 220) < 1e-9 and abs(q["off"] - 225) < 1e-9, str(q))
        ph = report["pitched"]
        check("the pitched harmonograph runs in the worklet, at the note's pitch, and strikes cleanly",
              ph["finite"] and ph["peak"] > 0.1 and abs(ph["pitch"] - 220) < 1e-9, str(ph))
        pl = report["plane"]
        check("the plane runs in the worklet at 1x, 2x and 4x: mirrored and held inside the radius",
              all(v["finite"] and v["low"] > -0.02 and 0.15 < v["high"] <= 0.31 for v in pl.values()), str(pl))
        pr = report["planeRest"]
        # The diagonal of 0.5 is 0.707 long: folded at 0.2, never past it.
        # Snapped at two bits, at 1x, every X is a whole number of halves.
        check("the rest of the plane and the time effects run in the worklet, each doing what it alone would",
              all(v.get("finite", True) for v in pr.values()) and pr["plain"]["apart"] < 1e-6
              and pr["fold"]["peak"] <= 0.2 + 1e-6 and pr["fold"]["peak"] > 0.1
              and pr["snap"]["offGrid"] < 1e-6 and pr["snap"]["peak"] > 0.3
              and pr["twist"]["apart"] > 0.1 and pr["kaleido"]["apart"] > 0.1 and pr["kaleido"]["lowY"] > -0.02
              and pr["chorus"]["apart"] > 0.1
              and abs(pr["matrix"]["ratio"] - 0.5) < 1e-3
              and pr["delay"]["echoed"] > 0.3 and pr["delay"]["after"] < 1e-6,
              str(pr))
        vo = report["voice"]
        check("the voice's oscillator runs in the worklet, everything on at once, inside its amplitude",
              vo["finite"] and 0.1 < vo["peak"] <= 0.5 + 1e-6, str(vo))
        # Shaped, the ceiling is the curve's full scale plus what band-limiting
        # a squared-off wave overshoots by - Gibbs, about 9 per cent - and a
        # crusher's step on top: 0.5625 of 0.5, measured.
        sh = report["shaped"]
        check("and with drive, fold and crush on it too, within the overshoot a band-limited square has",
              sh["finite"] and 0.1 < sh["peak"] <= 0.5 * 1.15, str(sh))
        fl = report["filtered"]
        # A 220 Hz sine under a resonant low pass tracked to 673 Hz comes out
        # lifted, 0.546 of a sine at 0.5. The first version asked only for a
        # finite, audible peak, and passed with the filter missing from the
        # worklet altogether, on the plain sine at exactly 0.5.
        check("and through the voice filter, whose resonance lifts the sine: 0.546, not the plain 0.5",
              fl["finite"] and 0.53 < fl["peak"] < 0.56, str(fl))
        c = report["crossings"]
        # 800 blocks at 48 kHz is 2.13 s: a 4 Hz beam crosses the X line 8
        # times, and Y - a quarter cycle on - 8 or 9.
        check("the crossings run in the worklet: a 4 Hz beam over 2.1 s fires each line eight times or so",
              8 <= c["x"] <= 9 and 8 <= c["y"] <= 9, str(c))
        fx = report.get("fx")
        print("    effects processor: %s" % fx)
        check("the effects processor is in the module too, and with nothing on it is an exact copy of its input",
              fx is not None and fx["copy"] == 0 and fx["mono"] == 0, str(fx))
        # The input goes to -0.8, so a copy could not pass this; the fold is
        # compared sample for sample with |x|, so a clamp at nought could not.
        check("told to mirror, it folds both channels to their absolute values, and silence in is finite",
              fx is not None and fx["inLow"] < -0.7 and fx["low"] >= 0 and fx["folded"] < 1e-6
              and fx["silentFinite"], str(fx))
        # An impulse into a 2 ms delay, 96 samples at 48 kHz, with the echo's
        # slider at nought: only the routing can put a repeat at 96, and with
        # the routing gone there is none.
        check("and a routing on the echo's level turns its delay on from nought: the impulse repeats 96 samples on",
              fx is not None and abs(fx["echoRouted"] - 0.25) < 1e-6 and fx["echoUnrouted"] == 0, str(fx))
        e = report["epoch"]
        check("a restart reaches the worklet's oscillators, and a repeated count does not restart them again",
              e["before"] > 0.1 and e["reset"] == 0 and e["again"] > 0.1, str(e))

    print("\n--- where the module is served from ---")
    served = p.evaluate("""async () => {
      const text = generatorModuleSource();
      const out = {};
      const tryOne = async (url, label) => {
        const ctx = new OfflineAudioContext(2, 256, 44100);
        try { await ctx.audioWorklet.addModule(url); out[label] = 'loaded'; }
        catch (error) { out[label] = String(error).slice(0, 60); }
      };
      await tryOne(URL.createObjectURL(new Blob([text], { type: 'application/javascript' })), 'blob');
      await tryOne('data:application/javascript,' + encodeURIComponent(text), 'data');
      out.origin = location.origin;
      return out;
    }""")
    print("    from %s: blob %s, data %s"
          % (served["origin"], served["blob"], served["data"]))
    check("a data URL loads, which is what makes the single file work at all",
          served["data"] == "loaded", served["data"])
    # Not asserted to fail - a served copy loads it fine, and this test runs
    # against both. Asserted to be the REASON the fallback exists: from a file
    # it does not load, and if that ever changes the note in `scope.html` is
    # the thing to revisit.
    if served["origin"] == "file://":
        check("and from a file the blob does not, which is why there is a fallback",
              served["blob"] != "loaded", served["blob"])

    print("\n--- switching it on ---")
    on = p.evaluate("""async () => {
      // A snapshot first, so "there are samples" cannot be satisfied by the
      // ones this thread put there before the switch was touched.
      window.__before = state.source.getLatestWindow(4096)[0].slice();
      state.genSound = true;
      await applyGeneratorSound();
      return {
        wanted: true, got: state.genSound,
        audible: state.source.audible(),
        from: state.source.moduleFrom,
        driver: lfoDriver(),
        latency: state.source.latencyMs,
      };
    }""")
    check("the generator says yes, and says how it loaded",
          on["got"] and on["audible"] and on["from"] in ("blob", "data"),
          str(on))
    check("and the oscillators are now driven by the worklet",
          on["driver"] == "worklet", on["driver"])

    p.wait_for_timeout(600)
    sounding = p.evaluate("""() => {
      const f = capture();
      let peak = 0, energy = 0;
      for (let i = 0; i < f.channels[0].length; i++) {
        peak = Math.max(peak, Math.abs(f.channels[0][i]));
        energy += f.channels[0][i] * f.channels[0][i];
      }
      const now = state.source.getLatestWindow(4096)[0];
      let rewritten = 0;
      for (let i = 0; i < now.length; i++) {
        rewritten = Math.max(rewritten, Math.abs(now[i] - window.__before[i]));
      }
      return { peak, mean: energy / f.channels[0].length,
               n: f.channels[0].length, rewritten,
               blocks: state.source.blocks };
    }""")
    # Counted, not compared. The first version of this held the ring against a
    # snapshot taken before the switch and required it to have changed, which
    # looked airtight and was not: the default tone is 220 Hz and the wait was
    # 600 ms, which is 132 whole cycles, so the two windows were the same
    # periodic waveform a whole number of periods apart and differed by
    # nothing. While the generator is sounding, `absorb` is the only thing
    # that writes the ring, so counting what it absorbed is the provenance.
    check("and the picture is being drawn from what it sent",
          sounding["peak"] > 0.05 and sounding["mean"] > 1e-4
          and sounding["blocks"] > 3,
          "peak %.3f, %d blocks absorbed (the ring moved by %.3f, which proves "
          "nothing on a periodic tone)"
          % (sounding["peak"], sounding["blocks"], sounding["rewritten"]))

    # The discriminator: with the loop on this thread, a stopped scope's ring
    # freezes, because `tick` is what fills it. With the worklet producing,
    # the samples keep arriving whether or not anything asks for them - which
    # is what "the worklet is the source of the samples" means.
    producing = p.evaluate("""async () => {
      const takePeak = () => {
        const w = state.source.getLatestWindow(2048)[0];
        let sum = 0;
        for (let i = 0; i < w.length; i++) sum += w[i] * w[i];
        return sum;
      };
      const was = state.running;
      state.running = false;                       // nothing calls tick now
      const before = state.source.getLatestWindow(2048)[0].slice();
      await new Promise((r) => setTimeout(r, 350));
      const after = state.source.getLatestWindow(2048)[0];
      let moved = 0;
      for (let i = 0; i < before.length; i++) {
        moved = Math.max(moved, Math.abs(before[i] - after[i]));
      }
      state.running = was;
      return { moved, energy: takePeak() };
    }""")
    check("the samples keep coming when nothing on this thread asks for them",
          producing["moved"] > 0.01, "moved by %.3f" % producing["moved"])

    # Both advance paths check the driver, and both throw when they are not it.
    guard = p.evaluate("""() => {
      const out = {};
      try { assertLfoDriver("fill"); out.fill = "allowed"; }
      catch (error) { out.fill = String(error.message); }
      try { assertLfoDriver("main"); out.main = "allowed"; }
      catch (error) { out.main = String(error.message); }
      try { assertLfoDriver("worklet"); out.worklet = "allowed"; }
      catch (error) { out.worklet = String(error.message); }
      return out;
    }""")
    check("and neither of the other two may step an oscillator",
          "allowed" not in (guard["fill"], guard["main"])
          and guard["worklet"] == "allowed", str(guard))

    # The plan's own check, across the boundary: a 2 Hz oscillator goes round
    # twice a second, counted from the values the worklet posts back rather
    # than from anything this thread advanced.
    print("\n--- an oscillator, measured through the boundary ---")
    cycles = p.evaluate("""async () => {
      const was = { shape: lfos[0].shape, rate: lfos[0].rate };
      lfos[0].shape = 'sine'; lfos[0].rate = 2;
      await new Promise((r) => setTimeout(r, 120));   // let the setting cross
      let crossings = 0, last = lfos[0].value, samples = 0;
      const started = performance.now();
      while (performance.now() - started < 1000) {
        await new Promise((r) => setTimeout(r, 8));
        const now = lfos[0].value;
        if (last < 0 && now >= 0) crossings++;
        last = now; samples++;
      }
      const seconds = (performance.now() - started) / 1000;
      lfos[0].shape = was.shape; lfos[0].rate = was.rate;
      return { crossings, seconds, samples, hz: crossings / seconds };
    }""")
    print("    %d rising zero crossings in %.2f s, from %d reads"
          % (cycles["crossings"], cycles["seconds"], cycles["samples"]))
    check("a 2 Hz oscillator goes round twice a second, in the worklet",
          abs(cycles["hz"] - 2) < 0.35, "%.2f Hz" % cycles["hz"])

    print("\n--- and switching it off again ---")
    off = p.evaluate("""async () => {
      state.genSound = false;
      await applyGeneratorSound();
      const driver = lfoDriver();
      let threw = null;
      try { assertLfoDriver("worklet"); } catch (error) { threw = error.message; }
      return { got: state.genSound, audible: state.source.audible(), driver, threw };
    }""")
    check("the switch answers with what actually happened",
          off["got"] is False and off["audible"] is False, str(off))
    check("and this thread has the oscillators back",
          off["driver"] == "fill" and off["threw"] is not None, str(off))

    p.wait_for_timeout(400)
    after = p.evaluate("""() => {
      const f = capture();
      let energy = 0;
      for (let i = 0; i < f.channels[0].length; i++) energy += f.channels[0][i] * f.channels[0][i];
      return energy / f.channels[0].length;
    }""")
    check("and the picture is still there, drawn on this thread again",
          after > 1e-4, "mean square %.5f" % after)

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the generator has an output, and only one loop is running")
