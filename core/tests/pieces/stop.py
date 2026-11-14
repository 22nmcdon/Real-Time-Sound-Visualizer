"""Stop holds the picture the instrument reads (stage 5, step 5a).

The owner's decision (STAGE5-PLAN.md, "Step 5 decided"): on the site, Stop
freezes the picture the instrument reads, so Scan plays a held picture and
what is seen is what is heard; notes still sound, and only the timbre stops
moving until Run. Until 5a the page's Stop held the face's screen and told the
instrument nothing, and a scanned fifth's timbre went on wandering under a
stopped screen (step 3, batch 3: 0.0084 held against 0.0079 running, where
the page's own brain held at 0.0001 to 0.0002). The page tells the
instrument by the `scopeRunning` control, which this renders, as the site's
setRunning sends it.

Read here as Scan's playing table: how far it moved, on average, between
readings a quarter of a second apart - from six seconds, four after the
stop, so the path's last glide onto the still figure is over (scantest's
reason for judging from 6 s). The null is the same run with no Stop.
"""
import base64, json

import numpy as np


def code(setup):
    return base64.b64encode(json.dumps(setup).encode()).decode().rstrip("=")


# A fifth of the Harmonic tone, just, in X-Y, Scan at its top: its figure
# turns, and Scan's table with it. The Picture amount at nought, so what moves
# the sound is Scan alone.
FIFTH = {"v": 11, "display": "xy", "midiMode": "mono", "shape": "harmonic", "interval": 7, "just": True, "freq": 220,
         "amp": 100, "oscScan": 100, "pictureAmount": 0, "persistence": "0.04"}


def run_of(kit, stop_at=None, run_at=None, more=None, seconds=10.0, strike=False):
    setup = dict(FIFTH, **({"scanStrike": 100} if strike else {}))
    lines = [["make", 48000, code(setup)], ["midi", 0x90, 57, 100], ["every", 0.25, "table", "heard", "gridstat", "sources"]]
    times = sorted([(t, op) for t, op in ((stop_at, "0"), (run_at, "1")) if t is not None] + [(t, m) for t, m in (more or [])],
                   key=lambda e: e[0])
    for t, op in times:
        lines.append(["to", t])
        lines.append(["control", "scopeRunning", op] if isinstance(op, str) else ["midi"] + op)
    lines.append(["to", seconds])
    rows = kit.render(lines)
    moved, last = [], None
    for r in rows:
        t = r.get("tableA")
        if t and last: moved.append((r["t"], float(np.mean(np.abs(np.array(t) - np.array(last))))))
        last = t
    return {"moved": moved, "rms": [(r["t"], float(r["heard"][2])) for r in rows],
            "grid": [(r["t"], float(r["gridstat"][1])) for r in rows],
            # The picture's raw Direction (signed area), which reads the frame held, not the grid.
            "signed": [(r["t"], float(r["sources"][6])) for r in rows]}


def mean_from(series, t0, t1=99.0):
    xs = [v for t, v in series if t0 <= t < t1]
    return float(np.mean(xs)) if xs else float("nan")


def run(kit):
    check, null = kit.check, kit.null
    running, stopped = run_of(kit), run_of(kit, stop_at=2.0)
    before, held, free = mean_from(stopped["moved"], 0, 2), mean_from(stopped["moved"], 6), mean_from(running["moved"], 6)
    print("    Scan's table, moved a quarter-second: before the stop %.5f; stopped, from 6 s %.5f; the same run never stopped %.5f"
          % (before, held, free))
    check("stopped, the scanned fifth's timbre holds still: Scan's table moves under a thousandth of what it moves running",
          held < free / 1000 and held < 1e-3, "%.6f against %.4f" % (held, free))
    null("the same run never stopped goes on moving", free > 0.01, "%.4f" % free)
    check("and the notes still sound under Stop: the heard pair from 6 s is the running run's, to a fifth",
          mean_from(stopped["rms"], 6) > 0.8 * mean_from(running["rms"], 6) > 0.05,
          "%.3f against %.3f" % (mean_from(stopped["rms"], 6), mean_from(running["rms"], 6)))
    gs = [v for t, v in stopped["grid"] if t >= 2.3]
    check("and the grid Scan reads stands: its sum the same at every reading after the stop", max(gs) - min(gs) == 0,
          "%.6g to %.6g" % (min(gs), max(gs)))
    gr = [v for t, v in running["grid"] if t >= 2.3]
    null("running, the grid's sum moves", max(gr) - min(gr) > 0, "%.6g to %.6g" % (min(gr), max(gr)))
    # And the frame the reads take their shape from is held too, as the
    # page keeps state.held: Direction, which reads the frame and not the
    # grid, stands.
    sg = [v for t, v in stopped["signed"] if t >= 2.3]
    check("and the frame held: Direction, read off the frame rather than the grid, stands", max(sg) - min(sg) == 0,
          "%.6g to %.6g" % (min(sg), max(sg)))
    sr = [v for t, v in running["signed"] if t >= 2.3]
    null("running, Direction moves", max(sr) - min(sr) > 0, "%.6g to %.6g" % (min(sr), max(sr)))
    # Run again: it moves again, and the grid with it.
    again = run_of(kit, stop_at=2.0, run_at=6.0, seconds=12.0)
    resumed = mean_from(again["moved"], 9)
    check("and Run lets it go: moving again from three seconds after", resumed > 0.01, "%.4f" % resumed)
    # A note struck under Stop lays nothing into the held picture (P7b's
    # strike), and the same note struck running does.
    note = [(7.0, [0x90, 69, 127])]
    s_held = run_of(kit, stop_at=2.0, more=note, seconds=8.0, strike=True)
    s_free = run_of(kit, more=note, seconds=8.0, strike=True)
    jump = lambda r: dict(r["grid"]).get(7.25, 0) - dict(r["grid"]).get(7.0, 0)
    check("a note struck under Stop lays no light into the held picture", jump(s_held) == 0, "%.4g" % jump(s_held))
    # Running, against the same run with no note: the strike is what moved it, not the figure's own turning.
    s_none = run_of(kit, seconds=8.0, strike=True)
    null("and struck running it does: the grid's quarter-second after the note is not the one without it",
         jump(s_free) != jump(s_none), "%.4g with the note, %.4g without" % (jump(s_free), jump(s_none)))
