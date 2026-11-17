"""Focus you can see, and Tab that stays where it is (the outside review, 17 Nov),
and the help sheet's opening lines.

What would go wrong, and what is checked for it:

- a knob with the keyboard's focus looking like one without it. The rule was
  there, an outline on the face's ::before, but that ::before carries the
  mask that cuts the ring out of a disc, and a mask clips its own outline: not
  one pixel moved. Read here as pixels of the accent (DESIGN.md's focus,
  --blush-deep) round the knob, focused against not;
- a right-click menu item with the focus told apart only by a background of
  cream on paper, about 1.05 to 1. Read as accent pixels in the item's box,
  focused against its unfocused neighbour;
- an overlay a screen reader cannot name, or that Tab walks out of: each of
  Settings, Scope & measure, Perform, the Picture's Advanced, the Panes, the
  modulation card's editor, Routings, the preset browser, the help, the
  right-click menu, a control's modulation editor and the info card is
  opened, its role and name read, and Tab and Shift+Tab pressed more times
  than it has stops: the focus must be inside after every press. The null is
  a panel opened with the trap taken away, which must let the focus out, so
  the check can fail;
- the page's language not said (<html lang>), which a reader needs to speak
  it in the right voice;
- the help sheet's opening paragraphs broken a line per key: the rule that
  makes each item's heading a block took every <b> in them, so ?, M, A and K
  each stood alone on a line. Read as where each sits against the text before
  it; the null is an item's heading, which is a block and must stay one.
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + str(detail)) if detail else ""))
    if not ok: fails.append(name)

ACCENT = (0xc0, 0x7f, 0x79)

def accent_pixels(png_bytes):
    from io import BytesIO
    try:
        from PIL import Image
    except ImportError:
        return None
    im = Image.open(BytesIO(png_bytes)).convert("RGB")
    n = 0
    for r, g, b in (im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata()):
        if abs(r - ACCENT[0]) + abs(g - ACCENT[1]) + abs(b - ACCENT[2]) < 40: n += 1
    return n

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(1000)
    ev = p.evaluate

    print("\n--- the page's language ---")
    check("<html lang> is British English", ev("() => document.documentElement.lang") == "en-GB", ev("() => document.documentElement.lang"))

    print("\n--- the help sheet's opening lines ---")
    if not ev("() => el.helpDialog.open"): ev("() => openHelp()")
    p.wait_for_timeout(200)
    lede = ev("""() => Array.from(document.querySelectorAll('#panelScreen .help-lede b')).map((b) => {
      // Beside the words before it or the words after it: a key can wrap to a line's start, but a block has neither.
      const before = b.previousSibling, after = b.nextSibling, r = document.createRange(), q = document.createRange();
      r.setStart(before, Math.max(0, before.textContent.trimEnd().length - 1)); r.setEnd(before, before.textContent.trimEnd().length);
      const lead = after.textContent.length - after.textContent.trimStart().length;
      q.setStart(after, lead); q.setEnd(after, Math.min(after.textContent.length, lead + 1));
      const t = r.getBoundingClientRect(), u = q.getBoundingClientRect(), k = b.getBoundingClientRect();
      return { key: b.textContent, display: getComputedStyle(b).display,
               sameLine: Math.abs(t.top - k.top) < 4 || Math.abs(u.top - k.top) < 4 };
    })""")
    check("the opening paragraphs have keys in them (the case under test)", len(lede) >= 4, [l["key"] for l in lede])
    check("each key sits on the line of the words before it, inline",
          all(l["sameLine"] and l["display"] == "inline" for l in lede), [l for l in lede if not (l["sameLine"] and l["display"] == "inline")])
    heading = ev("() => getComputedStyle(document.querySelector('#panelScreen li:not(.help-lede) > b')).display")
    check("null: an item's heading is still a block", heading == "block", heading)
    ev("() => el.helpDialog.close()")
    p.wait_for_timeout(100)

    print("\n--- focus you can see ---")
    cell = p.locator(".menu-row:has(#pictureAmount) .knob-face").first
    def shot_round(loc, pad=7):
        bb = loc.bounding_box()
        return p.screenshot(clip={"x": bb["x"] - pad, "y": bb["y"] - pad, "width": bb["width"] + 2 * pad, "height": bb["height"] + 2 * pad})
    ev("() => document.activeElement && document.activeElement.blur()")
    p.wait_for_timeout(100)
    rest = accent_pixels(shot_round(cell))
    # Focused from the keyboard: Tab onto it from the control before, so :focus-visible holds.
    # A key first, so the focus that follows is the keyboard's and :focus-visible holds, as after Tab.
    p.keyboard.press("Shift"); ev("() => el.pictureAmount.focus()"); p.wait_for_timeout(150)
    on_it = ev("() => document.activeElement === el.pictureAmount && el.pictureAmount.matches(':focus-visible')")
    focused = accent_pixels(shot_round(cell))
    if rest is None:
        check("PIL is there to read the pixels", False)
    else:
        check("the knob has the keyboard's focus (the case under test)", on_it)
        check("a knob with the focus shows a ring of the accent round it", focused - rest > 80, "%d accent pixels at rest, %d focused" % (rest, focused))
    ev("() => document.activeElement.blur()")
    # The right-click menu, opened from the keyboard so its first item has :focus-visible.
    ev("() => el.pictureAmount.focus()")
    p.keyboard.press("Shift+F10"); p.wait_for_timeout(250)
    items = p.locator(".over.ctx .ctx-item")
    first_focused = ev("() => document.activeElement.classList.contains('ctx-item') && document.activeElement.matches(':focus-visible')")
    p.keyboard.press("ArrowDown"); p.wait_for_timeout(100)
    at = ev("() => Array.from(document.querySelectorAll('.over.ctx .ctx-item')).indexOf(document.activeElement)")
    if rest is not None and at > 0:
        lit = accent_pixels(items.nth(at).screenshot())
        unlit = accent_pixels(items.nth(at - 1).screenshot())
        check("the menu's item has the focus from the keyboard (the case under test)", first_focused)
        check("a menu item with the focus is ringed in the accent, and its neighbour is not",
              lit - unlit > 2 * 60, "%d accent pixels focused, %d not" % (lit, unlit))
    p.keyboard.press("Escape"); p.wait_for_timeout(100)

    print("\n--- every overlay named, and Tab kept inside ---")
    def opener(js): return lambda: ev(js)
    def ctx():
        ev("() => el.pictureAmount.focus()"); p.keyboard.press("Shift+F10")
    def info():
        ev("() => openInfoCard(el.pictureAmount)")
    def control_editor():
        ev("""() => { const row = Array.from(document.querySelectorAll('[data-mod-dest]'))
                        .find((r) => r.querySelector('input[type=range]') && r.getClientRects().length);
                      openModEditor(row.dataset.modDest, row); }""")
    SURFACES = [
        ("Settings", opener("() => el.menuButton.click()"), "#menuPanel"),
        ("Scope & measure", opener("() => el.measureButton.click()"), "#measurePanel"),
        ("Perform", opener("() => el.performButton.click()"), "#performPanel"),
        ("the Picture's Advanced", opener("() => el.pictureMore.click()"), "#picturePanel"),
        ("the Panes", opener("() => { el.pictureMore.click(); el.panesButton.click(); }"), "#panesPanel"),
        ("a card's editor", opener("() => pressModCard('lfo1')"), "#modEditor"),
        ("Routings", opener("() => el.routingsButton.click()"), "#routingsPanel"),
        ("the preset browser", opener("() => openPresets()"), "#presetDialog"),
        ("the help", opener("() => openHelp()"), "#helpDialog"),
        ("the right-click menu", ctx, ".over.ctx"),
        ("the info card", info, ".over:not(.ctx)"),
        ("a control's modulation editor", control_editor, ".over:not(.ctx)"),
    ]
    def close_all():
        for _ in range(3): p.keyboard.press("Escape")
        ev("""() => { closeOverlay(); setMenuOpen(false); setMeasureOpen(false); setPerformOpen(false); setPictureOpen(false);
                      setPanesOpen(false); if (typeof closeModCard === 'function') closeModCard(); setRoutingsOpen(false);
                      if (el.presetDialog.open) el.presetDialog.close(); if (el.helpDialog.open) el.helpDialog.close(); }""")
        p.wait_for_timeout(100)
    def walk(sel, presses):
        out = []
        for key in ["Tab"] * presses + ["Shift+Tab"] * presses:
            p.keyboard.press(key)
            out.append(ev("(s) => { const c = document.querySelector(s); return !!(c && c.contains(document.activeElement)); }", sel))
        return out
    for name, open_it, sel in SURFACES:
        close_all()
        open_it(); p.wait_for_timeout(300)
        info_ = ev("""(s) => { const c = document.querySelector(s); if (!c) return null;
          const named = c.getAttribute('aria-labelledby') ? (document.getElementById(c.getAttribute('aria-labelledby')) || {}).textContent : c.getAttribute('aria-label');
          const stops = c.querySelectorAll('button, input, select, textarea, [tabindex]:not([tabindex="-1"])').length;
          return { role: c.getAttribute('role') || (c.tagName === 'DIALOG' ? 'dialog' : ''), modal: c.getAttribute('aria-modal') || (c.tagName === 'DIALOG' && c.matches(':modal') ? 'true' : ''),
                   named: (named || '').trim(), stops, shown: c.getClientRects().length > 0 }; }""", sel)
        if not info_ or not info_["shown"]:
            check("%s opens (the case under test)" % name, False, info_); continue
        role_ok = info_["role"] in ("dialog", "menu")
        check("%s is a %s, named %r" % (name, info_["role"] or "nothing", info_["named"][:30]),
              role_ok and info_["named"] and (info_["role"] == "menu" or info_["modal"] == "true"), info_)
        inside = walk(sel, min(info_["stops"], 60) + 3)
        check("%s keeps Tab and Shift+Tab inside, %d presses each way" % (name, len(inside) // 2), all(inside),
              "out at press %s" % [i for i, x in enumerate(inside) if not x][:5])
    # The null: Settings with the trap taken away must let the focus out.
    close_all()
    ev("() => { window.__noTrap = true; }")
    el_open = ev("() => el.menuButton.click()"); p.wait_for_timeout(200)
    stops = ev("() => el.menuPanel.querySelectorAll('button, input, select, textarea, [tabindex]:not([tabindex=\"-1\"])').length")
    left = walk("#menuPanel", stops + 3)
    check("null: without the trap Tab leaves Settings, so the check above can fail", not all(left))
    ev("() => { window.__noTrap = false; }")
    close_all()

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\nall passed" if not fails else "\n%d FAILED:\n  %s" % (len(fails), "\n  ".join(fails)))
sys.exit(1 if fails else 0)
