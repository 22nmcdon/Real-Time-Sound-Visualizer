"""The listening page for paint width: index.html beside this file, made from
results.json, which render.py and cost.py write. Re-run after them.

    python3 web/docs/listening/paint-width/page.py
"""
import html, json, os

HERE = os.path.dirname(os.path.abspath(__file__))

PHRASES = [
    ("pad", "Held pad", "Slow pad, Picture amount 100: C3 G3 D4 E4 B4 held 9 s, past one turn."),
    ("crossed", "Crossed hands", "The owner's setup, Picture amount 47: left-hand chords under a right-hand run that "
     "quickens, then two grace notes."),
    ("run", "Fast run", "Tine piano, Picture amount 0, so Scan alone: C4 to C5 and back three times at nine notes a second."),
    ("chords", "Chord change", "Drawbar organ, Picture amount 0: Dm7 G7 Cmaj7 Am7, 2.5 s each."),
]
WIDTHS = [("today", "Today", "1&times;, as step 2 shipped"), ("medium", "Medium", "2&times;"), ("wide", "Wide", "3.5&times;, near the study&rsquo;s brush")]


def column(key, w, label, sub, row):
    s, sh = row["scan"], row["shares"]
    return ('<div class=col><span class=tag>%s <span class=soft>%s</span></span>'
            '<audio controls preload="none" src="audio/%s-%s.mp3"></audio>'
            '<img class=look src="pictures/%s-%s-look.jpg" width="768" height="768" loading="lazy" alt="The live look at the end, %s">'
            '<img class=map src="pictures/%s-%s-map.png" width="384" height="384" loading="lazy" alt="The paint map Scan reads, %s">'
            '<table><tr><th>Centroid</th><td>%.2f <span class=soft>(%.2f&ndash;%.2f)</span></td></tr>'
            '<tr><th>Movement</th><td>%.4f</td></tr>'
            '<tr><th>Shared, a semitone</th><td>%.2f</td></tr>'
            '<tr><th>Shared, a fifth</th><td>%.2f</td></tr>'
            '<tr><th>Glow / Motion / Memory</th><td>%.2f / %.2f / %.2f</td></tr>'
            '<tr><th>Covered (p90)</th><td>%.0f%%</td></tr>'
            '<tr><th>Brush, median</th><td>%.1f cells</td></tr></table></div>'
            % (label, sub, key, w, key, w, label.lower(), key, w, label.lower(), s["centroid"], s["centroid_p10"], s["centroid_p90"],
               s["movement"], sh["semitone"], sh["fifth"], row["glow"], row["motion"], row["memory"], 100 * row["covered_p90"],
               row["brush_cells"]))


def pair(key, name, about, res):
    """A phrase at the width picked, joined and separate, side by side."""
    cols = "".join(column(key, k, label, sub, res[key][k]) for k, label, sub in
                   (("medium", "Joined", "as the instrument now paints"), ("medium-separate", "Separate", "every note its own, as step 2")))
    j, sep = res[key]["medium"], res[key]["medium-separate"]
    return ('<section><h3>%s</h3><p class=soft>%s %d strokes joined against %d separate.</p><div class=cols>%s</div></section>'
            % (name, html.escape(about), j["strokes"], sep["strokes"], cols))


def main():
    res = json.load(open(os.path.join(HERE, "results.json")))
    out = []
    for key, name, about in PHRASES:
        cols = "".join(column(key, w, label, sub, res[key][w]) for w, label, sub in WIDTHS)
        out.append('<section><h2>%s</h2><p class=soft>%s</p><div class=cols>%s</div></section>' % (name, html.escape(about), cols))
    c = res["cost"]
    cost_rows = "".join(
        "<tr><th>%s</th><td>%.3f</td><td>%.3f</td><td>%.2f</td><td>%.2f</td><td>%.2f</td><td>%.2f</td></tr>"
        % (label, c[w]["native_trace"], c[w]["native_paint"], c[w]["wasm_trace_ms"], c[w]["wasm_paint_ms"], c[w]["map_spread"],
           c[w]["brush_spread"]) for w, label, _ in WIDTHS)
    joined = "".join(pair(k, n, a, res) for k, n, a in (
        ("run", "Fast run, Tine piano", "Nine notes a second: each note still sounding at the next strike, so it joins."),
        ("slow-tine", "Slow melody, Tine piano", "A note a second, held 0.95 s each: C E G C B G E D C. Each note is about "
         "-14 dB of its peak at the next strike, above the floor, so it joins."),
        ("slow-pad", "Slow melody, Slow pad", "The same melody on a long pad: each note at about -3 dB at the next strike. It joins."),
        ("slow-pluck", "Slow melody, a short pluck", "The same melody on Tine piano's settings with the decay cut to a quarter "
         "second: each note silent long before the next. It does not join."),
        ("slow-pluck-pedal", "Slow melody, the pluck under the sustain pedal", "The pedal down throughout. It joins.")))
    page = TEMPLATE.replace("{{SECTIONS}}", "\n".join(out)).replace("{{JOINED}}", joined).replace("{{COST}}", cost_rows)
    with open(os.path.join(HERE, "index.html"), "w") as f: f.write(page)


TEMPLATE = """<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Paint width</title>
<!-- Paint width (18 Nov): the study's four phrases painted by the core at three
     base brush widths, with the live look painted from the same strokes, for the
     owner to choose between. Made by page.py from results.json, which render.py
     and cost.py write with the audio and the pictures. -->
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
  .scroll { overflow-x: auto; }
  .pick { background: var(--paper); border: 1px solid var(--gold); border-radius: 10px; padding: 12px 16px; margin-top: 16px; }
  .pair { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }
  figure { margin: 0; } figcaption { font-size: 0.85rem; color: var(--text-soft); }
  code { font-size: 0.9em; }
</style>
</head>
<body>
<main>
  <h1>Paint width</h1>
  <p class="soft">18 Nov. Three base brush widths, judged by sound and by sight together. Under your rule the picture is
    true to the sound: the look and the map Scan reads are the same strokes, in the same places and at the same widths.
    So a wider brush is wider for the sound too. Neighbouring notes then share more paint, and a note&rsquo;s tone takes
    on its register.</p>

  <div class="pick">
    <p><b>Your choice, 19 Nov: Medium (2&times;) is the default.</b> It reads as a brush rather than a wire, and each
      register keeps its own paint: in the two melodies a note&rsquo;s ring shares about a fifth of its paint with the
      ring a fifth away (0.22), against 0.06 today and about half wide.</p>
    <p><b>Motion now grows with the width.</b> Its full scale is today&rsquo;s times the base width, since the paint a
      stroke lays per length grows with its width. Measured over the four phrases, medium&rsquo;s Motion medians come
      back to today&rsquo;s: the pad 0.38 against 0.38, Crossed hands 0.15 against 0.15, the run 0.68 against 0.68 and
      the chords 0.56 against 0.52. Before the change medium read 0.75, 0.28, 0.94 and 1.00, and wide pinned at full on
      three phrases. Wide now reads 0.56 to 0.75.</p>
  </div>

  <h2>What else changed: the beads</h2>
  <p>The beads were not the frame rate. The core lays its strokes sixty times a second of audio time, 1.2 to 1.9 px
    apart on the 768 canvas, against a brush 13 px across. The look painted from the same strokes at 60 and at 4
    frames a second is the same picture (below). They came from the brushwork. Each note was a brush of its own, so a
    run of short notes was a row of dabs, each with a wide head where a hard strike jumped the width up for 60 ms.</p>
  <p>Now a melody is one stroke when the sound joins it (your rule, 19 Nov). A hand&rsquo;s next note struck alone
    takes up the last note&rsquo;s brush when that note still sounds at the strike, or when the sustain pedal is down.
    The brush is dipped again, and glides to the new pitch over 40 ms. A chord&rsquo;s notes stay strokes of their
    own. A strike presses the brush as the study&rsquo;s did, rising and falling smoothly.</p>
  <div class="pair">
    <figure><img src="pictures/run-today-look.jpg" width="768" height="768" loading="lazy" alt="The run painted at 60 frames a second">
      <figcaption>The run, today&rsquo;s width, the look painted at 60 frames a second.</figcaption></figure>
    <figure><img src="pictures/run-today-look-4fps.jpg" width="768" height="768" loading="lazy" alt="The same strokes painted at 4 frames a second">
      <figcaption>The same strokes painted at 4 frames a second: the same picture.</figcaption></figure>
  </div>

  <h2>Joined or separate, heard</h2>
  <p><b>The rule.</b> A note struck alone goes on with the last note&rsquo;s stroke when that note&rsquo;s own amp
    envelope, as the instrument plays it, is still above <b>&minus;24 dB of the peak it reached</b>. That holds whether
    its key is down or it is in its release. A note also joins whenever the sustain pedal is down. The core decides,
    so the map and the look agree. <b>Separate</b> below is step 2&rsquo;s rule, where every note is a stroke of its
    own.</p>
  <p><b>Why &minus;24 dB.</b> It sits in the middle of the range you gave. The sounds fall far apart at the next
    strike, so the line can be anywhere in that range without changing any of these renders. At a note a second the
    pad&rsquo;s last note is at about &minus;3 dB, the Tine piano&rsquo;s at about &minus;14 dB, and the pluck&rsquo;s
    is silent. Even three seconds apart a pad note is at &minus;6 dB, and joins. A Tine piano note is at &minus;18 dB
    two seconds on, joining, and at &minus;23 dB three seconds on, right at the line. At &minus;20 dB the Tine
    piano&rsquo;s slow melodies would break a second sooner; at &minus;30 dB a fading note would hold its stroke for
    longer than you hear it in a texture.</p>
  <p><b>The pluck under the pedal is one stroke, but you still see marks.</b> The pedal joins the stroke: one brush,
    carrying its colour on. The pluck still dies to silence within a quarter second with the pedal down, though, and a
    brush lays no paint where there is no sound. So the picture is nine marks of one stroke, true to what you hear.
    Keeping the brush on the canvas while the pedal is down, laying paint through the silence, is the pedal&rsquo;s
    item in step 3 (the controllers on the brush). It isn&rsquo;t made here.</p>
{{JOINED}}

  <h2>The look</h2>
  <p>The look now uses the core&rsquo;s brush footprint exactly, cell for cell. Before, it drew the tip shorter, which
    laid about half the paint per length and made the strokes faint wires. Within that footprint it is finer than the
    map and is the look only. Each of the core&rsquo;s eight bristle groups is drawn as four bristles, loaded unevenly,
    which makes the streaks. The outer bristles are ragged. Wet paint a brush crosses is ploughed into a bank past its
    flank, and the map holds that bank too. A dry brush catches on the weave, wet paint glistens, and the raking light
    raises the ridges. The images are the page&rsquo;s own paint view, rendered in headless Chromium&rsquo;s software
    WebGL 2. It was fed the core&rsquo;s strokes a sixtieth of a second at a time, as the live face is served them, so
    the pacing is the instrument&rsquo;s.</p>

  <h2>How to read the numbers</h2>
  <p><b>Centroid</b> is the brightness of what Scan reads, in harmonics: 1 is a sine, about 2 is mellow and 3 is reedy.
    <b>Movement</b> is how much it changes a sixtieth of a second to the next; under 0.005 is a steady tone.
    <b>Shared</b> is how much paint a note&rsquo;s ring has in common with the ring a semitone or a fifth away (the sum of
    the smaller over the sum of the larger, so 1 is the same paint and 0 is none). It is the median over every note
    played and every moment its ring had paint. Each ring reads a cell and a half across, about three semitones, so
    even today&rsquo;s neighbours a semitone apart share most of their paint. The fifth is where the widths differ.
    <b>Covered</b> is the share of the canvas with paint; past 35% the painting counts as running away. The map
    pictures show thickness in grey and wet paint in blue.</p>

{{SECTIONS}}

  <h2>What it costs, and what the map holds</h2>
  <p>The map stays 128 cells square. It holds every width here: a held note&rsquo;s paint across its ring reads within
    4% of the brush&rsquo;s own width, and a cell&rsquo;s own size is a twelfth of a cell squared on top. A wider brush
    needs less resolution, not more, so 256 was not needed. Cost doesn&rsquo;t change measurably with width: the ring
    reads are most of painting&rsquo;s cost, and they don&rsquo;t depend on it.</p>
  <div class="scroll"><table>
    <thead><tr><th></th><th>Native, trace (s a s)</th><th>Native, painting</th><th>WebAssembly, trace (ms a block)</th>
      <th>WebAssembly, painting</th><th>Map spread (cells)</th><th>Brush&rsquo;s own</th></tr></thead>
    <tbody>{{COST}}</tbody></table></div>
  <p class="soft">Native: a chord of sixteen held, seconds of one core a second, best of three. WebAssembly: the page&rsquo;s
    own module in Chromium, a chord of eight, milliseconds a block of 128 (2.67 ms at 48 kHz), best of three. These are
    single runs on a shared machine, so differences of a few hundredths are noise.</p>
  <p class="soft">Made by <code>render.py</code> (with <code>render.cpp</code>, the core playing the phrase),
    <code>cost.py</code> and <code>page.py</code>, beside this page. Every number is in <code>results.json</code>. The
    width is <code>PaintParams::width</code>, an internal parameter; testing still paints at today&rsquo;s.</p>
</main>
</body>
</html>
"""

if __name__ == "__main__":
    main()
