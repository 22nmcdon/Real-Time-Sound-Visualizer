"""Code with no caller (the outside review, 17 Nov).

What would go wrong: a function left behind when what called it went - the
review found clearInfo, an empty SEARCH_SKIP, an observer whose callback did
nothing and a CSS rule nothing wore. The cheap half of that is checkable:
every top-level function and arrow constant in the page's script is named
somewhere besides its own definition - the page, a suite, the plugin, the
core's tools - or it is dead. (A rule nothing wears and a constant read only
by itself are not caught here; web/README.md says how a name can look unread
and not be.) The null is the page's text with one orphan planted in it,
which must be found. No browser.
"""
import glob, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
ROOT = os.path.dirname(ART)

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + str(detail)) if detail else ""))
    if not ok: fails.append(name)

page = open(os.path.join(ART, "scope.html"), encoding="utf-8").read()
others = []
for pattern in ["web/tests/*.py", "web/tests/*.mjs", "web/tests/*.js", "web/tools/*.py", "plugin/**/*", "core/tests/**/*.py", "core/tests/tools/*"]:
    for path in glob.glob(os.path.join(ROOT, pattern), recursive=True):
        # Not this file, which names what it plants and what the review found.
        if os.path.isdir(path) or path.endswith(("check.js", "compiled_core.js", "deadtest.py")): continue
        try: others.append(open(path, encoding="utf-8", errors="ignore").read())
        except OSError: pass
elsewhere = "\n".join(others)

def orphans(text):
    names = set(re.findall(r"^(?:async )?function (\w+)\(", text, re.M))
    names |= set(re.findall(r"^const (\w+) = (?:\(|function|\w+ =>|async)", text, re.M))
    out = []
    for name in sorted(names):
        word = re.compile(r"\b" + re.escape(name) + r"\b")
        if len(word.findall(text)) <= 1 and not word.search(elsewhere): out.append(name)
    return out, len(names)

found, count = orphans(page)
print("\n--- every function has a caller ---")
check("the page's top-level functions are named (the case under test)", count > 500, count)
check("none of them is named only where it is defined", not found, found)
planted, _ = orphans(page + "\nfunction plantedOrphanForTheNull() { return 1; }\n")
check("null: a function planted with no caller is found", planted == found + ["plantedOrphanForTheNull"] or "plantedOrphanForTheNull" in planted, planted)

print("\nall passed" if not fails else "\n%d FAILED:\n  %s" % (len(fails), "\n  ".join(fails)))
sys.exit(1 if fails else 0)
