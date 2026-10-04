#!/usr/bin/env python3
"""Every check, in one go.

    python3 web/tests/run.py            all of them
    python3 web/tests/run.py lag cap    just those

Needs Playwright and a Chromium. Point CHROME at one if the default is wrong.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUITES = [
    ("beam", ["node", "beam.test.mjs"], "the beam-intensity mapping, no browser"),
    ("lag", [sys.executable, "lagtest.py"], "lag X-Y: geometry, the lock, exclusivity"),
    ("cap", [sys.executable, "captest.py"], "what capture asks a source for"),
    ("live", [sys.executable, "livetest.py"], "live input: shared stream, wiring, crossovers"),
    ("bench", [sys.executable, "benchtest.py"], "the Bench: one node per control, two views"),
    ("mod", [sys.executable, "modtest.py"], "the modulation matrix, and the enum it replaces"),
    ("midi", [sys.executable, "miditest.py"], "the keyboard: notes, the dyad, controllers"),
    ("alias", [sys.executable, "aliastest.py"], "band-limiting: what folds back, and what does not"),
    ("rotate", [sys.executable, "rotatetest.py"], "rotation as a signal transform, and the measurement tap"),
    ("ac", [sys.executable, "actest.py"], "AC coupling: one blocker, the picture and the speakers"),
    ("trig", [sys.executable, "trigtest.py"], "the trigger level as a fraction of full scale"),
    ("scale", [sys.executable, "scaletest.py"], "full scale as decibels, and the nine detents"),
    ("rate", [sys.executable, "ratetest.py"], "the sample-rate audit: 22k to 96k"),
    ("worklet", [sys.executable, "worklettest.py"], "the generator in the audio thread"),
    ("wasm", [sys.executable, "wasmtest.py"], "the compiled core in both worklets: the page's copy current, each worklet running it and the JavaScript core with ?core=js, a refused module falling back, every preset's sound and effects the same through both"),
    ("env", [sys.executable, "envtest.py"], "the gate, the envelope and the legato rule"),
    ("patch", [sys.executable, "patchtest.py"], "patching by pointer, keyboard and touch"),
    ("lane", [sys.executable, "lanetest.py"], "the modulation lane: does it draw the real law"),
    ("filter", [sys.executable, "filtertest.py"], "the picture-path filter, against Web Audio's"),
    ("tap", [sys.executable, "taptest.py"], "the two taps, and the block they straddle"),
    ("comb", [sys.executable, "combtest.py"], "the lag, heard, and where its comb is deepest"),
    ("along", [sys.executable, "alongtest.py"], "a backing track and a live input as lanes"),
    ("contract", [sys.executable, "contracttest.py"], "the lane contract, and a lane with no audio"),
    ("keys", [sys.executable, "keystest.py"], "the keyboard on the screen, and the letters"),
    ("voice", [sys.executable, "voicetest.py"], "the generator heard as a lane"),
    ("poly", [sys.executable, "polytest.py"], "every held note sounding, and which are drawn"),
    ("layer", [sys.executable, "layertest.py"], "a split or a layer: two sets of voices from one keyboard"),
    ("rack", [sys.executable, "racktest.py"], "the rack built a lane at a time, and taken apart the same way"),
    ("layout", [sys.executable, "layouttest.py"], "the Sources tab, reaching any control, and search"),
    ("pedal", [sys.executable, "pedaltest.py"], "the sustain pedal: holding notes, and a source"),
    ("drawbar", [sys.executable, "drawbartest.py"], "the saw on the menu, and the drawbars: footages, Nyquist, the level law, layers"),
    ("morph", [sys.executable, "morphtest.py"], "the morph: its stations, its crossfade, the fundamental it keeps, layers, setups"),
    ("key", [sys.executable, "keytest.py"], "the page's key and the quantiser: only the key's notes, no chatter, the rate limit, chords"),
    ("clock", [sys.executable, "clocktest.py"], "the clock: locked oscillators, tap tempo, MIDI clock, Start and Continue; the bar, Stop and Start, the score on it, a MIDI clock counted in ticks"),
    ("cross", [sys.executable, "crosstest.py"], "crossings: the interval as a rhythm, the drift in equal temperament, the notes heard and not drawn"),
    ("pitch", [sys.executable, "pitchtest.py"], "the pitch estimator: rich registrations, the range, two periods or nothing, noise, the readout and Autoset"),
    ("play", [sys.executable, "playtest.py"], "the drawings played: the pitched harmonograph, its strike, Play the figure"),
    ("plane", [sys.executable, "planetest.py"], "the plane as an effect: the matrix, mirror, twist, kaleidoscope, clip, fold and snap, their arithmetic, aliasing at 1x, 2x and 4x, every pair once"),
    ("drive", [sys.executable, "drivetest.py"], "shaping inside the voice: the drive's curve, the fold's Bessel harmonics, each voice on its own, before the envelope, crush, layers, the cost"),
    ("vcf", [sys.executable, "vcftest.py"], "the voice filter: Web Audio's biquad to 0.01 dB, swept at audio rate, key tracking, its envelope per note"),
    ("voicefx", [sys.executable, "voicefxtest.py"], "inside the voice: FM against Bessel, ring, sync band-limited and corrected once, the sub, unison, layers, setup codes"),
    ("time", [sys.executable, "timetest.py"], "delay and chorus: repeats to the sample, ping-pong, feedback held, the tempo, sidebands, every pair once"),
    ("livefx", [sys.executable, "livefxtest.py"], "the plane and the delay on a live input: drawn and heard, the generator's arithmetic, a routing on a mono input, a file's repeats, where it does not go"),
    ("hearing", [sys.executable, "hearingtest.py"], "the sound as sources: pitch, brightness, bands, width, flux, their continuity, and the loop"),
    ("drawing", [sys.executable, "drawingtest.py"], "the sound driving the drawings: energy in, a kick and its friction, events only to what is struck, onset, firing"),
    ("input", [sys.executable, "inputtest.py"], "live audio into the generator: off is off, FM a factor on the rate, the ride a scale, the clock a lock, and the stream opened only while it can be used"),
    ("score", [sys.executable, "scoretest.py"], "the picture as a score, and MIDI out: rows to notes, the playhead at the tempo, the voice heard and not drawn, channels, all-notes-off, the rate limit"),
    ("arp", [sys.executable, "arptest.py"], "the arpeggiator: the orders, struck steps, the hands kept, the tempo, the dyad's intervals, letting go"),
    ("threshold", [sys.executable, "thresholdtest.py"], "thresholds and Pluck: rising through a level, hysteresis, the gap, loops refused, the note struck and sent"),
    ("macro", [sys.executable, "macrotest.py"], "macros and the morph between sliders: fan-out, names in codes, a geometric pitch, menus left alone, the hand respected, a macro on the fader"),
    ("solid", [sys.executable, "solidtest.py"], "the new figures and solids: every route closed along its edges with the fewest retraces, the polygon and the butterfly exact"),
    ("text", [sys.executable, "texttest.py"], "text and SVG paths as figures: the beam's speed, the font, every path command, the panel, drawn on the path, in codes"),
    ("sketch", [sys.executable, "sketchtest.py"], "drawing a figure on the screen: it lands under the pointer turned and zoomed, the pen, the limit, the cursors wait, in codes"),
    ("second", [sys.executable, "secondtest.py"], "the second generator: its figure exactly, FM, ride and clock into the first against references, lanes, layers, codes"),
    ("cycle", [sys.executable, "cycletest.py"], "the drawn cycle: tables band-limited by numpy's FFT, scaled alike, no step at a hand-over, drawn with the mouse, played, in codes"),
    ("pulse", [sys.executable, "pulsetest.py"], "the pulse: a pulse's harmonics at a quarter, a third and a tenth, the square at a half, no DC or clip, the width read, patched, per layer, synced, in codes"),
    ("fit", [sys.executable, "fittest.py"], "no Bench tab scrolls: every tab on the tone and a rack of six, keyboard and Photocell on and off, every kind, and ten learned controllers; each section dealt at the height it measured"),
    ("host", [sys.executable, "hosttest.py"], "inside the plugin: the page finds JUCE's bridge, draws the plugin's frames at the plugin's rate, one fetch at a time, and reports how the picture gets through; without the bridge it is the website"),
    ("fade", [sys.executable, "fadetest.py"], "routings fading in and out on the sound, the picture and the picture's own sources, ghosts heard and never saved, and every preset gliding into itself"),
    ("picturepresets", [sys.executable, "picturepresettest.py"], "the picture playing itself: every preset turns the photocell on and routes the picture, every loop moves and none runs away, the wandering loop wanders, and presets that use several sources"),
    ("budget", [sys.executable, "budgettest.py"], "S10: sixteen voices and their releases, everything on, under half of real time; the model against the machine; the order things are given up in; caps that do not creep; a cut that fades; the readout; no preset governed"),
    ("drawnplay", [sys.executable, "drawnplaytest.py"], "the rest of J2: a dyad closes the rose, the solid's axes as destinations, the drawings as sources, Play fitting a rack of six in every kind"),
    ("wavetable", [sys.executable, "wavetabletest.py"], "the wavetable: each slot the drawn cycle's read exactly, the mix between, the default bank's harmonics, the position patched and per layer, the pane and Grab on the slot chosen, codes, a rack of six"),
    ("noise", [sys.executable, "noisetest.py"], "the noises: white flat, pink -3 and brown -6 dB an octave, their levels, each channel its own, sample and hold held, pitched and band-limited, the chord's path and layer B"),
    ("grab", [sys.executable, "grabtest.py"], "grab a cycle: a known file lane's cycle point for point with its note held, worse with the wrong note, measured without one, averaged on noise, the right lane, refusals, no scroll"),
    ("record", [sys.executable, "recordtest.py"], "Record: the clip is the screen and the speakers, across a change of source, an unheard input once, its length written in"),
    ("photo", [sys.executable, "phototest.py"], "the photocell: the phosphor grid, the reticle, the loop"),
    ("shape", [sys.executable, "shapetest.py"], "what the picture says: five sources and a verdict"),
    ("loop", [sys.executable, "looptest.py"], "the loop through the sound, and its bounds held"),
    ("preset", [sys.executable, "presettest.py"], "the preset library and its browser: every preset what it says, sections, search, keys, saved, where it lands"),
    ("perform", [sys.executable, "performtest.py"], "the presets for playing: every routing a hand moves, both layers sounding, live effects in the path"),
    ("regress", [sys.executable, "regress.py"], "presets, displays, source switching"),
    ("sources", [sys.executable, "sources.py"], "rack, file, tone, and a denied mic"),
]


def main(argv):
    want = set(argv[1:])
    # beam.test.mjs reads the shipped script, so it has to be extracted first.
    subprocess.run([sys.executable, "extract.py"], cwd=os.path.dirname(HERE), check=True)

    failed = []
    for name, cmd, blurb in SUITES:
        if want and name not in want:
            continue
        print("\n=== %s — %s ===" % (name, blurb), flush=True)
        if subprocess.run(cmd, cwd=HERE).returncode != 0:
            failed.append(name)

    print()
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print("everything passes")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
