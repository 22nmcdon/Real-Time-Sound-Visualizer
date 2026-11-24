"""The diagnostic report (24 Nov, the owner's: a tester whose sound breaks
up pastes it to them). Settings' This window has Copy diagnostic report,
which puts on the clipboard the browser, its sample rate and latencies, how
long the worklet's blocks have taken since the page opened (mean, 99th
percentile, worst, late), what the voice budget is giving up, and the setup
code. Nothing is sent anywhere.

What would go wrong, and what is checked for it:

- A field missing or not a number: every line is parsed back, by a reader
  that refuses a report with any line gone (the null: the same report with
  its setup line taken out is refused, and one made before the worklet has
  timed a block says so and is refused as a report of block times).
- Block times that are not the worklet's: they grow while the instrument
  plays (two reports a second and a half apart, the second with more
  blocks), the mean is under the worst, the deadline is the block's
  128 frames at the context's rate, and the late count is no more than the
  blocks.
- A setup code that is not the sound: loaded back, it gives the same setup.
- A report sent somewhere: every request the page makes while it copies is
  counted, and there are none; the button says Copied.
- The budget line: under the owner's setup and a chord of three a hand it
  says what is given up; on the plain sine, nothing (the null).
"""
import os, re, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
sys.path.insert(0, HERE)
from unisoncuttest_setup import OWNER, CHORD  # the owner's setup and chord, shared with unisoncuttest

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)
def null(name, ok, detail=""): check("null: " + name, ok, detail)

NUM = r"([0-9]+(?:\.[0-9]+)?)"
def parse(text):
    """The report's lines read back, or None if any is missing or does not read."""
    try:
        lines = dict(l.split(": ", 1) for l in text.split("\n")[1:])
        out = {"browser": lines["Browser"], "site": lines["Site"], "budget": lines["Voice budget"], "code": lines["Setup code"]}
        out["rate"] = float(re.match(NUM + " Hz$", lines["Sample rate"]).group(1))
        lat = re.match(r"(.+); output latency: (.+)$", lines["Base latency"])
        out["latency"] = [None if v == "not given" else float(v[:-3]) for v in lat.groups()]
        blocks = re.match(NUM + r" timed since the page opened, " + NUM + " ms each", lines["Audio blocks"])
        out["blocks"], out["deadline"] = int(float(blocks.group(1))), float(blocks.group(2))
        t = re.match("mean " + NUM + " ms, 99th percentile " + NUM + " ms, worst " + NUM + " ms", lines["Block time"])
        out["mean"], out["p99"], out["worst"] = (float(v) for v in t.groups())
        out["late"] = int(re.match(r"([0-9]+) of ", lines["Late blocks"]).group(1))
        return out
    except Exception:
        return None

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    ctx = b.new_context(viewport={"width": 1400, "height": 900})
    p = ctx.new_page()
    bad, requests = [], []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(1500)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_function("state.source && state.source.kind === 'host'", timeout=30000)

    early = p.evaluate("() => { const keep = state.source.workletTiming; state.source.workletTiming = null; const r = diagnosticReport(); state.source.workletTiming = keep; return r; }")
    null("a report before the worklet has timed a block says so, and is refused as one of block times",
         "none timed yet" in early and parse(early) is None, early.split("\n")[6] if len(early.split("\n")) > 6 else early)

    p.evaluate("() => scopeHost.midi([0x90, 60, 100])"); p.wait_for_timeout(2500)
    p.evaluate("() => showControl('diagCopy')"); p.wait_for_timeout(300)
    p.on("request", lambda r: requests.append(r.url))
    p.locator("#diagCopy").click(); p.wait_for_timeout(600)
    first = p.evaluate("() => window.__diagLast")
    said = p.evaluate("() => document.getElementById('diagCopied').textContent")
    r1 = parse(first)
    print("    " + first.replace("\n", "\n    ")[:900])
    check("the report reads back, every line, from the button", r1 is not None, first[:200])
    r1 = r1 or {}
    check("the button says it was copied, and nothing was asked of the network", said == "Copied" and requests == [],
          "%r, %d requests %s" % (said, len(requests), requests[:2]))
    check("the browser and the site are named", "Chrom" in r1.get("browser", "") and r1.get("site") in ("testing", "stable"), str(r1.get("site")))
    rate = p.evaluate("() => state.source.latencies.rate")
    check("the rate is the context's, and each block's deadline its 128 frames at that rate",
          r1.get("rate") == rate and abs(r1.get("deadline", 0) - 128 / rate * 1000) < 0.01, "%s Hz, %s ms" % (r1.get("rate"), r1.get("deadline")))
    check("the block times are times: mean under the 99th percentile's bin top and the worst, late no more than the blocks",
          0 < r1.get("mean", 0) <= r1.get("worst", -1) and r1.get("mean", 0) <= r1.get("p99", -1) + 0.05 and 0 <= r1.get("late", -1) <= r1.get("blocks", 0)
          and r1.get("blocks", 0) > 100, str({k: r1.get(k) for k in ("blocks", "mean", "p99", "worst", "late")}))
    p.wait_for_timeout(1500)
    p.locator("#diagCopy").click(); p.wait_for_timeout(300)
    r2 = parse(p.evaluate("() => window.__diagLast")) or {}
    check("they are the worklet's own, still counting: a second and a half later, more blocks", r2.get("blocks", 0) > r1.get("blocks", 0),
          "%s then %s" % (r1.get("blocks"), r2.get("blocks")))
    gone = "\n".join(l for l in first.split("\n") if not l.startswith("Setup code"))
    null("the same report with its setup line taken out is refused", parse(gone) is None)
    check("the light sound gives nothing up", r1.get("budget", "").endswith("nothing given up"), r1.get("budget"))
    back = p.evaluate("(c) => { const before = JSON.stringify(snapshot()); loadCode(c); return [before, JSON.stringify(snapshot())]; }", r1.get("code", ""))
    check("its setup code, loaded back, is the same setup", back[0] == back[1], "")
    p.evaluate("() => scopeHost.midi([0x80, 60, 0])")

    p.evaluate("(c) => loadCode(c)", OWNER); p.wait_for_timeout(1200)
    for n in CHORD: p.evaluate("(n) => scopeHost.midi([0x90, n, 100])", n)
    p.wait_for_timeout(2000)
    heavy = parse(p.evaluate("() => diagnosticReport()")) or {}
    check("under the owner's setup and a chord of three a hand the budget line says what is given up",
          "unison" in heavy.get("budget", "") and "nothing given up" not in heavy.get("budget", ""), heavy.get("budget"))
    for n in CHORD: p.evaluate("(n) => scopeHost.midi([0x80, n, 0])", n)
    check("no page errors", not bad, str(bad[:3]))
    b.close()

print()
if fails: print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("diagtest: all checks pass")
