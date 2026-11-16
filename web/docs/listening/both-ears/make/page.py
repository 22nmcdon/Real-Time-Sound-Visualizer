"""web/docs/listening/both-ears/index.html from numbers.json and proof.json."""
import json, html, os
HERE = os.path.dirname(os.path.abspath(__file__))
N = json.load(open(os.path.join(HERE, "numbers.json")))
P = json.load(open(os.path.join(HERE, "proof.json")))
OUT = "/home/user/Real-Time-Sound-Visualizer/web/docs/listening/both-ears"
T = {t["file"]: t for t in N["takes"]}
L = N["label"]
SHORT = {"today": "Today", "w1a": "Way 1 (a)", "w1b": "Way 1 (b)", "w1c": "Way 1 (c)", "w2": "Way 2"}

def num(v, f="%.1f"):
    s = f % v
    if s.lstrip("-").strip("0.") == "": s = s.lstrip("-")
    return s.replace("-", "&minus;")
def db(v): return "gone" if v < -40 else num(v)
def coh(v): return num(0.0 if abs(v) < 0.005 else v, "%.2f")
def svg(points, ink):
    pts = points[::2] if len(points) > 200 else points
    d = "M" + " L".join("%d %d" % (round(50 + 46 * x), round(50 - 46 * y)) for x, y in pts)
    return '<svg viewBox="0 0 100 100" class="fig" role="img" aria-label="figure"><rect x="1" y="1" width="98" height="98" class="frame"/><path d="%s" class="%s"/></svg>' % (d, ink)
def figrow(figs, caps, ink, label):
    cells = "".join('<figure>%s<figcaption>%s</figcaption></figure>' % (svg(f, ink), c) for f, c in zip(figs, caps))
    return '<div class="figlabel">%s</div><div class="figs">%s</div>' % (label, cells)
OWNER_CAPS = ["alone", "with the E", "alone again"]
CHORD_PICK = [0, 1, 3, 6]
CHORD_CAPS = ["C3", "C3 E3", "all four", "C3 again"]
LISTEN = {
 "owner-today": "The bass is in both ears, wide. When the E comes in the bass leaves your right ear at once and the E appears only there; when the E goes, the bass comes back narrow and centred, not wide as it started.",
 "owner-w1a": "Both notes in the middle of your head, each the same in both ears. Nothing moves between the ears at all; it is also the least spacious.",
 "owner-w1b": "Each note a little wide and centred. The E arrives in both ears and the bass does not move when it comes or goes.",
 "owner-w1c": "Each note as wide as a note alone is today, always. The E arrives wide and centred; the bass stays exactly as it was.",
 "owner-w2": "Heard as Way 1 (c): the screen is the speakers again, so the figure is what changes (under it).",
 "chord-today": "Each new top note lands on the right and pushes the one before it into the middle; the held C3 narrows and leans left from the second note until it is alone again. The chord also gets quieter as it fills (the limiter).",
 "chord-w1b": "Every note lands in the middle, a little wide, and stays there as the others come and go.",
 "chord-w2": "Heard much as Way 1 (c) would be: every note wide and centred. The screen draws the notes' rings summed.",
}
def take(f):
    t = dict(T[f]); key = t["key"]; owner = t["phrase"] == "owner"
    if owner: t.update(N["figs"]["owner-" + key])   # drawn with the picture off, so the notes alone draw it
    pick = (lambda xs: xs) if owner else (lambda xs: [xs[i] for i in CHORD_PICK])
    caps = OWNER_CAPS if owner else CHORD_CAPS
    if key == "today":
        figs = figrow(pick(t["drawn"]), caps, "ink", "On the screen, and on the speakers (they are the same)")
    elif key == "w2":
        figs = figrow(pick(t["drawn"]), caps, "ink2", "On the screen, and on the speakers: the notes' rings summed")
    else:
        figs = (figrow(pick(t["drawn"]), caps, "ink", "On the screen: today's, to the bit")
                + figrow(pick(t["heard"]), caps, "ink3", "What an oscilloscope on the speakers would draw"))
    name = L[key] if owner else {"today": "Today", "w1b": "Way 1 (b): gentle width", "w2": "Way 2: every note on both sides"}[key]
    return ('<div class="take"><div class="take-name">%s</div><audio controls preload="none" data-src="%s.wav"></audio>'
            '<p class="listen">%s</p>%s</div>') % (html.escape(name), f, LISTEN[f], figs)

def owner_row(key):
    o = N["owner"][key]
    a, w, b = o["alone"]["C2"], o["with the E"]["C2"], o["with the E"]["E4"]
    g = o["alone again"]["C2"]
    sw = N["sweep"][key]
    return ("<tr><td>%s</td><td class=num>%s / %s &middot; %s</td><td class=num>%s / %s &middot; %s</td><td class=num>%s / %s &middot; %s</td>"
            "<td class=num>%s / %s &middot; %s</td><td class=num>%s&hellip;%s</td></tr>") % (
        SHORT[key], db(a["L"]), db(a["R"]), coh(a["coh"]), db(w["L"]), db(w["R"]), coh(w["coh"]),
        db(b["L"]), db(b["R"]), coh(b["coh"]), db(g["L"]), db(g["R"]), coh(g["coh"]), coh(min(sw)), coh(max(sw)))
OWNER_TABLE = ("<table><thead><tr><th>Version</th><th>C2 alone<br>left / right dB &middot; coherence</th><th>C2, with the E</th>"
               "<th>E4, while held</th><th>C2 alone again</th><th>C2 again: coherence over sixteen releases</th></tr></thead><tbody>"
               + "".join(owner_row(k) for k, _ in N["builds"]) + "</tbody></table>")

NOTES = ["C3", "E3", "G3", "C4"]
SPAN_NAMES = ["C3 alone", "E3 added", "G3 added", "C4 added", "C4 let go", "G3 let go", "E3 let go"]
def chord_table(key):
    rows = []
    for k, (span, d) in enumerate(N["chord"][key]):
        cells = "".join("<td class=num>%s</td>" % ("%s / %s &middot; %s" % (db(d[n]["L"]), db(d[n]["R"]), coh(d[n]["coh"])) if n in d else "")
                        for n in NOTES)
        rows.append("<tr><td>%s</td>%s</tr>" % (SPAN_NAMES[k], cells))
    return ("<table><thead><tr><th>%s</th>%s</tr></thead><tbody>%s</tbody></table>"
            % (SHORT[key], "".join("<th>%s<br>left / right &middot; coh.</th>" % n for n in NOTES), "".join(rows)))
def limiter_table():
    keys = ["today", "w1b", "w2"]
    head = "<tr><th>The held C3, against C3 alone, dB</th>%s</tr>" % "".join("<th>%s</th>" % s for s in SPAN_NAMES)
    body = ""
    for key in keys:
        base = N["chord"][key][0][1]["C3"]["lim"]
        body += "<tr><td>%s</td>%s</tr>" % (SHORT[key], "".join("<td class=num>%s</td>" % num(d["C3"]["lim"] - base) for _, d in N["chord"][key]))
    return "<table><thead>%s</thead><tbody>%s</tbody></table>" % (head, body)

def proof_table():
    rows = ""
    for ph, desc in (("owner", "Owner's phrase"), ("chord", "Chord")):
        for exe, name in (("r-null", "the copy, every switch off"), ("r-w1a", L["w1a"]), ("r-w1b", L["w1b"]), ("r-w1c", L["w1c"]), ("r-w2", L["w2"] + " (the null)")):
            d = P["%s/%s" % (ph, exe)]
            yes = lambda v: "same" if v else "<strong>differs</strong>"
            rows += "<tr><td>%s</td><td>%s</td><td class=num>%s</td><td class=num>%s</td><td class=num>%s</td><td class=num>%s</td></tr>" % (
                desc, name, yes(d["lanes"]), yes(d["grid"]), yes(d["readings"]), yes(d["heard"]))
    o, c = P["owner/r-w1b"], P["chord/r-w1b"]
    return ("<table><thead><tr><th>Phrase</th><th>Build</th><th>Drawn lanes</th><th>Shown grid</th><th>The loop's readings</th><th>Heard pair</th></tr></thead><tbody>%s</tbody></table>"
            '<p class="small">Against the core on the same performance, byte for byte: the six drawn lanes at every sample '
            "(%s and %s samples), the shown grid at every hundredth of a second (%.1f and %.1f MB), and %d and %d reading lines - "
            "Scan's table, the picture's six sources and its reads, every routing's depth, the stages, the meters and their verdicts.</p>") % (
        rows, format(o["lane_samples"], ","), format(c["lane_samples"], ","), o["grid_bytes"] / 1e6, c["grid_bytes"] / 1e6, o["n_readings"], c["n_readings"])

lvl = {f: T[f]["rms_db"] for f in T}
page = open(os.path.join(HERE, "page.tmpl")).read()
for k, v in {
    "%OWNER_TODAY%": take("owner-today"),
    "%OWNER_W1%": "".join(take(f) for f in ("owner-w1a", "owner-w1b", "owner-w1c")),
    "%OWNER_W2%": take("owner-w2"),
    "%OWNER_TABLE%": OWNER_TABLE,
    "%CHORD_TAKES%": "".join(take(f) for f in ("chord-today", "chord-w1b", "chord-w2")),
    "%CHORD_TODAY%": chord_table("today"),
    "%CHORD_OTHERS%": "".join(chord_table(k) for k in ("w1a", "w1b", "w1c", "w2")),
    "%LIMITER%": limiter_table(),
    "%PROOF%": proof_table(),
    "%LOUD_OWNER%": num(lvl["owner-w1c"] - lvl["owner-today"]),
    "%LOUD_CHORD%": num(lvl["chord-w1b"] - lvl["chord-today"]),
}.items():
    assert page.count(k) == 1, k
    page = page.replace(k, v)
assert "%" + "OWNER" not in page
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, "index.html"), "w").write(page)
print(len(page))
