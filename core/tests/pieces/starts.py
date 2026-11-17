"""What the rack's switches start at, against the bank's headings (17 Nov).

Two of the rack's switches give a setting of their own when they have
nothing to put back: the Plane a Twist of 15 (PLANE_START) and the EQ the low
and high shelves up 3 dB (EQ_START), both read from the page here so a change
there is measured here. Most players will only press On, so On must leave a
Settled preset Settled - the reverb's switch was set at 0.15 for the same
reason - and this measures it as web/tests/honestytest.py does, but offline
(core/tests/tools/honesty_cpp.cpp, the instrument itself, the key at a
stated sample), at five key landings across half a second, since where the
key lands moves the reading (web/README.md, 13 Nov) and on the page that
spread is the sound's own, not the timer's. Each Settled preset a switch
would turn on, on each of its probes, at every landing.

The null is the third candidate the Plane's start was chosen against, a Turn
of 25 degrees, which took the Tine piano out of Settled on one landing of
five (web/docs/listening/plane-start/): the same check must go red on it.
"""
import base64, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "..", "..", "..", "web", "scope.html")
HOLD, AFTER = 10.0, 4.5
LANDINGS = [0.9 + 0.11 * k for k in range(5)]
# The Settled presets and their probes, as honestytest.py gives them.
SETTLED = [("Tine piano", [[60]]), ("Tines at the radius", [[60]]), ("Drawbar organ", [[60]]),
           ("Bass under the tine piano", [[36], [67]])]


def starts():
    text = open(PAGE, encoding="utf-8").read()
    out = {}
    for name in ("PLANE_START", "EQ_START"):
        m = re.search(r"const %s = (\[\[.*?\]\]);" % name, text)
        out[name] = {k: float(v) for k, v in json.loads(m.group(1))}
    return out


def mean(xs): return sum(xs) / len(xs) if xs else 0.0


def settled(reads):
    held = [r for r in reads if r[1] == "held"]
    early = mean([m for t, _, m, _ in held if 0.3 <= t < 2.0])
    late = mean([m for t, _, m, _ in held if t >= HOLD - 3.0])
    return early >= 0.008 and late <= 0.015 and late <= early / 2, late


def run(kit):
    check, null = kit.check, kit.null
    exe = kit.build("honesty_cpp")
    codes = kit.preset_codes()
    import subprocess

    def setup_of(code):
        return json.loads(base64.b64decode(code + "=" * (-len(code) % 4)))

    def measure(setup, notes):
        code = base64.b64encode(json.dumps(setup).encode()).decode()
        lates, ok = [], True
        for pre in LANDINGS:
            out = subprocess.run([exe, code, "44100", ",".join(map(str, notes)), "%.4f" % pre, str(HOLD), str(AFTER)],
                                 check=True, capture_output=True, text=True).stdout
            reads = [(float(w[1]), w[2], float(w[3]), float(w[4])) for w in (l.split() for l in out.splitlines()) if w and w[0] == "read"]
            good, late = settled(reads)
            ok = ok and good
            lates.append(late)
        return ok, lates

    given = starts()
    check("the page's two starts read: the Plane's and the EQ's", given["PLANE_START"] == {"planeTwist": 15}
          and given["EQ_START"] == {"eqLow": 30, "eqMid": 0, "eqHigh": 30}, str(given))
    for name, fields, off in (("Plane", given["PLANE_START"], ("planeMirror", "planeLimit", "planeTwist", "planeSnap", "rotate")),
                              ("EQ", given["EQ_START"], ("eqLow", "eqMid", "eqHigh"))):
        probes, bad = 0, []
        for preset, notes_list in SETTLED:
            base = setup_of(codes[preset])
            # Only where the switch would turn the module on: a preset with it on already is switched off by it.
            if any(base.get(k, 0) not in (0, "0") for k in off): continue
            for notes in notes_list:
                ok, lates = measure(dict(base, **fields), notes)
                probes += 1
                if not ok: bad.append("%s %s %s" % (preset, notes, ["%.4f" % x for x in lates]))
        check("the %s's start keeps every Settled preset it would switch on Settled, at five key landings (%d probes)"
              % (name, probes), probes >= 3 and not bad, "; ".join(bad))
    tine = setup_of(codes["Tine piano"])
    ok, lates = measure(dict(tine, rotate=7), [60])
    null("a Turn of 25 degrees, the candidate it was chosen against, takes the Tine piano out of Settled",
         not ok, ", ".join("%.4f" % x for x in lates))
