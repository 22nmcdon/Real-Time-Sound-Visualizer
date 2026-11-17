"""The mockup's EQ curve against the core's own (core/include/scope/plane.h, Plane::eqBand).

Builds eq_core_response.cpp, then compares the page's eqResponseDb with it over six
settings, 241 frequencies each, at 48 and 44.1 kHz, to 0.01 dB. The null hands the
mid's width to the page as Q unconverted, which must miss where the mid is in.

    CHROME=/opt/pw-browsers/chromium python3 web/docs/mockups/eq/checks/curve_against_core.py
"""
import os, subprocess, sys, tempfile
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
PAGE = "file://" + os.path.join(os.path.dirname(HERE), "index.html")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium")
BIN = os.path.join(tempfile.mkdtemp(), "eqcore")
subprocess.run(["g++", "-std=c++17", "-O1", "-I" + os.path.join(ROOT, "core", "include"),
                os.path.join(HERE, "eq_core_response.cpp"), "-o", BIN], check=True)
# name, gains (dB), positions (0-100), width (oct)
CASES = [
  ("The switch's start: low and high +3.0 dB, at 160 Hz and 4.0 kHz", [3, 0, 3], [50, 50, 50], 1.0),
  ("The mockup's opening: low +3.0, mid -4.0 dB at 688 Hz 1.4 oct, high +3.0", [3, -4, 3], [50, 41, 50], 1.4),
  ("Every band at an end: low +12 at 40 Hz, mid +12 at 8 kHz 0.2 oct, high -12 at 16 kHz", [12, 12, -12], [0, 100, 100], 0.2),
  ("The other ends: low -12 at 640 Hz, mid -12 at 125 Hz 4.0 oct, high +12 at 1 kHz", [-12, -12, 12], [100, 0, 0], 4.0),
  ("The mid alone, +6.5 dB at 1.0 kHz, 1.0 oct", [0, 6.5, 0], [50, 50, 50], 1.0),
  ("Off: every gain at nought", [0, 0, 0], [50, 50, 50], 1.0),
]
RATES = [48000, 44100]
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)
    p = b.new_page(viewport={"width": 1300, "height": 900})
    errs = []
    p.on("console", lambda m: errs.append(m.type + ": " + m.text) if m.type in ("error", "warning") else None)
    p.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
    p.goto(PAGE); p.wait_for_timeout(500)
    freqs = [20 * 1000 ** (i / 240) for i in range(241)]
    rows, lines, settings = [], [], []
    for name, g, pos, w in CASES:
        hz = p.evaluate("(pos) => pos.map((v, k) => eqHz(k, v))", pos)
        e = dict(low=g[0], lowHz=hz[0], mid=g[1], midHz=hz[1], width=w, high=g[2], highHz=hz[2])
        for r in RATES:
            settings.append((name, r, e))
            lines.append(f"{r} {g[0]} {hz[0]!r} {g[1]} {hz[1]!r} {w} {g[2]} {hz[2]!r}")
    out = subprocess.run([BIN], input="\n".join(lines) + "\n", capture_output=True, text=True, check=True).stdout.split("\n")
    worst = 0; worstNull = 1e9
    for (name, r, e), line in zip(settings, out):
        core = [float(v) for v in line.split()]
        page = p.evaluate("([e, f, r]) => eqResponseDb(e, f, r)", [e, freqs, r])
        null = p.evaluate("([e, f, r]) => eqResponseDb(e, f, r, true)", [e, freqs, r])
        d = max(abs(a - c) for a, c in zip(page, core))
        dn = max(abs(a - c) for a, c in zip(null, core))
        worst = max(worst, d)
        if e["mid"] != 0: worstNull = min(worstNull, dn)
        rows.append((name, r, d, dn if e["mid"] != 0 else None, max(core), min(core)))
        print(f"{name[:60]:60s} {r}  page-core {d:.2e} dB   null {dn:.3f} dB   range {min(core):.2f}..{max(core):.2f}")
    print("worst", worst, "dB; null's smallest miss", worstNull, "dB; page errors", errs)
    b.close()
ok = worst < 0.01 and worstNull > 0.01 and not errs
print("PASS" if ok else "FAILED")
sys.exit(0 if ok else 1)
