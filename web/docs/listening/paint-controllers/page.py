"""The listening page for the controllers on the brush (painting, step 3):
index.html beside this file, made from results.json, which render.py writes.
Re-run after it.

    python3 web/docs/listening/paint-controllers/page.py
"""
import html, json, os

HERE = os.path.dirname(os.path.abspath(__file__))

PHRASES = [
    ("pedal", "A pluck&rsquo;s slow melody under the pedal",
     "A short pluck (Tine piano&rsquo;s settings, decayed to nothing in a quarter second), C E G C B G E D C at a note a "
     "second, the sustain pedal down from the start and let go at the end. Each note is silent long before the next.",
     "Now the pedal only joins the notes into one stroke, as paint width had it: the brush lays while there is sound and "
     "the paint dries as it would, so <b>With</b> matches <b>Without</b> - a mark a note, as you heard it. Each mark is "
     "a little heavier with the pedal, since a joined stroke keeps what was left on the brush; the line between them "
     "is gone. <b>As first built</b>, the brush laid on through the silences and the paint stayed wet."),
    ("wheel", "A held chord with the mod wheel swept",
     "A slow pad, C3 G3 E4 held eight and a half seconds. The wheel starts at rest at the bottom, goes to the top over "
     "2.5 s, stays there 2 s, and comes back to rest over 2.5 s. The wheel is also Expression&rsquo;s vibrato, as it is "
     "by default, in all three.",
     "The wheel rests at the bottom now: there the brush is exactly the plain one, and up it only adds, so the top is a "
     "loaded brush - about twice as wide and five times the paint, laid thick and wet. <b>As first built</b> it was read "
     "from its middle, so the same sweep painted dry and thin at the bottom, and the top was only a little heavier."),
    ("bend", "A bend",
     "A fifth, A3 and E4, held seven seconds on a plain tone, the bend at its usual two semitones. Up quickly (a quarter "
     "second) and back, then down slowly (a second) and back.",
     "Two semitones move the stroke under one of the map&rsquo;s cells, which nobody can see under a stroke five wide, "
     "and where the stroke sits stays the pitch&rsquo;s. So a bend away from rest is a palette knife, the one you chose: "
     "it pushes the stroke&rsquo;s own paint aside the way the pitch went - outward for up, inward for down - as one "
     "flat, levelled slab the stroke&rsquo;s width, its grooves gone, at the stroke&rsquo;s tone, with a thin patchy film "
     "where the blade started and one lip along its far edge, easing in and out along the stroke. The bend back to rest "
     "cuts nothing. A quick flick pushes further and sharper, a slow bend shorter and broader. It is in the map too, so "
     "Scan hears it. <b>As first built</b> the stroke moved its cell and nothing else."),
    ("strikes", "Soft against hard strikes",
     "C D E F G F E D, a note every 0.6 s, alternating velocity 30 and 127, at Strike 100 so a hard strike&rsquo;s "
     "impact is full.",
     "Spatter is drops now, not strokes: a ragged blot where the brush lands, larger than the stroke, and round it drops "
     "of every size - many fine specks, a few large blots - thrown further and bigger the harder the strike, smaller the "
     "further they fly, some - the larger ones likelier - drawn out into a teardrop whose tail points away from the blot, every edge smooth and rounded. The soft strikes throw nothing (under "
     "about a third of a full impact, nothing). <b>Without</b>, none at all. <b>As first built</b>, a scatter of small "
     "strokes all alike. The close-ups are round the first hard strike."),
    ("lean", "Aftertouch leaned on",
     "A slow pad, A3 E4 A4 held six seconds. Channel pressure rises to full over a second, holds, and lets off over a "
     "second.",
     "Unchanged, as you asked: the strokes widen and press in while the keys are leaned on, smearing the wet paint they "
     "cross. <b>Without</b>, the same width throughout. <b>As first built</b> is the same brush."),
]
WAYS = [("with", "With it", "the brush hears the controller, as revised"),
        ("without", "Without", "the same performance, the brush deaf to it"),
        ("first", "As first built", "the controllers as step 3 was first built (7389e9c)")]


def column(key, way, label, sub, row):
    s = row["scan"]
    close = ('<img class=close src="pictures/%s-%s-close.jpg" width="338" height="338" loading="lazy" alt="Close-up round the first '
             'hard strike, %s">' % (key, way, label.lower())) if key == "strikes" else ""
    extra = ""
    if row.get("drops"): extra += '<tr><th>Drops of spatter</th><td>%d</td></tr>' % row["drops"]
    if row.get("pulls"): extra += '<tr><th>Pulls on the paint</th><td>%d</td></tr>' % row["pulls"]
    return ('<div class=col><span class=tag>%s <span class=soft>%s</span></span>'
            '<audio controls preload="none" src="audio/%s-%s.mp3"></audio>'
            '<img class=look src="pictures/%s-%s-look.jpg" width="768" height="768" loading="lazy" alt="The live look at the end, %s">%s'
            '<img class=map src="pictures/%s-%s-map.png" width="384" height="384" loading="lazy" alt="The paint map Scan reads, %s">'
            '<table><tr><th>Centroid</th><td>%.2f <span class=soft>(%.2f&ndash;%.2f)</span></td></tr>'
            '<tr><th>Movement</th><td>%.4f</td></tr>'
            '<tr><th>Glow / Motion / Memory</th><td>%.2f / %.2f / %.2f</td></tr>'
            '<tr><th>Brush, median (p90)</th><td>%.1f (%.1f) cells</td></tr>'
            '<tr><th>Paint at the end</th><td>%.0f, %.0f%% wet</td></tr>%s</table></div>'
            % (label, sub, key, way, key, way, label.lower(), close, key, way, label.lower(), s["centroid"], s["centroid_p10"],
               s["centroid_p90"], s["movement"], row["glow"], row["motion"], row["memory"], row["brush_cells"],
               row["brush_p90"], row["paint"], 100 * row["wet"], extra))


def main():
    res = json.load(open(os.path.join(HERE, "results.json")))
    out = []
    for key, name, plays, listen in PHRASES:
        cols = "".join(column(key, w, label, sub, res[key][w]) for w, label, sub in WAYS)
        out.append('<section><h2>%s</h2><p>%s</p><p class=soft>%s</p><div class=cols>%s</div></section>'
                   % (name, plays, listen, cols))
    page = TEMPLATE.replace("{{SECTIONS}}", "\n".join(out))
    with open(os.path.join(HERE, "index.html"), "w") as f: f.write(page)


TEMPLATE = """<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Controllers on the brush</title>
<!-- Painting, step 3 (20 Nov), revised the same day after the owner listened: five
     short phrases with a controller moving, each painted by the core with the brush
     hearing the controller, deaf to it, and as step 3 was first built, the live look
     painted from the same strokes. Made by page.py from results.json, which render.py
     writes with the audio and the pictures. -->
<style>
  :root { --cream: #faf6f0; --paper: #fffcf7; --charcoal: #241f1d; --text: #3a332f; --text-soft: #6b615a;
          --line: #e4d9cc; --gold: #b08d57; }
  body { background: var(--cream); color: var(--text); font: 16px/1.5 system-ui, sans-serif; margin: 0; padding: 24px 16px; }
  main { max-width: 1180px; margin: 0 auto; }
  h1 { color: var(--charcoal); font-size: 1.6rem; margin: 0 0 4px; }
  h2 { color: var(--charcoal); font-size: 1.2rem; margin: 36px 0 6px; }
  p { margin: 8px 0; }
  .soft { color: var(--text-soft); }
  .cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; margin-top: 12px; }
  .col { background: var(--paper); border: 1px solid var(--line); border-radius: 10px; padding: 12px; min-width: 0; }
  .tag { font-size: 0.8rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--gold); display: block; margin-bottom: 6px; }
  .tag .soft { text-transform: none; letter-spacing: 0; }
  audio { width: 100%; height: 32px; }
  img { display: block; width: 100%; height: auto; margin-top: 10px; border-radius: 6px; }
  img.map { width: 50%; image-rendering: pixelated; }
  img.close { width: 100%; }
  table { border-collapse: collapse; width: 100%; margin-top: 10px; }
  th, td { padding: 4px 6px; border-bottom: 1px solid var(--line); text-align: left; font-size: 0.85rem; }
  th { font-weight: 600; color: var(--charcoal); }
  .ask { background: var(--paper); border: 1px solid var(--gold); border-radius: 10px; padding: 12px 16px; margin-top: 16px; }
  code { font-size: 0.9em; }
</style>
</head>
<body>
<main>
  <h1>Controllers on the brush</h1>
  <p class="soft">20 Nov, revised the same day after you listened. Painting, step 3: the pedal now only joins notes,
    as the pluck sounds; the mod wheel rests at the bottom and loads the brush going up, plainly; a bend away from rest
    is a palette knife through the wet stroke; a hard strike throws drops of paint; aftertouch is as it was. Every one of them
    changes the strokes themselves, so the look draws what the map holds and Scan hears it. Expression (CC 11) is still
    the Picture amount.</p>
  <p class="soft">Each phrase below is one performance painted three times: with the brush hearing the controller as
    revised, with the brush deaf to it, and as step 3 was first built. The first two differ only by what Scan reads off
    the paint, and the pictures by what the brush did. Scan is at 60 and the Picture amount at nought throughout, so
    what you hear is Scan alone.</p>

  <div class="ask">
    <p><b>Things to decide.</b></p>
    <p><b>The knife, fine-tuned later.</b> You chose the full-width knife as a starting point. How far it pushes (four of
      the brush&rsquo;s half-widths at a whole tone), the lip&rsquo;s height and the film&rsquo;s thinness are one number
      each.</p>
    <p><b>The splayed strike is parked.</b> It was tried three ways (a fan of fingers with separate tracks, a flare
      closing into the stroke, and a lab of knobs) and you went back to the drops below: &ldquo;the closest one
      we&rsquo;ve had, and we can get this right later&rdquo;. The strike lab (<code>web/docs/labs/strike-lab/</code>) is
      where to resume: it paints with this page&rsquo;s own look from stamps the core already lays.</p>
    <p><b>Where spatter starts.</b> Nothing under about a third of a full impact (velocity times Strike). At the default
      Strike of 50 that is a velocity of about 90 before the first drop; at Strike 100, about 45.</p>
    <p><b>The wheel and pressure still do two things.</b> In Paint the brush reads them as well as whatever
      Expression&rsquo;s menus give them to: the wheel is still the vibrato by default. A switch could choose, if you
      want one.</p>
  </div>

  <h2>How to read the numbers</h2>
  <p><b>Centroid</b> is the brightness of what Scan reads, in harmonics: 1 is a sine, about 2 is mellow and 3 is reedy.
    <b>Movement</b> is how much it changes from one sixtieth of a second to the next; under 0.005 is a steady tone.
    <b>Glow, Motion, Memory</b> are the Picture amount&rsquo;s three reads, as medians. <b>Brush</b> is the strokes&rsquo;
    width in the map&rsquo;s cells (128 across), the median and the widest tenth. <b>Paint at the end</b> is the
    map&rsquo;s paint summed, and how much of it is wet. The map pictures show thickness in grey and wet paint in
    blue; the looks are the page&rsquo;s own paint view, fed the core&rsquo;s strokes a sixtieth of a second at a time.</p>

{{SECTIONS}}

  <p class="soft">Made by <code>render.py</code> (with <code>render.cpp</code>, the core playing each phrase, beside this
    page) and <code>page.py</code>. Every number is in <code>results.json</code>. The brush is deafened with
    <code>PaintParams::hears</code> and <code>spatterAt</code>, which exist for this and for the tests&rsquo; nulls;
    in the instrument the brush hears everything.</p>
</main>
</body>
</html>
"""

if __name__ == "__main__":
    main()
