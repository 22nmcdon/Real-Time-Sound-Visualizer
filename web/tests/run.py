#!/usr/bin/env python3
"""Every check, in one go.

    python3 web/tests/run.py            all of them
    python3 web/tests/run.py lag cap    just those
    python3 web/tests/run.py -j1        one at a time, streamed, as it used to be
    python3 web/tests/run.py -j3 ...    at most three suites at once

Needs Playwright and a Chromium. Point CHROME at one if the default is wrong.

Each suite says whether it may share the machine. "serial - why" suites judge
time: real seconds of motion, a cost in milliseconds, a fade over frames, a
rate. Load changes those verdicts, and every one of the timing flakes this page
has had came from a busy machine, so they run first, one at a time, with
nothing beside them, their output streamed as before. First rather than last:
run after half an hour of the pool, the photocell's reading 900 ms after a move
came in at exactly its threshold in two runs of two, where it passes every time
on a rested machine - the container is slower after sustained load, so the
suites that measure time go while it is fresh (README). "parallel" suites judge
values - codes, layouts, the generator's arithmetic, a rendered block - and run
after, side by side in a pool, their output held and printed whole as each
finishes, so two suites never interleave. A new suite has to say which it is; when
in doubt it is serial, since a suite wrongly serial costs a minute and one
wrongly parallel costs a false red that someone then learns to ignore.
"""
import os, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
SUITES = [
    ("beam", ["node", "beam.test.mjs"], "parallel", "the beam-intensity mapping, no browser"),
    ("design", [sys.executable, "designtest.py"], "parallel", "DESIGN.md's colours against the page: every token sorted into brand or product, at its value; every var() defined, no loose rgba(), the house's radii; no browser"),
    ("lag", [sys.executable, "lagtest.py"], "parallel", "lag X-Y: geometry, the lock, exclusivity"),
    ("cap", [sys.executable, "captest.py"], "parallel", "what capture asks a source for"),
    ("live", [sys.executable, "livetest.py"], "parallel", "live input: shared stream, wiring, crossovers"),
    ("bench", [sys.executable, "benchtest.py"], "parallel", "the Bench: one node per control, two views"),
    ("mod", [sys.executable, "modtest.py"], "serial - the octave sweep over real time; flaked under load", "the modulation matrix, and the enum it replaces"),
    ("midi", [sys.executable, "miditest.py"], "parallel", "the keyboard: notes, the dyad, controllers"),
    ("alias", [sys.executable, "aliastest.py"], "parallel", "band-limiting: what folds back, and what does not"),
    ("rotate", [sys.executable, "rotatetest.py"], "parallel", "rotation as a signal transform, and the measurement tap"),
    ("ac", [sys.executable, "actest.py"], "parallel", "AC coupling: one blocker, the picture and the speakers"),
    ("trig", [sys.executable, "trigtest.py"], "parallel", "the trigger level as a fraction of full scale"),
    ("scale", [sys.executable, "scaletest.py"], "parallel", "full scale as decibels, and the nine detents"),
    ("rate", [sys.executable, "ratetest.py"], "parallel", "the sample-rate audit: 22k to 96k"),
    ("worklet", [sys.executable, "worklettest.py"], "serial - the audio thread's own budget report", "the generator in the audio thread"),
    ("wasm", [sys.executable, "wasmtest.py"], "parallel", "the compiled core in both worklets: the page's copy current, each worklet running it and the JavaScript core with ?core=js, a refused module falling back, every preset's sound and effects the same through both"),
    ("env", [sys.executable, "envtest.py"], "serial - the gate held for measured milliseconds", "the gate, the envelope and the legato rule"),
    ("patch", [sys.executable, "patchtest.py"], "parallel", "patching by pointer, keyboard and touch"),
    ("knob", [sys.executable, "knobtest.py"], "parallel", "the knobs: which rows, the face at both ends and the middle and from nought, a value from code, drag, fine, two taps, the arrows, a finger does not scroll, the lit name, the lane ring"),
    ("lane", [sys.executable, "lanetest.py"], "parallel", "the modulation lane: does it draw the real law"),
    ("filter", [sys.executable, "filtertest.py"], "serial - the filter's cost per block in milliseconds", "the picture-path filter, against Web Audio's"),
    ("tap", [sys.executable, "taptest.py"], "parallel", "the two taps, and the block they straddle"),
    ("comb", [sys.executable, "combtest.py"], "parallel", "the lag, heard, and where its comb is deepest"),
    ("contract", [sys.executable, "contracttest.py"], "parallel", "the lane contract, and a lane with no audio"),
    ("keys", [sys.executable, "keystest.py"], "parallel", "the keyboard on the screen, and the letters"),
    ("poly", [sys.executable, "polytest.py"], "parallel", "every held note sounding, and which are drawn"),
    ("layer", [sys.executable, "layertest.py"], "parallel", "a split or a layer: two sets of voices from one keyboard"),
    ("harmony", [sys.executable, "harmonytest.py"], "parallel", "harmony as geometry: a chord built a note at a time draws the struck chord's figure, and the readout names the outline and how fast it turns"),
    ("layerpicture", [sys.executable, "layerpicturetest.py"], "serial - per-layer motion over real frames; flaked under load (P7b core)", "each layer's picture, and whose sound it moves: own, the other's or both, averaged, a crossed pair held"),
    ("layout", [sys.executable, "layouttest.py"], "parallel", "the Sources tab, reaching any control, and search"),
    ("pedal", [sys.executable, "pedaltest.py"], "parallel", "the sustain pedal: holding notes, and a source"),
    ("drawbar", [sys.executable, "drawbartest.py"], "parallel", "the saw on the menu, and the drawbars: footages, Nyquist, the level law, layers"),
    ("morph", [sys.executable, "morphtest.py"], "parallel", "the morph: its stations, its crossfade, the fundamental it keeps, layers, setups"),
    ("key", [sys.executable, "keytest.py"], "parallel", "the page's key and the quantiser: only the key's notes, no chatter, the rate limit, chords"),
    ("clock", [sys.executable, "clocktest.py"], "serial - the tempo and the bar against the wall clock", "the clock: locked oscillators, tap tempo, MIDI clock, Start and Continue; the bar, Stop and Start, the score on it, a MIDI clock counted in ticks"),
    ("pitch", [sys.executable, "pitchtest.py"], "serial - the tuner's cost in milliseconds", "the pitch estimator: rich registrations, the range, two periods or nothing, noise, the readout and Autoset"),
    ("play", [sys.executable, "playtest.py"], "parallel", "the drawings played: the pitched harmonograph, its strike, Play the figure"),
    ("plane", [sys.executable, "planetest.py"], "serial - under half of real time", "the plane as an effect: the matrix, mirror, twist, kaleidoscope, clip, fold and snap, their arithmetic, aliasing at 1x, 2x and 4x, every pair once"),
    ("layerplane", [sys.executable, "layerplanetest.py"], "parallel", "layer B's own plane and turn: its picture and its share of the sound, the panel, the screen's rotation, setup codes, the instrument"),
    ("drive", [sys.executable, "drivetest.py"], "serial - under half of real time", "shaping inside the voice: the drive's curve, the fold's Bessel harmonics, each voice on its own, before the envelope, crush, layers, the cost"),
    ("vcf", [sys.executable, "vcftest.py"], "parallel", "the voice filter: Web Audio's biquad to 0.01 dB, swept at audio rate, key tracking, its envelope per note"),
    ("voicefx", [sys.executable, "voicefxtest.py"], "parallel", "inside the voice: FM against Bessel, ring, sync band-limited and corrected once, the sub, unison, layers, setup codes"),
    ("overlay", [sys.executable, "overlaytest.py"], "serial - a frame's cost in milliseconds, and the read-head over real seconds", "the loop on the screen: off by default and never in a setup, the ring at the reader's circle and the circle at the figure, the read-head a stroboscope of the voice's phase, the newest table, the readout's verdict, over the trace and not into it, a split's and crossed hands' rings, Y-T and the spectrogram, a phone's width and a frame's cost"),
    ("phaser", [sys.executable, "phasertest.py"], "serial - reads the site's instrument in real time", "the phaser: four all-passes against their formula, a line opened into a loop and kept a line at no range, nought to the bit, the resonance held and bounded, nothing added and a silence ended, a routing, layer B's own, Memory on it, the panel, setup codes, the site's instrument"),
    ("bend", [sys.executable, "bendtest.py"], "parallel", "the Bend: off at nought to the bit, FM at one to one, the pinch where Bend at says, brighter, band-limited, chords, the dyad, layer B, sources, setup codes"),
    ("soundstart", [sys.executable, "soundstarttest.py"], "parallel", "the first press starts the sound with the browser's rule on: nothing before it, a finger's tap on the site's instrument and the page's brain, a click"),
    ("scan", [sys.executable, "scantest.py"], "serial - held still versus moving, over real seconds; flaked under load (P7b core)", "Scan: the reading's tables and band-limit, the off-centre path against P2's centred one, softness, the tick to the sample at three rates, the crossfade, nought to the bit, the note's pitch, the fifth kept, the hold, the bend, layer B, setup codes, the freeze, the first minute moving and held still"),
    ("strike", [sys.executable, "striketest.py"], "serial - a strike's fade over real frames", "notes strike the screen and each hand reads the other's picture: nought lays nothing, velocity times Strike, where Scan reads, each note its place, a hard note moves the timbre further, the phosphor's fade, the meters, a split's own layer, cross-scan and its holds, the loops that keep going"),
    ("hand", [sys.executable, "handtest.py"], "parallel", "bend the figure by hand: the grabbed moment is the point's, the figure follows the pointer, only near the figure, double-click off, the reticle and cursors keep their drags, a split's own layer, a finger does not scroll, the site's instrument draws it"),
    ("time", [sys.executable, "timetest.py"], "parallel", "delay and chorus: repeats to the sample, ping-pong, feedback held, the tempo, sidebands, every pair once"),
    ("livefx", [sys.executable, "livefxtest.py"], "serial - a burst's repeats waited for in real time", "the plane and the delay on a live input: drawn and heard, the generator's arithmetic, a routing on a mono input, a burst's repeats, where it does not go"),
    ("hearing", [sys.executable, "hearingtest.py"], "serial - reads the sound's continuity over live frames", "the sound as sources: pitch, brightness, bands, width, flux, their continuity, and the loop"),
    ("drawing", [sys.executable, "drawingtest.py"], "serial - counts drawn strokes against performance.now", "the sound driving the drawings: energy in, a kick and its friction, events only to what is struck, onset, firing"),
    ("input", [sys.executable, "inputtest.py"], "parallel", "live audio into the generator: off is off, FM a factor on the rate, the ride a scale, the clock a lock, and the stream opened only while it can be used"),
    ("score", [sys.executable, "scoretest.py"], "serial - the transport against performance.now", "the picture as a score, and MIDI out: rows to notes, the playhead at the tempo, the voice heard and not drawn, channels, all-notes-off, the rate limit"),
    ("arp", [sys.executable, "arptest.py"], "parallel", "the arpeggiator: the orders, struck steps, the hands kept, the tempo, the dyad's intervals, letting go"),
    ("solid", [sys.executable, "solidtest.py"], "parallel", "the new figures and solids: every route closed along its edges with the fewest retraces, the polygon and the butterfly exact"),
    ("text", [sys.executable, "texttest.py"], "parallel", "text and SVG paths as figures: the beam's speed, the font, every path command, the panel, drawn on the path, in codes"),
    ("sketch", [sys.executable, "sketchtest.py"], "parallel", "drawing a figure on the screen: it lands under the pointer turned and zoomed, the pen, the limit, the cursors wait, in codes"),
    ("second", [sys.executable, "secondtest.py"], "parallel", "the second generator: its figure exactly, FM, ride and clock into the first against references, lanes, layers, codes"),
    ("cycle", [sys.executable, "cycletest.py"], "parallel", "the drawn cycle: tables band-limited by numpy's FFT, scaled alike, no step at a hand-over, drawn with the mouse, played, in codes"),
    ("pulse", [sys.executable, "pulsetest.py"], "parallel", "the pulse: a pulse's harmonics at a quarter, a third and a tenth, the square at a half, no DC or clip, the width read, patched, per layer, synced, in codes"),
    ("fit", [sys.executable, "fittest.py"], "parallel", "no Bench tab scrolls: every tab on the tone and the band split, keyboard and Photocell on and off, every kind, and thirty learned controllers; each section dealt at the height it measured"),
    ("host", [sys.executable, "hosttest.py"], "serial - the readout's frame rate and fetch count", "inside the plugin: the page finds JUCE's bridge, draws the plugin's frames at the plugin's rate, one fetch at a time, and reports how the picture gets through; without the bridge it is the website"),
    ("brain", [sys.executable, "braintest.py"], "serial - gate phases read against performance.now", "?brain=core: the page as the face of the instrument compiled whole and playing in a worklet, as it is the plugin's - notes, hands, presets and a port's bytes reaching it, its MIDI out leaving by the page's port, the generator's panel kept, and nothing played before the first press"),
    ("setupmorph", [sys.executable, "setupmorphtest.py"], "parallel", "the morph between sliders: a geometric pitch, menus left alone, the hand respected, a source on the fader, codes; and the macros gone, an old code's routes to them dropped"),
    ("fade", [sys.executable, "fadetest.py"], "serial - routings fading in and out in real time; flaked under load", "routings fading in and out on the sound, the picture and the picture's own sources, ghosts heard and never saved, and every preset gliding into itself"),
    ("picturepresets", [sys.executable, "picturepresettest.py"], "serial - each preset listened to for real seconds", "the picture playing itself: every preset turns the photocell on and routes the picture, every loop moves and none runs away, the wandering loop wanders, and presets that use several sources"),
    ("budget", [sys.executable, "budgettest.py"], "serial - times sixteen voices against real time", "S10: sixteen voices and their releases, everything on, under half of real time; the model against the machine; the order things are given up in; caps that do not creep; a cut that fades; the readout; no preset governed"),
    ("drawnplay", [sys.executable, "drawnplaytest.py"], "parallel", "the rest of J2: a dyad closes the rose, the solid's axes as destinations, the drawings as sources, Play fitting in every kind"),
    ("wavetable", [sys.executable, "wavetabletest.py"], "parallel", "the wavetable: each slot the drawn cycle's read exactly, the mix between, the default bank's harmonics, the position patched and per layer, the pane and Grab on the slot chosen, codes, a generator built from the panel"),
    ("noise", [sys.executable, "noisetest.py"], "parallel", "the noises: white flat, pink -3 and brown -6 dB an octave, their levels, each channel its own, sample and hold held, pitched and band-limited, the chord's path and layer B"),
    ("grab", [sys.executable, "grabtest.py"], "serial - capture paced by performance.now", "grab a cycle: a known lane's cycle point for point with its note held, worse with the wrong note, measured without one, averaged on noise, the right lane, refusals, no scroll"),
    ("photo", [sys.executable, "phototest.py"], "serial - a fade rate over real frames; flaked under load (P7a)", "the photocell: the phosphor grid, the reticle, the loop"),
    ("shape", [sys.executable, "shapetest.py"], "serial - a 2.5 s trace of the picture's motion", "what the picture says: five sources and a verdict"),
    ("loop", [sys.executable, "looptest.py"], "serial - energy and motion over real seconds; flaked under load", "the loop through the sound, and its bounds held"),
    ("stage", [sys.executable, "stagetest.py"], "serial - the first minute, timed from opening", "the picture stage: a chord held on the site as it opens, moved by its picture within ten seconds"),
    ("preset", [sys.executable, "presettest.py"], "parallel", "the preset library and its browser: every preset what it says, the bank's four headings, menus, search, keys, saved, where it lands"),
    ("latch", [sys.executable, "latchtest.py"], "serial - what is heard after the keys come up, over real seconds", "the latch: the Play tab's switch, a chord let go heard on, the next one replacing it, a setup carrying it"),
    ("honesty", [sys.executable, "honestytest.py"], "serial - how far the sound moves over real seconds", "every preset does what its heading says, measured on the sound: Settled comes to rest, Breathing moves while held, Wandering goes on after, Open never moves; and none strains the limiter"),
    ("perform", [sys.executable, "performtest.py"], "parallel", "the presets for playing: every routing a hand moves, both layers sounding, live effects in the path"),
    ("regress", [sys.executable, "regress.py"], "parallel", "presets, displays, source switching"),
    ("sources", [sys.executable, "sources.py"], "parallel", "Tone, over a tone, and a denied mic"),
]


for _name, _cmd, _kind, _blurb in SUITES:
    assert _kind == "parallel" or _kind.startswith("serial - "), (
        "%s: say 'parallel' or 'serial - why'" % _name)

# Chromium is the cost: each parallel suite holds one or two browsers and a
# worklet. On the four-core container, three at once ran each suite about 1.8
# times slower than alone and took the pool from 20 minutes to 12 - the pool
# is bound by the processor, so more workers would only slow each one, and one
# core is left for the browsers' own threads (README).
DEFAULT_JOBS = max(1, min(3, (os.cpu_count() or 2) - 1))


def failed_in(text):
    # A printed FAIL is a failure whatever the exit code. Two suites printed
    # theirs and exited 0, and this said "everything passes" over them for the
    # whole of 5m to 5v (README).
    return any(line.lstrip().startswith("FAIL ") for line in text.splitlines())


def header(name, blurb):
    return "\n=== %s — %s ===" % (name, blurb)


def run_streamed(name, cmd, blurb):
    print(header(name, blurb), flush=True)
    start = time.monotonic()
    # Read as it streams, so a long suite still shows its progress.
    proc = subprocess.Popen(cmd, cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1)
    printed_fail = False
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        if line.lstrip().startswith("FAIL "): printed_fail = True
    bad = proc.wait() != 0 or printed_fail
    print("--- %s: %.0f s" % (name, time.monotonic() - start), flush=True)
    return bad


def parse(argv):
    jobs, want, args = DEFAULT_JOBS, [], list(argv[1:])
    while args:
        a = args.pop(0)
        if a.startswith("-j"):
            v = a[2:] or (args.pop(0) if args else "")
            jobs = max(1, int(v))
        elif a == "--jobs":
            jobs = max(1, int(args.pop(0)))
        else:
            want.append(a)
    unknown = set(want) - {name for name, *_ in SUITES}
    if unknown:
        raise SystemExit("no such suite: " + ", ".join(sorted(unknown)))
    return jobs, set(want)


def main(argv):
    jobs, want = parse(argv)
    # beam.test.mjs reads the shipped script, so it has to be extracted first.
    subprocess.run([sys.executable, "extract.py"], cwd=os.path.dirname(HERE), check=True)

    chosen = [s for s in SUITES if not want or s[0] in want]
    order = {s[0]: k for k, s in enumerate(SUITES)}
    began = time.monotonic()
    failed = []

    if jobs == 1:
        for name, cmd, kind, blurb in chosen:
            if run_streamed(name, cmd, blurb): failed.append(name)
    else:
        pool_suites = [s for s in chosen if s[2] == "parallel"]
        alone = [s for s in chosen if s[2] != "parallel"]
        lock = threading.Lock()

        def run_held(suite):
            name, cmd, kind, blurb = suite
            start = time.monotonic()
            proc = subprocess.run(cmd, cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            bad = proc.returncode != 0 or failed_in(proc.stdout)
            # Whole, under a lock, so a suite's lines are never split by another's.
            with lock:
                sys.stdout.write(header(name, blurb) + "\n" + proc.stdout)
                if not proc.stdout.endswith("\n"): sys.stdout.write("\n")
                sys.stdout.write("--- %s: %.0f s, beside up to %d others\n" % (name, time.monotonic() - start, jobs - 1))
                sys.stdout.flush()
                if bad: failed.append(name)

        print("\n%d suites alone, then %d side by side, %d at a time" % (len(alone), len(pool_suites), jobs), flush=True)
        # Nothing else is running yet: these judge time.
        for name, cmd, kind, blurb in alone:
            if run_streamed(name, cmd, blurb): failed.append(name)
        if pool_suites:
            with ThreadPoolExecutor(max_workers=jobs) as pool:
                list(pool.map(run_held, pool_suites))

    failed.sort(key=lambda n: order[n])
    print("\n%d suites in %.1f min" % (len(chosen), (time.monotonic() - began) / 60))
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print("everything passes")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
