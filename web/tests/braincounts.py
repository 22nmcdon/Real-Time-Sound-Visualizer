#!/usr/bin/env python3
"""The stage-5 inventory's harness (plugin/STAGE5-INVENTORY.md).

    python3 braincounts.py SUITE.py [args]      run one suite, dumping the counts
    python3 run.py --brain-counts DIR           every suite so, one file each in DIR

The page counts each of its brain's per-frame steps that does something
(`brainCount` at the top of its script). This runs a suite unchanged, with
Playwright's sync API wrapped so that before a page navigates, reloads or
closes - or its context, its browser or Playwright itself goes - the page is
asked for its counts and they are taken, which clears them. So each record is
a delta since the last, and a page read twice is never counted twice.

What it cannot see: a navigation the suite makes from inside the page (a
`location.reload()` in an evaluate, a click on a link), which loses the counts
since the last record. The suites that do it are few and named in the
inventory; it is a gap in coverage, never a count made up. The records go to
the file named by BRAIN_COUNTS as one JSON object a line - the suite, the page's
address, and its counts - and the aggregate is `braincounts.py --sum DIR`.
"""
import atexit, json, os, runpy, sys

TAKE = """() => {
  const c = globalThis.__brainCounts;
  if (!c) return null;
  const out = Object.assign({}, c);
  for (const k of Object.keys(c)) delete c[k];
  return { url: location.href, counts: out };
}"""


def install(out_path, suite):
    from playwright.sync_api import _generated as g
    pages = []          # every page seen, in order, for the ones never closed
    taken = set()       # pages already closed and read

    def record(page, why):
        if id(page) in taken:
            return
        try:
            got = page.evaluate(TAKE)
        except Exception:
            return      # closed under us, or a page with no script: nothing to read
        if not got or not got["counts"]:
            return
        with open(out_path, "a") as f:
            f.write(json.dumps({"suite": suite, "why": why, "url": got["url"],
                                "counts": got["counts"]}) + "\n")

    def seen(page):
        if all(p is not page for p in pages):
            pages.append(page)
        return page

    def wrap(cls, name, before):
        real = getattr(cls, name)
        def wrapped(self, *a, **k):
            before(self)
            result = real(self, *a, **k)
            return result
        setattr(cls, name, wrapped)

    # Pages are noted as they are made, so the last can be read at the end.
    for cls, name in ((g.BrowserContext, "new_page"), (g.Browser, "new_page")):
        real = getattr(cls, name)
        def made(self, *a, _real=real, **k):
            return seen(_real(self, *a, **k))
        setattr(cls, name, made)

    def page_before(why):
        def before(page):
            seen(page)
            record(page, why)
        return before

    for name in ("goto", "reload", "set_content", "go_back", "go_forward"):
        wrap(g.Page, name, page_before(name))

    def page_close(page):
        record(page, "close")
        taken.add(id(page))
    wrap(g.Page, "close", page_close)

    def context_close(context):
        for page in list(context.pages):
            page_close(page)
    wrap(g.BrowserContext, "close", context_close)

    def browser_close(browser):
        for context in list(browser.contexts):
            context_close(context)
    wrap(g.Browser, "close", browser_close)

    holders = []        # browsers and persistent contexts, whose pages a suite may never have made itself
    for cls, name in ((g.BrowserType, "launch"), (g.BrowserType, "launch_persistent_context")):
        real = getattr(cls, name)
        def launched(self, *a, _real=real, **k):
            made = _real(self, *a, **k)
            holders.append(made)
            return made
        setattr(cls, name, launched)

    def everything():
        for holder in holders:
            try:
                contexts = holder.contexts if hasattr(holder, "contexts") else [holder]
                for context in contexts:
                    for page in context.pages:
                        seen(page)
            except Exception:
                pass
        for page in list(pages):
            try:
                if not page.is_closed():
                    page_close(page)
            except Exception:
                pass

    # A suite that leaves `with sync_playwright()` without closing anything.
    from playwright.sync_api._context_manager import PlaywrightContextManager
    real_exit = PlaywrightContextManager.__exit__
    def exit_(self, *a):
        everything()
        return real_exit(self, *a)
    PlaywrightContextManager.__exit__ = exit_
    wrap(g.Playwright, "stop", lambda _self: everything())
    atexit.register(everything)


def total(directory):
    """Every record in DIR, summed: by key, the default site's and ?brain=js's
    apart, with the suites each key was seen in on the default."""
    from urllib.parse import urlparse, parse_qs
    sums = {}
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".jsonl"):
            continue
        for line in open(os.path.join(directory, name)):
            r = json.loads(line)
            q = parse_qs(urlparse(r["url"]).query)
            brain = (q.get("brain") or ["core"])[0]
            core = (q.get("core") or ["wasm"])[0]
            if brain == "js":
                mode = "brain=js&core=js" if core == "js" else "brain=js"
            else:
                mode = "core=js" if core == "js" else "default"
            for key, n in r["counts"].items():
                cell = sums.setdefault(mode, {}).setdefault(key, {"n": 0, "suites": {}})
                cell["n"] += n
                cell["suites"][r["suite"]] = cell["suites"].get(r["suite"], 0) + n
    return sums


if __name__ == "__main__":
    if sys.argv[1:2] == ["--sum"]:
        json.dump(total(sys.argv[2]), sys.stdout, indent=1, sort_keys=True)
        sys.exit(0)
    script = sys.argv[1]
    suite = os.path.splitext(os.path.basename(script))[0]
    install(os.environ.get("BRAIN_COUNTS") or suite + ".brain.jsonl", suite)
    sys.argv = sys.argv[1:]
    sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
    runpy.run_path(script, run_name="__main__")
