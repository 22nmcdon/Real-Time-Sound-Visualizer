"""Write web/docs/listening/index.html from numbers.json."""
import json, os, html
OUT = "/home/user/Real-Time-Sound-Visualizer/web/docs/listening"
n = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "numbers.json")))
V = {v["file"]: v for v in n["versions"]}
E = html.escape

def rng(a): return "%.4f&ndash;%.4f" % (a[0], a[1])
def player(file, title):
    return ('<div class="take"><div class="take-name">%s</div>'
            '<audio controls preload="none" data-src="%s"></audio></div>') % (E(title), file)

def honesty_table(rows, heading):
    rule = "Settled" if heading == "Settled" else "Breathing"
    out = ['<table><thead><tr><th>Version</th><th>Lower hand (C2) late</th><th>Upper hand (G4) late</th>'
           '<th>Under %s</th><th>Under the other</th></tr></thead><tbody>' % rule]
    for label, h in rows:
        lo, up = h["36"], h["67"]
        own = (lo["settled"] + up["settled"]) if rule == "Settled" else (lo["breathing"] + up["breathing"])
        other = (lo["breathing"] + up["breathing"]) if rule == "Settled" else (lo["settled"] + up["settled"])
        cls = "ok" if own == 32 and other == 0 else "edge"
        out.append('<tr class="%s"><td>%s</td><td class="num">%s</td><td class="num">%s</td><td class="num">%d of 32</td><td class="num">%d of 32</td></tr>'
                   % (cls, E(label), rng(lo["late"]), rng(up["late"]), own, other))
    out.append("</tbody></table>")
    return "\n".join(out)

def budget_lines(file):
    b = next(x for x in n["budget"] if x["file"] == file)
    return b

tine_rows = [(V[f]["label"], V[f]["honesty"]) for f in ("btp-dry", "btp-on", "btp-mix6", "btp-mix4", "btp-tone30")]
tine_more = [(m["label"], m["honesty"]) for m in n["measured"] if m["group"] == "btp"]
pad_rows = [(V[f]["label"], V[f]["honesty"]) for f in ("pad-on", "pad-mix25", "pad-scan30", "pad-scan35")]
pad_more = [(m["label"], m["honesty"]) for m in n["measured"] if m["group"] == "pad"]
tp = V["tp-dry"]["honesty"]["60"]

page = """<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Listening study</title>
<style>
/* DESIGN.md's paper and ink: the brand's tokens, its stacks without the webfonts (fallback faces only, so nothing is fetched). */
:root {
  --cream: #faf6f0; --cream-2: #f2ebe1; --paper: #fffcf7; --charcoal: #241f1d; --text: #3a332f;
  --text-soft: #6b615a; --line: #e4d9cc; --blush: #d9a6a0; --blush-deep: #c07f79; --gold: #b08d57;
  --sage: #6f7f63; --rust: #a4553f; --unresolved: #b6afa4;
  --serif: Georgia, "Times New Roman", serif;
  --sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: ui-monospace, Menlo, Consolas, monospace;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--cream); color: var(--text); font: 300 16px/1.65 var(--sans);
  -webkit-font-smoothing: antialiased; }
main { max-width: 900px; margin: 0 auto; padding: 32px 16px 64px; }
.eyebrow { font-size: 11px; text-transform: uppercase; letter-spacing: 0.28em; color: var(--blush-deep); font-weight: 500; }
h1, h2, h3 { font-family: var(--serif); font-weight: 600; color: var(--charcoal); line-height: 1.25; }
h1 { font-size: 34px; margin: 6px 0 12px; }
h2 { font-size: 24px; margin: 0 0 6px; }
h3 { font-size: 18px; margin: 22px 0 6px; }
.sheet { background: var(--paper); border: 1px solid var(--line); border-radius: 1px; padding: 24px;
  margin: 28px 0; box-shadow: 0 1px 0 var(--cream-2), 0 14px 34px rgba(36, 31, 29, 0.06); }
.listen { border-left: 3px solid var(--gold); padding: 2px 0 2px 12px; margin: 12px 0; color: var(--charcoal); }
.caps { font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.16em; font-weight: 500; color: var(--text-soft); }
.takes { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 12px; margin: 14px 0; }
.take { border: 1px solid var(--line); border-radius: 1px; padding: 10px; background: var(--cream); }
.take-name { font-size: 14px; color: var(--charcoal); margin-bottom: 6px; }
audio { width: 100%; }
table { width: 100%; border-collapse: collapse; font-size: 14px; margin: 10px 0; display: block; overflow-x: auto; }
th { text-align: left; font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.14em; font-weight: 500;
  color: var(--text-soft); border-bottom: 1px solid var(--line); padding: 6px 8px; }
td { border-bottom: 1px solid var(--line); padding: 6px 8px; vertical-align: top; }
td.num { font-family: var(--mono); font-variant-numeric: tabular-nums; white-space: nowrap; font-size: 13px; }
tr.ok td:first-child { box-shadow: inset 3px 0 0 var(--sage); }
tr.edge td:first-child { box-shadow: inset 3px 0 0 var(--rust); }
.verdict { font-family: var(--serif); color: var(--charcoal); }
.small { font-size: 14px; color: var(--text-soft); }
code { font-family: var(--mono); font-size: 0.9em; }
ul { padding-left: 20px; }
.status { font-size: 13px; color: var(--rust); }
</style>
</head>
<body>
<main>
<div class="eyebrow">Real-Time Sound Visualizer &middot; a listening study</div>
<h1>Two Bass presets on their headings' edges, and the voices' budget refit</h1>
<p>Two of the owner's decisions in <code>web/docs/after-stage-5.md</code> that need an ear. Every take is the instrument
itself, the core rendered offline through <code>core/tests/tools/render_cpp.cpp</code>, so a take is the same to the bit every
time it is made. Nothing here changes the instrument: the candidates are setups laid over the presets, and the refit is a
scratch copy of the core's headers.</p>
<p class="small">Each take is 6.2 seconds, 16-bit at 44.1 kHz, and <strong>the left channel alone</strong>. The instrument's two
channels are the figure's two lanes and are not a stereo image of one sound (on the Bass under the tine piano they correlate
at &minus;0.28), so a mono sum would cancel part of the sound; and both channels together would not fit the 8 MB this page
was given. The left is also the channel the honesty measure reads. <span id="status" class="status"></span></p>

<section class="sheet">
<div class="eyebrow">A, first half</div>
<h2>Bass under the tine piano, with the reverb switched on</h2>
<p>Settled promises a held note comes to rest: late (the last three of ten seconds held) at most 0.015, and at most half the
early. With its switch pressed (Mix 15) the preset reads up to 0.0187 late on the upper hand, depending only on where the key
lands. The phrase: C2 under a C major triad (C4 E4 G4) held, and C5 E5 G5 E5 over it, then let go.</p>
<p class="listen">Listen for whether the held chord settles under the melody or keeps a shimmer, and whether the reverb sounds
part of the piano or a room round it.</p>
<div class="takes">
""" + "\n".join(player(f + ".wav", V[f]["label"]) for f in ("btp-dry", "btp-on", "btp-mix6", "btp-mix4", "btp-tone30")) + """
</div>
<h3>Honesty against Settled, sixteen key times each</h3>
""" + honesty_table(tine_rows, "Settled") + """
<p class="small">Tried and measured, not rendered, because they do not sit clearly inside:</p>
""" + honesty_table(tine_more, "Settled") + """
<p class="small">A shorter reverb does not help: at Size 20 and Size 10 the lower hand, which was safe, goes over. Nor is the
late a smooth function of the Mix: Mix 10 is no better than 15, and only from 6 down do all sixteen key times sit inside. A
darker tail (Tone 30 of 100, against the default 60) at the switch's own Mix of 15 does.</p>
<p class="verdict">Reading: <strong>Tone 30</strong> sits best. It keeps the reverb at the 0.15 the switch gives, which is the
only Mix a player pressing the switch ever hears: a preset that stores Mix 6 has the reverb on when it loads, and one saved
off comes back to 0.15 when switched on. Tone is a preset field the switch leaves alone, and with the reverb off it changes
nothing, so the dry preset is the same to the bit. Its late stays at most 0.0134.</p>

<h3>The Tine piano alone, no reverb</h3>
<p>The single-hand Tine piano as shipped, on the same phrase, since the owner was unsure about it. It is well inside Settled:
late """ + rng(tp["late"]) + """, early """ + rng(tp["early"]) + """, """ + str(tp["settled"]) + """ of 16 (probed on C4).</p>
<div class="takes">""" + player("tp-dry.wav", V["tp-dry"]["label"]) + """</div>
</section>

<section class="sheet">
<div class="eyebrow">A, second half</div>
<h2>Bass under the pad, with the reverb switched on</h2>
<p>Breathing promises a held note keeps moving: late at least 0.02, and silent after it is let go. The pad's upper hand moves
plenty (0.05 and more); it is the filtered saw bass, the lower hand, that sits on the floor, 0.021 at its least with the
switch pressed. The phrase is the same as above.</p>
<p class="listen">Listen to the bass under the held pad: whether it keeps moving for as long as it is held, and whether a
candidate changes how the bass strikes.</p>
<div class="takes">
""" + "\n".join(player(f + ".wav", V[f]["label"]) for f in ("pad-on", "pad-mix25", "pad-scan30", "pad-scan35")) + """
</div>
<h3>Honesty against Breathing, sixteen key times each</h3>
""" + honesty_table(pad_rows, "Breathing") + """
<p class="small">Every version passes all thirty-two probes; the question is the margin on the lower hand's least, which the
first column's left figure gives. Also measured:</p>
""" + honesty_table(pad_more, "Breathing") + """
<p class="verdict">Reading: <strong>the bass hand's Scan from 25 to 30</strong>. It lifts the lower hand's least from 0.021
to 0.024 with the reverb on, and dry from 0.022 to 0.024, leaves the pad's hand untouched to the bit, and, like Tone above, holds
whatever the switch does, where a Mix of 25 is a Mix the switch never gives. Scan 35 lifts the mean further but doubles the
bass's early (its strike, 0.12 to 0.16 against 0.04 to 0.06), which is a change of character. The rust rule on a row marks
a version not clearly inside; none of the pad's are outside.</p>
</section>
"""

def gov_line(file):
    b = budget_lines(file)
    rows = b["rows"]
    cops = [(int(r["b"][3]), int(r["b"][4])) for r in rows if any(p.split(":")[3] == "0" for p in r["b"][8:])]
    let = set()
    for r in rows:
        for p in r["b"][8:]:
            l, note, held, cut = p.split(":")
            if held == "1" and cut == "1": let.add((int(l), int(note)))
    return cops, sorted(let)
NAMES = {36: "C2", 43: "G2", 48: "C3", 52: "E3", 55: "G3", 62: "D4", 67: "G4", 72: "C5"}
def notes(let): return ", ".join(("lower " if l == 0 else "upper ") + NAMES.get(nn, str(nn)) for l, nn in let) or "none"

dA, dF = gov_line("draw-asis"), gov_line("draw-fit")
pA, pF = gov_line("pink-asis"), gov_line("pink-fit")
def span(c, i): vals = [x[i] for x in c]; return "%d to %d" % (min(vals), max(vals)) if min(vals) != max(vals) else "%d" % vals[0]

page += """
<section class="sheet">
<div class="eyebrow">B</div>
<h2>The voices' budget, refitted to the core</h2>
<p>The governor gives copies and notes up by a model of what each voice costs, fitted to the page's JavaScript. Timed in the
core as WebAssembly (a WASI build of <code>budget_cpp</code> in node, blocks of 128, budget.py's twenty cases, two runs), four of
the model's terms are off by more than the runs' own scatter, as <code>web/docs/budget-on-the-core.md</code> found:</p>
<table><thead><tr><th>Term</th><th>Measured, of the median</th><th>The model now</th><th>Fitted</th></tr></thead><tbody>
<tr><td>Drawbars, one copy</td><td class="num">1.60, 1.70</td><td class="num">5.5</td><td class="num">10.7</td></tr>
<tr><td>Drawbars, each of seven copies</td><td class="num">1.43, 1.54</td><td class="num">5.3</td><td class="num">8.2</td></tr>
<tr><td>Pink noise</td><td class="num">0.62, 0.62</td><td class="num">3</td><td class="num">0.9</td></tr>
<tr><td>The voice filter</td><td class="num">0.77, 0.58</td><td class="num">4</td><td class="num">1.7</td></tr>
</tbody></table>
<p class="small">Each fitted term moves its case to the median (a unit is 0.35 ms of work a second in WebAssembly here); the
filter's is the filtered saw less the saw. The other sixteen cases read 0.72 to 1.4 in both runs and are left as they are. The
fit was applied in a scratch copy of <code>core/include</code> only. The governor is a model, not a clock, so what it gives up
is the same every run whatever the machine is doing.</p>

<h3>Drawbars, seven copies, two hands, a full chord</h3>
<p>Split at C4: C3 E3 G3 B3 under E4 G4 B4 D5, held, with E5 G5 B5 D6 over them. At the instrument's own budget of 350 the
governor acts in both.</p>
<p class="listen">Listen to the chorus of the copies: as it is the chord keeps most of its width; refitted it is thinner and
closer to a plain organ, and thins again under each melody note.</p>
<div class="takes">""" + player("draw-asis.wav", "The governor as it is") + player("draw-fit.wav", "Costs fitted to the core") + """</div>
<ul>
<li><strong>As it is:</strong> seven copies a hand while the chord alone sounds; under the melody the lower hand """ + span(dA[0], 0) + """, the upper """ + span(dA[0], 1) + """ copies. Notes let go: """ + notes(dA[1]) + """.</li>
<li><strong>Refitted:</strong> the lower hand """ + span(dF[0], 0) + """ copies and the upper """ + span(dF[0], 1) + """ from the moment the chord lands, and one fewer in the lower hand under each melody note. Notes let go: """ + notes(dF[1]) + """.</li>
</ul>

<h3>Pink noise through the filter, two hands</h3>
<p>Split at C4: C2 G2 C3 E3 G3 under D4 G4 C5, held, with D5 E5 G5 C6 over them. Pink noise and the filter never reach 350
units in either model (eight notes cost 76 as it is and 41 refitted), so both builds were given a budget of 45 to make the
governor act; what differs is how many notes it lets go.</p>
<p class="listen">Listen to the chord's body: as it is, half the chord's noise bands go as it lands and the hand under
the melody is thin; refitted, only one inner note goes, and only when the melody enters.</p>
<div class="takes">""" + player("pink-asis.wav", "The governor as it is (budget 45)") + player("pink-fit.wav", "Costs fitted to the core (budget 45)") + """</div>
<ul>
<li><strong>As it is:</strong> held notes let go, inner voices first: """ + notes(pA[1]) + """. The chord lands as four notes (C2, G3, D4, C5), C5 goes when the melody enters, and each melody note sounds over C2, G3 and D4.</li>
<li><strong>Refitted:</strong> held notes let go: """ + notes(pF[1]) + """, when the melody enters; the other seven of the chord sound under it.</li>
</ul>
<p class="verdict">Reading: the refit is audible. It is safer for the drawbars (they are the side that glitches) at the cost
of their width under any chord of eight, and kinder to pink noise and the filter, which today give notes up early. At the real
budget only the drawbars change; the noise case needs a budget far below 350 to differ at all.</p>
</section>

<p class="small">How it was made: the honesty readings are <code>core/tests/tools/honesty_cpp.cpp</code> at 48 kHz (the rate
that reproduces the 0.009 to 0.019 the after-stage-5 note gives), the key at sixteen places from 0.900 s to 1.134 s after the
load, a sixty-fourth of a second apart, with honestytest.py's summary and rules. The scripts are in <code>make/</code> beside
this page.</p>
</main>
<script>
/* Each take from its .wav, or, where the host will not serve that media type, from the base64 beside it
   (the painting study's way with strokes.b64.txt): fetched as text, atob'd into bytes, played from a blob. */
(function () {
  var failed = 0;
  function fromText(audio, src) {
    return fetch(src.replace(/\\.wav$/, ".b64.txt")).then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.text();
    }).then(function (t) {
      var bin = atob(t.trim()), bytes = new Uint8Array(bin.length);
      for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      audio.src = URL.createObjectURL(new Blob([bytes], { type: "audio/wav" }));
    });
  }
  document.querySelectorAll("audio[data-src]").forEach(function (audio) {
    var src = audio.getAttribute("data-src");
    fetch(src, { method: "HEAD" }).then(function (r) {
      var type = r.headers.get("content-type") || "";
      if (!r.ok || type.indexOf("audio") < 0) throw new Error("not served as audio");
      audio.src = src;
    }).catch(function () {
      return fromText(audio, src);
    }).catch(function () {
      failed++;
      document.getElementById("status").textContent = failed + " take(s) could not be loaded from here; open the page from a server.";
      audio.src = src;
    });
  });
})();
</script>
</body>
</html>
"""
open(os.path.join(OUT, "index.html"), "w").write(page)
print("dA", dA[1], "dF", dF[1], "pA", pA[1], "pF", pF[1])
