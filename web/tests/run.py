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
    ("bench", [sys.executable, "benchtest.py"], "parallel", "the Bench, the one face: one node per control, on the face and through Enlarge"),
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
    ("env", [sys.executable, "envtest.py"], "serial - the gate held for measured milliseconds", "the gate and the envelope on the site: a key on a keyboard reaching the instrument, the Envelope it reads back, the empty screen saying why (the renders are core/tests/pieces/env.py)"),
    ("patch", [sys.executable, "patchtest.py"], "parallel", "patching by pointer, keyboard and touch"),
    ("header", [sys.executable, "headertest.py"], "serial - undo records a change once it has held still for 400 ms, which load can stretch", "the header: the arrows in the browser's order and wrapping, the heading, Browse and Save, undo as one step a gesture and only after a hand, redo dropped by a new change, A and B and the views gone and one history, Ctrl+Z in a text field left to it"),
    ("rack", [sys.executable, "racktest.py"], "parallel", "the rack: the modules in the sound's order, a switch that moves the sound and puts back what it had, the Plane's shaping and B's turn, lines that follow a restore, one open at a time, off folds to its line, showControl into a module, the Reverb slot, Delay not Echo"),
    ("ring", [sys.executable, "ringtest.py"], "serial - the ring's dot is read moving over real time, and the long press is a timer", "modulation on a knob (G5b): the selected source's ring and its direction, the others' ticks, the dot as the sum; Alt-drag and Shift+Alt, the ring's handle; the editor named for the knob, its bar's bands, a typed depth; the right-click menu with and without sources and on a menu, Reset, Type a value, Copy to the other hand, What is this?, Esc, a click away, the arrows, Shift+F10, a long press, the browser's menu prevented; the info line's right-click; the silence stored and restored"),
    ("knob", [sys.executable, "knobtest.py"], "parallel", "the knobs: which rows, the face at both ends and the middle and from nought, a value from code, drag, fine, two taps, the arrows, a finger does not scroll, the lit name, the lane ring"),
    ("lane", [sys.executable, "lanetest.py"], "parallel", "the modulation lane: does it draw the real law"),
    ("filter", [sys.executable, "filtertest.py"], "serial - the capture's cost per frame in milliseconds", "the picture-path filter on the site: the capture's cost, the speakers' chain, its taps and glides, the limiter (its law: core/tests/pieces/filter.py)"),
    ("tap", [sys.executable, "taptest.py"], "parallel", "the two taps, and the block they straddle"),
    ("comb", [sys.executable, "combtest.py"], "parallel", "the lag, heard, and where its comb is deepest"),
    ("contract", [sys.executable, "contracttest.py"], "parallel", "the lane contract, and a lane with no audio"),
    ("keys", [sys.executable, "keystest.py"], "parallel", "the keyboard on the screen, and the letters"),
    ("poly", [sys.executable, "polytest.py"], "parallel", "every held note sounding, and which are drawn"),
    ("layer", [sys.executable, "layertest.py"], "parallel", "a split or a layer: two sets of voices from one keyboard"),
    ("hands", [sys.executable, "handstest.py"], "parallel", "the hands (G6): the header's Editing, a link on each section, linked editing both hands and unlinked one, unlinking copying, codes from before loading each hand its own, the Picture's Amount and Strike per hand, routings that follow the link, the tab cards' differences"),
    ("output", [sys.executable, "outputtest.py"], "serial - undo's step is judged after a change holds still for 400 ms, which load can stretch", "Level in the Generator and the master Output (G7): where each is, Level on the Generator's link, the Output's law and reading, no setup's (a preset, a code, undo with real keys, the morph), this browser's storage and the page with it refused, the picture the same to the bit and the heard pair a quarter on the compiled instrument and the page's generator, the meter, the site's instrument told; each with its null"),
    ("width", [sys.executable, "widthtest.py"], "serial - undo's step is judged after a change holds still for 400 ms, and the Key's release is heard at the speakers in real time", "The master Width (12 Nov): where it is, its law and reading, no setup's (a preset, a code, New, undo with real keys, the morph), this browser's storage and the page with it refused, mono to the bit at nought and glided there, half the side at fifty, the drawn pair to the bit at a hundred, the picture the same to the bit, on the compiled instrument and the page's generator, the site's instrument told; and the Key held through a note's release on the page and at the speakers; each with its null"),
    ("harmony", [sys.executable, "harmonytest.py"], "parallel", "harmony as geometry: a chord built a note at a time draws the struck chord's figure, and the readout names the outline and how fast it turns"),
    ("layerpicture", [sys.executable, "layerpicturetest.py"], "serial - per-layer motion over real frames; flaked under load (P7b core)", "each layer's picture, and whose sound it moves: own, the other's or both, averaged, a crossed pair held"),
    ("layout", [sys.executable, "layouttest.py"], "parallel", "the modulation cards and their editor, reaching any control, and search"),
    ("pedal", [sys.executable, "pedaltest.py"], "parallel", "the sustain pedal: holding notes, and a source"),
    ("drawbar", [sys.executable, "drawbartest.py"], "parallel", "the saw on the menu, and the drawbars: footages, Nyquist, the level law, layers"),
    ("morph", [sys.executable, "morphtest.py"], "parallel", "the morph on the face: its row and reading, a routing on it, the hands, setups (its sound: core/tests/pieces/morph.py)"),
    ("key", [sys.executable, "keytest.py"], "parallel", "the page's key and the quantiser: only the key's notes, no chatter, the rate limit, chords"),
    ("clock", [sys.executable, "clocktest.py"], "serial - the tempo and the bar against the wall clock", "the clock: locked oscillators, tap tempo, MIDI clock, Start and Continue; the bar, Stop and Start, the score on it, a MIDI clock counted in ticks"),
    ("pitch", [sys.executable, "pitchtest.py"], "serial - the tuner's cost in milliseconds", "the pitch estimator: rich registrations, the range, two periods or nothing, noise, the readout and Autoset"),
    ("schema", [sys.executable, "schematest.py"], "parallel", "the setup's table of fields: snapshot and the table key for key, every menu and range its control's, every default its own rule's, the readers and restore through them, each with its null"),
    ("plane", [sys.executable, "planetest.py"], "parallel", "the plane on the face: its panel, units, codes and the version-4 pass (its arithmetic, aliasing, cost and sound: core/tests/pieces/plane.py)"),
    ("layerplane", [sys.executable, "layerplanetest.py"], "parallel", "layer B's own plane and turn: its picture and its share of the sound, the panel, the screen's rotation, setup codes, the instrument"),
    ("drive", [sys.executable, "drivetest.py"], "serial - under half of real time", "shaping inside the voice: the drive's curve, the fold's Bessel harmonics, each voice on its own, before the envelope, crush, layers, the cost"),
    ("vcf", [sys.executable, "vcftest.py"], "parallel", "the voice filter: Web Audio's biquad to 0.01 dB, swept at audio rate, key tracking, its envelope per note"),
    ("voicefx", [sys.executable, "voicefxtest.py"], "parallel", "inside the voice: FM against Bessel, ring, sync band-limited and corrected once, the sub, unison, layers, setup codes"),
    ("words", [sys.executable, "wordstest.py"], "serial - the line waits a third of a second of real time, and a sweep has to beat it", "the info line: the words are the doc's, every control has its line, a sweep leaves it and a rest changes it, touching takes it at once, More and ? open the card, the switch, the compact face's Picture section; and no word the page shows names a retired tab, view or drawer"),
    ("enlarge", [sys.executable, "enlargetest.py"], "serial - the Trail is read over real frames of fading", "Enlarge: opened and closed by the button and Esc, Picture only hiding every overlay and the readouts, nothing sent to the instrument by it or by Which hands, the Trail fading the canvas and not the grid, the light kept as it opens, the panes beside it, the plugin's minimum, no undo step; and the header one row before a sound"),
    ("wash", [sys.executable, "washtest.py"], "serial - waits on real seconds of fading at the frame rate", "the screen fades to the paper at 0.0255 and 0.12, read off the canvas's pixels, and no axis name or time mark stays under the next one; Crossed hands stays the paper on an accelerated canvas"),
    ("overlay", [sys.executable, "overlaytest.py"], "serial - a frame's cost in milliseconds, and the read-head over real seconds", "the loop on the screen: off by default and never in a setup, the ring at the reader's circle and the circle at the figure, the read-head a stroboscope of the voice's phase, the newest table, the readout's verdict, over the trace and not into it, a split's and crossed hands' rings, Y-T and the spectrogram, a phone's width and a frame's cost"),
    ("phaser", [sys.executable, "phasertest.py"], "serial - reads the site's instrument in real time", "the phaser: four all-passes against their formula, a line opened into a loop and kept a line at no range, nought to the bit, the resonance held and bounded, nothing added and a silence ended, a routing, layer B's own, Memory on it, the panel, setup codes, the site's instrument"),
    ("wheel", [sys.executable, "wheeltest.py"], "parallel", "the mod wheel on the Picture amount: past nought and back with no step in the instrument's sound, against the stages switched straight; each step sent once, as the port's bytes, and a hand still sent"),
    ("bend", [sys.executable, "bendtest.py"], "parallel", "the Bend: off at nought to the bit, FM at one to one, the pinch where Bend at says, brighter, band-limited, chords, the dyad, layer B, sources, setup codes"),
    ("note", [sys.executable, "notetest.py"], "parallel", "a note's first 20 ms with no step where a route on its FM depth catches up, on the Bass under the tine piano's two hands and the sine with Velocity on FM, each against the step at the block's top as it was; and no lag past the block"),
    ("soundstart", [sys.executable, "soundstarttest.py"], "parallel", "the first press starts the sound with the browser's rule on: nothing before it, a finger's tap on the site's instrument, a click"),
    ("scan", [sys.executable, "scantest.py"], "serial - held still versus moving, over real seconds; flaked under load (P7b core)", "Scan: the reading's tables and band-limit, the off-centre path against P2's centred one, softness, the tick to the sample at three rates, the crossfade, nought to the bit, the note's pitch, the fifth kept, the hold, the bend, layer B, setup codes, the freeze, the first minute moving and held still"),
    ("constellation", [sys.executable, "constellationtest.py"], "serial - milliseconds a frame, and real seconds of notes and fading", "the constellation prototype (ways-to-draw step 2): off, the grid, Scan's table and the sound the same to the bit as without it, and never stored; on, each note at its place by pitch, its size its level's (velocity, envelope in time, Level), a ring for a sine and a diamond for a triangle, Scan's circle crossing every figure on the clock and passing clear by pitch, a fast run's trail, Play fitting at five windows, and the cost of a frame of many figures"),
    ("strike", [sys.executable, "striketest.py"], "serial - a strike's fade over real frames", "notes strike the screen and each hand reads the other's picture: nought lays nothing, velocity times Strike, where Scan reads, each note its place, a hard note moves the timbre further, the phosphor's fade, the meters, a split's own layer, cross-scan and its holds, the loops that keep going"),
    ("hand", [sys.executable, "handtest.py"], "parallel", "bend the figure by hand: the grabbed moment is the point's, the figure follows the pointer, only near the figure, double-click off, the reticle and cursors keep their drags, a split's own layer, a finger does not scroll, the site's instrument draws it"),
    ("time", [sys.executable, "timetest.py"], "parallel", "delay and chorus: repeats to the sample, ping-pong, feedback held, the tempo, sidebands, every pair once"),
    ("livefx", [sys.executable, "livefxtest.py"], "parallel", "the site's microphone through the instrument's effects, mirrored, and what each source's effects act on (the arithmetic is core/tests/pieces/livefx.py's since stage 5's batch 5)"),
    ("hearing", [sys.executable, "hearingtest.py"], "serial - reads the sound's continuity over live frames", "the sound as sources: pitch, brightness, bands, width, flux, their continuity, and the loop"),
    ("onset", [sys.executable, "onsettest.py"], "serial - onsets counted against performance.now, a gap of real milliseconds", "Onset and the events it fires, against stand-in destinations since G2 took the drawings' Swing again and Kick: events only to what is struck, one attack one onset, the gap, firing once a count"),
    ("input", [sys.executable, "inputtest.py"], "parallel", "live audio into the generator on the site: the input opened, the instrument's figure riding on it, the code (off is off, FM, the ride and the clock are core/tests/pieces/input.py's)"),
    ("score", [sys.executable, "scoretest.py"], "serial - the transport against performance.now", "the picture as a score, and MIDI out: rows to notes, the playhead at the tempo, the voice heard and not drawn, channels, all-notes-off, the rate limit"),
    ("arp", [sys.executable, "arptest.py"], "parallel", "the arpeggiator: the orders, struck steps, the hands kept, the tempo, the dyad's intervals, letting go"),
    ("cycle", [sys.executable, "cycletest.py"], "parallel", "the drawn cycle: tables band-limited by numpy's FFT, scaled alike, no step at a hand-over, drawn with the mouse, played, in codes"),
    ("pulse", [sys.executable, "pulsetest.py"], "parallel", "the pulse: a pulse's harmonics at a quarter, a third and a tenth, the square at a half, no DC or clip, the width read, patched, per layer, synced, in codes"),
    ("menv", [sys.executable, "menvtest.py"], "serial - a held note's envelope read at moments of real time", "the Envelope's own: its controls moved into its editor and home, one of each id; the switch and knobs by hand into the generator; the source reading its own slow attack, not Play's quick one; what it is routed to following it; codes, and an old one following the amp envelope"),
    ("reverb", [sys.executable, "reverbtest.py"], "parallel", "the reverb: Spread nought identical to the bit on one asymmetric burst into both channels and different at full, Size's T60 by its law, Mix's tail exactly in proportion, Tone darkening the tail, Pre-delay to the sample, Mix nought the plain sound, the switch, the readings, destinations, the host knob, last in the rack whatever the order, codes and B's own"),
    ("delay", [sys.executable, "delaytest.py"], "parallel", "the delay's tone, low cut, width and wow: each pass of a burst round the loop losing the one-pole's gain, width nought on the diagonal and two twice one, wow's swing by its law, the knobs into the generator with their readings, codes and B's own"),
    ("ink", [sys.executable, "inktest.py"], "parallel", "the inks: A's and B's figures drawn in the inks chosen, read off the screen's pixels; the overlay's rings in their figure's; one frame in two inks laying the same light in the grid Scan reads; codes, a nonsense ink and an old code; the swatches by mouse and arrow keys"),
    ("window", [sys.executable, "windowtest.py"], "serial - a module switched on by a value is waited for through the rack's repaint, a few times a second", "the window (F8): Size pressed and remembered, Auto at the plugin's sizes and either side of the thresholds, the compact face from the window in the page's pixels, a resize in place, the verdict under the screen on the Bench and back on Scope, the rack folding only when the tab would scroll"),
    ("fit", [sys.executable, "fittest.py"], "parallel", "no Bench tab scrolls: every tab on the tone and the band split, keyboard and Photocell on and off, every kind, and thirty learned controllers; each section dealt at the height it measured; the modulation row in place, cards or chips"),
    ("modrow", [sys.executable, "modrowtest.py"], "serial - the dots move over real time, and the photocell's graph is four real seconds", "the modulation row (G5a): four cards across the window under the screen and the tabs, each drawing its source with a dot that moves; the Photocell routed from its card by a drag, switched on by it, turning the screen; each editor's drawing read off its canvas - the LFO's wave, the Envelope's curve following Play and its own and its dot along a note, the photocell's crop and its four seconds; Routings by source and by destination, a silence that stops a control and keeps its routing, the fade from its new home; chips under 900 tall; the Envelope's corner word whole on its card and chip at the five windows fittest.py measures"),
    ("host", [sys.executable, "hosttest.py"], "serial - the readout's frame rate and fetch count", "inside the plugin: the page finds JUCE's bridge, draws the plugin's frames at the plugin's rate, one fetch at a time, and reports how the picture gets through; without the bridge it is the website"),
    ("brain", [sys.executable, "braintest.py"], "serial - gate phases read against performance.now", "?brain=core: the page as the face of the instrument compiled whole and playing in a worklet, as it is the plugin's - notes, hands, presets and a port's bytes reaching it, its clock at each tick's own time so a synced delay holds still, its MIDI out leaving by the page's port, the generator's panel kept, and nothing played before the first press"),
    ("setupmorph", [sys.executable, "setupmorphtest.py"], "parallel", "the morph between sliders: a geometric pitch, menus and the scope's view left alone and the tempo walked, the hand respected, a source on the fader, codes; and the macros gone, an old code's routes to them dropped"),
    ("fade", [sys.executable, "fadetest.py"], "serial - routings fading in and out in real time; flaked under load", "routings fading in and out on the sound, the picture and the picture's own sources, ghosts heard and never saved, and a sound loaded landing at once - every way one is loaded, every preset, and heard on the instrument"),
    ("picturepresets", [sys.executable, "picturepresettest.py"], "parallel", "the picture playing itself: every preset turns the photocell on and routes the picture, and presets that use several sources (each loop run is core/tests/pieces/picturepresets.py's)"),
    ("budget", [sys.executable, "budgettest.py"], "serial - times sixteen voices against real time", "S10: sixteen voices and their releases, everything on, under half of real time; the model against the machine; the order things are given up in; caps that do not creep; a cut that fades; the readout; no preset governed"),
    ("wavetable", [sys.executable, "wavetabletest.py"], "parallel", "the wavetable: each slot the drawn cycle's read exactly, the mix between, the default bank's harmonics, the position patched and per layer, the pane and Grab on the slot chosen, codes, a generator built from the panel"),
    ("noise", [sys.executable, "noisetest.py"], "parallel", "the noises: white flat, pink -3 and brown -6 dB an octave, their levels, each channel its own, sample and hold held, pitched and band-limited, the chord's path and layer B"),
    ("grab", [sys.executable, "grabtest.py"], "serial - capture paced by performance.now", "grab a cycle: a known lane's cycle point for point with its note held, worse with the wrong note, measured without one, averaged on noise, the right lane, refusals, no scroll"),
    ("photo", [sys.executable, "phototest.py"], "serial - a fade rate over real frames; flaked under load (P7a)", "the photocell: the phosphor grid, the reticle, the loop"),
    ("shape", [sys.executable, "shapetest.py"], "serial - the readout read after six and a half real seconds of the loop", "what the picture says: its sources on the photocell and the readout (the measures and the survey are core/tests/pieces/shape.py's)"),
    ("loop", [sys.executable, "looptest.py"], "serial - the speakers' limiter read over real milliseconds", "the speakers' chain on the site: its limiter read and its clamp holding (the loop's bounds and stability runs are core/tests/pieces/loop.py's)"),
    ("response", [sys.executable, "responsetest.py"], "parallel", "how the picture responds (11 Nov): the owner's sequence through the compiled core offline - Change's fast run swelling as the study's option 3, its soft notes no more than from a fresh start; a held chord not swelling by itself with Swell off, split and unsplit, and breathing at the Persistence's period with it on; Level holding a run up, Both a base and a flare, Motion on a fixed scale; each with its null"),
    ("stage", [sys.executable, "stagetest.py"], "serial - the first minute, timed from opening", "the picture stage: a chord held on the site as it opens, moved by its picture within ten seconds"),
    ("preset", [sys.executable, "presettest.py"], "parallel", "the preset library and its browser: every preset what it says, the bank's four headings, menus, search, keys, saved, where it lands"),
    ("latch", [sys.executable, "latchtest.py"], "serial - what is heard after the keys come up, over real seconds", "the latch, gone (P8h): its switch, an old code losing it through both codecs, and the pedal holding a chord instead"),
    ("honesty", [sys.executable, "honestytest.py"], "serial - how far the sound moves over real seconds", "every preset does what its heading says, measured on the sound: Settled comes to rest, Breathing moves while held and stops when let go; none is still; and none strains the limiter; the reverb switched on keeps every heading, and at its fullest a Settled note moves no more than 0.10 late"),
    ("perform", [sys.executable, "performtest.py"], "parallel", "the presets for playing: what the sections are (played, both layers sounding, and the microphone through the effects are core/tests/pieces/perform.py's)"),
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


BRAIN_COUNTS = None


def counted(name, cmd):
    """The command and environment a suite runs with: unchanged, or with
    --brain-counts through braincounts.py, its counts in a file of its own."""
    if not BRAIN_COUNTS or cmd[0] != sys.executable:
        return cmd, None
    env = dict(os.environ, BRAIN_COUNTS=os.path.join(BRAIN_COUNTS, name + ".jsonl"))
    return [sys.executable, "braincounts.py"] + cmd[1:], env


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
    cmd, env = counted(name, cmd)
    proc = subprocess.Popen(cmd, cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1, env=env)
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
        elif a == "--brain-counts":
            # The stage-5 inventory: each Python suite run through braincounts.py,
            # its page brain's counts dumped to a file of its own in this directory.
            global BRAIN_COUNTS
            BRAIN_COUNTS = os.path.abspath(args.pop(0))
            os.makedirs(BRAIN_COUNTS, exist_ok=True)
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
            cmd, env = counted(name, cmd)
            proc = subprocess.run(cmd, cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
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
