"""Everything the listening page carries: honesty over sixteen key times for each version, the renders as WAV,
and their base64 beside them; numbers into numbers.json."""
import base64, json, os, sys
import measure, phrase, gov
OUT = "/home/user/Real-Time-Sound-Visualizer/web/docs/listening"
os.makedirs(OUT, exist_ok=True)
c = [l.strip() for l in open("codes.txt")]
btp, pad, tp = (measure.decode(x) for x in c)
def w(base, **kw): s = dict(base); s.update(kw); return s
PHRASE = phrase.notes_script([36, 60, 64, 67], [(1.5, 72), (2.2, 76), (2.9, 79), (3.6, 76)], chord_off=4.9, over_len=0.6)
VERSIONS = [
 ("btp", "btp-dry", "As shipped, the reverb off", w(btp), True),
 ("btp", "btp-on", "The reverb switched on (Mix 15)", w(btp, reverbMix=15), True),
 ("btp", "btp-mix6", "Candidate: Mix 6", w(btp, reverbMix=6), True),
 ("btp", "btp-mix4", "Candidate: Mix 4", w(btp, reverbMix=4), True),
 ("btp", "btp-tone30", "Candidate: Mix 15, Tone 30 (a darker tail)", w(btp, reverbMix=15, reverbTone=30), True),
 ("tp", "tp-dry", "Tine piano alone, as shipped, no reverb", w(tp), True),
 ("pad", "pad-on", "The reverb switched on (Mix 15)", w(pad, reverbMix=15), True),
 ("pad", "pad-mix25", "Candidate: Mix 25", w(pad, reverbMix=25), True),
 ("pad", "pad-scan30", "Candidate: Mix 15, the bass hand's Scan 25 to 30", w(pad, reverbMix=15, oscScan=30), True),
 ("pad", "pad-scan35", "Candidate: Mix 15, the bass hand's Scan 25 to 35", w(pad, reverbMix=15, oscScan=35), True),
]
# Measured, not rendered: the shorter reverbs tried for the tine piano, which did not sit clearly inside.
MEASURED_ONLY = [
 ("btp", "Mix 15, Size 20 (shorter)", w(btp, reverbMix=15, reverbSize=20)),
 ("btp", "Mix 15, Size 10 (shorter)", w(btp, reverbMix=15, reverbSize=10)),
 ("btp", "Mix 10", w(btp, reverbMix=10)),
 ("btp", "Mix 8", w(btp, reverbMix=8)),
 ("pad", "As shipped, the reverb off", w(pad)),
 ("pad", "Mix 20", w(pad, reverbMix=20)),
 ("pad", "Mix 15, Strike 40 to 50", w(pad, reverbMix=15, scanStrike=50)),
 ("pad", "Mix 15, the pad hand's Scan 60 to 70", w(pad, reverbMix=15, bScan=70)),
]
def probes(group): return [[60]] if group == "tp" else [[36], [67]]
def stats(setup, group):
    out = {}
    for notes in probes(group):
        ms = measure.sweep(setup, notes)
        lates = [m["late"] for m in ms]; earlies = [m["early"] for m in ms]
        out[str(notes[0])] = {"late": [min(lates), max(lates), measure.mean(lates)], "early": [min(earlies), max(earlies)],
                              "settled": sum(m["v"]["Settled"] for m in ms), "breathing": sum(m["v"]["Breathing"] for m in ms)}
    return out
def save_wav(name, raw):
    L, R = phrase.stereo(raw)
    path = os.path.join(OUT, name + ".wav")
    phrase.wav(path, [L])           # the left channel alone: see the page
    open(path[:-4] + ".b64.txt", "w").write(base64.b64encode(open(path, "rb").read()).decode())
    return max(abs(x) for x in L)
numbers = {"versions": [], "measured": [], "budget": []}
for group, name, label, setup, render in VERSIONS:
    st = stats(setup, group)
    peak = None
    if render:
        phrase.render(setup, PHRASE, name + ".raw"); peak = save_wav(name, name + ".raw")
    numbers["versions"].append({"group": group, "file": name, "label": label, "setup": setup, "honesty": st, "peak": peak})
    print(name, json.dumps(st), peak, flush=True)
for group, label, setup in MEASURED_ONLY:
    st = stats(setup, group)
    numbers["measured"].append({"group": group, "label": label, "honesty": st}); print(label, json.dumps(st), flush=True)
for case, setup, ev, budget in (("draw", gov.DRAW, gov.EVD, 350), ("pink", gov.PINK, gov.EVP, 45)):
    for v in ("asis", "fit"):
        name = "%s-%s" % (case, v)
        out = phrase.render(setup, ev, name + ".raw", exe="bin/render-%s-%d" % (v, budget), budget_every=0.05)
        peak = save_wav(name, name + ".raw")
        numbers["budget"].append({"file": name, "budget": budget, "setup": setup, "rows": [r for r in gov.rows(out)], "peak": peak})
        print(name, peak, flush=True)
json.dump(numbers, open("numbers.json", "w"), indent=1)
