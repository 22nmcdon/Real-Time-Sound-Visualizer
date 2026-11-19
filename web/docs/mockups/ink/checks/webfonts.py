"""The brand's webfonts for these checks' Chromium.

The pages load Jost, Playfair Display and Cormorant Garamond from Google Fonts.
Headless Chromium in the cloud sessions cannot fetch them itself (it does not
trust the network proxy's certificate), so without this every width was
measured in a fallback face, which the owner never sees. Python can, so each
font request is routed through it. Offline, the fonts stay missing and
`loaded()` says so; the checks report which faces they measured in.
"""
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"

def _handle(route):
    try:
        r = urllib.request.urlopen(urllib.request.Request(route.request.url, headers={"User-Agent": UA}), timeout=20)
        route.fulfill(status=200, body=r.read(), headers={"content-type": r.headers.get("content-type", ""), "access-control-allow-origin": "*"})
    except Exception:
        route.abort()

def route(target):
    """Route a page's or a context's font requests through Python."""
    target.route("https://fonts.googleapis.com/**", _handle)
    target.route("https://fonts.gstatic.com/**", _handle)

LOADED = "() => document.fonts.check('300 12px Jost') && document.fonts.check('500 14px \"Playfair Display\"')"

def settle(page):
    """Wait for the faces, and say whether they came."""
    page.evaluate("() => document.fonts.ready")
    page.wait_for_timeout(300)
    return page.evaluate(LOADED)
