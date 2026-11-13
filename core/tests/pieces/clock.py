"""The clock, on the core alone: oscillators locked to the tempo, tap tempo, a
MIDI clock, Start, Stop and Continue, the bar, and the score on it.

These were clocktest.py's on ?brain=js until stage 5, step 3, batch 2 (13
Nov): there the page's own clockTap, setTempo, clockStep, midiBytes,
midiRealtime, transportStart, transportBeat and scoreTick were called at
made-up times and its lfos[] and transport read back, and the running
oscillator's crossings counted over two real seconds. Here scope::Clock as
the Brain holds it (clock_cpp), the score on it (score_cpp) and the
keyboard's byte parser (keyboard_cpp), every time the run's own, so nothing
here waits on a wall clock. Each check has a null beside it, a known-wrong
reading seen red.

What stayed in clocktest.py, on the default page: what the face says - the
LFO card's reading and the Rate slider standing aside, the tempo slider and
its readings, the Bar row's button and reading, and setup codes. See there.
"""


def _lines(kit, tool, commands):
    return kit.run(tool, "run\n%s\nend\n" % "\n".join(commands)).strip().split("\n")


def _f(line, name):
    t = line.split(" | ", 1)[1].split()
    return t[t.index(name) + 1]


def _lfo(line, i=0):
    """An oscillator's rate, phase and restarts, off a clock_cpp line."""
    t = line.split(" | ", 1)[1].split()
    k = t.index("lfo%d" % i)
    return [float(v) for v in t[k + 1:k + 4]]


def _said(line):
    return [p.strip() for p in line.split(" | ")[0].split(" :: ")[1:]]


class Script:
    """Commands for one run, with a name on the lines to be read back."""
    def __init__(self): self.cmds, self.marks = [], {}
    def __call__(self, *cmds, mark=None):
        self.cmds += cmds
        if mark: self.marks[mark] = len(self.cmds) - 1
    def read(self, kit, tool):
        out = _lines(kit, tool, self.cmds)
        return {k: out[i] for k, i in self.marks.items()}, out


def run(kit):
    # --- an oscillator locked to the tempo (clocktest :73, :77, :100) -------
    # On ?brain=js: the LFO card's sync menu changed on the page and the
    # page's lfos[0].rate read, then setTempo(90) and clockStep. Here the
    # core's clock frame (clockFrame, as the Brain runs it) writes the rate.
    s = Script()
    for v in ("1/4", "1", "1/8t", "4", "1/8"):
        s("sync 0 %s" % v, "step", mark=v)
    s("sync 0 1/4", "tempo 90", "step", mark="at90")
    r, _ = s.read(kit, "clock_cpp")
    rates = {k: _lfo(r[k])[0] for k in ("1/4", "1", "1/8t", "4", "at90", "1/8")}
    kit.check("at 120, 1/4 is 2 Hz, a bar 0.5, a quaver triplet 6 and four bars 0.125",
              (rates["1/4"], rates["1"], rates["1/8t"], rates["4"]) == (2, 0.5, 6, 0.125), str(rates))
    kit.null("a plain quaver is not the triplet's 6", rates["1/8"] != 6, str(rates["1/8"]))
    kit.check("it follows the tempo: 1/4 at 90 is 1.5 Hz", rates["at90"] == 1.5, str(rates["at90"]))
    kit.null("and 1.5 is not what 1/4 was at 120", rates["1/4"] != 1.5)
    # The rate half of clocktest :348 ("restored, the lock runs at the code's
    # tempo: 1/2 at 96 is 0.8 Hz"), the page's lfos[1] after restore() on
    # ?brain=js; the code coming back whole stays in clocktest.py, on the
    # default page, and the core's decode of it is parity's restore section.
    o96 = _lfo(_lines(kit, "clock_cpp", ["tempo 96", "sync 1 1/2", "step"])[-1], 1)[0]
    o120 = _lfo(_lines(kit, "clock_cpp", ["sync 1 1/2", "step"])[-1], 1)[0]
    kit.check("the second oscillator locked to a minim at 96 runs at 0.8 Hz", abs(o96 - 0.8) < 1e-12, repr(o96))
    kit.null("at 120 the same lock is 1 Hz", abs(o120 - 0.8) >= 1e-12, repr(o120))
    # Counted off the oscillator going round, as the web check counted
    # lfos[0].value over two real seconds (+-0.6 Hz for the page's timers):
    # here two seconds of audio through the generator that steps it, so a
    # locked rate the stepping never used fails, and nothing waits.
    def round_at(tempo):
        out = _lines(kit, "clock_cpp", ["tempo %d" % tempo, "sync 0 1/8", "step", "play 2000"])
        return int(_said(out[-1])[0].split()[1])
    four, two = round_at(120), round_at(60)
    kit.check("and the running oscillator goes round at it: 1/8 at 120, four times a second", four in (7, 8),
              "%d rising crossings in two seconds" % four)
    kit.null("at 60 the same lock goes round half as often", two in (3, 4), "%d" % two)

    # --- tap tempo (clocktest :119 to :125) ---------------------------------
    # On ?brain=js the page's clockTap at made-up times, its transport.set
    # and lfos[0] read. Here the core's tapTempo. One change of fixture: the
    # tempo starts at 100 rather than the default 120, so "one tap leaves the
    # tempo where it was" cannot pass by the tempo already being the 120 the
    # next taps make.
    s = Script()
    s("tempo 100", "sync 0 1/4", "phase 0 2", "at 10000", "tap", mark="one")
    s("at 10500", "tap", "at 11000", "tap", "at 11500", "tap", mark="tapped")
    s("at 11900", "tap", mark="blended")
    s("at 20000", "tap", mark="paused")
    s("at 20400", "tap", "at 20800", "tap", mark="fresh")
    r, _ = s.read(kit, "clock_cpp")
    tapped = (float(_f(r["tapped"], "set")), _lfo(r["tapped"])[1:])
    kit.check("taps half a second apart are 120, and restart the locked oscillator on each",
              tapped == (120, [0, 3]), str(tapped))
    kit.null("before them the oscillator stood at its phase of two, unrestarted", _lfo(r["one"])[1:] == [2, 0])
    kit.check("and one tap on its own is no tempo: it leaves the tempo where it was",
              float(_f(r["one"], "set")) == 100 and float(_f(r["paused"], "set")) == 129,
              "%s, %s" % (_f(r["one"], "set"), _f(r["paused"], "set")))
    kit.check("the tempo is the mean of the last four taps' gaps: 500, 500 and 400 is 129",
              float(_f(r["blended"], "set")) == 129, _f(r["blended"], "set"))
    kit.null("the last gap alone, 400 ms, would be 150", float(_f(r["blended"], "set")) != 150)
    kit.check("after a pause of two seconds it starts again: 400 apart is 150, not a blend with before",
              float(_f(r["fresh"], "set")) == 150, _f(r["fresh"], "set"))
    v = Script(); moved = {"at 20000": "at 13000", "at 20400": "at 13400", "at 20800": "at 13800"}
    v.cmds = [moved.get(c, c) for c in s.cmds]; v.marks = dict(s.marks)
    kit.null("after a pause under two seconds the taps blend, and it is not 150",
             float(_f(v.read(kit, "clock_cpp")[0]["fresh"], "set")) != 150)

    # --- MIDI clock (clocktest :168, :170's rate, :174, :176, :180) --------
    # On ?brain=js: 25 ticks through the page's midiBytes, jittered as USB
    # gives them and ending now, then clockStep; then clockStep 700 ms on.
    # Here the core's clock, the ticks at the same made-up times.
    gap = 60000 / 120 / 24
    T = 50000
    s = Script()
    s("tempo 90", "sync 0 1/4")
    times = []
    for i in range(24, -1, -1):
        jitter = 0 if i in (0, 24) else (4 if i % 3 == 0 else -3 if i % 3 == 1 else -1)
        times.append(T - i * gap + jitter)
        s("at %r" % times[-1], "tick")
    s("at %r" % T, "step", mark="running")
    s("at %r" % (T + 700), "step", mark="stopped")
    r, _ = s.read(kit, "clock_cpp")
    bpm = float(_f(r["running"], "bpm"))
    kit.check("25 ticks at 120, jittered, read as 120 - the mean of the gaps, not the last one",
              abs(bpm - 120) < 0.2 and _f(r["running"], "from") == "midi", "%.3f from %s" % (bpm, _f(r["running"], "from")))
    last_gap = 60000 / ((times[-1] - times[-2]) * 24)
    kit.null("the last gap alone reads another tempo", abs(last_gap - 120) >= 0.2, "%.2f" % last_gap)
    # The rate half of :170; the slider and the readings, the face's, stay in clocktest.py.
    kit.check("while it runs the locked oscillator follows it", _lfo(r["running"])[0] == bpm / 60, str(_lfo(r["running"])))
    kit.null("and not the slider's 90", _lfo(r["running"])[0] != 1.5)
    kit.check("half a second after the last tick the tempo is the slider's again",
              float(_f(r["stopped"], "bpm")) == 90 and _f(r["stopped"], "from") == "internal",
              "%s from %s" % (_f(r["stopped"], "bpm"), _f(r["stopped"], "from")))
    s = Script()
    s("sync 0 1/4", "phase 0 3", "rt 250", mark="start")
    s("phase 0 3", "rt 251", mark="cont")
    s("sync 0 -", "phase 0 3", "rt 250", mark="free")
    r, _ = s.read(kit, "clock_cpp")
    kit.check("Start restarts the locked oscillators, and Continue does not",
              _lfo(r["start"])[1:] == [0, 1] and _lfo(r["cont"])[1:] == [3, 1], "%s %s" % (_lfo(r["start"]), _lfo(r["cont"])))
    kit.null("and a free one Start leaves where it was", _lfo(r["free"])[1:] == [3, 1], str(_lfo(r["free"])))
    # The parser: on ?brain=js the page's midiBytes, with transport.ticks and
    # midi.notes read. Here the core's Keyboard::bytes, whose real-time bytes
    # go to the clock (keyboard_cpp logs them as `realtime`). Only the parser
    # is held: on the site a port's message reaches the instrument cut at
    # every status byte (scope.html's midiBytes, `piece`), and the keyboard
    # does not carry half a message from one call to the next, so the same
    # bytes from a real port lose the note there. Found by this move; it is
    # the page's or the core's to change, not this batch's.
    def parsed(data):
        out = _lines(kit, "keyboard_cpp", ["mode mono", "bytes %s" % data])
        line = out[-1]
        ticks = sum(1 for s_ in _said(line) if s_ == "realtime 248")
        notes = _f(line, "notes")
        return notes, ticks
    notes, ticks = parsed("0x90,64,0xf8,100")
    held = lambda n, t: n.startswith("64/") and abs(float(n[3:]) - 100 / 127) < 1e-12 and t == 1
    kit.check("a clock byte in the middle of a note-on is a tick, and the note lands with its own velocity",
              held(notes, ticks), "%s, %d ticks" % (notes, ticks))
    soft = parsed("0x90,64,0xf8,50")
    plain = parsed("0x90,64,100")
    kit.null("the same bytes with a velocity of 50 are read as 50, and without the clock byte there is no tick",
             not held(*soft) and not held(*plain) and plain[0] == notes, "%s; %s" % (soft, plain))

    # --- the bar: start and stop (clocktest :267 to :273, :286 to :299) ----
    # On ?brain=js the page's transportStart, transportBeat, transportSaid,
    # setTempo, transportStop, midiRealtime, clockStep and clockTap at times
    # far ahead of its own frames. Here the core's, at the run's times; a
    # line's `beat` and `said` are where the bar is at that line's `at`.
    T = 10_000_000
    s = Script()
    s("at %d" % T, "tempo 120", "start", "at %d" % (T + 1000), mark="second")
    s("at %d" % (T + 1500), mark="said")
    s("at %d" % (T + 1000), "tempo 60", mark="atChange")
    s("at %d" % (T + 2000), mark="after")
    s("at %d" % (T + 2500), "stop", "at %d" % (T + 9000), mark="stood")
    s("sync 0 1/4", "phase 0 3", mark="beforeRestart")
    s("at %d" % (T + 10000), "start", mark="restart")
    M = T + 40000
    s("tempo 120", "at %d" % M, "rt 250", "at %d" % (M + 10), mark="beforeTick")
    s("at %r" % (M + gap), "tick", mark="firstTick")
    at = M + gap
    for k in range(1, 49):
        at = M + gap * (k + 1) + (4 if k % 3 == 0 else -3 if k % 3 == 1 else -1)
        s("at %r" % at, "tick")
    s("at %r" % at, mark="ticked")
    s("at %r" % (at + 300), mark="ahead")
    s("at %r" % (at + 5), "rt 252", mark="stood2")
    s("at %r" % (at + 2000), "rt 251", "at %r" % (at + 2010), mark="contBefore")
    s("at %r" % (at + 2000 + gap), "tick", mark="continued")
    last = at + 2000 + gap
    s("at %r" % (last + 700), mark="letGoBefore")
    s("step", mark="letGo")
    s("at %r" % (last + 10000), "rt 250", "at %r" % (last + 10600), mark="noClockBefore")
    s("step", mark="noClock")
    P = T + 80000
    s("at %d" % P, "start", "at %d" % (P + 100), "tap", "at %d" % (P + 600), "tap", mark="tapOne")
    s("at %d" % (P + 1100), mark="tapNext")
    s("at %d" % (P + 1200), "stop", "at %d" % (P + 4000), "tap", "at %d" % (P + 4400), "tap", mark="tapStopped")
    r, out = s.read(kit, "clock_cpp")
    beat = lambda k: float(_f(r[k], "beat"))
    # The same script with one thing changed, each the null of a check below.
    def variant(old, new, mark):
        v = Script()
        v.cmds = list(s.cmds); v.marks = dict(s.marks)
        i = v.cmds.index(old); v.cmds[i] = new
        return float(_f(v.read(kit, "clock_cpp")[0][mark], "beat"))
    kit.check("started, the bar moves at the tempo from nought: a second at 120 is two beats, and 1.5 s is bar 1, beat 4",
              beat("second") == 2 and _f(r["said"], "said") == "1.4", "%s, %s" % (beat("second"), _f(r["said"], "said")))
    kit.null("and 1.5 s is not two beats", beat("said") != 2)
    kit.check("a tempo change goes on from where the bar is: two beats at the change, three a second later at 60",
              beat("atChange") == 2 and beat("after") == 3, "%s, %s" % (beat("atChange"), beat("after")))
    kit.null("with no change of tempo it would have been four", variant("tempo 60", "tempo 120", "after") == 4)
    kit.check("stopped, it stands where it stopped, and says so", beat("stood") == 3.5 and _f(r["stood"], "said") == "1.4",
              "%s, %s" % (beat("stood"), _f(r["stood"], "said")))
    kit.null("with no Stop it would have run on to ten", variant("stop", "at %d" % (T + 2500), "stood") == 10)
    kit.check("Start is the one again, and the locked oscillators start with it",
              beat("restart") == 0 and _lfo(r["restart"])[1:] == [0, 1], "%s %s" % (beat("restart"), _lfo(r["restart"])))
    kit.null("before the Start the bar stood at 3.5 and the oscillator at three",
             beat("beforeRestart") == 3.5 and _lfo(r["beforeRestart"])[1] == 3)
    kit.check("a MIDI Start waits for the device's first tick: the bar before it, nought on it",
              beat("beforeTick") < 0 and beat("firstTick") == 0, "%s, %s" % (beat("beforeTick"), beat("firstTick")))
    # Jittered by up to 4 ms, which in time would be a hundredth of a beat
    # either way: counted in ticks it is exact.
    kit.check("under a clock the bar is counted in ticks: 48 jittered ticks on, exactly two beats",
              abs(beat("ticked") - 2) < 1e-9, repr(beat("ticked")))
    in_time = (at - (M + gap)) * 120 / 60000
    kit.null("counted in time from the first tick it would be off by the jitter", abs(in_time - 2) > 1e-6, repr(in_time))
    kit.check("and between ticks it never guesses past the next one", abs(beat("ahead") - (2 + 1 / 24)) < 1e-9, repr(beat("ahead")))
    kit.null("let go by the frame half a second on, it does go past the tick", beat("letGo") > beat("ahead") + 1 / 24)
    stood = beat("stood2")
    kit.check("MIDI Stop stands and Continue goes on from there at the next tick, restarting nothing",
              beat("contBefore") < stood and abs(beat("continued") - stood) < 1e-9
              and _lfo(r["continued"])[2] == _lfo(r["stood2"])[2],
              "stood %r, before %r, now %r" % (stood, beat("contBefore"), beat("continued")))
    kit.null("a Start in its place puts the bar back at nought on the tick", variant("rt 251", "rt 250", "continued") == 0)
    want = float(_f(r["continued"], "beat")) + 700 * 120 / 60000
    kit.check("a clock that stops lets the bar go on to where it would have been, not half a second behind",
              abs(beat("letGo") - want) < 1e-6 and _f(r["letGo"], "from") == "internal", "%r against %r" % (beat("letGo"), want))
    kit.null("before the frame lets it go, it stands a tick on, short of where it should be",
             abs(beat("letGoBefore") - want) > 0.5, repr(beat("letGoBefore")))
    kit.check("and a Start that no clock follows starts anyway, rather than waiting for ever", beat("noClock") > 1, repr(beat("noClock")))
    kit.null("and until the frame lets it go it is held at nought, a tick short", beat("noClockBefore") <= 0, repr(beat("noClockBefore")))
    kit.check("a tap is the one while the bar runs", (beat("tapOne"), beat("tapNext")) == (0, 1),
              "%s, %s" % (beat("tapOne"), beat("tapNext")))
    kit.null("without the taps the bar would be at 1.2 there",
             abs(variant("tap", "at %d" % (P + 100), "tapOne") - 1.2) < 1e-9)
    kit.check("stopped, taps set the tempo and start nothing",
              _f(r["tapStopped"], "running") == "0" and float(_f(r["tapStopped"], "set")) == 150,
              "%s %s" % (_f(r["tapStopped"], "running"), _f(r["tapStopped"], "set")))
    kit.null("the taps made a tempo: it was 120 before them", float(_f(r["tapOne"], "set")) == 120)

    # --- the score on the bar (clocktest :275 to :280) ----------------------
    # On ?brain=js the page's scoreTick with phosphor.grid lit by hand and
    # the source's strike wrapped to count. Here score_cpp: the core's
    # scoreTick on the Brain's clock, a row lit in its own grid, strikes
    # logged.
    lit = ["cell 40 %d 0.9" % c for c in range(64)]
    s = Script()
    s(*lit, "tempo 120", "at %d" % (T + 20000), "start", "score on 1/16 1 48 3", "at %d" % (T + 21300), "frame", mark="joined")
    s("at %d" % (T + 25000), "start", "frame", mark="downbeat")
    s("at %d" % (T + 25100), "stop")
    for t in range(25100, 27000, 50): s("at %d" % (T + t), "frame")
    s(mark="stopped")
    s("at %d" % M, "midistart", "at %d" % (M + 10), "frame", mark="beforeTick")
    s("at %r" % (M + gap), "tick", "frame", mark="onTick")
    r, out = s.read(kit, "score_cpp")
    struck_from = lambda a, b: sum(1 for l in out[a:b + 1] for x in _said(l) if x.startswith("strike"))
    kit.check("the score switched on mid-bar joins the bar where it is, not at its own column nought",
              _f(r["joined"], "col") == "10", _f(r["joined"], "col"))
    kit.null("2.6 beats in is not column nought", _f(r["joined"], "col") != "0")
    kit.check("and Start brings it back to column nought on the downbeat", _f(r["downbeat"], "col") == "0", _f(r["downbeat"], "col"))
    stop_at = s.marks["downbeat"] + 1
    kit.check("stopped, the score strikes nothing and lets go of its notes",
              struck_from(stop_at, s.marks["stopped"]) == 0 and _f(r["stopped"], "col") == "-1" and _f(r["stopped"], "notes") == "-",
              "struck %d, col %s, notes %s" % (struck_from(stop_at, s.marks["stopped"]), _f(r["stopped"], "col"), _f(r["stopped"], "notes")))
    kit.null("running, the same frames would have struck", struck_from(s.marks["joined"], s.marks["downbeat"]) > 0)
    before = struck_from(s.marks["stopped"] + 1, s.marks["beforeTick"])
    on = struck_from(s.marks["beforeTick"] + 1, s.marks["onTick"])
    kit.check("a MIDI Start waits for the device's first tick: nothing struck before it, column nought on it",
              before == 0 and float(_f(r["beforeTick"], "beat")) < 0 and _f(r["onTick"], "col") == "0" and on == 1,
              "before %d (beat %s), on the tick %d at column %s" % (before, _f(r["beforeTick"], "beat"), on, _f(r["onTick"], "col")))
    kit.null("a Start that did not wait would have struck at once", on == 1 and before != 1)
