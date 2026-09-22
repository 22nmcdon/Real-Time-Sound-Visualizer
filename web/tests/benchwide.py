import os
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)
    p = b.new_page(viewport={"width": 430, "height": 900})
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.evaluate("() => setView('bench')"); p.wait_for_timeout(500)
    print("viewport 430; documentElement.scrollWidth =",
          p.evaluate("() => document.documentElement.scrollWidth"))
    print("\nelements wider than the viewport, or sticking out past its right edge:")
    for row in p.evaluate("""() => {
      const out = [];
      for (const node of document.querySelectorAll('body *')) {
        const r = node.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) continue;
        if (r.right > window.innerWidth + 0.5 || r.width > window.innerWidth + 0.5) {
          out.push({
            tag: node.tagName.toLowerCase(),
            id: node.id || '', cls: (node.className || '').toString().slice(0, 40),
            w: Math.round(r.width), right: Math.round(r.right),
            parent: (node.parentElement && (node.parentElement.id || node.parentElement.className || '')).toString().slice(0, 30),
          });
        }
      }
      return out.slice(0, 14);
    }"""):
        print("   %-8s %-14s %-24s w=%4d right=%4d   in %s"
              % (row["tag"], row["id"], row["cls"], row["w"], row["right"], row["parent"]))
    b.close()
