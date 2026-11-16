"""web/docs/listening/one-to-two/index.html from numbers.json."""
import json, html
n = json.load(open("numbers.json"))
T = {t["file"]: t for t in n["takes"]}
OUT = "/home/user/Real-Time-Sound-Visualizer/web/docs/listening/one-to-two/index.html"
LISTEN = {
 "dyad-today": "The bass leaves your right ear the instant the E comes in, and the E takes its place. When the E goes the bass comes back, but narrow, in the middle of your head, where it started wide.",
 "dyad-today-later": "The same playing with the E let go 1.9 ms later: now the bass comes back wide and hollow, its two ears in opposite phase. Where it lands is decided by the instant you let go.",
 "poly-today": "The moment the E comes in the bass narrows and leans left - its right ear 6 dB down and moving in step with its left - and opens out again when the E goes.",
 "split-today": "The bass stays where it was: each hand is a figure of its own. What moves is the picture's breathing, which every take here has.",
 "dyad-instep": "As today while the E is held. Listen for the bass coming back wide, as it started, however the E is let go.",
 "dyad-lean": "The bass stays in both ears while the E is held, a little to the left, and comes back as it started.",
 "poly-turn": "The bass keeps its width while the E is held and only leans left, where today it narrows as well.",
 "poly-nolean": "The bass does not move at all; the E sits round it.",
}
SPEED = {"dyad-today": "one sample", "dyad-today-later": "one sample", "poly-today": "4 ms (90% in 9 ms)", "split-today": "&ndash;",
         "dyad-instep": "30 ms crossfade", "dyad-lean": "30 ms crossfade", "poly-turn": "4 ms, gain only", "poly-nolean": "&ndash;"}
def num(v, f="%.1f"):
    s = f % v
    return s.replace("-", "&minus;") if not s.startswith("-0.0") or f != "%.1f" else s.replace("-", "")
def db(v):
    return "silent" if v < -40 else num(v)
def coh(v): return num(0.0 if abs(v) < 0.005 else v, "%.2f")
def svg(points, ink):
    d = "M" + " L".join("%d %d" % (round(50 + 46 * x), round(50 - 46 * y)) for x, y in points[::2])
    return '<svg viewBox="0 0 100 100" class="fig" role="img"><rect x="1" y="1" width="98" height="98" class="frame"/><path d="%s" class="%s"/></svg>' % (d, ink)
def take(f):
    t = T[f]
    figs = "".join('<figure>%s<figcaption>%s</figcaption></figure>' % (svg(t["image"][k], "ink"), c)
                   for k, c in (("fig_alone", "alone"), ("fig_with", "with the E"), ("fig_back", "alone again")))
    return ('<div class="take"><div class="take-name">%s</div><audio controls preload="none" data-src="%s.wav"></audio>'
            '<p class="listen">%s</p><div class="figs">%s</div></div>') % (html.escape(t["label"]), f, LISTEN[f], figs)
def row(f):
    t = T[f]; im = t["image"]
    return ("<tr><td>%s</td><td class=num>%s &rarr; %s &rarr; %s</td><td class=num>%s &rarr; %s &rarr; %s</td>"
            "<td class=num>%s</td><td class=num>%s</td></tr>") % (
        html.escape(t["label"]), db(im["alone"]["lr"]), db(im["with"]["lr"]), db(im["back"]["lr"]),
        coh(im["alone"]["coh"]), coh(im["with"]["coh"]), coh(im["back"]["coh"]),
        num(im["with"]["power"] - im["alone"]["power"]), SPEED[f])
TABLE_HEAD = ("<table><thead><tr><th>Version</th><th>Bass: right ear against left, dB<br>alone &rarr; with the E &rarr; alone again</th>"
              "<th>Bass: its two ears' coherence<br>alone &rarr; with &rarr; again</th><th>Bass, both ears, with the E</th><th>How fast</th></tr></thead><tbody>")
def table(files): return TABLE_HEAD + "".join(row(f) for f in files) + "</tbody></table>"
sw = n["sweep"]
sweep_rows = "".join("<td class=num>%s</td>" % coh(c) for _, c in sw["render_cpp"])
sweep_rows_a = "".join("<td class=num>%s</td>" % coh(c) for _, c in sw["r-instep"])
pic = "".join("<tr><td>%s</td><td class=num>%.2f</td><td class=num>%s</td></tr>" % (html.escape(T[f]["label"]), T[f]["picture"]["cent_vs_alone"], num(T[f]["picture"]["lvl_vs_alone"]))
              for f in T)
size = None
page = open("page.tmpl").read()
for k, v in {"%TODAY%": "".join(take(f) for f in ("dyad-today", "dyad-today-later", "poly-today", "split-today")),
             "%TODAY_TABLE%": table(["dyad-today", "dyad-today-later", "poly-today", "split-today"]),
             "%OPTIONS_DYAD%": "".join(take(f) for f in ("dyad-instep", "dyad-lean")),
             "%OPTIONS_POLY%": "".join(take(f) for f in ("poly-turn", "poly-nolean")),
             "%OPTIONS_TABLE%": table(["dyad-today", "dyad-instep", "dyad-lean", "poly-today", "poly-turn", "poly-nolean"]),
             "%SWEEP%": "<tr><td>Today</td>%s</tr><tr><td>A</td>%s</tr>" % (sweep_rows, sweep_rows_a),
             "%PICTURE%": pic}.items():
    assert page.count(k) == 1, k
    page = page.replace(k, v)
open(OUT, "w").write(page)
print(len(page))
