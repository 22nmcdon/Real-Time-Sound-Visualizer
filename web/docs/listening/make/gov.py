import phrase, json, sys
DRAW = {"v": 11, "shape": "drawbars", "bShape": "drawbars", "bars": "888000000", "bBars": "888000000", "oscUnison": 7, "bUnison": 7,
        "oscSpread": 12, "bSpread": 12, "freq": 220, "midiMode": "poly", "layers": "split", "splitAt": 60, "amp": 30, "bAmp": 30,
        "rel": 300, "bRel": 300, "display": "xy", "pictureAmount": 0, "polyRound": True}
PINK = {"v": 11, "shape": "pink", "bShape": "pink", "vcfType": 1, "vcfCut": 500, "vcfRes": 30, "bVcf": 1, "bVcfCut": 650, "bVcfRes": 30,
        "midiMode": "poly", "layers": "split", "splitAt": 60, "amp": 40, "bAmp": 40, "rel": 400, "bRel": 400, "display": "xy",
        "pictureAmount": 0, "polyRound": True}
EVD = phrase.notes_script([48, 52, 55, 59, 64, 67, 71, 74], [(1.4, 76), (2.1, 79), (2.8, 83), (3.5, 86)], chord_off=4.6, over_len=0.6)
EVP = phrase.notes_script([36, 43, 48, 52, 55, 62, 67, 72], [(1.4, 74), (2.1, 76), (2.8, 79), (3.5, 84)], chord_off=4.6, over_len=0.6)
def rows(out):
    r = []
    for l in out.split("\n"):
        w = l.split()
        if w and w[0] == "at": r.append({"t": float(w[1])})
        elif w and w[0] == "budget": r[-1]["b"] = w[1:]
    return r
def show(name, setup, ev, exe):
    out = phrase.render(setup, ev, name + ".raw", exe=exe, budget_every=0.05)
    last = None
    for r in rows(out):
        b = r["b"]; units, aA, aB, uA, uB, af, f, sil = b[:8]
        pool = b[8:]
        live = [p for p in pool if p.split(":")[3] == "0"]
        heldcut = [p for p in pool if p.split(":")[2] == "1" and p.split(":")[3] == "1"]
        key = (uA, uB, f, len(live), tuple(sorted(heldcut)))
        if key != last:
            print("  %.2f units %s copies %s/%s,%s/%s %sx live %d held-let-go %s" % (r["t"], units, uA, aA, uB, aB, f, len(live), heldcut))
            last = key
if __name__ == "__main__":
    for v in ("asis", "fit"):
        print("drawbars x7,", v); show("draw-" + v, DRAW, EVD, "bin/render-%s-350" % v)
    for v in ("asis", "fit"):
        print("pink+filter, budget 45,", v); show("pink-" + v, PINK, EVP, "bin/render-%s-45" % v)
