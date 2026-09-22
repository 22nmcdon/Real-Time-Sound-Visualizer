import os
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
SHOTS = os.path.join(HERE, "shots"); os.makedirs(SHOTS, exist_ok=True)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=[
        "--autoplay-policy=no-user-gesture-required",
        "--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"])
    c = b.new_context(permissions=["microphone"])
    p = c.new_page(); p.set_viewport_size({"width": 1400, "height": 900})
    p.on("pageerror", lambda e: print("PAGEERROR", e))
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.locator("#menuButton").click(); p.wait_for_timeout(150)
    p.locator("#srcMic").click(no_wait_after=True); p.wait_for_timeout(1800)
    p.locator("#micBands").click(no_wait_after=True); p.wait_for_timeout(2000)
    p.screenshot(path=f"{SHOTS}/live-panel.png")
    p.evaluate("() => { applyPreset('b:Bands, stacked'); el.menuButton.click(); }")
    p.wait_for_timeout(2000)
    p.screenshot(path=f"{SHOTS}/live-stacked.png")
    print("stacked:", p.evaluate("() => el.readoutDetail.textContent"))
    p.evaluate("() => applyPreset('b:Bands, low against high')")
    p.wait_for_timeout(2500)
    p.screenshot(path=f"{SHOTS}/live-xy.png")
    print("xy:     ", p.evaluate("() => el.readoutDetail.textContent"))
    print("credit: ", p.evaluate("() => el.credit.textContent"))
    b.close()
