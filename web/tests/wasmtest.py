"""The core in WebAssembly, as the site carries it (stage 5).

The page carries the C++ core compiled, as base64 between two marker
comments, and the site is that core: the instrument whole in an audio
worklet (makeBrainHost), and on the main thread the setup codec the face
reads the instrument's state by. What can go wrong with that, and is checked:

THE PAGE'S COPY IS NOT THIS CORE. The module is generated, not written, and
has to be built again whenever the core changes; `core/wasm/build.py --check`
builds it and compares. That needs clang's wasm32 target and the WASI libc,
which not everyone running the web suite has, so without them the check says
SKIP, by name, rather than passing.

A BROWSER THAT CANNOT RUN IT. Without WebAssembly the site has nothing to
play - the page's own JavaScript engine went in stage 5's step 6 - so it says
so on the screen and under the title, and draws and steps nothing; and a
browser that will not make the module on the main thread cannot read the
instrument's state, which comes as a setup code, so it waits and says why.
Each has its null: the same page with WebAssembly plays the instrument and
says nothing of it.

Until step 6 this suite held the page's two cores to each other in both
worklets - every preset, every preset's effects, the picture's sources, the
setup codecs and the main thread's settings - and the fallbacks to the
JavaScript ones; the JavaScript went, and the compiled core is held to what
it answered by core/tests/core_tests.py and its golden files.
"""
import os, shutil, subprocess, sys, tempfile
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
ROOT = os.path.dirname(ART)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)


print("\n--- the page's copy of the core ---")
def toolchain():
    if not shutil.which("clang++"): return False
    with tempfile.TemporaryDirectory() as tmp:
        probe = os.path.join(tmp, "probe.cpp")
        with open(probe, "w") as f: f.write("#include <vector>\nint main() { return std::vector<int>(1).size(); }\n")
        # Compiled and not linked: whether the target and its headers are
        # here. Whether the core links is the check's business, and fails it.
        return subprocess.run(["clang++", "--target=wasm32-wasi", "--sysroot=/usr", "-c", probe, "-o", os.path.join(tmp, "p.o")],
                              capture_output=True).returncode == 0
if toolchain():
    fresh = subprocess.run([sys.executable, os.path.join(ROOT, "core", "wasm", "build.py"), "--check"],
                           capture_output=True, text=True)
    check("the module in the page is the core as it stands, compiled", fresh.returncode == 0,
          (fresh.stdout + fresh.stderr).strip()[-300:])
else:
    print("  SKIP  the module in the page is the core as it stands: no clang++ with the wasm32-wasi target here")



with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])

    def site(init=None):
        q = b.new_page(viewport={"width": 1400, "height": 900})
        if init: q.add_init_script(init)
        errors = []
        q.on("pageerror", lambda e: errors.append(str(e)))
        q.goto(f"file://{ART}/scope.html"); q.wait_for_timeout(1500)
        first = q.evaluate("() => state.frames + (state.fps > 0 ? 1 : 0)")
        q.wait_for_timeout(600)
        got = q.evaluate("""() => ({ hint: el.playHint.hidden ? '' : el.playHint.textContent, credit: el.credit.textContent,
          kind: state.source ? state.source.kind : null, face: !!instrumentFace(), frames: state.frames, fps: state.fps })""")
        got["first"] = first
        q.close()
        got["errors"] = errors
        return got

    print("\n--- the site in a browser without WebAssembly ---")
    # The null is the same page with WebAssembly, which does not say it.
    bare, wasm = site("delete window.WebAssembly;"), site()
    print("    without: %s\n    with: %s" % ({k: bare[k] for k in ("hint", "kind", "frames")}, {k: wasm[k] for k in ("hint", "kind", "frames")}))
    check("without WebAssembly the screen says the instrument needs it, and so does the line under the title",
          "WebAssembly" in bare["hint"] and "WebAssembly" in bare["credit"], "%r / %r" % (bare["hint"][:80], bare["credit"][:80]))
    check("and nothing plays in its place: it waits, draws no frame and steps nothing, with no errors",
          bare["kind"] == "awaited" and not bare["face"] and bare["frames"] == 0 and bare["fps"] == 0 and not bare["errors"],
          str({k: bare[k] for k in ("kind", "face", "frames", "fps")}) + " " + "; ".join(bare["errors"][:2]))
    check("null: with WebAssembly the page plays the instrument, draws, and says nothing of it",
          "WebAssembly" not in wasm["hint"] and "WebAssembly" not in wasm["credit"] and wasm["kind"] == "host" and wasm["face"]
          and wasm["fps"] > 0, str({k: wasm[k] for k in ("hint", "kind", "face", "fps")}))

    print("\n--- a main thread that will not make the module ---")
    # The page's own WebAssembly.Module refused before it loads; the worklet
    # has a global scope of its own, and its is untouched, so the instrument
    # starts - and the face, which reads its state as a code, waits.
    refused = site("WebAssembly.Module = function () { throw new Error('refused for the test'); };")
    print("    %s" % {k: refused[k] for k in ("hint", "kind", "frames")})
    check("the page says the module will not make here, and why, and waits",
          "refused for the test" in refused["hint"] and "refused for the test" in refused["credit"]
          and refused["frames"] == 0 and refused["fps"] == 0, "%r / %r" % (refused["hint"][:100], refused["frames"]))
    check("with no errors on the page", not refused["errors"], "; ".join(refused["errors"][:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("all wasm checks pass")
