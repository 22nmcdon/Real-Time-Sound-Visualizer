"""The listening page for painting, step 1: index.html beside this file, made
from results.json, which render.py writes. Re-run after render.py.

    python3 web/docs/listening/painting-step1/page.py
"""
import html, json, os

HERE = os.path.dirname(os.path.abspath(__file__))

PHRASES = [
    ("pad", "Held pad", "Slow pad, Breathing, Picture amount 100: a Cmaj9 voicing (C3 G3 D4 E4 B4) held 9 s, 12 s in all. "
     "Held past one turn, so its strokes come back round over their own start."),
    ("crossed", "Crossed hands", "The owner's own setup code, Picture amount 47: the left hand's chords under a right-hand run "
     "that quickens, then two grace notes after a breath, 15.5 s."),
    ("run", "Fast run", "Tine piano, Settled, Picture amount 0 and Scan at 50: C major from C4 to C5 and back three "
     "times at nine notes a second, swelling to each top, 7.2 s."),
    ("chords", "Chord change", "Drawbar organ, Settled, Picture amount 0 and Scan at 14: Dm7 G7 Cmaj7 Am7, 2.5 s each, "
     "11.6 s."),
]
VERSIONS = [("trace", "Trace", "As the instrument ships: Scan and the Picture amount read the trace."),
            ("paint", "Paint", "The owner's drying: thin paint 2 s, a thick stroke 6 s."),
            ("slow", "Paint, slow drying", "Three times slower: 6 s and 18 s, so a thick stroke is still wet a turn later.")]


def ear(row, trace):
    """A sentence on what the numbers mean to the ear, against the trace."""
    s, t = row["scan"], trace["scan"]
    bright = s["centroid"] / t["centroid"]
    parts = []
    if bright > 1.25: parts.append("brighter than the trace (centroid %.2f against %.2f)" % (s["centroid"], t["centroid"]))
    elif bright < 0.8: parts.append("duller than the trace (centroid %.2f against %.2f)" % (s["centroid"], t["centroid"]))
    else: parts.append("about as bright as the trace (centroid %.2f against %.2f)" % (s["centroid"], t["centroid"]))
    if s["movement"] < 0.6 * t["movement"]: parts.append("steadier note by note (movement %.4f against %.4f)" % (s["movement"], t["movement"]))
    elif s["movement"] > 1.6 * t["movement"]: parts.append("moving more (movement %.4f against %.4f)" % (s["movement"], t["movement"]))
    else: parts.append("moving about as much (movement %.4f against %.4f)" % (s["movement"], t["movement"]))
    return "Scan's tone is " + " and ".join(parts) + "."


def measures_row(key, label, row, trace):
    s = row["scan"]
    land = ("%d / %d / %d" % (round(100 * row["into_wet"]), round(100 * row["onto_dry"]), round(100 * row["onto_bare"]))
            if "into_wet" in row else "&ndash;")
    return ("<tr><th>%s</th><td>%.2f <span class=soft>(%.2f&ndash;%.2f)</span></td><td>%.4f</td><td>%.1f%%</td>"
            "<td>%.2f</td><td>%.2f</td><td>%.2f</td><td>%s</td></tr>"
            % (label, s["centroid"], s["centroid_p10"], s["centroid_p90"], s["movement"], 100 * s["high"],
               row["glow"], row["motion"], row["memory"], land))


def main():
    res = json.load(open(os.path.join(HERE, "results.json")))
    out = []
    for key, name, about in PHRASES:
        r = res[key]
        rows = "\n".join(measures_row(v, label, r[v], r["trace"]) for v, label, _ in VERSIONS)
        audio = "\n".join('<div class=ver><span class=tag>%s</span><audio controls preload="none" src="audio/%s-%s.mp3"></audio>'
                          '<p class=soft>%s</p></div>' % (label, key, v, html.escape(why)) for v, label, why in VERSIONS)
        pics = []
        for v, label, _ in VERSIONS[1:]:
            times = ", ".join("%.1f" % t for t in r[v]["strip_times"])
            pics.append('<figure><img src="pictures/%s-%s.png" width="384" height="384" alt="The paint map at the end of the %s, %s">'
                        '<figcaption>%s, at the phrase&rsquo;s end. %s</figcaption>'
                        '<img class=strip src="pictures/%s-%s-strip.png" alt="Eight moments of the %s painted, %s">'
                        '<figcaption>Eight moments, at %s s.</figcaption></figure>'
                        % (key, v, name.lower(), label.lower(), label, html.escape(ear(r[v], r["trace"])), key, v, name.lower(),
                           label.lower(), times))
        out.append('<section><h2>%s</h2><p class=soft>%s</p><div class=vers>%s</div><div class=pics>%s</div>'
                   '<div class=scroll><table><thead><tr><th></th><th>Centroid <span class=soft>(p10&ndash;p90)</span></th>'
                   '<th>Movement</th><th>Above the 8th</th><th>Glow</th><th>Motion</th><th>Memory</th>'
                   '<th>Into wet / onto dry / bare, %%</th></tr></thead><tbody>%s</tbody></table></div></section>'
                   % (name, html.escape(about), audio, "".join(pics), rows))
    cost = ", ".join("%s %+d%%" % (name.lower(), round(100 * (res[key]["paint"]["realtime"] / res[key]["trace"]["realtime"] - 1)))
                     for key, name, _ in PHRASES)
    page = TEMPLATE.replace("{{SECTIONS}}", "\n".join(out)).replace("{{COST}}", cost)
    with open(os.path.join(HERE, "index.html"), "w") as f: f.write(page)


TEMPLATE = """<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Painting, step 1</title>
<!-- Painting, step 1 (web/docs/painting-design.md): the core paints, and Scan
     and the Picture amount read the paint. The study's four phrases rendered
     offline by the core, on the trace and painting with two dryings, for the
     owner to judge by ear before anything is live. Made by page.py from
     results.json, which render.py writes with the audio and the pictures. -->
<style>
  :root { --cream: #faf6f0; --paper: #fffcf7; --charcoal: #241f1d; --text: #3a332f; --text-soft: #6b615a;
          --line: #e4d9cc; --gold: #b08d57; --slate: #5c6488; }
  body { background: var(--cream); color: var(--text); font: 16px/1.5 system-ui, sans-serif; margin: 0; padding: 24px 16px; }
  main { max-width: 1040px; margin: 0 auto; }
  h1 { color: var(--charcoal); font-size: 1.6rem; margin: 0 0 4px; }
  h2 { color: var(--charcoal); font-size: 1.2rem; margin: 36px 0 6px; }
  p { margin: 8px 0; }
  .soft { color: var(--text-soft); }
  .vers { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 12px; margin: 12px 0; }
  .ver { background: var(--paper); border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; }
  .ver p { font-size: 0.85rem; margin: 6px 0 0; }
  .tag { font-size: 0.75rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--gold); display: block; margin-bottom: 6px; }
  audio { width: 100%; height: 32px; }
  .pics { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }
  figure { margin: 0; background: var(--paper); border: 1px solid var(--line); border-radius: 10px; padding: 12px; }
  figure img { display: block; max-width: 100%; height: auto; margin: 0 auto; image-rendering: pixelated; }
  figure img.strip { margin-top: 12px; }
  figcaption { font-size: 0.85rem; color: var(--text-soft); margin-top: 6px; }
  table { border-collapse: collapse; width: 100%; background: var(--paper); border: 1px solid var(--line); margin-top: 12px; }
  th, td { padding: 7px 9px; border-bottom: 1px solid var(--line); text-align: left; font-size: 0.9rem; }
  th { font-weight: 600; color: var(--charcoal); }
  .scroll { overflow-x: auto; }
  .key { display: inline-block; width: 0.9em; height: 0.9em; vertical-align: -0.1em; border-radius: 2px; }
  code { font-size: 0.9em; }
</style>
</head>
<body>
<main>
  <h1>Painting, step 1</h1>
  <p class="soft">18 Nov. The core now paints: from each voice it decides where a stroke goes, how wide, how wet and
    which hand, and keeps a map of how much paint is where. Here Scan and the Picture amount read that map in place
    of the trace. Nothing on the page has changed yet; these are offline renders by the instrument&rsquo;s own core, of
    the painting study&rsquo;s four phrases, for you to judge by ear before step 2 puts it live.</p>

  <h2>What you are hearing</h2>
  <p><b>The canvas is a record.</b> Time goes clockwise from the top, one turn in 8 s, and pitch goes outward:
    A0 a third of the way out, C8 at the edge, so a held note is an arc at its own radius and a chord is concentric arcs.
    <b>Each note reads the ring at its own pitch</b> and plays a table of its own, so its tone is the paint in its
    own register. Scan reads thickness, never colour, and wet paint reads 1.4 times as strong as dry. The paint fades
    by a half-life of 16 s, two turns.</p>
  <p><b>The Picture amount&rsquo;s three reads come off the paint.</b> Glow is wet coverage, Motion is paint being
    laid, and Memory is new paint landing on old. They go through the picture stage as the trace&rsquo;s do, so
    Responds to, Rise and Fall and Swell work as now. The Tine piano and the Drawbar organ are Settled presets at
    Picture amount 0, so there you hear Scan alone. The Slow pad (100) and Crossed hands (47) hear the reads too.</p>
  <p><b>Two dryings.</b> Yours: thin paint falls to a tenth wet in 2 s and a thick stroke in 6 s, smoothly by
    thickness. Beside it is drying three times slower (6 s and 18 s), chosen because it is the setting that crosses
    the turn: a thick stroke is still wet when the brush comes round 8 s later, so a held note merges into its own
    start rather than laying over it dry. Through Scan the two differ only a little, since wet paint reads only 1.4
    times dry. Where the Picture amount is up, the slower drying doubles Glow on Crossed hands (0.17 to 0.33) and
    lifts it by half on the pad, which is the difference to listen for. A faster drying (0.5 s and 1.5 s) was rendered
    too and moved Glow as far the other way, but you had already asked for slower than the study&rsquo;s 1.2 s.</p>
  <p class="soft">In the pictures, thickness is grey (a thick stroke near black) and wet paint is blue over it, as far
    as it is wet. Ink is the look only and never reaches the sound, so it is not drawn here.</p>

  <h2>What the numbers mean</h2>
  <p><b>Centroid</b> is the brightness of the table Scan reads, in harmonics. A sine is 1, around 2 is a mellow,
    hollow tone and 3 is reedier. The bracket is the tenth and ninetieth percentile: how far it ranges.
    <b>Movement</b> is how much the table changes from one sixtieth of a second to the next, from nought (still) to
    one (replaced). Under about 0.005 you hear a steady tone; 0.02 and up shimmers or shifts. <b>Above the 8th</b> is
    the share of energy past the eighth harmonic, which is harsh when large. <b>Glow</b>, <b>Motion</b> and
    <b>Memory</b> are the stage&rsquo;s medians, what the Picture amount pushes with. The last column is where the paint
    landed: into wet paint (merging), onto dry (layering) or on bare canvas. Painting reads one table a note, so its
    numbers are over every sounding note; the trace reads one a hand.</p>

{{SECTIONS}}

  <h2>What it costs</h2>
  <p>A held chord of sixteen voices: the instrument takes 0.168 s of one core for each second of audio on the trace,
    and 0.185 s painting (best of three, natively, on the cloud machine these were made on). That is about 0.35
    microseconds a sample more, under 2 per cent of a core. Over these phrases, against the trace: {{COST}}, each one run, so within
    the run-to-run noise of a shared machine. The painter runs once a picture frame
    (sixty a second), and the voices&rsquo; own tables cost one ring read and one table each, a frame.</p>
  <p class="soft">Made by <code>render.py</code> (and <code>render.cpp</code>, the core playing the script) and then
    <code>page.py</code>, beside this page; every number is in <code>results.json</code>. The audio is MP3 at 64 kbps.</p>
</main>
</body>
</html>
"""

if __name__ == "__main__":
    main()
