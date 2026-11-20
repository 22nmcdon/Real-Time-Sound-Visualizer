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
     "With the pedal, the brush stays on the canvas through the silences, laying what it still holds, and the paint stays "
     "wet until the pedal goes up. Without, the brush lays only while there is sound: nine marks of one stroke, as paint "
     "width left it."),
    ("wheel", "A held chord with the mod wheel swept",
     "A slow pad, C3 G3 E4 held eight seconds. The wheel goes to the top over 2.5 s, down to the bottom over 2.5 s, then "
     "back to its middle. The wheel is also Expression&rsquo;s vibrato, as it is by default, so both renders have the "
     "vibrato in them.",
     "With it, the brush loads heavier and presses wider at the top, and dries to a scratchy brush at the bottom. "
     "Without, it is the brush at rest throughout."),
    ("bend", "A bend",
     "A fifth, A3 and E4, held seven seconds on a plain tone, the bend range set to an octave. The pitch wheel goes up an "
     "octave and back, then down one and back. At the usual two semitones the stroke moves under one of the map&rsquo;s "
     "cells, which the eye cannot find under a stroke ten cells wide, though the pieces measure it.",
     "With it, the strokes bend with the pitch, since pitch is the radius, and each note reads the ring it is bent to. "
     "Without, they stay on their notes&rsquo; rings while the sound bends."),
    ("strikes", "Soft against hard strikes",
     "C D E F G F E D, a note every 0.6 s, alternating velocity 30 and 127, at Strike 100 so a hard strike&rsquo;s "
     "impact is full.",
     "With it, each hard strike throws spatter, further the harder; the soft ones throw almost none. Without, no "
     "spatter at all (the strike&rsquo;s dip and press are the same in both)."),
    ("lean", "Aftertouch leaned on",
     "A slow pad, A3 E4 A4 held six seconds. Channel pressure rises to full over a second, holds, and lets off over a "
     "second.",
     "With it, the strokes widen and press in while the keys are leaned on, smearing the wet paint they cross. "
     "Without, the same width throughout."),
]
WAYS = [("with", "With it", "the brush hears the controller"), ("without", "Without", "the same performance, the brush deaf to it")]


def column(key, way, label, sub, row):
    s = row["scan"]
    return ('<div class=col><span class=tag>%s <span class=soft>%s</span></span>'
            '<audio controls preload="none" src="audio/%s-%s.mp3"></audio>'
            '<img class=look src="pictures/%s-%s-look.jpg" width="768" height="768" loading="lazy" alt="The live look at the end, %s">'
            '<img class=map src="pictures/%s-%s-map.png" width="384" height="384" loading="lazy" alt="The paint map Scan reads, %s">'
            '<table><tr><th>Centroid</th><td>%.2f <span class=soft>(%.2f&ndash;%.2f)</span></td></tr>'
            '<tr><th>Movement</th><td>%.4f</td></tr>'
            '<tr><th>Glow / Motion / Memory</th><td>%.2f / %.2f / %.2f</td></tr>'
            '<tr><th>Brush, median (p90)</th><td>%.1f (%.1f) cells</td></tr>'
            '<tr><th>Paint at the end</th><td>%.0f, %.0f%% wet</td></tr></table></div>'
            % (label, sub, key, way, key, way, label.lower(), key, way, label.lower(), s["centroid"], s["centroid_p10"],
               s["centroid_p90"], s["movement"], row["glow"], row["motion"], row["memory"], row["brush_cells"],
               row["brush_p90"], row["paint"], 100 * row["wet"]))


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
<!-- Painting, step 3 (20 Nov): five short phrases with a controller moving, each
     painted by the core with the brush hearing the controller and deaf to it, the
     live look painted from the same strokes. Made by page.py from results.json,
     which render.py writes with the audio and the pictures. -->
<style>
  :root { --cream: #faf6f0; --paper: #fffcf7; --charcoal: #241f1d; --text: #3a332f; --text-soft: #6b615a;
          --line: #e4d9cc; --gold: #b08d57; }
  body { background: var(--cream); color: var(--text); font: 16px/1.5 system-ui, sans-serif; margin: 0; padding: 24px 16px; }
  main { max-width: 1180px; margin: 0 auto; }
  h1 { color: var(--charcoal); font-size: 1.6rem; margin: 0 0 4px; }
  h2 { color: var(--charcoal); font-size: 1.2rem; margin: 36px 0 6px; }
  p { margin: 8px 0; }
  .soft { color: var(--text-soft); }
  .cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px; margin-top: 12px; }
  .col { background: var(--paper); border: 1px solid var(--line); border-radius: 10px; padding: 12px; min-width: 0; }
  .tag { font-size: 0.8rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--gold); display: block; margin-bottom: 6px; }
  .tag .soft { text-transform: none; letter-spacing: 0; }
  audio { width: 100%; height: 32px; }
  img { display: block; width: 100%; height: auto; margin-top: 10px; border-radius: 6px; }
  img.map { width: 50%; image-rendering: pixelated; }
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
  <p class="soft">20 Nov. Painting, step 3: your table of 16 Nov, built in the core. The pedal keeps the brush on the
    canvas and the paint wet, the mod wheel is the brush&rsquo;s load, the pitch wheel bends the stroke, a hard strike
    spatters and leaning on a key widens the stroke. Every one of them changes the strokes themselves, their width,
    pressure and paint, so the look draws what the map holds and Scan hears it. Expression (CC 11) is still the Picture
    amount.</p>
  <p class="soft">Each phrase below is one performance painted twice: once with the brush hearing the controller, and
    once with the brush deaf to it. The sound differs only by what Scan reads off the paint, and the pictures by what
    the brush did. Scan is at 60 and the Picture amount at nought throughout, so what you hear is Scan alone.</p>

  <div class="ask">
    <p><b>Two things to decide.</b></p>
    <p><b>Where the wheel rests.</b> The wheel is read from its middle. A wheel you have never moved leaves the brush as
      it was; down from the middle is drier, to a scratchy brush at the bottom; up is heavier. A mod wheel rests at the
      bottom, though, so if you sweep it and let it fall back, the brush paints dry. The other way round, with
      today&rsquo;s brush at the bottom and only heavier going up, there would be no way to reach the dry brush.</p>
    <p><b>The wheel and pressure do two things.</b> In Paint the brush reads the wheel and pressure as well as whatever
      Expression&rsquo;s menus give them to: the wheel is still the vibrato by default, so sweeping it bends the
      pitch a little and loads the brush at once. Nothing chooses between them yet. A switch could, if you want one.</p>
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
