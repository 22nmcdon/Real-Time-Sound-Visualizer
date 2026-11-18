"""Painting, step 1 (core/include/scope/paint.h): the brushwork, the paint map,
its drying, the layout and the reads, each by its own numbers through
core/tests/tools/paint_cpp.cpp, and each check with its null.

What is held, in the order the paint goes: a note paints at the radius the
round layout gives its pitch; thin paint dries faster than thick; a brush
carries wet paint it crosses on to where it goes next (the pick-up the
study's graphics-card test cut); each note reads the ring at its own pitch
and plays a table of its own; wet paint reads stronger than dry; the
Picture amount's three reads come off the map (Glow wet coverage, Motion
paint being laid, Memory new paint on old) and through the stage as the
trace's do; a second layout moves only where the paint lands; the same
performance paints the same map to the bit; and what it costs.

Nothing here touches the trace: with painting off nothing in paint.h runs,
which core_tests.py's recordings hold to the bit.
"""
import math


def run(kit):
    check, null = kit.check, kit.null

    def nums(*args):
        # paint_cpp takes its command and numbers; the scenario file kit.run adds after them is not read.
        return [float(v) for v in kit.run("paint_cpp", "", *args).split()]

    # --- where a note paints ---
    got, layout_says, octave = nums("radius")
    # The owner's layout (18 Nov), written here rather than read from the core: A0 a third of the
    # way out to the outermost radius (0.47 of the canvas), C8 at it, log frequency between.
    def radius(note):
        u = math.log2(440 * 2 ** ((note - 69) / 12) / 27.5) / math.log2(4186.009044809578 / 27.5)
        return 0.47 * (1 / 3 + 2 / 3 * min(1, max(0, u))) * 128
    want = radius(57)
    check("the round layout puts A3 where the owner's record does: A0 a third out, C8 at the edge", abs(layout_says - want) < 1e-3,
          "%.3f cells, by hand %.3f" % (layout_says, want))
    null("a layout with no hole puts it elsewhere", abs(0.47 * (radius(57) / (0.47 * 128) - 1 / 3) * 1.5 * 128 - want) > 5)
    check("a held note paints at its own pitch's radius on the round layout", abs(got - want) < 0.6,
          "thickness-weighted radius %.2f cells, the layout's %.2f" % (got, want))
    null("the same paint against the radius an octave up", abs(got - octave) > 3, "%.2f against %.2f" % (got, octave))

    # --- drying, thin faster than thick ---
    thin_a, thick_a, thin2, thick2, thin6, thick6 = nums("dry", "2", "6")
    check("a thick stroke is a tenth wet after the thick drying time (6 s)", 0.07 < thick6 < 0.13,
          "thickness %.2f: %.3f wet at 6 s" % (thick_a, thick6))
    # The thin dab's expected wetness from its own thickness, by the smooth rule.
    x = min(1, thin_a); want_thin = 10 ** (-2 / (2 + 4 * x * x * (3 - 2 * x)))
    check("a thin dab dries by its own thickness's time", abs(thin2 - want_thin) < 0.03,
          "thickness %.2f: %.3f wet at 2 s, the rule %.3f" % (thin_a, thin2, want_thin))
    check("thin paint dries faster than thick: at 2 s the thick is over twice as wet", thick2 > 2 * thin2,
          "%.3f against %.3f" % (thick2, thin2))
    _, _, one_thin, one_thick, _, _ = nums("dry", "4", "4")
    null("one drying time for all: the thick no wetter than the thin", not (one_thick > 2 * one_thin),
         "%.3f against %.3f" % (one_thick, one_thin))

    # --- the pick-up ---
    wet, = nums("pickup", "0.2")
    dry, = nums("pickup", "20")
    check("an empty brush across a wet stroke carries its paint on past it", wet > 0.05, "%.3f laid past the crossing" % wet)
    null("across the same stroke dried, there is nothing to carry", dry < 1e-6, "%.3g" % dry)

    before, after = nums("own", "own")
    check("a brush does not drag its own fresh stroke: back over it a moment later, the map is unmoved", after == before,
          "%.4f, %.4f" % (before, after))
    _, other = nums("own", "other")
    null("another brush over the same stroke does move it", abs(other - before) > 0.1, "%.4f to %.4f" % (before, other))

    # --- the fade ---
    left, = nums("fade", "16")
    check("paint fades by its half-life: half of it left after 16 s", abs(left - 0.5) < 0.005, "%.4f" % left)
    null("a fade of 32 s leaves more", nums("fade", "32")[0] > 0.65)

    # --- what a painted voice plays ---
    heard, again = nums("heard")
    check("a painted voice plays its table: Scan at 60 sounds apart from Scan at nought", heard > 0.1,
          "%.3f of the sound's RMS apart" % heard)
    null("the same render twice is not apart at all, so the difference is the table's", again == 0, "%.3g" % again)

    # --- each note reads its own ring ---
    low, high, mid, _, _ = nums("rings")
    check("each note reads the ring at its own pitch: three dabs round one, five round another", low == 3 and high == 5,
          "strongest harmonics %d and %d" % (low, high))
    null("a shared circle between them holds neither note's paint", mid not in (3, 5), "strongest %d" % mid)
    voices, shared, apart, painting, own_err, other_err = nums("tables")
    check("in the instrument, two held notes play a table each, not one between them", voices == 2 and shared == 0,
          "%d tables, shared %d, harmonics apart %.3f" % (voices, shared, apart))
    check("and each voice's table is the one its own ring reads", own_err < 1e-9, "largest difference %.2g" % own_err)
    null("against the other note's ring it is not", other_err > 0.1, "%.3f" % other_err)
    off, _, _, painting_off, _, _ = nums("tables", "off")
    null("on the trace the same notes have no table of their own", painting == 1 and off == 0 and painting_off == 0,
         "%d tables" % off)

    # --- wet reads stronger than dry ---
    ratio, wet_now, dry_now, _ = nums("wet", "0.4")
    check("wet paint reads a little stronger than dry: 1.4 times, thickness for thickness", abs(ratio - 1.4) < 0.01,
          "%.3f (wet %.2f, dry %.3f)" % (ratio, wet_now, dry_now))
    flat, _, _, _ = nums("wet", "0")
    null("with no wet reading, wet and dry read the same", abs(flat - 1) < 1e-6 and abs(flat - 1.4) > 0.3, "%.3f" % flat)

    # --- the three reads ---
    fresh, dried, covered, laying, idle, bare, over, own = nums("reads")
    check("Glow reads wet coverage: fresh paint covers, the same paint dried does not", fresh > 0.01 and dried < 1e-4,
          "%.4f fresh, %.2g dried" % (fresh, dried))
    null("the paint is still there when dry, so it is the wetness the read follows", covered > 1e-3, "%.4f covered" % covered)
    check("Motion is paint being laid: full while laying, nothing once it stops", laying > 0.5 and idle == 0,
          "%.2f laying, %.2f after" % (laying, idle))
    check("Memory reads new paint on old: none on bare canvas, most over another's dried stroke", bare == 0 and over > 0.5,
          "%.2f bare, %.2f over" % (bare, over))
    check("a brush's own fresh stroke is not old paint to it", own == 0, "%.2f" % own)
    null("over another brush's paint the same strokes do count", over > 0.5 and over != own)
    glow_level, level, glow_change, motion, memory = nums("stage")
    check("the stage takes the paint's reads as the trace's: Level reads the cover on the same scale",
          abs(glow_level - level) < 1e-4, "%.4f against %.4f" % (glow_level, level))
    null("Change on the same steady cover reads nothing, so Responds to is heard", glow_change < 1e-3 and abs(glow_level - glow_change) > 0.3,
         "%.4f" % glow_change)
    check("Motion and Memory come through the stage's own Rise and Fall and gathering", abs(motion - 0.4) < 1e-3 and 0.4 < memory < 0.63,
          "Motion %.3f, Memory %.3f" % (motion, memory))

    # --- the layout is a piece of its own ---
    back, wrong, unturned, wet_back, glow, reads, tables, frames = nums("layout")
    check("a second layout (round turned a quarter) moves where the paint lands: the map turned back is the same",
          back < 0.03 and wet_back < 0.08, "%.3f of the paint differs (wet %.3f), from where stamps meet the cells" % (back, wet_back))
    null("the turned map turned back the wrong way is not", wrong > 1, "%.2f" % wrong)
    null("nor is it the same map unturned: the paint did move", unturned > 1, "%.2f" % unturned)
    check("and nothing the layout does not own moves: the reads and every note's table agree", glow < 0.005 and reads < 0.01 and tables < 0.01,
          "Glow %.4f, Motion and Memory %.4f, tables %.4f over %d frames" % (glow, reads, tables, frames))

    # --- deterministic ---
    same, same_other, apart = nums("same")
    check("the same performance paints the same map, to the bit", same == 1)
    null("another drying paints another map", same_other == 0 and apart > 0.01, "wetness apart by %.3f" % apart)

    # --- step 2: the stored switch and the painting's own Persistence ---
    (paints, p30, t03, knob30, p40, t40, traced, knob_trace, p_after, t80, again, again_p, again_t, again_knob) = nums("switch")
    check("a setup that draws Paint paints, at its own Persistence, the knob showing it", paints == 1 and p30 == 30 and knob30 == 71,
          "painting %d, %.1f s, knob at %d" % (paints, p30, knob30))
    check("the knob moved in Paint moves the painting's Persistence and leaves the trace's",
          abs(p40 - 6.8) < 1e-9 and t40 == t03 == 0.3, "painting's %.1f s, the trace's %.3f" % (p40, t40))
    check("Trace pressed: the core stops painting and the knob shows the trace's", traced == 0 and knob_trace == 9,
          "painting %d, knob at %d" % (traced, knob_trace))
    check("the knob moved in Trace moves the trace's and leaves the painting's", p_after == p40 and t80 != t03,
          "painting's %.1f s, the trace's %.4f" % (p_after, t80))
    null("one value for both would have moved the painting's with the trace's", t80 != t03 and p_after != 0.0038)
    check("reopened from its state, both are where the hands left them and Paint is shown again",
          again == 1 and again_p == p40 and again_t == t80 and again_knob == 40,
          "painting %d, %.1f s and %.4f, knob at %d" % (again, again_p, again_t, again_knob))
    null("the reopened knob is not the trace's place", again_knob != knob_trace)

    # --- step 2: Mono and Dyad paint ---
    on, radius_mono, near_a, near_e, table = nums("line", "mono")
    check("Mono paints its line at the note's radius and plays a table read off it", on == 1 and near_a > 0.9 and table == 1,
          "%.0f%% of the paint within a cell and a half of A3's ring" % (100 * near_a))
    null("none of it on E4's ring", near_e < 0.05, "%.1f%%" % (100 * near_e))
    _, _, dyad_a, dyad_e, dyad_table = nums("line", "dyad")
    check("Dyad paints both notes of its pair, each on its own ring", dyad_a > 0.3 and dyad_e > 0.3 and dyad_table == 1,
          "%.0f%% on A3's ring, %.0f%% on E4's" % (100 * dyad_a, 100 * dyad_e))

    # --- paint width (18 Nov): a melody is one stroke, so a run is a line, not beads ---
    covered, longest, arc, dip = nums("chain", "0.45", "1")
    check("a run of short notes struck alone paints one unbroken line: paint along all of its arc, dipping little between notes",
          covered > 0.9 and longest <= 2 and dip > 0.3,
          "%.0f%% of %d degrees, longest gap %d, thinnest tenth %.2f of the median" % (100 * covered, arc, longest, dip))
    off_covered, off_longest, _, off_dip = nums("chain", "0", "1")
    null("each note a stroke of its own (step 2's) dips to almost nothing between notes: beads", off_dip < 0.1,
         "thinnest tenth %.3f of the median, %.0f%% covered" % (off_dip, 100 * off_covered))

    # --- paint width: the map holds the stroke's real width ---
    # A held note's paint across its ring, as an RMS about the ring, against the core's own contact half-width: the
    # brush's edge (1 - |u/hw|^4) has an RMS of 0.488 of its half-width, and a cell's own width adds a twelfth of a
    # cell squared, so a map that holds the width reads sqrt((0.488 hw)^2 + 1/12).
    spreads = {}
    for width in ("1", "2", "3.5"):
        spread, hw, _ = nums("width", width)
        want = math.sqrt((0.488 * hw) ** 2 + 1 / 12)
        spreads[width] = (spread, hw, want)
        check("at base width %s the map holds the stroke's width: its spread across the ring is the brush's own" % width,
              abs(spread / want - 1) < 0.1, "%.3f cells against %.3f from a half-width of %.2f" % (spread, want, hw))
    s1, hw1, _ = spreads["1"]
    s35, hw35, want35 = spreads["3.5"]
    null("the wide brush's map read against today's brush's width is not it", abs(s35 / math.sqrt((0.488 * hw1) ** 2 + 1 / 12) - 1) > 0.5,
         "%.3f against %.3f" % (s35, math.sqrt((0.488 * hw1) ** 2 + 1 / 12)))
    check("and the width is the brush's: three and a half times as wide, three and a half times the half-width",
          abs(hw35 / hw1 - 3.5) < 0.05, "%.2f over %.2f" % (hw35, hw1))

    # --- step 2: the strokes the face is served ---
    count, last, served, err, none = nums("served")
    check("the face is served every stamp the painter lays: the ring's newest are the last frame's", served == last > 0 and err == 0,
          "%d laid, the last frame's %d served exactly" % (count, served))
    null("asked from the count itself, nothing new", none == 0)

    # --- what it costs ---
    trace, paint = nums("cost", "2")
    check("painting a held chord of sixteen costs under a tenth of a core more than the trace", paint - trace < 0.1,
          "%.3f s a second on the trace, %.3f painting (best of three)" % (trace, paint))
