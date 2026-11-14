"""The limiter's lookahead, on the core: an impulse through the instrument
comes out of the limiter six milliseconds after it went in, at every rate -
a time, not a block of frames - which is the six the site's latency figure
adds (`MONITOR_LOOKAHEAD_MS`); and below its threshold the limiter adds its
make-up gain and nothing else.

These were ratetest.py's and rotatetest.py's until stage 5's step 6, measured
on the page's own monitor chain, whose DynamicsCompressor was the limiter
the page's brain was heard through. The instrument has had its own since 5a
(scope/limiter.h), the page's chain has none now, and the figure the panel
quotes is the instrument's. So here render_cpp plays an impulse in as a
microphone and records the heard pair before the limiter and after it, in
the same run; the delay is the first sample over a floor in each, which a
periodic signal could not give (a sine correlates with itself a period on).
"""
import base64, json, os, re

import numpy as np

from pieces.kit import BUILD

RATES = [22050, 44100, 48000, 96000]
HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "..", "..", "..", "web", "scope.html")


def code():
    return base64.b64encode(json.dumps({"v": 11, "pictureAmount": 0}).encode()).decode().rstrip("=")


def through(kit, rate, amp=0.25):
    """An impulse of `amp` in both channels a tenth of a second in: the
    first sample over a floor before the limiter and after it, and the
    heard peak over the pre-limit one."""
    os.makedirs(BUILD, exist_ok=True)
    feed = os.path.join(BUILD, "lookahead-%d.f32" % rate)
    pre, post = feed + ".pre", feed + ".post"
    x = np.zeros((int(rate * 0.3), 2), "<f4")
    x[int(rate * 0.1)] = amp
    x.tofile(feed)
    kit.render([["make", rate, code()], ["click", "srcMic"], ["input", "file", feed, 2],
                ["record", "prelimit", pre], ["record", "heard", post], ["to", 0.25]])
    a = np.fromfile(pre, "<f4").reshape(-1, 2)[:, 0].astype(float)
    b = np.fromfile(post, "<f4").reshape(-1, 2)[:, 0].astype(float)
    first = lambda s: int(np.argmax(np.abs(s) > 1e-4)) if np.any(np.abs(s) > 1e-4) else None
    return first(a), first(b), float(np.max(np.abs(b)) / max(np.max(np.abs(a)), 1e-30))


def run(kit):
    check, null = kit.check, kit.null
    quoted = float(re.search(r"const MONITOR_LOOKAHEAD_MS = ([\d.]+);", open(PAGE, encoding="utf-8").read()).group(1))
    runs = {rate: through(kit, rate) for rate in RATES}
    late = {rate: (b - a if a is not None and b is not None else None) for rate, (a, b, _) in runs.items()}
    ms = {rate: (d / rate * 1000 if d is not None else float("nan")) for rate, d in late.items()}
    for rate in RATES:
        print("    %5d Hz: in at %s, out at %s, %s samples late, %.3f ms, peak x%.4f"
              % (rate, runs[rate][0], runs[rate][1], late[rate], ms[rate], runs[rate][2]))
    check("an impulse reaches the limiter's input at all, at every rate",
          all(a is not None and b is not None for a, b, _ in runs.values()), str(runs))
    as_ms = lambda lates: [d / r * 1000 for r, d in zip(RATES, lates)]
    a_time = lambda lates: max(as_ms(lates)) - min(as_ms(lates)) < 0.05 and len(set(lates)) == len(RATES)
    the_quote = lambda lates: all(abs(m - quoted) < 0.05 for m in as_ms(lates))
    made_up = lambda gains: all(1.0 < g < 10 ** (2 / 20) for g in gains)
    lates = [late[r] for r in RATES]
    check("the limiter's lookahead is a time, not a block of frames: one millisecond figure in four sample counts",
          a_time(lates), "%s samples" % lates)
    check("so the %g ms the site's latency figure adds is right at every rate" % quoted,
          the_quote(lates), "%s ms" % ["%.3f" % m for m in as_ms(lates)])
    # The nulls, through the same two readings: a block of 288 frames at
    # every rate (6 ms at 48 kHz only) is not one time and not the figure;
    # and nought, the page's own chain as it is now, is not the figure.
    null("288 frames at every rate reads as no one time", not a_time([288] * 4) and not the_quote([288] * 4))
    null("a chain that delays nothing reads as not the quoted figure", not the_quote([0] * 4))
    # Under its threshold the limiter is its make-up gain: a quarter of full
    # scale comes out a little louder, never quieter, by under two decibels.
    gains = [runs[r][2] for r in RATES]
    check("a quarter of full scale comes through the limiter at its make-up gain: louder, by under 2 dB",
          made_up(gains), "x%s" % ["%.4f" % g for g in gains])
    null("the pre-limit pair against itself, unity, reads as no make-up gain", not made_up([1.0] * 4))
