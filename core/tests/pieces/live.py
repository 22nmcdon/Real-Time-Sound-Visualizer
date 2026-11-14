"""The band split, on the core: which band each frequency lands in, the
crossovers' corners, a broadband input in all four bands, and the mixer's
gains on what is heard - livetest.py's numbers rows (:196, :197, :408, :409,
:433) and the half of its mute row (:171) that is the instrument's.

These were livetest.py's on `?brain=js` until stage 5, step 3, batch 6 (14
Nov). There the probes and the corners were BiquadFilterNodes built afresh
from the page's BANDS constants in an OfflineAudioContext, which read
nothing the running page did; the bands' signal was the page's own analysers
on the fake microphone; and the mute moved the page's own lane gain nodes.
On the site the instrument does the split (`srcBands`, scope/instrument.h's
bandStep: a Butterworth highpass then lowpass per band, at kButterworthQDb),
and its mixer's gains arrive as `laneMix`. So here render_cpp draws an input
split through the instrument itself: probe sines in both channels at 0.5,
the band lanes read off the ring (lanes 0 to 3, each band of the two channels
averaged), and the heard pair, which is the bands summed at the mixer's gains.
Each check has its null.
"""
import base64, json, math, os

import numpy as np

from pieces.kit import BUILD

RATE = 48000
NAMES = ["Low", "Low mid", "High mid", "High"]
CORNERS = [("Low", "lowpass", 120), ("Low mid", "highpass", 120), ("Low mid", "lowpass", 800),
           ("High mid", "highpass", 800), ("High mid", "lowpass", 4000), ("High", "highpass", 4000)]


def code():
    return base64.b64encode(json.dumps({"v": 11, "pictureAmount": 0}).encode()).decode().rstrip("=")


def split(kit, inputs, mix=None, seconds=1.0, tag="probe"):
    """The input split by the instrument for `seconds`: its last half second's
    four band lanes (rows) and the heard pair's left. `inputs` is a render_cpp
    input command."""
    os.makedirs(BUILD, exist_ok=True)
    lanes, heard = os.path.join(BUILD, "live-%s-lanes.f32" % tag), os.path.join(BUILD, "live-%s-heard.f32" % tag)
    lines = [["make", RATE, code()], ["click", "srcMic"], ["control", "srcBands", "1"], inputs]
    if mix: lines.append(["control", "laneMix", mix])
    lines += [["record", "lanes", lanes], ["record", "heard", heard], ["to", seconds]]
    kit.render(lines)
    half = RATE // 2
    d = np.fromfile(lanes, "<f4").reshape(-1, 6)[-half:]
    h = np.fromfile(heard, "<f4").reshape(-1, 2)[-half:]
    return d[:, :4].T.astype(float), h[:, 0].astype(float)


def rms(x):
    return float(np.sqrt(np.mean(np.square(x))))


def db(x, ref):
    return 20 * math.log10(max(rms(x), 1e-15) / ref)


def run(kit):
    check, null = kit.check, kit.null
    ref = 0.5 / math.sqrt(2)   # the probe's own RMS

    # --- each probe in the band that owns it ---
    probes = [40, 300, 2000, 9000]
    table = []
    for hz in probes:
        bands, _ = split(kit, ["input", "sine", hz, 0.5, hz, 0.5])
        table.append([db(b, ref) for b in bands])
    print("                 " + "  ".join("%7s" % ("%d Hz" % hz) for hz in probes))
    for j, name in enumerate(NAMES):
        print("    %-9s %s" % (name, "  ".join("%7.1f" % table[i][j] for i in range(4))))
    owns = lambda t: [(NAMES[i], NAMES[j]) for i in range(4) for j in range(4) if j != i and t[i][j] > t[i][i] - 0.01]
    wrong = owns(table)
    check("each probe is loudest in the band that owns it", wrong == [], str(wrong[:3]))
    swapped = [list(reversed(row)) for row in table]
    null("the lanes read in the opposite order fail the same rule", owns(swapped) != [], str(owns(swapped)[:2]))
    check("and at least 20 dB down two bands away", table[0][3] < -20 and table[3][0] < -20,
          "High at 40 Hz %.1f dB, Low at 9 kHz %.1f dB" % (table[0][3], table[3][0]))
    null("while each owner passes its probe within a decibel", all(abs(table[i][i]) < 1 for i in range(4)),
         str([round(table[i][i], 2) for i in range(4)]))

    # --- the crossovers ---
    # Read at each band's corner through both its stages; the other stage is
    # five to seven times away, where a Butterworth takes off under 0.01 dB.
    corners = []
    for name, kind, hz in CORNERS:
        bands, _ = split(kit, ["input", "sine", hz, 0.5, hz, 0.5])
        corners.append(db(bands[NAMES.index(name)], ref))
        print("    %-9s %-9s at %5d Hz  %+.3f dB" % (name, kind, hz, corners[-1]))
    worst = max(corners, key=lambda v: abs(v + 3.0103))
    check("every crossover is -3.01 dB at its corner", all(abs(v + 3.0103) < 0.05 for v in corners), "worst %+.3f dB" % worst)
    off, _ = split(kit, ["input", "sine", 132, 0.5, 132, 0.5])
    near = db(off[0], ref)
    null("a tenth past the corner the Low band is no longer at -3.01", abs(near + 3.0103) > 0.05, "%+.3f dB at 132 Hz" % near)

    # --- a broadband input reaches every band, differently ---
    # instrument_cpp's saw feed, the same in both channels: a pulse-like,
    # broadband input, as the browser's fake microphone is.
    bands, _ = split(kit, ["input", "saw", 109, 109], tag="saw")
    levels = [rms(b) for b in bands]
    print("    a saw a band: %s" % ", ".join("%s %.4f" % (n, v) for n, v in zip(NAMES, levels)))
    check("audio arrives at every band", all(v > 1e-3 for v in levels), str([round(v, 4) for v in levels]))
    check("and the bands are not all the same signal", max(levels) > 2 * min(levels) and
          min(float(np.max(np.abs(bands[i] - bands[j]))) for i in range(4) for j in range(i)) > 1e-3,
          "loudest %.4f, quietest %.4f" % (max(levels), min(levels)))
    quiet, _ = split(kit, ["input", "none"], tag="none")
    null("with no input nothing arrives", all(rms(b) < 1e-9 for b in quiet), str([rms(b) for b in quiet]))

    # --- the mixer's gains, on what is heard ---
    # The heard pair is the four bands summed at the gains, sample for sample
    # (both channels carry the same probe, so a band's lane is its left).
    lanes1, whole = split(kit, ["input", "sine", 40, 0.5, 40, 0.5], tag="mix1")
    lanes0, muted = split(kit, ["input", "sine", 40, 0.5, 40, 0.5], mix="0,1,1,1", tag="mix0")
    gap = lambda heard, lanes, g: float(np.max(np.abs(heard - sum(gi * l for gi, l in zip(g, lanes)))))
    print("    a 40 Hz probe heard: every band %.1f dB, the Low band muted %.1f dB; against the bands summed at the gains %.1e, %.1e"
          % (db(whole, ref), db(muted, ref), gap(whole, lanes1, [1, 1, 1, 1]), gap(muted, lanes0, [0, 1, 1, 1])))
    check("the mixer's gains are what is heard: the bands summed at them, sample for sample, the muted Low band taking the probe 15 dB down",
          gap(whole, lanes1, [1, 1, 1, 1]) < 1e-5 and gap(muted, lanes0, [0, 1, 1, 1]) < 1e-5 and db(muted, ref) < db(whole, ref) - 15,
          "%.1f against %.1f dB" % (db(muted, ref), db(whole, ref)))
    null("the muted run is not the bands summed at one each", gap(muted, lanes0, [1, 1, 1, 1]) > 0.1, "%.3f" % gap(muted, lanes0, [1, 1, 1, 1]))
