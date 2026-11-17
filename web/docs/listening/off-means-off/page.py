"""Write index.html, the listening page, from results.json (render.py writes both).

    python3 web/docs/listening/off-means-off/page.py

The words above the pairs are written here by hand; every number on the page
comes from results.json, so a new render is a new page.
"""
import html, json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))


def f(v, fmt="%.1f"):
    return "&minus;&infin;" if v is None or (isinstance(v, float) and not math.isfinite(v)) else (fmt % v).replace("-", "&minus;")


def verdict(per):
    return "; ".join("%s %s (late %.4f)" % ("+".join(str(n) for n in p["notes"]), "/".join(p["under"]) or "<b>neither</b>", p["late"])
                     for p in per)


INTRO = """
<p>Today a rack module's switch takes its Mix to nought (the Plane: its shaping and the turn to rest),
and the Picture amount's fixed pushes are added on top of the knob: Motion onto the delay (0.5 of the
amount), Memory onto the Plane's twist and the phaser (0.3 each), and onto the Phase and Glow onto the
fold, which are no rack module's and are left alone here. A push makes its stage run, so a delay,
phaser or Plane switched off is brought back in from nought by the picture.</p>
<p><b>Off means off</b> is a render's question only (<code>["offmeansoff", true]</code> in
<code>core/tests/tools/render_cpp.cpp</code>; no setup field, nothing on the face): while a module is
switched off, the Picture's push onto it is ignored and its stage does not run. Off is told as the
switch leaves it: the delay or the phaser at a Mix of nought, the Plane with all its shaping at rest and
the screen unturned. What that costs: a Mix turned to nought by hand or by a host knob is &ldquo;off&rdquo; too,
since the switch keeps no state of its own; to make it the instrument's, the switch would have to become
a field, with a migration.</p>
<p>Every pair is the same performance from the core's offline renderer: a chord held six seconds
(C3 G3 C4 E4; in a split C2 G2 under E4 G4), then a phrase of eighths at 120, with a bass under it in a
split. Every bank preset under Settled and Breathing, at its own Picture amount, with the delay, the
phaser and the Plane as it ships them, which is off in all nine; and Harmonic tone again at Amount 100.
The files are 22.05 kHz 16-bit stereo. The picture under each is the 64 by 64 grid Scan reads, at the
end of the held chord, both drawn to the brighter of the two.</p>
<p>The line under each pair: how far apart the two are in level and in spectrum (honestytest's
fifth-octave band shares, window against window, a mean over the part: 0.02 is about what a Breathing
preset moves in a quarter second); the most the picture pushed each stage today; and the heading each
way, by honestytest's measure ported to the core's render (each preset's own probe held ten seconds:
Settled is early at least 0.008, late at most 0.015 and half of early; Breathing late at least 0.02).
Today's renders all measure under their own headings, which is the check on the port. The mono fold-down is what the pair loses summed to one channel: about &minus;3 dB is two channels
in quadrature, as the figure's circle is, and cancellation would read far lower; none is under &minus;6 dB.
The difference as a level (the two subtracted) is in results.json, but read it with care: past 0 dB it
says the two have drifted apart in phase, which a delay's repeats do, more than how different they sound.</p>
"""

RECOMMEND = """
<h2>Recommendation</h2>
<p>Do not make off mean off on its own. On the four Settled presets it changes nothing at all - they
are at Picture nought, so there is no push to stop, and the two renders are the same to the bit. On all
six Breathing renders it changes the sound plainly: 0.04 to 0.25 apart in spectrum, about as much as
the presets move in a second, and most of it the delay, which the picture pushes to 0.5 at full Amount
and is the larger part of what Breathing means. Slow pad stops measuring as Breathing at all (late
0.016 against the floor of 0.02; it fails Settled too), so the change would take a preset out of its
heading, and the bank would have to be voiced again around it - a delay switched on at a low Mix in each
Breathing preset, so the picture had something to push. If the owner hears the switched-off pairs as
right, that is the cost, and the switch must become a field first. If not, the honest fix is in the
words: a module's line on the rack says &ldquo;Off - the Picture brings it in&rdquo; while the Amount is
pushing it, rather than &ldquo;Off&rdquo;.</p>
"""


def main():
    results = json.load(open(os.path.join(HERE, "results.json")))
    rows = []
    for r in results:
        title = "%s &middot; <span>%s</span> &middot; Picture %s" % (html.escape(r["name"]), r["heading"], r["amount"])
        audio = lambda way: '<figure><figcaption>%s</figcaption><img src="fig/%s-%s.png" width="128" height="128" alt="the grid Scan reads, %s"><audio controls preload="none" src="wav/%s-%s.wav"></audio></figure>' % (
            "Today" if way == "today" else "Off means off", r["tag"], way, way, r["tag"], "today" if (way == "today" or r["same"]) else way)
        if r["same"]:
            line = ("Identical to the bit: at Picture %s there is no push to stop, so both players play the one file. "
                    "Heading: %s.") % (r["amount"], verdict(r["verdicts"]["today"]))
        else:
            t = r["routes"]["today"]
            line = ("Held: level %s dB, spectrum %s apart. Phrase: level %s dB, spectrum %s apart. "
                    "Pushed today, at most: delay %.2f, twist %.2f, phaser %.2f (off: %.2f, %.2f, %.2f). "
                    "Heading today: %s. Off: %s. Mono fold-down %s / %s dB.") % (
                f(r["level"]["held"]), f(r["spectral"]["held"], "%.3f"), f(r["level"]["phrase"]), f(r["spectral"]["phrase"], "%.3f"),
                t["echo"][0], t["twist"][0], t["phaser"][0],
                r["routes"]["off"]["echo"][0], r["routes"]["off"]["twist"][0], r["routes"]["off"]["phaser"][0],
                verdict(r["verdicts"]["today"]), verdict(r["verdicts"]["off"]), f(r["mono"]["today"]), f(r["mono"]["off"]))
        rows.append('<section><h3>%s</h3><div class="pair">%s%s</div><p class="measure">%s</p></section>'
                    % (title, audio("today"), audio("off"), line))
    page = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Off means off</title>
<style>
:root { --bg: #f6f4ef; --ink: #1d1f1c; --muted: #5d625a; --rule: #d9d5cb; --card: #fffdf8; }
@media (prefers-color-scheme: dark) { :root { --bg: #141613; --ink: #e8e6df; --muted: #a3a89e; --rule: #33372f; --card: #1b1e1a; } }
body { background: var(--bg); color: var(--ink); font: 15px/1.55 system-ui, sans-serif; margin: 0 auto; max-width: 860px; padding: 24px 16px 64px; }
h1 { font-size: 26px; margin: 0 0 8px; } h2 { font-size: 19px; margin-top: 32px; } h3 { font-size: 16px; margin: 0 0 10px; }
h3 span { color: var(--muted); font-weight: normal; }
section { background: var(--card); border: 1px solid var(--rule); border-radius: 8px; padding: 14px 16px; margin: 14px 0; }
.pair { display: flex; flex-wrap: wrap; gap: 16px; }
figure { margin: 0; display: grid; gap: 6px; justify-items: start; }
figcaption { font-weight: 600; font-size: 13px; }
img { image-rendering: pixelated; border-radius: 4px; }
audio { width: 300px; max-width: 100%%; }
.measure { color: var(--muted); font-size: 13.5px; margin: 10px 0 0; }
code { font-size: 13px; }
</style></head><body>
<h1>Off means off</h1>
<p class="measure">The WAVs and PNGs this page plays and shows are not kept in the repository: <code>render.py</code> beside it writes them again (they were sent to the owner separately).</p>
<p class="measure">Rendered by <code>render.py</code> beside this page, from the core as it stands on the branch; the numbers are results.json's.</p>
%s%s
<h2>The pairs</h2>
%s
</body></html>
""" % (INTRO, RECOMMEND, "\n".join(rows))
    with open(os.path.join(HERE, "index.html"), "w") as fh: fh.write(page)


if __name__ == "__main__":
    main()
