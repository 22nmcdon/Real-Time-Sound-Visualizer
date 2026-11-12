"""Measure the graphics-card test (`../gpu/index.html`) in headless Chromium
and screenshot it beside the CPU render of the same moments.

Headless Chromium has no graphics card: it runs WebGL in software
(SwiftShader, on the CPU), so these frame times are a floor - the owner's
machine with a real GPU should be many times faster - and say only that the
page works and roughly how the cost grows with the canvas.

    python3 gpu_measure.py        # writes ../gpu/measure.json and ../build/gpu-*.png
"""
import http.server, json, os, socketserver, threading
from functools import partial
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
GPU = os.path.join(STUDY, "gpu")
ARGS = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--autoplay-policy=no-user-gesture-required"]


def main():
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=GPU)
    handler.log_message = lambda *a: None
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    out = {"renderer": None, "sizes": {}}
    with sync_playwright() as p:
        # The browser the cloud image ships (CHROME, as the repository's suites use it).
        b = p.chromium.launch(args=ARGS, executable_path=os.environ.get("CHROME", "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"))
        page = b.new_page(viewport={"width": 1280, "height": 900})
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.goto(f"http://127.0.0.1:{port}/index.html?jump=end&size=1000")
        page.wait_for_function("window.__ready || (window.__bench && window.__bench.error)", timeout=120000)
        out["renderer"] = page.evaluate("""() => { const g = document.createElement('canvas').getContext('webgl2');
            const e = g && g.getExtension('WEBGL_debug_renderer_info'); return g ? (e ? g.getParameter(e.UNMASKED_RENDERER_WEBGL) : g.getParameter(g.RENDERER)) : null; }""")
        out["timer_query"] = page.evaluate("() => { const g = document.createElement('canvas').getContext('webgl2'); return !!(g && g.getExtension('EXT_disjoint_timer_query_webgl2')); }")
        page.locator(".stage").screenshot(path=os.path.join(STUDY, "build", "gpu-end.png"))
        page.goto(f"http://127.0.0.1:{port}/index.html?jump=mid&size=1000")
        page.wait_for_function("window.__ready", timeout=120000)
        page.locator(".stage").screenshot(path=os.path.join(STUDY, "build", "gpu-mid.png"))
        for size in (512, 1000, 1600):
            page.goto(f"http://127.0.0.1:{port}/index.html?bench={size}")
            page.wait_for_function("window.__bench", timeout=400000, polling=500)
            out["sizes"][str(size)] = page.evaluate("window.__bench")
            print(size, out["sizes"][str(size)])
        out["console_errors"] = errors
        b.close()
    httpd.shutdown()
    json.dump(out, open(os.path.join(GPU, "measure.json"), "w"), indent=1)
    print(out["renderer"], "timer query:", out.get("timer_query"), "errors:", errors[:3])


if __name__ == "__main__":
    main()
