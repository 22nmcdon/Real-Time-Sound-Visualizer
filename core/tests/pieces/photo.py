"""The photocell's reach ceiling, on the core: phototest.py's :338 and :343;
and since batch 6 the rest of its numbers rows - the grid's fade, its two
ends and its compositing (:177, :199, :201, :218), the photocell's reading,
its smoothness and its slew (:245, :246, :247, :283, :286), and the loop it
closes held inside its ranges (:371).

These were phototest.py's on its `?brain=js` leg until stage 5, step 3, batch
3 (13 Nov): `photo.value` forced to one by hand, a routing's amount written
past the ceiling round every setter, and the page's `applyModMatrix` read
back. Here the core's matrix (matrix_cpp): the photocell a scripted source
held at one, marked as the picture's, with the core's own reach
(`reach=photo`, kPhotoReach), on stand-in destinations of screen.h's spans.
Its neighbour, "and stored back within it, so the control says what
applies", is the face's and stays in the suite. Each check has its null.

Batch 6 (14 Nov): those rows read the page's grid with genSet and
state.persistence set by hand, photo.value with movePhoto, and the page's
visual matrix for four seconds of real frames. On the site the grid the
face draws and the photocell's card reads is the face's (the second grid
STAGE5-INVENTORY.md section 1 found); what the instrument hears is its own.
So here the core's Phosphor and PictureSources directly (picture_cpp: a
segment laid, a fade, a read, the photocell stepped by its frame time), and
for the photocell on a played figure and the loop, the instrument rendered
offline (render_cpp), the reticle put on the figure's brightest cell as the
page's drag sends it (`photoReticle`).
"""
import base64, json, math, os

import numpy as np

from pieces.kit import BUILD
from pieces.loop import matrix, sources

N = 64           # kPhosphorN
PLOT = "plot 0 0 640 640"   # ten pixels a cell


def pic(kit, commands):
    """picture_cpp on one run: each command's line, as its words."""
    return [l.split() for l in kit.run("picture_cpp", "run\n%s\nend\n" % "\n".join(commands)).strip().split("\n")]


def after(words, key, n=1):
    """The `n` numbers after `key` in a line - its last mention, not the command's own name."""
    i = len(words) - 1 - words[::-1].index(key)
    return [float(w) for w in words[i + 1:i + 1 + n]]


def centre(cx, cy):
    """A cell's centre, as u and v, and as a pixel of PLOT."""
    return (cx + 0.5) / N, (cy + 0.5) / N, (cx + 0.5) * 10, (cy + 0.5) * 10


def lit_cell(kit, cx, cy, level=1.0):
    """A segment one pixel long inside one cell, at `level`."""
    _, _, x, y = centre(cx, cy)
    return "seg %r %r %r %r %r" % (x - 0.5, y, x + 0.5, y, level)


def code(setup):
    return base64.b64encode(json.dumps(dict({"v": 11, "pictureAmount": 0, "midiMode": "mono", "shape": "sine",
                                              "interval": 7, "display": "xy", "timebase": 3}, **setup)).encode()).decode().rstrip("=")


def run(kit):
    check, null = kit.check, kit.null
    run_batch6(kit)
    # The photocell at a half, not one: at one its push and the loop's total
    # are both a half, and a ceiling of three quarters would read the same
    # through the total (batch 3's mutation pass). The page read the ratio
    # of the offset to the value, as here.
    view = ["visual view.rotate 1 -2 2 0", "visual filter.res 50 0 100 20"]
    f = matrix(kit, sources(["photo.1"], 0.5) + view + ["route photo.1 view.rotate 1", "frame"])[0][0]
    check("an amount past the ceiling is held to it where it is used", abs(f["view.rotate"] / 0.5 - 0.5) < 1e-9,
          "applied %.4f of the value, of rotation's span" % (f["view.rotate"] / 0.5))
    o = matrix(kit, sources(["test.one"], 0.5, "1", "") + view + ["route test.one view.rotate 1", "frame"])[0][0]
    null("a source that is not the picture's is not held to it", abs(o["view.rotate"] / 0.5 - 0.5) > 0.1, "%.4f" % (o["view.rotate"] / 0.5))
    # A setup code carrying a routing past the ceiling, to the resonance.
    r = matrix(kit, sources(["photo.1"], 0.5) + view + ["load photo.1>filter.res@0.9", "frame"])[0][0]
    check("a routing that arrives in a code past the ceiling moves its destination no further than the ceiling",
          0 < r["filter.res"] <= 0.5 * 0.5 * 50 + 1e-9, str(r["filter.res"]))
    r2 = matrix(kit, sources(["test.one"], 0.5, "1", "") + view + ["load test.one>filter.res@0.9", "frame"])[0][0]
    null("the same code from a source that is not the picture's goes past it", r2["filter.res"] > 0.5 * 0.5 * 50, str(r2["filter.res"]))


def played(kit, setup, reticle=None, seconds=5.0, every=0.05):
    """The instrument playing A3 in Mono, held, with `setup`: the brightest
    cell at a second, and then the readings every `every` to `seconds` with
    the reticle put on that cell (or at `reticle`) at a second."""
    os.makedirs(BUILD, exist_ok=True)
    path = os.path.join(BUILD, "photo-grid.f32")
    head = [["make", 48000, code(setup)], ["midi", 0x90, 57, 127], ["record", "grid", path], ["to", 1.0], ["read", "griddump"]]
    kit.render(head)
    g = np.fromfile(path, "<f4")[-N * N:].reshape(N, N)
    cy, cx = np.unravel_index(int(np.argmax(g)), g.shape)
    # Plain floats: numpy's repr would hand the control "np.float64(...)", which reads as no number.
    u, v = reticle or (float((cx + 0.5) / N), float((cy + 0.5) / N))
    rows = kit.render(head[:2] + [["to", 1.0], ["control", "photoReticle", "%r,%r" % (u, v)],
                                  ["every", every, "loop", "sources", "gridstat"], ["to", seconds]])
    return (u, v), rows


def run_batch6(kit):
    check, null = kit.check, kit.null

    # --- the grid fades by one minus the persistence a frame ---
    at = lambda w: after(w, "read")[0]
    u, v, _, _ = centre(30, 30)
    def fade_rate(persist, frames=10):
        w = pic(kit, [PLOT, "persist %r" % persist, lit_cell(kit, 30, 30), "read %r %r" % (u, v)]
                + ["fade 0"] * frames + ["read %r %r" % (u, v)])
        reads = [at(x) for x in w if x[0] == "read"]
        return (reads[1] / reads[0]) ** (1 / frames)
    r = fade_rate(0.12)
    check("the grid fades by one minus the persistence every frame", abs(r - 0.88) < 1e-6, "%.7f" % r)
    null("at a persistence of 0.2 it is not 0.88", abs(fade_rate(0.2) - 0.88) > 0.05, "%.4f" % fade_rate(0.2))

    # --- the two ends ---
    sums = lambda w: after(w, "grid", 2)
    w = pic(kit, [PLOT, "persist -1", lit_cell(kit, 20, 20), lit_cell(kit, 40, 44)] + ["fade 0"] * 20)
    kept = sums(w[-1])[1] / sums(w[3])[1]
    check("infinite persistence keeps everything, as the screen does", kept == 1.0, "%.6f of it left" % kept)
    w = pic(kit, [PLOT, "persist 0.01", lit_cell(kit, 20, 20)] + ["fade 0"] * 20)
    null("a persistence of a hundredth keeps less over twenty frames", sums(w[-1])[1] / sums(w[2])[1] < 0.99)
    ua, va, _, _ = centre(20, 20)
    ub, vb, _, _ = centre(40, 44)
    def off(persist):
        w = pic(kit, [PLOT, "persist %r" % persist, lit_cell(kit, 20, 20), "fade 0", lit_cell(kit, 40, 44),
                      "read %r %r" % (ua, va), "read %r %r" % (ub, vb)])
        return [at(x) for x in w if x[0] == "read"]
    gone, kept12 = off(0), off(0.12)
    check("and with persistence off nothing is kept but what was just drawn", gone[0] == 0 and gone[1] > 0.3, str(gone))
    null("at 0.12 the stroke before is still there", kept12[0] > 0.3, str(kept12))

    # --- a cell keeps the brighter of two strokes, never their sum ---
    # The dim stroke laid twice, and a dimmer after it, against one stroke.
    once = sums(pic(kit, [PLOT, lit_cell(kit, 32, 32, 0.375)])[-1])
    thrice = sums(pic(kit, [PLOT, lit_cell(kit, 32, 32, 0.375), lit_cell(kit, 32, 32, 0.375), lit_cell(kit, 32, 32, 0.25)])[-1])
    summed = sums(pic(kit, [PLOT, lit_cell(kit, 32, 32, 1.0)])[-1])
    check("a cell keeps the brighter of two strokes, never their sum", thrice == once and abs(math.sqrt(once[1]) - 0.375) < 1e-7,
          "%s against one stroke's %s" % (thrice, once))
    null("their sum, one at a full 1.0, reads otherwise", summed != thrice, str(summed))

    # --- the reading: bright on a stroke, dark off it, and smooth ---
    # A vertical stroke down column 40, at full; walked across in tenths of a cell.
    line = ["seg 405 0 405 640 1"]
    def walk(step):
        cmds = [PLOT] + line + ["read %r 0.5" % ((40.5 + k * step) / N) for k in range(int(-3 / step), int(3 / step) + 1)]
        return [at(x) for x in pic(kit, cmds) if x[0] == "read"]
    tenths = walk(0.1)
    worst = max(abs(b - a) for a, b in zip(tenths, tenths[1:]))
    check("on the figure it reads bright", max(tenths) > 0.5, "%.3f" % max(tenths))
    check("and off it, dark", min(tenths) < 0.02, "%.3f" % min(tenths))
    check("the reading moves smoothly as the reticle does - no jump at a cell edge", worst < 0.1, "%.3f" % worst)
    halves = walk(0.5)
    null("in half-cell steps the same rule goes red, so 0.1 is a bound the walk can break",
         max(abs(b - a) for a, b in zip(halves, halves[1:])) > 0.1)

    # --- the slew ---
    # Off the stroke for a second, then on it, stepped at 60 frames a second.
    frame = 1000 / 60
    cmds = [PLOT] + line + ["photo 1 0.2 0.5"] + ["step %r" % frame] * 60 + ["photo 1 %r 0.5" % (40.5 / N)] + ["step %r" % frame] * 48
    out = [x for x in pic(kit, cmds) if x[0] == "step"][60:]
    trace = [((k + 1) * frame, after(x, "photo", 2)) for k, x in enumerate(out)]
    over = max(sl - 2 * t / 1000 for t, (raw, sl) in trace)
    half = next((t for t, (raw, sl) in trace if sl >= 0.35), None)
    raw_end, sl_end = trace[-1][1]
    print("    stepped from dark to bright: halfway after %s ms, reached %.3f of %.3f, over the envelope by %.4f"
          % (half and round(half), sl_end, raw_end, over))
    check("it never moves faster than two full swings a second", over <= 1e-9 and half is not None and half >= 150,
          "over by %.4f, halfway at %s ms" % (over, half))
    check("and still gets there", abs(sl_end - raw_end) < 0.05 and raw_end > 0.5, "%.3f of %.3f" % (sl_end, raw_end))
    raw_over = max(raw - 2 * t / 1000 for t, (raw, sl) in trace)
    null("the raw reading, unslewed, breaks the same envelope", raw_over > 0.1, "%.3f" % raw_over)

    # --- a loop that cannot run away ---
    # Four seconds with the photocell on the instrument's own figure, routed
    # at its ceiling to the rotation and the zoom, persistence infinite: every
    # offset inside the ceiling's range, the reading and the grid inside
    # theirs, nothing not finite. The null: an oscillator at full depth on the
    # rotation, which is not held to the ceiling, goes past the same bound.
    # Routed at full in the code, past the ceiling, so the ceiling is what holds them.
    loop = {"persistence": -1, "photoOn": True, "mod": "photo.1>view.rotate@1.000;photo.1>view.zoom@1.000"}
    (ru, rv), rows = played(kit, loop)
    rot = max(abs(float(r["loop"][2])) for r in rows)
    zoom = max(abs(float(r["loop"][3])) for r in rows)
    value = max(float(r["sources"][1]) for r in rows)
    grid = max(float(r["gridstat"][0]) for r in rows)
    bad = sum(int(r["gridstat"][2]) for r in rows) + sum(1 for r in rows for w in r["loop"][1:] + r["sources"] if not math.isfinite(float(w)))
    print("    four seconds at the ceiling on rotation and zoom, the reticle on %.3f,%.3f: rotation %.3f, zoom %.3f, photocell %.3f, grid %.3f, %d not finite"
          % (ru, rv, rot, zoom, value, grid, bad))
    check("on the instrument's own figure the photocell reads it", value > 0.3, "%.3f" % value)
    check("everything stays inside its range and nothing goes NaN", bad == 0 and rot <= 0.5 + 1e-9 and zoom <= 0.5 * 8 + 1e-9
          and value <= 1 and grid <= 1 and len(rows) >= 79, "rotation %.3f, zoom %.3f, %d rows" % (rot, zoom, len(rows)))
    # And row by row no further than the ceiling takes the photocell's own
    # value: the bound above holds by a margin with the reading at a half,
    # so a reach of 0.9 passed it (the mutation pass); this does not.
    over = max(abs(float(r["loop"][2])) - 0.5 * float(r["sources"][1]) for r in rows)
    check("each frame's rotation is at most half the photocell's value, the ceiling's", over <= 1e-9, "%.2e over" % over)
    _, wild = played(kit, {"persistence": -1, "mod": "lfo1>view.rotate@1.000", "l0r": 100}, reticle=(0.5, 0.5), seconds=3.0)
    wrot = max(abs(float(r["loop"][2])) for r in wild)
    null("an oscillator at full depth on the rotation goes past the same bound", wrot > 0.5 + 1e-9, "%.3f" % wrot)
    wover = max(abs(float(r["loop"][2])) - 0.5 * float(r["sources"][1]) for r in wild)
    null("and past half the photocell's value, which it does not answer to", wover > 0.1, "%.3f over" % wover)
