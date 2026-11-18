"""The MSEG mockup's curves against the core's own (web/docs/mockups/mseg).

The page's `levelAt`, given the old envelope's four numbers and nothing else
(the shape a setup from before the MSEG decodes to), against the core's
`Envelope` from core/include/scope/envelope.h stepped at 48 kHz, sample for
sample, held and let go. The null is the page with the release's aim made
relative (a fifth of its own fall, as the decay's is), which must miss where
the key comes up before the sustain - so the check can see the one thing
that makes the old release different. A second null, every stretch straight,
must miss everywhere.

The filter: the page's `svfDb` against the core's `svfStep` run on sines,
four settings, 24 frequencies.

Writes checks/results.json and the numbers into the page's CORE_RESULTS.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/mseg/checks/curves_against_core.py
"""
import json, os, re, subprocess, sys, tempfile
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(os.path.dirname(HERE), "index.html")
CORE = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "..", "core", "include"))
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium")
RATE = 48000
ENV = [("8 ms, 120 ms, 0.70, 180 ms; held 400 ms", 8, 120, 0.7, 180, 19200, 30000),
       ("A pluck: 2 ms, 700 ms, 0, 250 ms; let go at 300 ms, in the decay", 2, 700, 0.0, 250, 14400, 30000),
       ("200 ms, 300 ms, 0.50, 400 ms; let go at 60 ms, in the attack", 200, 300, 0.5, 400, 2880, 30000),
       ("150 ms, 1 s, 0.25, 2 s; held 2 s", 150, 1000, 0.25, 2000, 96000, 200000)]
FILTERS = [("Low pass, 1 kHz, Q 0.71", 1, 1000, 0.7071), ("Low pass, 1.6 kHz, Q 2.06", 1, 1600, 2.06),
           ("High pass, 400 Hz, Q 5", 3, 400, 5), ("Band pass, 2 kHz, Q 1.5", 2, 2000, 1.5)]
FREQS = [30, 50, 80, 120, 200, 300, 450, 700, 900, 1000, 1200, 1500, 1600, 1800, 2000, 2500, 3000, 4000, 5000, 7000, 9000, 12000, 15000, 19000]
# The drawing is the analytic curve; the core is its recursion, which ends a stage on the first sample at
# or past its end - after rounding sometimes one sample after the drawn time, and a note let go after
# that carries the sample's difference into its release. So the drawing is held to 1e-4 of full scale
# (-80 dB), and the nulls must miss by ten times that. The MSEG engine keeps the recursion and the end
# test, so the migration's exactness is the core's own test (mseg-design.md), not this one.
ENV_TOL, NULL_MIN, DB_TOL = 1e-4, 1e-3, 0.01

def main():
    exe = os.path.join(tempfile.mkdtemp(), "env_core")
    subprocess.run(["g++", "-std=c++17", "-O2", "-I" + CORE, os.path.join(HERE, "env_core.cpp"), "-o", exe], check=True)
    core = json.loads(subprocess.run([exe], check=True, capture_output=True, text=True).stdout)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME if os.path.exists(CHROME) else None)
        page = b.new_page()
        page.goto("file://" + PAGE)
        page_env = page.evaluate("""(cases) => cases.map(([a, d, s, r, up, n]) => {
            const ms = (k) => k * 1000 / 48000;
            const run = (bends) => { const e = makeEnv({ attack: a, decay: d, sus: s, release: r }, bends), out = [];
              for (let k = 1; k <= n; k++) out.push(levelAt(e, ms(k), ms(up))); return out; };
            return { page: run(null), relative: run({ release: { p: 0.2 } }),
                     straight: run({ attack: { l: 1 }, decay: { l: 1 }, release: { l: 1 } }) };
          })""", [list(c[1:]) for c in ENV])
        page_f = page.evaluate("([fs, freqs]) => fs.map(([t, hz, q]) => freqs.map((f) => svfDb(t, hz, q, f, 48000)))",
                               [[list(f[1:]) for f in FILTERS], FREQS])
        # The null: the resonance read as the damping (k = Q rather than 1 / Q), which must miss.
        null_f = page.evaluate("([fs, freqs]) => fs.map(([t, hz, q]) => freqs.map((f) => svfDb(t, hz, 1 / q, f, 48000)))",
                               [[list(f[1:]) for f in FILTERS], FREQS])
        b.close()
    rows, ok = [], True
    for i, c in enumerate(ENV):
        cv = core["env"][i]
        pv = page_env[i]["page"]
        err = max(abs(a - b) for a, b in zip(pv, cv))
        # The old envelope ends a stage on the first sample at or past its end, which after rounding
        # can be one sample after the drawn time; the drawing is the curve, so allow that one sample.
        lagged = max(min(abs(pv[k] - cv[k]), abs(pv[k - 1] - cv[k]) if k else 1) for k in range(len(cv)))
        late = lagged < err * 0.5 and err > 1e-9
        rel = max(abs(a - b) for a, b in zip(page_env[i]["relative"], cv))
        st = max(abs(a - b) for a, b in zip(page_env[i]["straight"], cv))
        good = err < ENV_TOL
        ok &= good
        early = c[5] * 1000 / RATE < (c[1] + c[2])
        rows.append({"what": "Envelope: " + c[0], "ok": good, "page": ("%.1e of full scale, %d samples" % (err, len(cv))) if not late else
                     ("%.1e: the core a sample late at a stage's end (%.1e with that sample allowed)" % (err, lagged)),
                     "null": "relative release %s; straight %.3f" % (("%.4f" % rel) if rel > 1e-9 else "0 (released at the sustain, so the same)", st)})
        if early and rel <= NULL_MIN:
            ok = False
            print("NULL FAILED to miss:", c[0])
        if st <= NULL_MIN:
            ok = False
            print("STRAIGHT NULL FAILED to miss:", c[0])
    for i, f in enumerate(FILTERS):
        err = max(abs(a - b) for a, b in zip(page_f[i], core["filter"][i]))
        good = err < DB_TOL
        ok &= good
        nul = max(abs(a - b) for a, b in zip(null_f[i], core["filter"][i]))
        if nul <= 10 * DB_TOL:
            ok = False
            print("FILTER NULL FAILED to miss:", f[0])
        rows.append({"what": "Filter: " + f[0], "ok": good, "page": "%.1e dB at 24 frequencies" % err, "null": "resonance as damping %.2f dB" % nul})
    note = ("Run by checks/curves_against_core.py: the core's Envelope stepped at 48 kHz against the page's levelAt "
            "with the old four numbers, within %g of full scale (-80 dB); where it is not within 1e-12 it is because the core "
            "ends a stage a sample after the drawn time, which the MSEG engine keeps (the design note). The filter to %g dB. %s" % (ENV_TOL, DB_TOL, "All pass." if ok else "SOME FAIL."))
    res = {"rows": rows, "note": note, "ok": ok}
    with open(os.path.join(HERE, "results.json"), "w") as fh:
        json.dump(res, fh, indent=1)
    src = open(PAGE).read()
    src2 = re.sub(r"const CORE_RESULTS = .*?;\n", lambda m: "const CORE_RESULTS = " + json.dumps(res, ensure_ascii=False) + ";\n", src, count=1, flags=re.S)
    open(PAGE, "w").write(src2)
    for r in rows:
        print(("ok  " if r["ok"] else "BAD ") + r["what"] + ": " + r["page"] + " | null: " + r["null"])
    sys.exit(0 if ok else 1)

main()
