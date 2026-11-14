"""What the face holds that the core's panel must hold the same, read off the
default page in a browser: every slider's range, step and starting value and
every menu's options and the one it shows on the defaults (and the sliders
the morph walks, in its order); the
preset bank, as the page carries it; the base it opens on; and the
modulation sources it has registered, with their reach. Nothing here plays:
these are the face's own tables, which parity's restore section holds
restore_cpp's to, character for character.

Until stage 5's step 6 this was restore_page.py, which also ran the page's
own `restore` - on the page's own brain, by parity's init script - and wrote
out what each setup left in the page's generator, keyboard, oscillators and
effects. The brain went with step 6; what it answered for every setup parity
loads is kept in core/tests/golden/restore.json.gz, recorded the day before
it was deleted, and the core's restore is held to that.

    python3 page_tables.py --controls       the panel's sliders and menus, and the morph's
    python3 page_tables.py --sources        the page's sources and their reach
    python3 page_tables.py --presets        every preset's setup, one JSON line each
    python3 page_tables.py --library        the whole bank, as PRESETS
    python3 page_tables.py --base           the base it opens on
"""
import json, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "..", "..", "..", "web", "scope.html")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

# Every slider and menu: what a value written into it becomes is the browser's
# business, so the port carries each one's range, step and options.
# And the sliders the morph walks, in its order.
CONTROLS = """() => {
  const out = { ranges: {}, selects: {} };
  for (const input of document.querySelectorAll('input[type="range"][id]')) {
    out.ranges[input.id] = { min: input.min, max: input.max, step: input.step, value: input.defaultValue };
  }
  for (const select of document.querySelectorAll('select[id]')) {
    out.selects[select.id] = { options: Array.from(select.options).map((o) => o.value), value: select.value };
  }
  out.morph = MORPH_IDS;
  return JSON.stringify(out);
}"""


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto("file://" + os.path.abspath(PAGE))
        page.wait_for_function("typeof MORPH_IDS !== 'undefined' && typeof PRESETS !== 'undefined'")
        # Once the instrument has answered and the page has given it the base
        # it opens on, the page put on the defaults, which the core's panel
        # starts from - as restore_page.py did before it read the controls.
        page.wait_for_function("state.source && state.source.kind === 'host' && !!instrumentFace()", timeout=20000)
        page.wait_for_timeout(500)
        page.evaluate("() => restore(Object.assign({}, DEFAULTS))")
        what = sys.argv[1]
        if what == "--controls":
            print(page.evaluate(CONTROLS))
        elif what == "--presets":
            for line in page.evaluate("""() => PRESETS.flatMap(([, entries]) => entries.map(([, setup]) => JSON.stringify(setup)))"""):
                print(line)
        elif what == "--base":
            print(page.evaluate("() => JSON.stringify(BASE_SETUP)"))
        elif what == "--library":
            print(page.evaluate("() => JSON.stringify(PRESETS)"))
        elif what == "--sources":
            # The sources the page has registered, with the reach `touchRoutings`
            # holds a stored depth to, and which are events: the C++ runner
            # registers stand-ins for them.
            print(page.evaluate("""() => JSON.stringify([...MOD_SOURCES.values()].map((s) =>
              ({ id: s.id, reach: s.reach > 0 ? s.reach : 0, varies: !!s.reachVaries, event: s.event === true })))"""))
        else:
            raise SystemExit("page_tables.py: --controls, --sources, --presets, --library or --base")
        browser.close()
        if errors:
            print("page errors: " + "; ".join(errors[:3]), file=sys.stderr)
            sys.exit(1)


main()
