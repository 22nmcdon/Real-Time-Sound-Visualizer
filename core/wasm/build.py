"""Builds the core for the browser, and puts it in the page.

    python3 core/wasm/build.py           build, and write it into web/scope.html
    python3 core/wasm/build.py --check   build, and say whether the page's copy is this one
    python3 core/wasm/build.py --sources say whether the page's copy was built from these sources,
                                         without building (no compiler: what CI runs on every push)

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

Beside the module the page records a hash of what it was built from
(`WASM_CORE_SOURCES`): every file under core/include, the bridge and the
compiler's flags. `--sources` compares that with the tree and needs nothing
but Python, so the site's publishing workflow can refuse a push that changed
the core and did not build it again (17 Nov), on a runner with no wasm32
toolchain. What it cannot see is a build that differs for the same sources -
a new clang - which `--check` still catches where the toolchain is. A change
under core/include the module never reads (a header only the plugin uses)
reads as stale too; building again costs a few seconds and writes the same
bytes with the new hash, which is the cheaper mistake.
"""
import base64, hashlib, os, re, subprocess, sys, tempfile

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

SOURCES = re.compile(r"/\* WASM_CORE_SOURCES ([0-9a-f]{64}|none) \*/")

def sources_hash(source):
    """sha256 over the flags, then each source's path from the root and its bytes, in a fixed order."""
    root = os.path.normpath(ROOT)
    files = [os.path.normpath(source)]
    for at, _, names in os.walk(os.path.join(root, "core", "include")):
        files += [os.path.join(at, n) for n in names]
    h = hashlib.sha256(" ".join(f for f in FLAGS if not f.startswith(root)).encode() + b"\0")
    for path in sorted(set(files), key=lambda p: os.path.relpath(p, root).replace(os.sep, "/")):
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        with open(path, "rb") as f:
            h.update(rel.encode() + b"\0" + f.read().replace(b"\r\n", b"\n") + b"\0")
    return h.hexdigest()

def recorded(page):
    m = SOURCES.search(page)
    return m.group(1) if m else None

def embedded(page):
    a, b = page.index(BEGIN), page.index(END)
    body = page[a + len(BEGIN):b].strip()
    return body[1:-1] if body.startswith('"') else body

def main():
    source = option("--source", os.path.join(HERE, "scope_wasm.cpp"))
    if "--sources" in sys.argv:
        page = open(option("--page", PAGE), encoding="utf-8").read()
        want, have = sources_hash(source), recorded(page)
        same = want == have
        print("the page's core was %s" % ("built from these sources" if same else
              "NOT built from these sources - run core/wasm/build.py (recorded %s, the tree %s)" % (have, want)))
        sys.exit(0 if same else 1)
    wasm = build(source)
    if "--out" in sys.argv:
        open(option("--out", None), "wb").write(wasm)
        return
    text = base64.b64encode(wasm).decode("ascii")
    path = option("--page", PAGE)
    page = open(path, encoding="utf-8").read()
    if "--check" in sys.argv:
        same = embedded(page) == text
        print("the page's core is %s (%d bytes)" % ("this build" if same else "NOT this build - run core/wasm/build.py", len(wasm)))
        # And its record of what it was built from, which --sources reads.
        noted = recorded(page) == sources_hash(source)
        if same and not noted:
            print("but the page's record of its sources is stale - run core/wasm/build.py")
        sys.exit(0 if same and noted else 1)
    a, b = page.index(BEGIN), page.index(END)
    page = page[:a + len(BEGIN)] + '"' + text + '"' + page[b:]
    mark = "/* WASM_CORE_SOURCES %s */" % sources_hash(source)
    page = SOURCES.sub(lambda m: mark, page, count=1) if SOURCES.search(page) else page.replace(
        "const WASM_CORE = " + BEGIN, mark + "\nconst WASM_CORE = " + BEGIN, 1)
    open(path, "w", encoding="utf-8").write(page)
    print("wrote %d bytes of core, %d of base64, into the page" % (len(wasm), len(text)))

main()
