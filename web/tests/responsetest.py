"""How the picture responds (11 Nov, web/docs/the-picture-amount.md, its last section).

The owner likes the Picture amount's swell - louder and a little harsher as
they play harder and faster - and asked for it to be consistent: the same
gesture the same response whatever came before. The study found two things
in the way. Each hand's sound was pushed by its own picture through the fold,
a loop that swelled and collapsed every four to eight seconds with nothing
played; and the reads were rescaled to a range that closed in two seconds,
so after a quiet spell a small nudge read as full scale. This holds the fix
to the owner's own test, rebuilt from the study's repro, with their setup
code: Crossed hands at Picture 47 with the delay, phaser and reverb on, split
at C4. Their sequence, in time:

    0.5 s      the left hand holds Db2 Ab2 C3
    2 to 4     the right hand runs up and down Db major pentatonic with C, five a second, velocity 55
    4 to 9     faster and harder, eight a second, velocity 95
    6.5        the chord changed to Gb2 Db3 F3, the right hand still running
    9          the right hand stops; the chord held
    15         soft (velocity 40): a Bb4 grace note into C5
    16.8       a Gb4 grace note into Ab4, held to 20 s
    21.5, 22.5 a soft F4; a soft Db5 held to 25 s
    27         the chord let go

and the same soft notes from a fresh start: the second chord at 0.5 s, the
soft notes from 6.5 s on the same spacing.

Rendered by the compiled core offline (response_cpp, a 128-frame step at a
time at 48 kHz with each message at its own sample), which parity holds the
page to sample for sample; so this is the site's sound and the plugin's.
The swell is the heard level against the same performance at Picture nought,
a quarter second at a time, its mean over a stretch.

The amount: the routes reach their top at a Picture of 100 now, where they
were clamped by reach from 62.5, so the owner's 47 pushes as about 75 does
now (47 x 0.8 / 0.5). The run's swell is judged at 100, the depth today's
stage reached at its top, against the bar the study's option 3 measured
(+6.3 dB on the study's own reconstruction of the sequence, where today's
stage swelled +4.5; on this one today's swells +4.1, measured with the stage
as it was before this change and kept here as TODAY). The soft notes are
judged at 75, the owner's own depth.

The checks, each with its null:

- Change: the fast run swells by at least +6.0 dB and 1.5 dB more than today
  did, and is as harsh as option 3 (at least 5.4 per cent of its energy above
  1 kHz). Null: Picture nought, which does not swell.
- Change: the soft notes after the swell swell no more than the same soft
  notes from a fresh start (by half a decibel), and by no more than a decibel
  at all. Null: Level, where a lit screen is a drive, and both swell.
- Swell off: a held chord alone does not swell - the most the level rises
  above where it has been since six seconds in is under a decibel and a half
  - in a split and in an unsplit sound, the unsplit at Picture 100, where the
  loop's gain is highest. Null: Swell on, which breathes by design (today's
  stage rose 4.5 to 6.7 dB here).
- Swell on: the push breathes, its peaks evenly spaced, at the period the
  Persistence sets - and a longer Persistence breathes more slowly. Null: the
  same at the other Persistence's period.
- Level: the fast run holds the push up while it lasts - the right hand's
  glow over the last second of the run at least nine tenths of the first
  second's. Null: Change, which settles while it is kept up.
- Both: a held chord keeps a base under it and a strike flares above it.
  Nulls: Change, with no base; Level, with no flare.
- Motion, the echo's read: one soft note on a dark screen moves it a little,
  and the fast run a lot. Null: the fast run, read the same way, is not small.

Parallel: offline renders, no real time.
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CORE = os.path.join(ROOT, "core")
BUILD = os.path.join(CORE, "build", "response")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def null(name, red, detail=""):
    check("null: " + name, red, detail)

OWNER = ("eyJ2IjoxMCwic2hhcGUiOiJzaW5lIiwib3NjU2NhbiI6MTAwLCJzY2FuUmVhZHNBIjoiQiIsInNjYW5SZWFkc0IiOiJBIiwiZnJlcSI6MTEw"
         "LCJjeWNsZXMiOiIiLCJkaXNwbGF5IjoieHkiLCJwZXJzaXN0ZW5jZSI6IjAuMDI1NSIsIm1pZGlNb2RlIjoicG9seSIsInBvbHlSb3VuZCI6dHJ1"
         "ZSwibGF5ZXJzIjoic3BsaXQiLCJwaWN0dXJlQW1vdW50Ijo0NywiZGVsYXlNaXgiOjM1LCJkZWxheUZlZWRiYWNrIjo0NywicGhhc2VyTWl4Ijoz"
         "MCwicmV2ZXJiTWl4IjoyNn0")
# Today's stage on this rendering of the sequence, at the owner's 47 (11 Nov,
# measured on the core before this change): the run's swell, and the most
# a held chord alone rose by itself, split and unsplit at 100.
TODAY = {"fast": 4.1, "held": (5.1, 6.7)}

os.makedirs(BUILD, exist_ok=True)
EXE = os.path.join(BUILD, "response_cpp")
subprocess.run(["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-I", os.path.join(CORE, "include"),
                os.path.join(CORE, "tests", "tools", "response_cpp.cpp"), "-o", EXE], check=True)

def on(t, n, v): return (t, 0x90, n, v)
def off(t, n): return (t, 0x80, n, 0)
PENT = [61, 63, 65, 68, 70, 72, 73, 75, 77]
CH1, CH2 = [37, 44, 48], [42, 49, 53]
def run(t0, t1, per, vel):
    ev, seq, i, t = [], PENT + PENT[-2:0:-1], 0, t0
    while t < t1 - 1e-9:
        n = seq[i % len(seq)]
        ev += [on(t, n, vel), off(t + 0.8 / per, n)]
        i += 1; t += 1.0 / per
    return ev
def soft(t0):
    s = lambda d: t0 + d
    return [on(s(0), 70, 40), off(s(0.12), 70), on(s(0.12), 72, 40), off(s(1.2), 72),
            on(s(1.8), 66, 40), off(s(1.92), 66), on(s(1.92), 68, 40), off(s(5.0), 68),
            on(s(6.5), 65, 40), off(s(6.8), 65), on(s(7.5), 73, 40), off(s(10.0), 73)]
SEQUENCE = (sorted([on(0.5, n, 80) for n in CH1] + run(2, 4, 5, 55) + run(4, 9, 8, 95) + [off(6.5, n) for n in CH1]
                   + [on(6.5, n, 80) for n in CH2] + soft(15) + [off(27, n) for n in CH2]), 28.0)
FRESH = (sorted([on(0.5, n, 80) for n in CH2] + soft(6.5) + [off(18.5, n) for n in CH2]), 19.5)
HELD = (sorted([on(0.5, n, 80) for n in CH2] + [off(19.5, n) for n in CH2]), 20.0)
LONG = (sorted([on(0.5, n, 80) for n in CH2] + [off(29.5, n) for n in CH2]), 30.0)  # a slow breath's few periods

def render(events, seconds, patch):
    path = os.path.join(BUILD, "events-%d.txt" % os.getpid())
    with open(path, "w") as f:
        for e in events: f.write("%.6f %d %d %d\n" % e)
    out = subprocess.run([EXE, OWNER, json.dumps(patch), path, str(seconds)], check=True, capture_output=True, text=True).stdout
    level, band, stage = [], [], []
    for line in out.split("\n"):
        w = line.split()
        if not w: continue
        if w[0] == "level": level.append((float(w[1]), float(w[2])))
        elif w[0] == "band": band.append((float(w[1]), float(w[2]), float(w[3])))
        elif w[0] == "stage":
            v = [float(x) for x in w[1:]]
            stage.append({"t": v[0], "live": v[1], "A": dict(zip(("glow", "level", "change", "motion", "hold"), v[2:7])),
                          "B": dict(zip(("glow", "level", "change", "motion", "hold"), v[7:12]))})
    return {"level": level, "band": band, "stage": stage}

def mean(xs): return sum(xs) / len(xs) if xs else float("nan")
def swell(a, z, t0, t1):
    """The mean of the level against Picture nought's over [t0, t1)."""
    return mean([x[1] - y[1] for x, y in zip(a["level"], z["level"]) if t0 <= x[0] < t1])
def harsh(a, t0, t1):
    rows = [r for r in a["band"] if t0 <= r[0] and r[0] + 4096 / 48000 <= t1]
    return sum(r[2] for r in rows) / sum(r[1] for r in rows)
def rise(a, z, t0=6.0, t1=19.25):
    """The most the level, against Picture nought's, rises above its least since t0: from six seconds, by
    when the chord's own strike has flared, as the study measured it (a strike's flare building in its first
    seconds is a rise from two), to the quarter second before the keys come up."""
    least, most = float("inf"), 0.0
    for x, y in zip(a["level"], z["level"]):
        if x[0] < t0 or x[0] >= t1: continue
        d = x[1] - y[1]
        least = min(least, d); most = max(most, d - least)
    return most
def reads(a, hand, key, t0, t1): return [s[hand][key] for s in a["stage"] if t0 <= s["t"] < t1]
def peaks(xs, ts):
    """The times of the local maxima of a read, each the top of a rise of at least a twentieth."""
    out, low, cand = [], xs[0], None
    for x, t in zip(xs, ts):
        if cand is None:
            if x - low > 0.05: cand = (x, t)
            low = min(low, x)
        elif x > cand[0]: cand = (x, t)
        elif cand[0] - x > 0.05: out.append(cand[1]); cand, low = None, x
    return out

def at(patch, **more): p = dict(patch); p.update(more); return p
def responds(mode, amount, **more): return at({"pictureResponds": mode, "pictureAmount": amount}, **more)

# --- Change, the owner's sequence -------------------------------------------------
seq100, seq0 = render(*SEQUENCE, responds("change", 100)), render(*SEQUENCE, responds("change", 0))
fast, after = swell(seq100, seq0, 4, 9), swell(seq100, seq0, 9, 14.5)
h100, h0 = harsh(seq100, 4, 9), harsh(seq0, 4, 9)
check("Change, at the routes' top: the fast run swells by %+.2f dB (today's stage +%.1f, the study's option 3 +6.3), "
      "and nothing after it (%+.2f)" % (fast, TODAY["fast"], after), fast >= 6.0 and fast >= TODAY["fast"] + 1.5 and after < 1.0)
check("and it is as harsh as option 3: %.1f per cent of its energy above 1 kHz (%.1f at Picture nought)" % (100 * h100, 100 * h0),
      h100 >= 0.054 and h100 > h0 * 1.5)
null("at Picture nought the run does not swell (%+.2f dB)" % swell(seq0, seq0, 4, 9), not (swell(seq0, seq0, 4, 9) >= 6.0))

seq75, fr75, fr0 = render(*SEQUENCE, responds("change", 75)), render(*FRESH, responds("change", 75)), render(*FRESH, responds("change", 0))
seq75z = render(*SEQUENCE, responds("change", 0))
inseq, fresh = swell(seq75, seq75z, 15, 25), swell(fr75, fr0, 6.5, 16.5)
print("        at 75, the owner's depth: the run %+.2f dB, after it %+.2f" % (swell(seq75, seq75z, 4, 9), swell(seq75, seq75z, 9, 14.5)))
check("Change, at the owner's depth: the soft notes after the swell swell %+.2f dB, the same from a fresh start %+.2f: "
      "no more in sequence, and not at all" % (inseq, fresh), inseq <= fresh + 0.5 and inseq <= 1.0)
lseq, lfr = render(*SEQUENCE, responds("level", 75)), render(*FRESH, responds("level", 75))
linseq, lfresh = swell(lseq, seq75z, 15, 25), swell(lfr, fr0, 6.5, 16.5)
null("Level, a drive the lit screen turns: the soft notes swell %+.2f in sequence and %+.2f fresh" % (linseq, lfresh),
     not (linseq <= lfresh + 0.5 and linseq <= 1.0))

# --- Swell off and on, a chord held alone ----------------------------------------------
for name, patch, null_patch, today in (
        ("in a split, at 75", responds("change", 75), None, TODAY["held"][0]),
        ("unsplit, at 100", responds("change", 100, layers="off"), None, TODAY["held"][1])):
    a, z = render(*HELD, patch), render(*HELD, at(patch, pictureAmount=0))
    r = rise(a, z)
    check("Swell off, a chord held alone %s does not swell: it rises %.2f dB at most (today's stage %.1f)" % (name, r, today), r < 1.5)
    on_ = render(*HELD, at(patch, pictureSwell=True))
    null("Swell on, the same chord rises %.2f dB" % rise(on_, z), not (rise(on_, z) < 1.5))

# Swell on: the breath's period follows the Persistence. Level, so the push
# under the breath is steady and each peak is the breath's.
periods = {}
for persistence, half in (("0.0255", 0.4501), ("0.12", 0.0886)):
    a = render(*LONG, responds("level", 75, pictureSwell=True, persistence=persistence))
    rows = [s for s in a["stage"] if 4 <= s["t"] < 29.5]
    p = peaks([s["A"]["glow"] for s in rows], [s["t"] for s in rows])
    gaps = [b - a_ for a_, b in zip(p, p[1:])]
    want = 2 + 8 * half
    periods[persistence] = (gaps, want)
    even = bool(gaps) and max(gaps) - min(gaps) < 0.25 * want
    check("Swell on at a Persistence of %s: the push breathes every %s s, evenly, at the %.2f s it sets"
          % (persistence, ", ".join("%.2f" % g for g in gaps), want),
          len(gaps) >= 2 and even and abs(mean(gaps) - want) < 0.15 * want)
g1, w1 = periods["0.0255"]; g2, w2 = periods["0.12"]
check("and the longer Persistence breathes the more slowly: %.2f s against %.2f" % (mean(g1), mean(g2)), mean(g1) > 1.5 * mean(g2))
null("the quicker Persistence's breath is not at the slower one's period", abs(mean(g2) - w1) > 0.15 * w1)
off_rows = [s for s in render(*HELD, responds("level", 75))["stage"] if s["t"] >= 4]
offp = peaks([s["A"]["glow"] for s in off_rows], [s["t"] for s in off_rows])
null("Swell off breathes not at all: %d peaks" % len(offp), len(offp) < 2)

# --- Level and Both -------------------------------------------------------------------
lvl = render(*SEQUENCE, responds("level", 75))
first, last = mean(reads(lvl, "B", "glow", 4.5, 5.5)), mean(reads(lvl, "B", "glow", 8, 9))
check("Level: the fast run holds the right hand's push up while it lasts, %.2f over its last second against %.2f over its first"
      % (last, first), first > 0.6 and last >= 0.9 * first)
cfirst, clast = mean(reads(seq75, "B", "glow", 4.5, 5.5)), mean(reads(seq75, "B", "glow", 8, 9))
null("Change settles while it is kept up: %.2f against %.2f" % (clast, cfirst), not (clast >= 0.9 * cfirst))

def base_and_flare(a):
    settled = mean(reads(a, "A", "glow", 16, 19))
    flare = max(reads(a, "A", "glow", 0.5, 4))
    return settled, flare - settled
both = render(*HELD, responds("both", 75))
bs, bf = base_and_flare(both)
check("Both: a held chord keeps a base under it (%.2f) and its strike flares above it (by %.2f)" % (bs, bf), bs >= 0.25 and bf >= 0.2)
cs, cf = base_and_flare(render(*HELD, responds("change", 75)))
ls, lf = base_and_flare(render(*HELD, responds("level", 75)))
null("Change has no base (%.2f)" % cs, not (cs >= 0.25))
null("Level has no flare (%.2f)" % lf, not (lf >= 0.2))

# --- Motion, the echo's read ----------------------------------------------------------
softm = max(reads(fr75, "B", "motion", 6.5, 16.5))
fastm = max(reads(seq75, "B", "motion", 4, 9))
check("Motion, on a fixed scale: the soft notes on a dark screen move it %.2f at most (today's read went to its top, 0.86 to 1.00, "
      "on every one), the fast run %.2f" % (softm, fastm), softm < 0.2 and fastm > 0.5)
null("the fast run, read the same way, is not small (%.2f)" % fastm, not (fastm < 0.2))

print("\n%d failed" % len(fails) if fails else "\nall passed")
sys.exit(1 if fails else 0)
