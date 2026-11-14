"""render_cpp itself, before anything is believed of it: two runs of one
script are the same to the bit, one changed input changes them, reading does
not move what is rendered, and an input drawn goes through the instrument's
effects (stage 5, step 3, batch 5).

render_cpp (core/tests/tools/render_cpp.cpp, which lists its commands) is
the instrument rendered offline from a setup code, MIDI at its own samples,
an input and the hands a player has, read at a stated interval of audio. The
batch's moved rows - the loop's stability runs, the picture presets' runs,
shape's survey, the microphone through the effects - all stand on it, and
every one of them is only as good as its being deterministic: the page's
runs of the same scenarios were the flakiest in the suite because their
frames, reads and keys landed where the browser's timing put them. So that is
proved here, on the heaviest script the batch has (the loop closed, Scan at
its top, the reverb at full, a split each reading the other's picture, an
input, every reading and every record), with the null that shows the
comparison can see a difference.
"""
import base64, hashlib, json, os, time

import numpy as np

from pieces.kit import BUILD


def code(setup):
    return base64.b64encode(json.dumps(setup).encode()).decode().rstrip("=")


READINGS = ["heard", "stage", "meter", "lmeter", "loop", "scan", "table", "sources", "gridstat", "settings", "griddump",
            "tone", "routed", "layers"]


def heavy(tag, velocity=127, input_file=None, every=0.1):
    """A crossed split at Scan's top with the reverb full and the picture's
    sources routed, a random oscillator on the twist, an input fed to the
    generator's ride, twelve seconds; every reading at `every` and every
    record into files named by `tag`."""
    s = {"v": 11, "timebase": 3, "display": "xy", "photoOn": True, "midiMode": "poly", "layers": "split", "shape": "harmonic",
         "interval": 7, "amp": 100, "persistence": "0.04", "fOn": True, "fRes": 80, "pictureAmount": 100, "oscScan": 100, "bScan": 100,
         "scanReadsA": "B", "scanReadsB": "A", "reverbMix": 100, "reverbSize": 100, "reverbSpread": 100, "inputMode": 2, "inputDepth": 50,
         # The second oscillator a random one, sample and hold, on the twist:
         # so the generator's random source is in the run, and a seed that
         # moved from run to run would show (a mutation that seeded it from the
         # processor's clock left a run without it the same to the bit).
         "l1s": "random", "l1r": 300,
         "mod": "photo.1>filter.res@1.000;picture.cover>gen.freq@1.000;picture.novelty>view.rotate@1.000;picture.signed>view.zoom@1.000;"
                "lfo2>gen.twist@0.300"}
    files = {k: os.path.join(BUILD, "render-%s-%s.f32" % (tag, k)) for k in ("heard", "lanes", "grid")}
    lines = [["make", 48000, code(s)], ["input", "file", input_file, 1] if input_file else ["input", "sine", 3, 0.5]]
    lines += [["record", k, p] for k, p in files.items()]
    lines += [["midi", 0x90, n, velocity] for n in (48, 55, 79, 84)]
    if every: lines.append(["every", every] + READINGS)
    lines += [["to", 6.0], ["midi", 0x80, 55, 0], ["to", 6.05], ["midi", 0x90, 62, 90], ["to", 12.0], ["read"] + READINGS]
    return lines, files


def digest(path):
    with open(path, "rb") as f: return hashlib.sha256(f.read()).hexdigest()


def run(kit):
    check, null = kit.check, kit.null

    # --- the same to the bit ---
    kit.build("render_cpp")  # built first, so the time below is the render's (and the build directory is made)
    t0 = time.time()
    a_lines, a_files = heavy("a")
    out_a = kit.render(a_lines, raw=True)
    took = time.time() - t0
    a = {k: digest(p) for k, p in a_files.items()}
    b_lines, b_files = heavy("b")
    out_b = kit.render(b_lines, raw=True)
    b = {k: digest(p) for k, p in b_files.items()}
    reads = out_a.count("\nat ") + 1
    print("    twelve seconds of the heaviest script, %d readings: %.1f s to render; %d bytes of readings"
          % (reads, took, len(out_a)))
    same = lambda x, y, fx, fy: x == y and fx == fy
    check("two runs of one script are the same to the bit: every reading, the heard pair, the lanes and the grid",
          same(out_a, out_b, a, b) and reads > 100 and os.path.getsize(a_files["heard"]) == 12 * 48000 * 2 * 4,
          "readings %s, files %s" % (out_a == out_b, a == b))

    # The null: one changed input - the third note struck at 126 rather than
    # 127, and separately one sample of the input changed - and the same
    # comparison must see it.
    c_lines, c_files = heavy("c", velocity=126)
    out_c = kit.render(c_lines, raw=True)
    c = {k: digest(p) for k, p in c_files.items()}
    null("one note a velocity softer is not the same run", not same(out_a, out_c, a, c),
         "readings differ %s, heard differs %s" % (out_a != out_c, a["heard"] != c["heard"]))
    x = (0.5 * np.sin(2 * np.pi * 3 * np.arange(12 * 48000) / 48000)).astype("<f4")
    one, two = os.path.join(BUILD, "render-in-1.f32"), os.path.join(BUILD, "render-in-2.f32")
    x.tofile(one)
    x[48000 * 3] += 1e-3
    x.tofile(two)
    d1_lines, d1_files = heavy("d1", input_file=one)
    d2_lines, d2_files = heavy("d2", input_file=two)
    out_d1, out_d2 = kit.render(d1_lines, raw=True), kit.render(d2_lines, raw=True)
    h1, h2 = digest(d1_files["heard"]), digest(d2_files["heard"])
    null("and one input sample a thousandth off, three seconds in, is not either", out_d1 != out_d2 and h1 != h2)
    # The file input is the sine input, as written: the same sine through either way.
    check("an input given as a file plays as the same input made by render_cpp", digest(d1_files["heard"]) != "" and
          np.max(np.abs(np.fromfile(d1_files["heard"], "<f4") - np.fromfile(a_files["heard"], "<f4"))) < 1e-4,
          "%.2e" % np.max(np.abs(np.fromfile(d1_files["heard"], "<f4") - np.fromfile(a_files["heard"], "<f4"))))

    # --- reading moves nothing ---
    # A reading splits the render at its own sample; the instrument steps every
    # 128 frames whatever block it is handed, so where the reads fall must not
    # change what is heard. Read every 7 ms (never on a step's edge) and never.
    e_lines, e_files = heavy("e", every=0.007)
    f_lines, f_files = heavy("f", every=0)
    kit.render(e_lines, raw=True); kit.render(f_lines, raw=True)
    he, hf = digest(e_files["heard"]), digest(f_files["heard"])
    check("reading every 7 ms, or never, renders the same heard pair and lanes as reading every tenth of a second",
          he == hf == a["heard"] and digest(e_files["lanes"]) == digest(f_files["lanes"]) == a["lanes"])
    null("a run that differs is told apart by the same digest", c["heard"] != a["heard"])

    # --- an input drawn goes through the instrument's effects ---
    # The question batches 3 and 4 left (STAGE5-INVENTORY.md section 3): does
    # the instrument put a microphone through its effects at all? Drawing the
    # input (srcMic), its render runs the input through the generator's
    # `effect` - the plane and the time effects - and what comes out is both
    # the picture and what is heard. A delay at full mix, 150 ms: the input's
    # click comes back 150 ms later in the heard pair.
    def mic(setup, click_at=0.5):
        x = np.zeros(48000 * 2, dtype="<f4")
        x[int(click_at * 48000)] = 0.8
        path = os.path.join(BUILD, "render-click.f32")
        x.tofile(path)
        rec = os.path.join(BUILD, "render-mic.f32")
        kit.render([["make", 48000, code(dict({"v": 11}, **setup))], ["click", "srcMic"], ["input", "file", path, 1],
                    ["record", "prelimit", rec], ["to", 2.0]], raw=True)  # before the limiter (5a), 6 ms late after it
        return np.fromfile(rec, "<f4").reshape(-1, 2)
    dry = mic({})
    wet = mic({"delayMix": 100, "delayMs": 150, "delayFeedback": 0})
    # Read in windows of 96 samples, not at the sample: the plane's
    # oversampling (planeOS, two by default) delays what it passes by about
    # twenty samples and spreads a click over a few.
    hit = 24000
    near = lambda h, at: float(np.max(np.abs(h[at: at + 96, 0])))
    echo = lambda h: near(h, hit + 7200)
    print("    a click on the input at 0.5 s: heard dry %.3f at it and %.4f 150 ms on; with the delay %.4f 150 ms on"
          % (near(dry, hit), echo(dry), echo(wet)))
    check("an input drawn goes through the instrument's effects: a delay on it repeats a click 150 ms on",
          echo(wet) > 0.1 and near(dry, hit) > 0.1, "%.4f" % echo(wet))
    null("and without the delay nothing comes 150 ms on", echo(dry) < 1e-3, "%.4f" % echo(dry))
