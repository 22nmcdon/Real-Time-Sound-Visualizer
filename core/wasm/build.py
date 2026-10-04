"""Builds the core for the browser, and puts it in the page.

    python3 core/wasm/build.py           build, and write it into web/scope.html
    python3 core/wasm/build.py --check   build, and say whether the page's copy is this one

and for the tests: `--source FILE` builds another copy of the bridge (a
mutant, or one broken on purpose for a null), `--out FILE` writes the module
there rather than into a page, and `--page FILE` checks or writes another copy
of the page.

The page is one file and is opened from the disk as often as it is served, and
a worklet cannot fetch from file://, so the module goes inside it: base64
between two marker comments, `WASM_CORE_BEGIN` and `WASM_CORE_END`. That is
the cost of keeping the page one file - a quarter of a megabyte of text that
is generated, not written, and has to be built again whenever the generator
changes. `--check` is what the web suite runs to say when it has not been.

Built with clang's wasm32 target against the WASI libc and libc++ (Ubuntu:
wasi-libc libc++-18-dev-wasm32 libc++abi-18-dev-wasm32
libclang-rt-18-dev-wasm32). The build is deterministic, so the same core makes
the same bytes and the check can compare them.
"""
import base64, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
PAGE = os.path.join(ROOT, "web", "scope.html")
BEGIN, END = "/* WASM_CORE_BEGIN */", "/* WASM_CORE_END */"
FLAGS = ["--target=wasm32-wasi", "--sysroot=/usr", "-std=c++17", "-O2", "-fno-exceptions", "-fno-rtti",
         "-I", os.path.join(ROOT, "core", "include"), "-mexec-model=reactor", "-Wl,--strip-all",
         "-Wall", "-Wextra", "-Werror"]

def option(name, otherwise):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else otherwise

def build(source):
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "scope.wasm")
        subprocess.run(["clang++", *FLAGS, source, "-lc++abi", "-o", out], check=True)
        return open(out, "rb").read()

def embedded(page):
    a, b = page.index(BEGIN), page.index(END)
    body = page[a + len(BEGIN):b].strip()
    return body[1:-1] if body.startswith('"') else body

def main():
    wasm = build(option("--source", os.path.join(HERE, "scope_wasm.cpp")))
    if "--out" in sys.argv:
        open(option("--out", None), "wb").write(wasm)
        return
    text = base64.b64encode(wasm).decode("ascii")
    path = option("--page", PAGE)
    page = open(path, encoding="utf-8").read()
    if "--check" in sys.argv:
        same = embedded(page) == text
        print("the page's core is %s (%d bytes)" % ("this build" if same else "NOT this build - run core/wasm/build.py", len(wasm)))
        sys.exit(0 if same else 1)
    a, b = page.index(BEGIN), page.index(END)
    page = page[:a + len(BEGIN)] + '"' + text + '"' + page[b:]
    open(path, "w", encoding="utf-8").write(page)
    print("wrote %d bytes of core, %d of base64, into the page" % (len(wasm), len(text)))

main()
