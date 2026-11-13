"""Onset (J1) and the events it fires (S3), on the core - onsettest.py's
numbers rows, and its firing rows.

These were onsettest.py's on `?brain=js` until stage 5, step 3, batch 4 (13
Nov): there a microphone faked from an oscillator whose gain was switched,
the page's `hearing.fluxRaw` and `onsetStep` driven by hand in a busy loop
of real milliseconds, and stand-in destinations the suite registered on the
page's own registry and fired through the page's `fireEvents`. Here the
core's hearing (hearing_cpp: windows of sines built sample by sample, a note
starting or stopping inside one by `gap`, and the frame's time given, so the
80 ms gap is counted on a clock that does not depend on how busy the machine
is), and the core's matrix with event destinations of its own (matrix_cpp's
`event`, a scripted source's `count`), whose rule an event reaches only an
event is `routingAllowed`. The core's hearing is the instrument's, on the
audio thread since 5t. onsettest.py keeps the face's registry. Each check
has its null.
"""
FRAME = 1000 / 60


def run(kit):
    check, null = kit.check, kit.null

    def onsets(frames):
        """Frames of (tones, gap, elapsed): tones a list of (hz, amp), the
        window built from them at the run's clock. The onset count after each."""
        cmds, t = ["len 4096", "lanes 1"], 0.0
        for tones, gap, dt in frames:
            t += dt
            cmds += ["at %r" % t, "clear"] + ["tone 0 %r %r 0" % (hz, amp) for hz, amp in tones] + ["gap " + gap, "frame %r" % dt]
        out = kit.run("hearing_cpp", "run\n" + "\n".join(cmds) + "\nend").strip().split("\n")
        counts = []
        for line in out:
            if line.startswith("frame "):
                w = line.split()
                counts.append(int(w[w.index("onset") + 1]))
        return counts

    NOTE = [(330, 0.8)]
    silent = lambda n, dt=FRAME: [([], "none", dt)] * n
    held = lambda n: [(NOTE, "none", FRAME)] * n
    attack = [(NOTE, "first", FRAME)]    # the note starting half-way through the window
    cut = [(NOTE, "second", FRAME)]      # and stopping half-way through, in one sample: a click
    release = [([(330, a)], "none", FRAME) for a in (0.6, 0.4, 0.2, 0.05)]   # 80 ms down to nothing

    # --- one attack, held, and released (:149) ---
    c = onsets(silent(30) + attack + held(120) + release + silent(48))
    at_attack, after_held = c[30], c[30 + 120]
    check("one attack is one onset however long it is held, and a release is none",
          c[29] == 0 and at_attack == 1 and after_held == 1 and c[-1] == 1, "%d, %d, then %d" % (at_attack, after_held, c[-1]))
    again = onsets(silent(30) + attack + held(20) + silent(10) + attack + held(20))
    null("a second attack is a second onset", again[-1] == 2, str(again[-1]))

    # A smaller rise, added by the mutation pass: every fixture above starts
    # from silence or a new pitch, a flux of about one, so an onset threshold
    # raised to 0.95 passed them all. A held note stepping up a fifth in
    # level, heard rising through the window, is a flux of about 0.57: an
    # onset at the threshold of 0.3. Its null is the same step heard steady.
    louder = onsets(silent(30) + [([(330, 0.4)], "none", FRAME)] * 10 + [([(330, 0.48)], "early", FRAME)])
    steady = onsets(silent(30) + [([(330, 0.4)], "none", FRAME)] * 10 + [([(330, 0.48)], "none", FRAME)])
    check("a held note stepping up in level, the window rising through it, is an onset", louder[-1] - louder[-2] == 1,
          "%d" % (louder[-1] - louder[-2]))
    null("and the same step with the window steady is none", steady[-1] - steady[-2] == 0)

    # --- eight strikes, each cut off (:151) ---
    strike = attack + held(6) + cut + silent(7)
    c = onsets(silent(30) + strike * 8)
    check("eight strikes are eight onsets, the click of each cut-off not counted", c[-1] == 8, str(c[-1]))
    c = onsets(silent(30) + strike * 4)
    null("and four are four, not eight", c[-1] == 4, str(c[-1]))

    # --- a swell, and the gap (:154, :156) ---
    # A flux held high: each frame a new pitch whose window grows louder
    # through it (`gap early`, the first three eighths silent), so the
    # energy rises and the spectrum is new every frame, for 400 ms.
    swell = [([(330 + 37 * k, 0.8)], "early", FRAME) for k in range(24)]
    fall = [([(330 + 37 * 23, 0.8)], "none", FRAME)] * 5  # the same pitch held: no new energy, the flux falls
    rise = [([(2000, 0.8)], "early", FRAME)]
    c = onsets(silent(30) + swell + fall + rise)
    check("a flux held high through a 400 ms swell is one onset, and fires again once it has fallen",
          c[30 + 23] == 1 and c[-1] == 2, "%d, then %d" % (c[30 + 23], c[-1]))
    c = onsets(silent(30) + sum([[([(330 + 37 * k, 0.8)], "early", FRAME), ([], "none", FRAME)] for k in range(12)], []))
    null("the same 400 ms falling between every frame fires more than once", c[-1] > 1, str(c[-1]))
    # A millisecond apart for 400 ms, rising and falling every frame: the
    # gap of 80 ms is all that holds it, so four to six.
    flicker = sum([[([(330 + 37 * (k % 40), 0.8)], "early", 1.0), ([], "none", 1.0)] for k in range(200)], [])
    c = onsets(silent(30) + flicker)
    fired = c[-1]
    check("and a flux flickering every millisecond fires no faster than the 80 ms gap allows",
          4 <= fired <= 400 / 80 + 1, "%d in 400 ms" % fired)
    slow = sum([[([(330 + 37 * (k % 40), 0.8)], "early", 10.0), ([], "none", 10.0)] for k in range(20)], [])
    many = onsets(silent(30) + slow * 10)[-1]
    null("and over four seconds the same flicker fires far more than six times: the bound is the gap's, not a stall",
         many > 400 / 80 + 1, str(many))

    # --- events reach only what is struck, and fire on a count (:100, :103, :184, :186, :188, :189) ---
    def matrix(cmds):
        return kit.run("matrix_cpp", "run\n" + "\n".join(cmds) + "\nend").strip().split("\n")
    def routings(line):
        return line.split(" amounts ")[1].split(" ")[0]
    # The face refuses such a routing (onsettest.py, on its registry); the
    # core keeps whatever a setup lists and acts on none of it: an event
    # source on a value moves nothing, a value on an event strikes nothing.
    # The event source is given a value too, its flash, which an event on a
    # value would carry if the rule let it (the mutation pass: without it the
    # check passed with the rule taken out).
    rows = matrix(["source test.hit event", "source lfo1", "event test.once",
                   "visual view.rotate 1 -1 1 0", "value lfo1 1", "value test.hit 1", "count test.hit 1",
                   "route test.hit view.rotate 1", "route lfo1 test.once 1", "frame",
                   "count test.hit 2", "value lfo1 -1", "frame"])
    acted = [f for r in rows if r.startswith("frame") for f in r.split(" | ")[0].split(" :: ")[1:] if not f.endswith(" 0")]
    check("an event reaches only what is struck: a value on an event strikes nothing, an event on a value moves nothing",
          acted == [], str(acted))
    rows = matrix(["source test.hit event", "source lfo1", "event test.once", "visual view.rotate 1 -1 1 0", "value lfo1 1",
                   "count test.hit 1", "route lfo1 view.rotate 1", "route test.hit test.once 1", "frame", "count test.hit 2", "frame"])
    acted = [f for r in rows if r.startswith("frame") for f in r.split(" | ")[0].split(" :: ")[1:] if not f.endswith(" 0")]
    null("the same two sources each on its own kind both act", any(f.startswith("fire") for f in acted)
         and any(f.startswith("visual") for f in acted), str(acted))

    rows = matrix(["source test.hit event", "event test.once", "event test.depth", "count test.hit 5",
                   "route test.hit test.once 1", "route test.hit test.depth 0.5", "frame",
                   "count test.hit 6", "frame", "count test.hit 9", "frame", "frame"])
    fires = [[f for f in r.split(" | ")[0].split(" :: ")[1:]] for r in rows if r.startswith("frame")]
    check("a routing does not fire when it is made, only on a count it has not seen", fires[0] == [], str(fires[0]))
    check("then a new count strikes each destination once, at its depth",
          sorted(fires[1]) == ["fire test.depth 0.5", "fire test.once 1"], str(fires[1]))
    check("and three counts in one frame are one strike, not three",
          sorted(fires[2]) == ["fire test.depth 0.5", "fire test.once 1"], str(fires[2]))
    null("and a frame with no new count strikes nothing", fires[3] == [], str(fires[3]))

    rows = matrix(["source hear.onset event picture", "event test.once", "count hear.onset 1",
                   "route hear.onset test.once 1", "frame", "count hear.onset 2", "frame"])
    struck = [f for r in rows if r.startswith("frame") for f in r.split(" | ")[0].split(" :: ")[1:]]
    check("and an onset hearing the generator it would strike is refused", struck == [], str(struck))
    rows = matrix(["source hear.onset event", "event test.once", "count hear.onset 1",
                   "route hear.onset test.once 1", "frame", "count hear.onset 2", "frame"])
    null("an onset hearing a microphone strikes", [f for r in rows if r.startswith("frame") for f in r.split(" | ")[0].split(" :: ")[1:]]
         == ["fire test.once 1"])
