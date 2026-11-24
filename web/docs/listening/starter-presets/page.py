"""The listening page for the starter presets: index.html beside this file,
made from candidates.py, measured.json (measure.py) and results.json
(render.py). Re-run after either.

    python3 web/docs/listening/starter-presets/page.py
"""
import html, importlib.util, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("candidates", os.path.join(HERE, "candidates.py"))
cand = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cand)

KIND = {"Felt piano": "clean and warm", "Plucked wire": "plucked", "Tidal glass": "evolving pad", "Round bass": "bass",
        "Mirrored hands": "two hands, layered", "Velocity brass": "the filter's sweep with Velocity"}
VIEW = {"xy": "X-Y, as it ships", "yt": "Y-T, the display switched"}


def esc(s): return html.escape(s, quote=True)


def slug(name): return name.lower().replace(" ", "-")


def heading_table(m):
    rows = ""
    for p in m["probes"]:
        rows += ("<tr><td>%s</td><td>%s</td><td>%s</td><td>%.4f</td><td><b>%s</b></td></tr>"
                 % ("C4" if p["notes"] == [60] else p["notes"], " / ".join("%.3f" % v for v in p["early"]),
                    " / ".join("%.3f" % v for v in p["late"]), p["after_rms"], p["verdict"]))
    return rows


def section_table(r):
    rows = ""
    for a in r["sections"]:
        rows += ("<tr><td>%s <span class=soft>%.1f&ndash;%.1f s</span></td><td>%d</td><td>%s</td><td>%.3f</td><td>%.1f</td></tr>"
                 % (esc(a["label"]), a["t0"], a["t1"], a["hz"], "%.3f" % a["changed"] if a["changed"] else "&ndash;",
                    a["rms"], a["peak_db"]))
    return rows


def moments(name, r):
    s, out = slug(name), ""
    for view in ("xy", "yt"):
        cells = "".join('<figure class=moment><img src="pictures/%s-%s-%d.jpg" width="467" height="467" loading="lazy" '
                        'alt="%s in %s at %.1f s"><figcaption>%.1f s</figcaption></figure>'
                        % (s, view, k, esc(name), view.upper(), t, t) for k, t in enumerate(r["moments"][view]))
        out += '<p class="tag">%s</p><div class="moments">%s</div>' % (VIEW[view], cells)
    return out


def compare(res, measured):
    rows = ""
    for name in cand.ALL:
        c4 = res["candidates"][name]["c4"]
        rows += ("<tr><td><b>%s</b></td><td>%s</td><td>%d</td><td>%.2f</td><td>%.2f</td><td>%.2f</td></tr>"
                 % (esc(name), esc(measured[name]["probes"][0]["verdict"]), c4["hz"], c4["grit"], c4["top_strike"], c4["top_held"]))
    for name, c4 in res["bank"].items():
        rows += ("<tr class=soft><td>%s <span class=soft>(bank)</span></td><td></td><td>%d</td><td>%.2f</td><td>%.2f</td><td>%.2f</td></tr>"
                 % (esc(name), c4["hz"], c4["grit"], c4["top_strike"], c4["top_held"]))
    return rows


def main():
    measured = json.load(open(os.path.join(HERE, "measured.json")))
    res = json.load(open(os.path.join(HERE, "results.json")))
    out, toc = [], []
    for name, c in cand.ALL.items():
        m, r = measured[name], res["candidates"][name]
        verdict = m["probes"][0]["verdict"]
        listen, watch = c["lines"]
        s = slug(name)
        toc.append('<li><a href="#%s">%s</a> <span class=soft>%s &middot; %s</span></li>' % (s, esc(name), esc(KIND[name]), esc(verdict)))
        out.append(f"""
<section id="{s}">
  <h2>{esc(name)} <span class="badge">{esc(verdict)}</span> <span class="kind">{esc(KIND[name])}</span></h2>
  <p class="lines"><b>Listen for</b> {esc(listen)}<br><b>Watch for</b> {esc(watch)}</p>
  <p>{esc(c["about"])}</p>
  <p><b>Try turning:</b> {esc(cand.TRY[name])}</p>
  <p class="soft"><b>Played:</b> {esc(cand.PLAYED[name])}</p>
  <div class="col"><span class="tag">{esc(name)} <span class="soft">the core playing the code below, {r["length"]:.0f} s</span></span>
    <audio controls preload="none" src="audio/{s}.mp3"></audio></div>
  {moments(name, r)}
  <div class="wrap"><table><tr><th>Section</th><th>Brightness, Hz</th><th>Changed from the first</th><th>RMS</th><th>Peak, dBFS</th></tr>
    {section_table(r)}</table></div>
  <details><summary>Its heading, measured as <code>honestytest.py</code> measures the bank</summary>
    <div class="wrap"><table><tr><th>Probe</th><th>Early, five moments</th><th>Late</th><th>After, RMS</th><th>Verdict</th></tr>
      {heading_table(m)}</table></div>
    <p class="soft">The limiter on the suite's four-note chord: {m["limiter"]:.1f} dB (the bound is six).</p></details>
  <div class="code"><span class="soft">Setup code - on the testing site, Browse, paste it into the code box and press Paste:</span>
    <textarea readonly rows="3" aria-label="Setup code for {esc(name)}">{esc(m["code"])}</textarea>
    <button type="button" class="copy">Copy</button></div>
</section>""")
    counts = {}
    for name in cand.ALL: counts[measured[name]["probes"][0]["verdict"]] = counts.get(measured[name]["probes"][0]["verdict"], 0) + 1
    page = (TEMPLATE.replace("{{SECTIONS}}", "\n".join(out)).replace("{{TOC}}", "\n".join(toc))
            .replace("{{COMPARE}}", compare(res, measured))
            .replace("{{COUNTS}}", " and ".join("%d %s" % (v, k) for k, v in sorted(counts.items(), reverse=True))))
    with open(os.path.join(HERE, "index.html"), "w") as f: f.write(page)


TEMPLATE = """<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Starter presets</title>
<!-- Six candidate starter presets for the first release, each heard through a short
     performance and seen on the page. None is in the bank: the owner chooses.
     Made by page.py from candidates.py, measured.json (measure.py) and results.json
     (render.py), which writes the audio and the pictures. -->
<style>
  :root { --cream: #faf6f0; --paper: #fffcf7; --charcoal: #241f1d; --text: #3a332f; --text-soft: #6b615a;
          --line: #e4d9cc; --gold: #b08d57; --slate: #4a5a6a; }
  @media (prefers-color-scheme: dark) {
    :root { --cream: #1d1a18; --paper: #262220; --charcoal: #f3ece4; --text: #e2d9cf; --text-soft: #a89c90;
            --line: #3a332f; --gold: #c9a56c; --slate: #8fa3b5; }
  }
  body { background: var(--cream); color: var(--text); font: 16px/1.5 system-ui, sans-serif; margin: 0; padding: 24px 16px; }
  main { max-width: 1180px; margin: 0 auto; }
  h1 { color: var(--charcoal); font-size: 1.6rem; margin: 0 0 4px; }
  h2 { color: var(--charcoal); font-size: 1.3rem; margin: 48px 0 6px; }
  p { margin: 8px 0; }
  a { color: var(--slate); }
  .soft { color: var(--text-soft); }
  .badge { font-size: 0.75rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--gold);
           border: 1px solid var(--gold); border-radius: 999px; padding: 1px 8px; vertical-align: middle; }
  .kind { font-size: 0.85rem; font-weight: normal; color: var(--text-soft); vertical-align: middle; }
  .lines { background: var(--paper); border-left: 3px solid var(--gold); padding: 6px 12px; }
  .col { background: var(--paper); border: 1px solid var(--line); border-radius: 10px; padding: 12px; margin-top: 12px; }
  .tag { font-size: 0.8rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--gold); display: block; margin: 14px 0 6px; }
  .col .tag { margin-top: 0; }
  .tag .soft { text-transform: none; letter-spacing: 0; }
  audio { width: 100%; height: 32px; }
  .moments { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
  .moment { background: var(--paper); border: 1px solid var(--line); border-radius: 10px; padding: 8px; margin: 0; min-width: 0; }
  .moment img { display: block; width: 100%; height: auto; border-radius: 6px; }
  .moment figcaption { font-size: 0.8rem; color: var(--text-soft); margin-top: 4px; }
  .wrap { overflow-x: auto; }
  table { border-collapse: collapse; width: 100%; margin-top: 12px; }
  th, td { padding: 4px 6px; border-bottom: 1px solid var(--line); text-align: left; font-size: 0.85rem; }
  th { font-weight: 600; color: var(--charcoal); }
  tr.soft td { color: var(--text-soft); }
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
  <h1>Starter presets</h1>
  <p class="soft">24 Nov. Six candidates for the first release, to start from and tweak. <b>None of them is in the
    bank</b>, and nothing in the page, the core or the bank was changed; nothing is added until you choose. None draws
    Paint, so each works on the stable site as well as on testing.</p>
  <p class="soft">You hear the bank converging on one gritty sound, so these were made to differ from it and from each
    other: one clean and warm, one plucked, one evolving pad, one bass, one for two hands and one that shows the
    filter's new sweep with Velocity. Each uses the EQ and one or two modules of the rack where the sound wants them,
    never all at once. In every one, the screen moves the sound: Scan reads the figure back (each key strikes it), and
    in the two Breathing ones the picture keeps pushing the sound while a chord is held.</p>

  <ul>
{{TOC}}
  </ul>

  <div class="ask">
    <p><b>How they were measured.</b> Each heading was measured as <code>honestytest.py</code> measures the bank: the
      page loads the candidate as you would load a preset, hands over the setup code it sends the instrument, and the
      core plays C4 held ten seconds from five moments after the load, judged by its worst moment. As shipped,
      {{COUNTS}}. Every field each candidate names came back out of the setup the page made, as
      <code>presettest.py</code> requires of the bank.</p>
    <p><b>How they were heard and seen.</b> The audio is the core (<code>render_cpp</code>) playing the performance
      written for each from its setup code alone, at the instrument's own level: nothing normalised, so loudness compares
      across them (every peak is under -3 dBFS). The pictures are the page itself, the performance played into it in real
      time as a keyboard's MIDI, at moments through it; the time under each is when it was taken. Y-T is the same setup
      with the display switched to Y-T, played again. Scan reads what the screen shows, so in Y-T the sound is a little
      different from what you hear here; it ships in X-Y.</p>
    <p><b>Against the bank.</b> One C4 at velocity 100, held three seconds from the load. <i>Brightness</i> is the heard
      spectral centroid two and a half seconds in. <i>Grit</i> is the share of the power not on the note's harmonics
      (aliasing, crushing, the picture's noise), in per cent; <i>top</i> is the share above 2 kHz, at the strike and held,
      since a stepped or crushed wave is harmonic and grit misses it. By these, the bank is mostly clean on a single
      held note, so the gritty sound you hear is likely in the strike, in chords, or in what Scan does to a figure
      once it is played on; these numbers do not settle it.</p>
    <div class="wrap"><table><tr><th>Preset</th><th>Heading</th><th>Brightness, Hz</th><th>Grit, %</th><th>Top at the strike, %</th><th>Top held, %</th></tr>
      {{COMPARE}}</table></div>
    <p><b>Things to decide.</b> Which, if any, go in the bank, and with what changes. Each goes under the heading it
      measures as, with its two lines (all twelve to sixty characters) and its description, then
      <code>write_presets.py</code> and its thumbnail by <code>write_figures.py</code>. Each is a starting point, so
      turn them freely: a change it does not contain may take it under the other heading, which is not a fault.</p>
  </div>

{{SECTIONS}}

  <p class="soft">Made by <code>measure.py</code> (the headings and the setup codes, through the page),
    <code>render.py</code> (the audio by the core, the measures, the pictures from the page) and <code>page.py</code>.
    The candidates and their performances are in <code>candidates.py</code>; every number is in
    <code>measured.json</code> and <code>results.json</code>.</p>
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
