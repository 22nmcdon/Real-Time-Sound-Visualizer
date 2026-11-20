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
performance paints the same map to the bit; the player's controllers on the
brush (step 3: the pedal, the wheel, the bend, velocity's spatter and
aftertouch), each against the brush deaf to it; and what it costs.

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
    covered, longest, arc, dip, strokes = nums("chain", "1", "1")
    check("a run on Tine piano's envelope, each note struck alone and still sounding at the next, paints one unbroken line",
          strokes == 1 and covered > 0.9 and longest <= 2 and dip > 0.3,
          "%d stroke, %.0f%% of %d degrees, longest gap %d, thinnest tenth %.2f of the median" % (strokes, 100 * covered, arc, longest, dip))
    _, _, _, _, apart = nums("chain", "0", "1")
    null("each note a stroke of its own (step 2's) is eleven strokes", apart == 11, "%d" % apart)

    # --- the join (19 Nov, the owner's): a note goes on with the last one's stroke while that one still sounds, or under
    # the pedal; by the sound, not the clock ---
    pluck, gone = nums("join", "pluck", "1")
    check("a pluck's slow melody, a note a second, is a stroke a note: each is silent by the next strike", pluck == 6,
          "%d strokes, the last note at %.3f of its peak at a strike" % (pluck, gone))
    quick, at = nums("join", "pluck", "0.111")
    null("the same pluck nine notes a second, its tails meeting the next strike, is one stroke", quick == 1,
         "%d strokes, the last note at %.2f of its peak" % (quick, at))
    pad, still = nums("join", "pad", "1")
    check("a pad's slow melody, a note a second, is one stroke: each note still sounding at the next (above -24 dB of its peak)",
          pad == 1 and still > 0.063, "%d stroke, the last note at %.2f of its peak" % (pad, still))
    pad3, still3 = nums("join", "pad", "3")
    check("and three seconds apart, which no rule by the clock that joins a run would join, still one", pad3 == 1,
          "%d stroke, at %.2f" % (pad3, still3))
    split, _ = nums("join", "pad", "1", "1.01")
    null("the pad at a floor above where it sounds splits a stroke a note: the join is its level's", split == 6, "%d strokes" % split)
    held, _ = nums("join", "pluck", "1", "0.063", "1")
    check("the pluck's slow melody under the sustain pedal is one stroke", held == 1, "%d stroke" % held)
    null("and without the pedal, a stroke a note (above)", pluck == 6 and held != pluck)

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

    # --- step 3: the player's controllers on the brush (the owner's table, 16 Nov) ---
    ALL, PEDAL, WHEEL, BEND, PRESSURE = 15, 1, 2, 4, 8
    def holds(spread, hw):
        # The map holds the stroke's width (paint width's measure, above): what the look draws is the stamp's.
        return abs(spread / math.sqrt((0.488 * hw) ** 2 + 1 / 12) - 1) < 0.1

    # The pedal (revised 20 Nov, the owner: "the only one that matches the sound properly for pluck"): it joins a hand's
    # notes into one stroke and nothing else - the brush lays only while there is sound and the paint dries as it would.
    covered, gap, wet_down, wet_after, last, strokes = nums("pedal", str(ALL))
    d_covered, d_gap, d_wet, _, _, d_strokes = nums("pedal", str(ALL - PEDAL))
    check("under the pedal a pluck's slow melody is painted as it sounds: the brush lays nothing through the silences",
          covered < d_covered + 0.05 and gap >= d_gap - 5 and gap > 60,
          "%.0f%% of its arc painted, the longest stretch without %d degrees (deaf to the pedal %.0f%%, %d)" % (100 * covered, gap, 100 * d_covered, d_gap))
    h_covered, h_gap, _, _, _, _ = nums("pedal", str(ALL), "1")
    null("the same melody held, sounding through, covers its arc, so the measure can read a brush laying", h_covered > 0.6 and h_gap <= 10,
         "%.0f%%, a gap of %d degrees" % (100 * h_covered, h_gap))
    check("and the paint dries under the pedal as it does without it", wet_down < 0.5 and wet_after < 0.5 and last == 0,
          "%.2f wet with it down, %.2f two seconds after, %d stamps then" % (wet_down, wet_after, last))
    null("a drying read that cannot go red: fresh paint is read wet", nums("pedal", str(ALL), "1")[2] > wet_down,
         "%.2f wet held" % nums("pedal", str(ALL), "1")[2])
    check("and it still joins the notes into one stroke", strokes < d_strokes, "%d strokes, %d deaf to it" % (strokes, d_strokes))
    null("deaf to the pedal they are more strokes than one", d_strokes > 1, "%d" % d_strokes)

    # The mod wheel (revised 20 Nov): it rests at the bottom, where the brush is step 2's to the bit, and up it only adds -
    # at the top plainly a loaded brush. The owner's mark: at the top, the median width at least 1.8 times rest's and
    # the paint laid at least 2.5 times.
    rest = nums("wheel", "-1", str(ALL))
    bottom = nums("wheel", "0", str(ALL))
    deaf_rest = nums("wheel", "-1", str(ALL - WHEEL))
    check("a wheel that has not moved, and a wheel at the bottom, paint step 2's brush, to the bit",
          rest[4] == deaf_rest[4] and bottom[4] == deaf_rest[4], "%.9g, %.9g against %.9g" % (rest[4], bottom[4], deaf_rest[4]))
    heavy, half = nums("wheel", "1", str(ALL)), nums("wheel", "0.5", str(ALL))
    null("the same comparison against the wheel at the top is not to the bit", rest[4] != heavy[4], "%.9g" % heavy[4])
    def loaded(top, base):
        return top[5] >= 1.8 * base[5] and top[2] >= 2.5 * base[2]
    check("the wheel at the top is a loaded brush: at least 1.8 times as wide and 2.5 times the paint, and half-way between",
          loaded(heavy, rest) and rest[5] < half[5] < heavy[5] and rest[2] < half[2] < heavy[2] and heavy[3] > 1.8 * rest[3],
          "median half-width %.2f, %.2f, %.2f cells; paint %.1f, %.1f, %.1f; load %.2f, %.2f (rest, half-way, top)"
          % (rest[5], half[5], heavy[5], rest[2], half[2], heavy[2], rest[3], heavy[3]))
    null("the wheel at the bottom does not pass the loaded brush's mark", not loaded(bottom, rest),
         "%.2f cells, paint %.1f" % (bottom[5], bottom[2]))
    deaf_top = nums("wheel", "1", str(ALL - WHEEL))
    null("the brush deaf to the wheel paints the same at the top as at rest", deaf_top[4] == bottom[4],
         "half-width %.2f, paint %.1f" % (deaf_top[1], deaf_top[2]))
    check("and at the top the map holds the stamp's width, which the look draws", holds(heavy[0], heavy[1]),
          "spread %.2f for a half-width of %.2f" % (heavy[0], heavy[1]))
    null("the heavy brush's map read against the resting brush's width is not it", not holds(heavy[0], rest[1]))

    # The pitch wheel: the stroke bends with the pitch, continuously...
    before, after, want, step, back = nums("bend", str(ALL))
    check("a bend to the top moves the brush's radius to the pitch two semitones up, smoothly", abs(after - want) < 0.05 and step < 0.1 and back == 0,
          "%.2f to %.2f cells (the layout's %.2f), at most %.3f a frame, never back" % (before, after, want, step))
    d_before, d_after, _, _, _ = nums("bend", str(ALL - BEND))
    null("the brush deaf to the bend stays on its note's radius", abs(d_after - d_before) < 1e-9, "%.2f to %.2f" % (d_before, d_after))
    # ...and (20 Nov, the owner's palette knife, a710a49) pushes the stroke's own paint aside the way the pitch went, as a
    # flat blade does, so a bend at its usual two semitones is seen: a share of the paint on the arc it went round lies out
    # past the stroke's own band on that side, and none on the other.
    up_out, up_in, up_all, pulls, _ = nums("pull", "2", "0.4", str(ALL))
    dn_out, dn_in, _, _, _ = nums("pull", "-2", "0.4", str(ALL))
    deaf_out, deaf_in, deaf_all, deaf_pulls, _ = nums("pull", "2", "0.4", str(ALL - BEND))
    check("a quick bend of two semitones up pushes paint out past the stroke, and one down pushes it in",
          up_out > 0.1 and up_in < 1e-3 and dn_in > 0.1 and dn_out < 1e-3 and pulls > 0,
          "%.1f%% out, %.1f%% in going up; %.1f%% in, %.1f%% out going down; %d strips" % (100 * up_out, 100 * up_in, 100 * dn_in, 100 * dn_out, pulls))
    null("deaf to the bend no paint lies past the band", deaf_out < 1e-3 and deaf_pulls == 0, "%.2f%%" % (100 * deaf_out))
    check("and the knife moves the stroke's paint, adding no more than keeps its tone", abs(up_all / deaf_all - 1) < 0.03,
          "%.1f against %.1f" % (up_all, deaf_all))
    slow_out = nums("pull", "2", "1.5", str(ALL))[0]
    check("a slow bend pushes too, less far", 0.03 < slow_out < up_out, "%.2f%% over 1.5 s against %.2f%% over 0.4" % (100 * slow_out, 100 * up_out))
    # Only a bend away from rest cuts: the wheel springing back is no knife stroke (the owner: too much of the ring was
    # flattened when every return cut a swath of its own).
    k_quick = nums("knife", "0.3", str(ALL))
    k_slow = nums("knife", "1.0", str(ALL))
    check("the knife cuts as the bend goes away from rest and not as it comes back", k_quick[0] > 10 and k_quick[1] == 0 and k_slow[0] > 10 and k_slow[1] == 0,
          "%d strips away and %d back, quickly; %d and %d slowly" % (k_quick[0], k_quick[1], k_slow[0], k_slow[1]))
    k_deaf = nums("knife", "0.3", str(ALL - BEND))
    null("deaf to the bend it cuts nothing either way, so the count can read nought where nought is right", k_deaf[0] == 0 and k_deaf[1] == 0,
         "%d and %d" % (k_deaf[0], k_deaf[1]))
    # The levelled plane keeps the stroke's tone (the owner: "A knife levels the paint, it doesn't thin the colour"): its
    # cover over the stroke's, which 5ece483's wider swath and larger lip left at 0.59 and 0.71 (the mutation pass).
    check("the levelled plane keeps the stroke's tone", k_quick[2] > 0.68 and k_slow[2] > 0.77,
          "its cover %.2f of the stroke's after a quick bend, %.2f after a slow one" % (k_quick[2], k_slow[2]))
    null("the same measure reads the thin film behind the blade as pale, so the bound can fail", not (k_quick[5] > 0.68) and not (k_slow[5] > 0.77),
         "the film's cover %.2f and %.2f of the stroke's" % (k_quick[5], k_slow[5]))
    # The far edge is one line along the swath (its lip), not a saw: the RMS of the second difference of where it stands,
    # strip to strip, which a push worked out a frame at a time, unsmoothed, left at 0.19 cells (the mutation pass).
    check("the swath's far edge, and its lip, run as one line along the stroke", k_quick[3] < 0.16 and k_slow[3] < 0.16,
          "roughness %.3f cells quickly, %.3f slowly" % (k_quick[3], k_slow[3]))

    # Velocity: the strike's spatter (rebuilt 20 Nov, the owner: "splattered paint", not small strokes all alike): drops,
    # a blot where the brush lands, larger than the stroke, sizes off a heavy tail, further and more the harder, smaller
    # the further they fly, some drawn out pointing away from the blot; none from a soft strike or at Strike nought.
    sp = {v: nums("spatter", str(v), "-1") for v in (40, 80, 127)}
    off, far, n, blot, hw, rmed, rmax, longer, away, strayed, near_r, far_r = sp[127]
    check("a hard strike throws drops, not strokes: a blot larger than the stroke and the rest round it, no brush stamp off its ring",
          n > 30 and blot > 1.05 * hw and strayed == 0, "%d drops, the blot %.2f cells across its radius, the stroke %.2f; %d stray brush stamps" % (n, blot, hw, strayed))
    check("the drops' sizes are off a heavy tail: the largest four times the median", rmax > 4 * rmed > 0, "median %.2f, largest %.2f cells" % (rmed, rmax))
    null("a tail that is not there fails it: the median against itself", not (rmed > 4 * rmed > 0))
    check("they are smaller the further they fly", far_r < 0.8 * near_r, "median %.2f cells nearer the blot, %.2f further" % (near_r, far_r))
    check("some, not all, are drawn out, every one pointing away from the blot", 0.15 < longer < 0.6 and away == round(longer * (n - 1)),
          "%.0f%% drawn out, %d of them away" % (100 * longer, away))
    check("a harder strike throws more, further", sp[127][2] > sp[80][2] > 0 and sp[127][1] > sp[80][1] and sp[127][0] > sp[80][0],
          "%d and %d drops, the farthest %.1f and %.1f cells (velocity 80, 127)" % (sp[80][2], sp[127][2], sp[80][1], sp[127][1]))
    check("a soft strike throws nothing", sp[40][2] == 0 and sp[40][0] == 0, "%d drops at velocity 40" % sp[40][2])
    null("the soft check reads drops: the same strike spattered as a hard one throws them", nums("spatter", "40", "1")[2] > 30)
    f_soft = nums("spatter", "40", "0.8")
    f_hard = nums("spatter", "127", "0.8")
    null("spatter fixed whatever the strike is the same soft and hard", f_soft[2] == f_hard[2] and f_soft[0] == f_hard[0],
         "%d and %d drops" % (f_soft[2], f_hard[2]))
    check("and Strike at nought throws none", nums("spatter", "127", "0")[2] == 0)

    # Aftertouch: the stroke widens and presses in while the key is leaned on.
    leaned, lean_hw = nums("lean", "1", str(ALL))
    _, light_hw = nums("lean", "0", str(ALL))
    check("leaning on the key widens the stroke, and the map holds the width the look draws",
          lean_hw > 1.6 * light_hw and holds(leaned, lean_hw), "half-width %.2f against %.2f, spread %.2f" % (lean_hw, light_hw, leaned))
    _, deaf_hw = nums("lean", "1", str(ALL - PRESSURE))
    null("the brush deaf to pressure is as wide leaned on as not", deaf_hw == light_hw, "%.2f" % deaf_hw)

    # --- step 2: the strokes the face is served ---
    count, last, served, err, none = nums("served")
    check("the face is served every stamp the painter lays: the ring's newest are the last frame's", served == last > 0 and err == 0,
          "%d laid, the last frame's %d served exactly" % (count, served))
    null("asked from the count itself, nothing new", none == 0)

    # --- what it costs ---
    trace, paint = nums("cost", "2")
    check("painting a held chord of sixteen costs under a tenth of a core more than the trace", paint - trace < 0.1,
          "%.3f s a second on the trace, %.3f painting (best of three)" % (trace, paint))
