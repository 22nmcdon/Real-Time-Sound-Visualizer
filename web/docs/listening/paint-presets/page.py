"""The listening page for the paint presets: index.html beside this file, made
from candidates.py, measured.json (measure.py) and results.json (render.py).
Re-run after either.

    python3 web/docs/listening/paint-presets/page.py
"""
import html, importlib.util, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("candidates", os.path.join(HERE, "candidates.py"))
cand = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cand)

PLAYS = {
    "Tines in wet paint": "A sixteen-note phrase in A minor, half a second a note, eight seconds long - one turn of the "
                          "canvas - played three times, so each pass lands where the last one painted.",
    "Drying pad": "One chord, A minor, held four and a half seconds three times over, five seconds of rest while the paint "
                  "dries, and the same chord again. The same notes every time, so what changes is what they land on.",
    "Palette knife organ": "A fifth, A3 and E4, held: the mod wheel brought up from rest over two seconds (4 s), a quick "
                           "bend up a fourth and back (6 s), a slow bend down and back (9 s), the wheel let down (12 s); "
                           "then the same fifth struck again plain at 15 s, over what was painted.",
    "Spattered mallets": "C E G C B G E D, half a second a note, three times: soft (velocity 50); every other note struck "
                         "hard (127); soft again, over what the hard notes threw.",
}
WHAT = {
    "Tines in wet paint": "The only changes from the Tine piano are the screen (Paint), Scan at 70 where it is 50, and "
                          "the painting's Persistence at 32 s to half, so four passes of the phrase are still on the "
                          "canvas.",
    "Drying pad": "The Slow pad with two changes: the screen in Paint, and the painting's Persistence short, 8 s to half, "
                  "so a rest clears the canvas. Everything else is the Slow pad's, the Picture amount at full included.",
    "Palette knife organ": "From the Drawbar organ: Paint, Scan at 40 where it is 14, the wheel given to nothing in "
                           "Expression (Off) so in Paint it only loads the brush, the bend at five semitones, and the "
                           "painting's Persistence at 24 s. The Picture amount stays at nought: what moves is Scan "
                           "reading the painting.",
    "Spattered mallets": "Not a bank preset's: a sine with FM at 4:1 whose index follows the note's envelope, a short "
                         "decay, Strike at 100 (so drops start at a velocity of about 45) and Scan at 70; the painting's "
                         "Persistence 40 s. Nearest in the bank is the Tine piano, the other struck FM sound. What Paint adds here is mostly "
                         "to see: struck hard, it is brighter in Paint and on the trace alike (2,980 against 2,028 Hz; "
                         "2,610 against 1,823 with the same setup on the trace). The soft pass after the hard one is not "
                         "coloured by it: it is 0.114 from the first soft pass, and the same phrase played soft all three "
                         "times is 0.129 - the change any repeat makes on the canvas, measured with the middle pass soft.",
}


def esc(s): return html.escape(s, quote=True)


def chart(series_a, series_b, key, label, top=None):
    """One small line chart of a read over the performance: the candidate (Paint) solid, the bank preset dashed."""
    w, h, pad = 560, 120, 26
    ta, va = series_a["t"], series_a[key]
    tb, vb = series_b["t"], series_b[key]
    tmax = max(ta[-1] if ta else 1, tb[-1] if tb else 1)
    vmax = top or max([1e-6] + va + vb) * 1.08
    def path(ts, vs):
        if not ts: return ""
        pts = ["%.1f,%.1f" % (pad + (w - pad - 6) * t / tmax, h - 18 - (h - 30) * min(v, vmax) / vmax) for t, v in zip(ts, vs)]
        return "M" + " L".join(pts)
    ticks = "".join('<text x="%.1f" y="%d" class=ax>%d s</text>' % (pad + (w - pad - 6) * s / tmax, h - 4, s)
                    for s in range(0, int(tmax) + 1, 4))
    return ('<figure class=chart><figcaption>%s</figcaption><svg viewBox="0 0 %d %d" role="img" aria-label="%s over the '
            'performance, Paint and the bank preset">'
            '<line x1="%d" y1="%d" x2="%d" y2="%d" class=base />'
            '<text x="2" y="16" class=ax>%.2g</text><text x="2" y="%d" class=ax>0</text>'
            '<path d="%s" class=bank /><path d="%s" class=paint />%s</svg></figure>'
            % (label, w, h, label, pad, h - 18, w - 6, h - 18, vmax, h - 18, path(tb, vb), path(ta, va), ticks))


def heading_table(m):
    rows = ""
    for p in m["probes"]:
        rows += ("<tr><td>%s</td><td>%s</td><td>%s</td><td>%.4f</td><td><b>%s</b></td></tr>"
                 % ("C4" if p["notes"] == [60] else p["notes"], " / ".join("%.3f" % v for v in p["early"]),
                    " / ".join("%.3f" % v for v in p["late"]), p["after_rms"], p["verdict"]))
    return rows


def section_table(paint, bank):
    rows = ""
    for a, b in zip(paint["sections"], bank["sections"]):
        f = lambda v, d=2: ("%.*f" % (d, v)) if v is not None else "&ndash;"
        rows += ("<tr><td>%s <span class=soft>%.1f&ndash;%.1f s</span></td><td>%s <span class=soft>/ %s</span></td>"
                 "<td>%d <span class=soft>/ %d</span></td><td>%s <span class=soft>/ %s</span></td><td>%s</td></tr>"
                 % (esc(a["label"]), a["t0"], a["t1"], f(a["changed"], 3) if a["changed"] else "&ndash;",
                    f(b["changed"], 3) if b["changed"] else "&ndash;", a["hz"], b["hz"], f(a["centroid"]), f(b["centroid"]),
                    "%.0f, %.0f%% wet" % (a["paint"], 100 * a["wet"]) if "paint" in a else ""))
    return rows


def slug(name): return name.lower().replace(" ", "-")


def main():
    measured = json.load(open(os.path.join(HERE, "measured.json")))
    res = json.load(open(os.path.join(HERE, "results.json")))
    out = []
    for name, c in cand.ALL.items():
        m, bm, r = measured[name], measured["bank: " + c["nearest"]], res[name]
        verdict = m["probes"][0]["verdict"]
        listen, watch = c["lines"]
        s = slug(name)
        moments = "".join(
            '<div class=moment><span class=soft>%.1f s</span>'
            '<img src="pictures/%s-look-%d.jpg" width="512" height="512" loading="lazy" alt="The painting at %.1f s">'
            '<img class=map src="pictures/%s-map-%d.png" width="256" height="256" loading="lazy" alt="The map Scan reads at %.1f s"></div>'
            % (t, s, k, t, s, k, t) for k, t in enumerate(c["moments"]))
        out.append(f"""
<section id="{s}">
  <h2>{esc(name)} <span class="badge">{esc(verdict)}</span></h2>
  <p class="lines"><b>Listen for</b> {esc(listen)}<br><b>Watch for</b> {esc(watch)}</p>
  <p>{esc(c["about"])}</p>
  <p class="soft">{esc(WHAT[name])}</p>
  <p class="soft"><b>Played:</b> {esc(PLAYS[name])}</p>
  <div class="pair">
    <div class="col"><span class="tag">{esc(name)} <span class="soft">Paint</span></span>
      <audio controls preload="none" src="audio/{s}-paint.mp3"></audio></div>
    <div class="col"><span class="tag">{esc(c["nearest"])} <span class="soft">the bank's, as shipped, on the trace</span></span>
      <audio controls preload="none" src="audio/{s}-bank.mp3"></audio></div>
  </div>
  <div class="moments">{moments}</div>
  {chart(r["paint"]["centroid"], r["bank"]["centroid"], "centroid", "What Scan reads over the performance: its brightness in harmonics (1 a sine)")}
  <div class="wrap"><table class="sections"><tr><th>Section</th><th>Heard: changed from the first <span class=soft>/ bank</span></th>
    <th>Heard: brightness, Hz <span class=soft>/ bank</span></th><th>Scan reads <span class=soft>/ bank</span></th><th>Paint on the canvas</th></tr>
    {section_table(r["paint"], r["bank"])}</table></div>
  <details><summary>Its heading, measured as <code>honestytest.py</code> measures the bank</summary>
    <div class="wrap"><table><tr><th>Probe</th><th>Early, five moments</th><th>Late</th><th>After, RMS</th><th>Verdict</th></tr>
      {heading_table(m)}</table></div>
    <p class="soft">The limiter on the suite's four-note chord: {m["limiter"]:.1f} dB (the bound is six).
      {esc(c["nearest"])}, as shipped, on the same probe: {esc(bm["probes"][0]["verdict"])}, late
      {" / ".join("%.3f" % v for v in bm["probes"][0]["late"])}.</p></details>
  <div class="code"><span class="soft">Setup code - paste it into Browse &rsaquo; the code box on the testing site and press Paste:</span>
    <textarea readonly rows="3" aria-label="Setup code for {esc(name)}">{esc(m["code"])}</textarea>
    <button type="button" class="copy">Copy</button></div>
</section>""")
    page = TEMPLATE.replace("{{SECTIONS}}", "\n".join(out))
    with open(os.path.join(HERE, "index.html"), "w") as f: f.write(page)


TEMPLATE = """<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Paint presets</title>
<!-- Four candidate presets made for Paint, each heard through a short performance
     beside the nearest bank preset as it ships. None is in the bank: the owner chooses.
     Made by page.py from candidates.py, measured.json (measure.py) and results.json
     (render.py), which writes the audio and the pictures. -->
<style>
  :root { --cream: #faf6f0; --paper: #fffcf7; --charcoal: #241f1d; --text: #3a332f; --text-soft: #6b615a;
          --line: #e4d9cc; --gold: #b08d57; --slate: #4a5a6a; }
  body { background: var(--cream); color: var(--text); font: 16px/1.5 system-ui, sans-serif; margin: 0; padding: 24px 16px; }
  main { max-width: 1180px; margin: 0 auto; }
  h1 { color: var(--charcoal); font-size: 1.6rem; margin: 0 0 4px; }
  h2 { color: var(--charcoal); font-size: 1.3rem; margin: 44px 0 6px; }
  p { margin: 8px 0; }
  .soft { color: var(--text-soft); }
  .badge { font-size: 0.75rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--gold);
           border: 1px solid var(--gold); border-radius: 999px; padding: 1px 8px; vertical-align: middle; }
  .lines { background: var(--paper); border-left: 3px solid var(--gold); padding: 6px 12px; }
  .pair { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; margin-top: 12px; }
  .col { background: var(--paper); border: 1px solid var(--line); border-radius: 10px; padding: 12px; min-width: 0; }
  .tag { font-size: 0.8rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--gold); display: block; margin-bottom: 6px; }
  .tag .soft { text-transform: none; letter-spacing: 0; }
  audio { width: 100%; height: 32px; }
  .moments { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-top: 14px; }
  .moment { background: var(--paper); border: 1px solid var(--line); border-radius: 10px; padding: 8px; min-width: 0; }
  .moment img { display: block; width: 100%; height: auto; margin-top: 6px; border-radius: 6px; }
  .moment img.map { width: 50%; image-rendering: pixelated; }
  .chart { margin: 14px 0 0; }
  .chart figcaption { font-size: 0.85rem; color: var(--text-soft); }
  .chart svg { width: 100%; height: auto; display: block; background: var(--paper); border: 1px solid var(--line); border-radius: 8px; }
  .chart .base { stroke: var(--line); }
  .chart .paint { fill: none; stroke: var(--charcoal); stroke-width: 1.6; }
  .chart .bank { fill: none; stroke: var(--gold); stroke-width: 1.4; stroke-dasharray: 4 3; }
  .chart .ax { font-size: 10px; fill: var(--text-soft); }
  .key span { display: inline-block; width: 22px; border-top: 2px solid var(--charcoal); vertical-align: middle; margin: 0 4px 0 10px; }
  .key span.bank { border-top: 2px dashed var(--gold); }
  .wrap { overflow-x: auto; }
  table { border-collapse: collapse; width: 100%; margin-top: 12px; }
  th, td { padding: 4px 6px; border-bottom: 1px solid var(--line); text-align: left; font-size: 0.85rem; }
  th { font-weight: 600; color: var(--charcoal); }
  details { margin-top: 12px; }
  summary { cursor: pointer; color: var(--charcoal); }
  .code { margin-top: 14px; }
  .code textarea { display: block; width: 100%; box-sizing: border-box; font: 12px/1.4 ui-monospace, monospace;
                   background: var(--paper); color: var(--text); border: 1px solid var(--line); border-radius: 6px;
                   padding: 6px; margin-top: 4px; resize: vertical; }
  .code button { margin-top: 6px; font: inherit; font-size: 0.85rem; background: var(--paper); color: var(--charcoal);
                 border: 1px solid var(--gold); border-radius: 6px; padding: 3px 12px; cursor: pointer; }
  .ask { background: var(--paper); border: 1px solid var(--gold); border-radius: 10px; padding: 12px 16px; margin-top: 16px; }
  code { font-size: 0.9em; }
</style>
</head>
<body>
<main>
  <h1>Paint presets</h1>
  <p class="soft">22 Nov. You said of painting that a preset that works well with it would be one of its true tests.
    These are four candidates for you to hear and see. <b>None of them is in the bank</b>; nothing is added until you
    choose.</p>
  <p class="soft">Each is meant to be at its best in Paint, where Scan reads the painting, so the sound remembers what
    was played and changes as the paint builds, dries and is pushed about. Each is heard through a short performance
    made for it, and the same performance on the nearest bank preset as it ships, on the trace, so you hear what Paint
    adds. The pictures are the painting at moments through the performance - the page&rsquo;s own look, fed the
    core&rsquo;s strokes a sixtieth of a second at a time - each with the map Scan reads under it (thickness grey, wet
    paint blue).</p>
  <p class="soft">Each heading was measured as <code>honestytest.py</code> measures the bank&rsquo;s: the page loads the
    preset as you would, and the core plays C4 held ten seconds from five moments after the load. Two are Settled and two
    Breathing, as shipped.</p>

  <div class="ask">
    <p><b>Can a preset switch the screen to Paint?</b> Yes, today, with nothing changed. What the screen draws is a setup
      field since painting&rsquo;s step 2 (<code>screenDraws</code>, with <code>paintPersistence</code> beside it), so a
      preset or a code that names Paint loads in Paint: the page switches the display to Paint as it restores the setup,
      and the core follows the field at its next picture frame. Each code below carries it. The other side of that is
      already true of the bank too: every preset that does not name it draws the trace, so loading one of today&rsquo;s
      presets from Paint goes back to the trace.</p>
    <p><b>Things to decide.</b></p>
    <p><b>Which, if any, go in the bank, and under which heading.</b> Each would go under the heading it measures as;
      adding one is the bank&rsquo;s usual steps (its lines, <code>write_presets.py</code>, its thumbnail by
      <code>write_figures.py</code>).</p>
    <p><b>A preset&rsquo;s thumbnail is the trace&rsquo;s figure.</b> <code>write_figures.py</code> draws each card from
      the instrument&rsquo;s figure, so a Paint preset&rsquo;s card would show a ring of the trace rather than a painting.
      Whether a painted thumbnail is wanted is yours.</p>
    <p><b>Painting can change a sound&rsquo;s heading.</b> The Drawbar organ is Settled on the trace; painted, a held
      note keeps changing as its own arc comes round the turn (0.024 late at its own Scan of 14, Breathing&rsquo;s floor
      0.019), so the Palette knife organ, at Scan 40, is Breathing. The Tine piano and the Slow pad keep theirs painted.
      Under your rule of 17 Nov that is not a fault of the organ preset, since Paint is not in it; but a preset that
      ships in Paint answers to its heading in Paint, as these were measured.</p>
    <p><b>The knife at a wider bend.</b> The Palette knife organ&rsquo;s bend is a fourth, so a quick bend pushes the
      paint further than the step 3 page showed at a whole tone. The thin, patchy film where the blade starts then
      covers a wide patch and draws as squares a map cell across, in the map and the look alike (the second and third
      pictures, at the right). At two semitones it is the small film you saw. Whether to keep the fourth, or to smooth
      the film when the push is large, is yours.</p>
    <p><b>How each was measured, heard.</b> Each performance is cut into sections, and each section&rsquo;s sound is read
      as <code>honestytest.py</code> reads a quarter second - forty-eight bands a fifth of an octave wide, loudness
      taken out - so <i>changed from the first</i> is how far a section is from the first section on the same scale as
      the suite&rsquo;s movement (a held note moving 0.019 a quarter second breathes). <i>Brightness</i> is the heard
      spectral centroid. <i>Scan reads</i> is the brightness of the table Scan reads, in harmonics (a sine is 1).</p>
  </div>

  <p class="key soft">In the charts: <span></span>the candidate, in Paint <span class="bank"></span>the nearest bank preset, on the trace</p>

{{SECTIONS}}

  <p class="soft">Made by <code>measure.py</code> (the headings and the setup codes, through the page), <code>render.py</code>
    (with <code>render.cpp</code>, the core playing each performance from the code alone, beside this page) and
    <code>page.py</code>. The candidates are in <code>candidates.py</code>; every number is in
    <code>measured.json</code> and <code>results.json</code>. The look is rendered by SwiftShader; on a real graphics
    card it is the same picture.</p>
</main>
<script>
  for (const b of document.querySelectorAll(".code button.copy")) {
    b.addEventListener("click", () => {
      const t = b.parentElement.querySelector("textarea");
      t.select();
      const done = () => { b.textContent = "Copied"; setTimeout(() => { b.textContent = "Copy"; }, 1500); };
      try {
        if (navigator.clipboard) navigator.clipboard.writeText(t.value).then(done, () => { document.execCommand("copy"); done(); });
        else { document.execCommand("copy"); done(); }
      } catch (e) { /* the text stays selected to copy by hand */ }
    });
  }
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
