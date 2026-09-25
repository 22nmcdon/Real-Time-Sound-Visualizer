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
    ("clock", [sys.executable, "clocktest.py"], "the clock: locked oscillators, tap tempo, MIDI clock, Start and Continue"),
    ("cross", [sys.executable, "crosstest.py"], "crossings: the interval as a rhythm, the drift in equal temperament, the notes heard and not drawn"),
    ("pitch", [sys.executable, "pitchtest.py"], "the pitch estimator: rich registrations, the range, two periods or nothing, noise, the readout and Autoset"),
    ("play", [sys.executable, "playtest.py"], "the drawings played: the pitched harmonograph, its strike, Play the figure"),
    ("photo", [sys.executable, "phototest.py"], "the photocell: the phosphor grid, the reticle, the loop"),
    ("shape", [sys.executable, "shapetest.py"], "what the picture says: five sources and a verdict"),
    ("loop", [sys.executable, "looptest.py"], "the loop through the sound, and its bounds held"),
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
