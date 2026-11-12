"""Write the study's page, index.html, from results.json (study.py).

    python3 page.py

One file, no scripts, the brand's type stacks with system fallbacks (no
webfont is fetched: the page must read the same offline), images and media
beside it by relative paths."""
import html, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import palettes  # noqa: E402

STUDY = os.path.dirname(HERE)
R = json.load(open(os.path.join(STUDY, "results.json")))

PHRASE = {
    "pad": ("A held pad", "<em>Slow pad</em>, from the bank: a Cmaj9 voicing (C3 G3 D4 E4 B4) held nine seconds and let go into its 1.5 s release."),
    "crossed": ("Crossed hands", "The owner's repeatable setup (Picture 47, delay, phaser and reverb on, split at C4) and sequence, compressed from 27 s to 15: D♭2 A♭2 C3 held; a right-hand run in D♭ major pentatonic with C, five notes a second at velocity 55 and then eight at 95; the chord changed to G♭2 D♭3 F3 during it; the run stopping; soft B♭-to-C and G♭-to-A♭4 grace notes."),
    "run": ("A fast run", "<em>Tine piano</em>, from the bank: C major from C4 to C5 and back three times at nine notes a second, each pass swelling to its top and falling back, a little louder each time, ending on a held C4."),
    "chords": ("A chord change", "<em>Drawbar organ</em>, from the bank: Dm7, G7, Cmaj7 and Am7 in four-note voicings, two and a half seconds each."),
}
STYLE = {
    "physical": ("Physical paint", "Oil on canvas, simulated: a bristle brush whose paint runs out along the stroke, pressed wider and heavier by loudness; paint kept as a height map and lit from the side; strokes laid into wet paint drag and mix into it (Kubelka-Munk), strokes laid on dry paint sit on top and dry-brush across its ridges."),
    "ink": ("Ink and wash", "Washes that deepen while a note is held; a broad nib at a fixed angle following the melody, drying as it goes; a few drops on a hard strike."),
    "gesture": ("Gestural", "Poured pools for held notes, which drip when heavy; flung skeins for the melody, thinner the faster the hand moves, overshooting on hard strikes; spatter in the direction of travel."),
    "geometry": ("Geometric", "A circle for each held note with a halo; arcs for steps and straight lines for leaps; a band round the turn for a consonant chord, a plane across it for a tense one; a dot and rays for each strike."),
}
PAL_NAME = {k: v["name"] for k, v in palettes.PALETTES.items()}


def e(s): return html.escape(s, quote=True)


def fig(src, cap, cls=""):
    return (f'<figure class="{cls}"><a href="{e(src)}"><img src="{e(src)}" loading="lazy" alt="{e(cap)}"></a>'
            f'<figcaption>{cap}</figcaption></figure>')


def swatches(key):
    p = palettes.PALETTES[key]
    m = R["palette_measures"][key]
    cells = []
    for role in palettes.ROLES:
        cells.append(f'<li><span class="chip" style="background:{p["inks"][role]}"></span>'
                     f'<span><b>{e(p["names"][role])}</b><br><code>{p["inks"][role]}</code> · {m["contrast"][role]}:1</span></li>')
    sim = m["simulated"]
    worst = {k: v for k, v in m["worst"].items() if k != "normal"}
    return (f'<div class="palette" style="--g:{p["ground"]};--fg:{p["inks"]["a_main"]}">'
            f'<h3>{e(p["name"])}</h3><p class="ground">ground <code>{p["ground"]}</code></p>'
            f'<ul class="sw">{"".join(cells)}</ul>'
            f'<p class="meas">Worst pair <b>{m["worst"]["normal"][0]}</b> ({e(m["worst"]["normal"][1])}) with normal vision, '
            f'<b>{sim[0]}</b> simulated ({", ".join(f"{k} {v[0]}" for k, v in worst.items())}); bars 15 and 8. '
            f'Least contrast on the ground {min(m["contrast"].values())}:1.</p></div>')


def main():
    by = {(s["phrase"], s["style"]): s["src"] for s in R["stills"]}
    C = R["cycle2"]
    LEAD = C["lead"]
    COMP = {
        "travel": ("Travel", "Each hand's brush travels, turned by each interval and bent by spectral change, hurried by agitation and lingering on held notes, drifting to its register's height, and steered back to where a recently played note was painted."),
        "cycles": ("Cycles", "Travel, but where the sound is cyclic the gesture is: a hand holding notes without striking circles, and a repeated figure, steered hard back to its own marks, loops."),
        "clusters": ("Clusters", "Time across, warped by how much is happening (a run takes room, a long hold little); pitch up; each gesture drawn in towards its own centre, so the phrase falls into clusters with air between."),
    }
    def grid(kind):
        rows = []
        for comp in ("travel", "cycles", "clusters"):
            cells = "".join(fig(C[kind][comp][n]["src"] if kind == "physical" else C[kind][comp][n], f"<b>{PHRASE[n][0]}</b>") for n in ("pad", "crossed", "run", "chords"))
            rows.append(f'<h3>{COMP[comp][0]}{" (the lead)" if comp == LEAD else ""}</h3><p class="measures">{COMP[comp][1]}</p><div class="four">{cells}</div>')
        return "".join(rows)
    pgrid, ggrid = grid("physical"), grid("gesture")
    merged = []
    for n in ("pad", "crossed", "run", "chords"):
        L = C["physical"][LEAD][n]["landed"]; other = L["wet"] + L["dry"]
        merged.append(f"<tr><td>{PHRASE[n][0]}</td><td>{100 * L['wet'] / other:.0f} per cent</td><td>{100 * L['dry'] / other:.0f} per cent</td></tr>" if other else f"<tr><td>{PHRASE[n][0]}</td><td colspan=2>none met other paint</td></tr>")
    merged = "".join(merged)
    def brushline(f):
        stiff = max(0.0, min(1.0, (f["bright"] + 0.3) / 1.6))
        return (f"brightness {f['bright']} (stiffness {stiff:.2f}), spread {f['splay']} (splay), richness {f['rich']} (load), "
                f"roughness {f['rough']} (tremor), noise {f['grain']} (dry drag)")
    details = "".join(fig(d["src"], f"<b>{PHRASE[d['phrase']][0]}</b> · {brushline(d['features'])}") for d in C["details"])
    cbuilds = "".join(f'<figure><video controls preload="none" playsinline src="{e(b["src"])}"></video><figcaption><b>{PHRASE[b["phrase"]][0]}</b> · built up with its sound: the gloss is the paint still wet, and goes from thin paint first</figcaption></figure>' for b in C["builds"])
    cpals = "".join(fig(p["src"], f"<b>Physical paint</b> · {e(PAL_NAME[p['palette']])} · Crossed hands, {COMP[LEAD][0]}") for p in C["palettes"])
    cothers = "".join(fig(o["src"], f"<b>{STYLE[o['style']][0]}</b> · {PHRASE[o['phrase']][0]}") for o in C["others"] if o["style"] == "geometry")
    cink = "".join(fig(o["src"], f"<b>{STYLE[o['style']][0]}</b> · {PHRASE[o['phrase']][0]}") for o in C["others"] if o["style"] == "ink")
    costs = "".join(f"<tr><td>{k} × {k}</td><td>{v['brush_ms_per_frame']} ms</td><td>{v['render_ms_per_frame']} ms</td></tr>" for k, v in C["costs"].items())
    audio = "".join(f'<figure><figcaption><b>{PHRASE[n][0]}</b></figcaption><audio controls preload="none" src="audio/{n}.mp3"></audio></figure>' for n in ("pad", "crossed", "run", "chords"))
    out = []
    for name in ("pad", "crossed", "run", "chords"):
        title, desc = PHRASE[name]
        ph = R["phrases"][name]
        figs = "".join(fig(by[(name, st)], f"<b>{STYLE[st][0]}</b> · Layered, Accumulate, the house palette") for st in ("ink", "gesture", "geometry"))
        out.append(f'''<section class="phrase" id="{name}">
<p class="eyebrow">Phrase</p><h2>{title}</h2><p>{desc}</p>
<audio controls preload="none" src="audio/{name}.mp3"></audio>
<p class="measures">Measured: median level {ph["db"]:.1f} dB, brightness {ph["bright"]} octaves over the pitch, agitation {ph["agitation"]}, grain {ph["grain"]}; {ph["notes"]} notes.</p>
<div class="three">{figs}</div></section>''')
    phr = "\n".join(out)
    scroll = "".join(fig(s["src"], f"<b>{STYLE[s['style']][0]}</b> · Scroll: Crossed hands left to right, pitch up", "wide") for s in R["scroll"])
    pals = "".join(swatches(k) for k in ("brand", "earth", "night"))
    palfigs = "".join(fig(s["src"], f"<b>{STYLE[s['style']][0]}</b> · {e(PAL_NAME[s['palette']])} · Crossed hands")
                      for s in sorted(R["palettes"], key=lambda s: (s["palette"], ["ink", "gesture", "geometry"].index(s["style"]))))
    fades = "".join(f'<figure><video controls preload="none" playsinline src="{e(f["src"])}"></video>'
                    f'<figcaption><b>{STYLE[f["style"]][0]}</b> · {PHRASE[f["phrase"]][0]} · Fade, a mark at a tenth after four seconds, with its sound</figcaption></figure>'
                    for f in R["fades"])
    scan = "".join(f'''<div class="scan"><h3>{STYLE[s["style"]][0]}</h3>
<p>The finished painting, held under A3:</p><audio controls preload="none" src="{e(s["held"])}"></audio>
<p>{"The canvas read as it is painted (paint does not fade, so it builds up):" if s["style"] == "physical" else "The fading canvas, read as it is painted:"}</p><audio controls preload="none" src="{e(s["fade"])}"></audio>
<p class="measures">Harmonic centroid of the table: {s["held_centroid"]} finished; {s["fade_centroid_median"]} median while {"painting" if s["style"] == "physical" else "fading"} (10th to 90th percentile {s["fade_centroid_range"][0]} to {s["fade_centroid_range"][1]}); {s["dark_frames"]} of {s["frames"]} frames too dark to read.</p></div>'''
                   for s in R["scan"])
    styles = "".join(f"<li><b>{v[0]}.</b> {v[1]}</li>" for v in STYLE.values())
    chk = R["checks"]
    page = f'''<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Painting the sound</title>
<meta name="description" content="A visual study, in two cycles: four phrases rendered by the instrument's own core and painted as simulated oil paint and in three other styles, in compositions the sound steers.">
<style>
:root {{
  --cream: #faf6f0; --cream-2: #f2ebe1; --paper: #fffcf7; --charcoal: #241f1d; --text: #3a332f; --text-soft: #6b615a;
  --line: #e4d9cc; --blush: #d9a6a0; --blush-deep: #c07f79;
  --serif: "Playfair Display", Georgia, "Times New Roman", serif;
  --script: "Cormorant Garamond", Georgia, serif;
  --sans: "Jost", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: ui-monospace, Menlo, Consolas, monospace;
}}
* {{ box-sizing: border-box; }}
html {{ -webkit-text-size-adjust: 100%; }}
body {{ margin: 0; background: var(--cream); color: var(--text); font: 300 16px/1.65 var(--sans); -webkit-font-smoothing: antialiased; }}
main {{ max-width: 1180px; margin: 0 auto; padding: 32px 16px 80px; }}
h1, h2, h3 {{ font-family: var(--serif); font-weight: 600; color: var(--charcoal); line-height: 1.2; }}
h1 {{ font-size: clamp(32px, 6vw, 52px); margin: 4px 0 8px; }}
h2 {{ font-size: clamp(24px, 4vw, 32px); margin: 4px 0 8px; }}
h3 {{ font-size: 19px; margin: 24px 0 6px; }}
h2.sub {{ margin-top: 36px; }}
.lede {{ font-family: var(--script); font-style: italic; font-size: 22px; line-height: 1.4; color: var(--text); max-width: 46em; }}
.eyebrow {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.28em; color: var(--blush-deep); font-weight: 500; margin: 0; }}
p {{ max-width: 46em; }}
section {{ border-top: 1px solid var(--line); padding-top: 28px; margin-top: 40px; }}
a {{ color: inherit; text-decoration-color: var(--blush); text-underline-offset: 3px; }}
code {{ font-family: var(--mono); font-size: 0.86em; }}
.measures, figcaption, .meas, .ground {{ font-size: 13px; color: var(--text-soft); }}
figure {{ margin: 0; }}
figure img, figure video {{ display: block; width: 100%; height: auto; background: var(--paper);
  box-shadow: 0 1px 0 var(--cream-2), 0 14px 34px rgba(36, 31, 29, 0.06); }}
figcaption {{ padding: 8px 2px 0; }}
.three {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; margin-top: 16px; }}
.four {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-top: 16px; }}
.two {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 18px; margin-top: 12px; }}
.pair {{ margin-top: 28px; }}
.wide {{ margin-top: 18px; }}
audio {{ width: 100%; max-width: 520px; margin: 4px 0; }}
.palettes {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }}
.palette {{ background: var(--g); color: var(--fg); padding: 16px; border: 1px solid var(--line); }}
.palette h3, .palette .meas, .palette .ground {{ color: var(--fg); }}
.sw {{ list-style: none; padding: 0; margin: 8px 0; display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 13px; }}
.sw li {{ display: flex; gap: 8px; align-items: center; }}
.chip {{ width: 28px; height: 28px; border-radius: 50%; flex: none; }}
.scans {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 18px; }}
.scan p {{ margin: 6px 0; font-size: 14px; }}
table {{ border-collapse: collapse; font-size: 14px; width: 100%; max-width: 900px; }}
td, th {{ border-bottom: 1px solid var(--line); padding: 6px 8px; text-align: left; vertical-align: top; }}
th {{ font-weight: 500; font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.16em; color: var(--text-soft); }}
.table-wrap {{ overflow-x: auto; }}
@media (max-width: 760px) {{
  .three, .palettes, .scans, .two {{ grid-template-columns: 1fr; }}
  .four {{ grid-template-columns: 1fr 1fr; }}
}}
</style></head>
<body><main>
<p class="eyebrow">A study, 12 November</p>
<h1>Painting the sound</h1>
<p class="lede">Four phrases played through the instrument's own core, and each painted - as oil paint on canvas, and in three other languages - from what the sound contains: a wash where a note is held, a stroke where a melody moves, spatter where a key is struck hard, grain where the sound is noisy, and harmony as which ink.</p>
<p>Nothing in the instrument was changed to make this. The write-up, with what was found and the questions for the owner, is <a href="../painting-the-sound.md"><code>painting-the-sound.md</code></a>; the scripts that made every file here are in <code>tools/</code>, and run again to the same pictures.</p>

<section id="cycle2"><p class="eyebrow">Second cycle, after the owner's look</p><h2>Where the sound puts the paint</h2>
<p>The first cycle put every painting on rings, so every painting looked alike. Here are three compositions in which the sound decides where marks go - nothing placed at random beyond a brush's own small variation - on all four phrases, side by side. Physical paint first, then gestural, the style that already looked most like art. Listen to the four phrases:</p>
<div class="four">{audio}</div>
<h2 class="sub">Physical paint</h2>
{pgrid}
<h2 class="sub">Gestural</h2>
{ggrid}
</section>

<section id="brush"><p class="eyebrow">Physical paint</p><h2>The sound guides the brush</h2>
<p>Each stroke's brush is set by the spectrum as it goes: <b>brightness</b> makes the bristles stiff - streakier, harder-edged, ploughing more and blending less - and a dark sound soft; <b>spectral spread</b> splays them wider, with gaps; <b>harmonic richness</b> loads the brush; <b>noise</b> drags it dry, catching only on the weave; <b>roughness</b> (partials beating) shakes the line; the <b>attack</b> shapes the start, tapering in over a slow attack and pressing in square on a sharp one; <b>spectral change</b> bends the path (in the composition). Each stroke adds its own small seeded variation. Details at full resolution, one pixel to one, each captioned with its phrase's median measures:</p>
<div class="two">{details}</div>
<p>Also fixed: the thin hard lines that shot out of a stroke's end (a lifting brush's bristles were squeezed into the narrowing contact; now they keep their places and the end feathers), and the boxy patches and ribbing (paint was shoved from the whole footprint to one spot every step; now the leading edge ploughs it into a spread bank).</p>
</section>

<section id="drying"><p class="eyebrow">Physical paint</p><h2>Drying</h2>
<p>Slower, and by thickness: paint's wetness falls to 1/e in 1.5 × (1 + 3 × thickness) seconds - about 1.5 s for a scumble, 3.5 s for an ordinary stroke and 6 s or more for a heavy, hard-struck one, where the first cycle dried everything in 1.2 s. So a scumble dries first and a loaded stroke stays wet to be dragged. In the videos the gloss is the wet paint. Where the paint landed on other paint in {COMP[LEAD][0]}:</p>
<div class="table-wrap"><table><tr><th>Phrase</th><th>Into wet paint (merging)</th><th>Onto dry paint (layering)</th></tr>{merged}</table></div>
<div class="two">{cbuilds}</div>
<h3>What it costs</h3><p>Measured on one core of this machine, Crossed hands in {COMP[LEAD][0]} at 20 frames a second: the brushwork for each frame's twentieth of a second, and lighting and mixing the whole canvas once. Drying by thickness costs one multiply per pixel; it does not show in these numbers.</p>
<div class="table-wrap"><table><tr><th>Canvas</th><th>Brushwork per frame</th><th>Render per frame</th></tr>{costs}</table></div>
</section>

<section id="others"><p class="eyebrow">Carried along</p><h2>The other styles in {COMP[LEAD][0]}</h2>
<p>Physical paint in the two proposed palettes:</p>
<div class="two">{cpals}</div>
<p>Geometric, whose pieces all looked alike on rings:</p>
<div class="four">{cothers}</div>
<p>Ink and wash:</p>
<div class="four">{cink}</div>
</section>

<section id="cycle1"><p class="eyebrow">First cycle</p><h2>As first shown</h2>
<p>The first cycle's paintings in the other three styles, on the Layered layout that put time round the canvas, kept for comparison. Physical paint's first layout is superseded above.</p>
</section>

<section id="read"><p class="eyebrow">How to read them</p><h2>The mapping</h2>
<div class="table-wrap"><table>
<tr><th>The sound</th><th>Read from</th><th>The mark</th></tr>
<tr><td>Which note, how loud, still held</td><td>The core's own voices, every 2.7 ms</td><td>Where it lands; a stroke's width (tapering as the level falls)</td></tr>
<tr><td>A held tone</td><td>A voice's level above a twelfth of its peak, past its attack</td><td>A wash (or pool, or circle) that grows and deepens as long as it is held</td></tr>
<tr><td>A melody</td><td>Strikes in one hand within 0.45 s of each other</td><td>One stroke through them, gliding to each next note</td></tr>
<tr><td>A sharp attack</td><td>Velocity and the core's attack time</td><td>Spatter, drops or rays: how many by velocity squared and sharpness, how far by velocity</td></tr>
<tr><td>Agitation</td><td>Strikes in the last half second, and how fast the spectrum changes</td><td>How far the brush shakes off its line; how far a strike flings</td></tr>
<tr><td>Brightness</td><td>Spectral centroid against the sounding pitch</td><td>How fast the ink-and-wash brush dries into dry-brush streaks</td></tr>
<tr><td>Noise and grit</td><td>Spectral flatness</td><td>Granulation in washes; specks of grain; a grit of small squares</td></tr>
<tr><td>Harmony</td><td>Each note against the lowest sounding, round the circle of fifths</td><td>Its hand's own ink (unison, fifth, fourth), a related ink (seconds, thirds, sixths), or the clash ink (semitone, major seventh, tritone)</td></tr>
<tr><td>Each hand</td><td>The split (Crossed hands only; the others are one hand)</td><td>Its own three inks</td></tr>
</table></div>
<p><b>Layered</b> lays the piece round the canvas, one turn every eight seconds clockwise from the top, pitch outward from the centre, so a longer piece paints over its own beginning. <b>Scroll</b> lays it left to right in time, pitch up. <b>Accumulate</b> keeps everything; <b>Fade</b> lets every mark fall to a tenth in four seconds.</p>
<ul>{styles}</ul>
</section>

{phr}

<section id="scroll"><p class="eyebrow">The other layout</p><h2>Scroll</h2>
<p>The same marks laid left to right in time, so the piece can be read back. Crossed hands, the busiest phrase, in each style.</p>
{scroll}</section>

<section id="palettes"><p class="eyebrow">Palettes</p><h2>Three palettes</h2>
<p>The house palette is the six lane inks on the cream, exactly as <code>DESIGN.md</code> has them: the left hand's figure inks charcoal and slate, the right hand's olive and sage, terracotta and plum as each hand's clash. Earth and Night are proposals for a product table, not tokens. Measured as <code>DESIGN.md</code> measures the lane inks: OKLab distance times a hundred, worst of all pairs, with colour vision deficiency simulated (Machado et al., full severity). The palette is only the look: the ink density the paintings are made of was compared across all three palettes and differs by {chk["density_palette_max_difference"]} (the lightness of the coloured images, the null, differs by up to {chk["lightness_palette_max_difference_null"]}).</p>
<div class="palettes">{pals}</div>
<div class="three">{palfigs}</div></section>

<section id="fades"><p class="eyebrow">Memory</p><h2>Fade</h2>
<p>Each painting made in time with its sound, older marks fading to a tenth in four seconds, as the screen's Persistence fades the trace. Two phrases per style; press play for sound.</p>
<div class="three">{fades}</div></section>

<section id="scan"><p class="eyebrow">A first approximation</p><h2>What Scan would hear</h2>
<p>Each style's Crossed hands painting, reduced to a 64 by 64 grid of ink density (for physical paint, how far the paint hides the ground) and read by the core's own Scan functions (<code>scanGeometry</code>, <code>scanBlur</code> at the default Softness of 3, <code>scanRead</code>, <code>scanTables</code>), then played as a held A3 with the table at a depth of 0.6 against a sine. This is not the instrument playing a painting: nothing yet puts a painting on its screen, the voice's other stages are left out, and the density grid is the study's assumption about what Scan would read.</p>
<div class="scans">{scan}</div></section>
</main></body></html>
'''
    open(os.path.join(STUDY, "index.html"), "w").write(page)
    print("index.html", len(page), "bytes")


if __name__ == "__main__":
    main()
