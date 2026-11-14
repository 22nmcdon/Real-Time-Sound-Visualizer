"""The page's own monitor chain, in a browser, on a sound handed to it
(stage 5, step 5a): the chain `makeMonitorChain` builds - its limiter and
clamp as the browser's own nodes - made on an OfflineAudioContext and fed a
stereo file, so parity can hold the core's port of them (scope/limiter.h) to
what the page's speakers get, sample for sample.

    python3 limiter_page.py IN OUT RATE EVERY MODE [RELEASE]

IN is float32 pairs interleaved, as render_cpp records them; OUT gets the
chain's output the same way, and OUT.json the limiter's reduction read every EVERY frames (a multiple of 128, so each read falls between two
of the context's quanta). MODE is `limited`, the chain every source had
before 5a, or `instrument`, the instrument's own since (no limiter, the
backstop for the clamp). RELEASE, for a null, sets the limiter's release.
Scope & measure's "heard" is left where the page opens it, before the shaped
side, so the chain between the input and the limiter is the identity.
"""
import base64, json, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "..", "..", "..", "web", "scope.html")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium")

RUN = """async ([b64, rate, every, mode, release]) => {
  const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
  const pairs = new Float32Array(bytes.buffer);
  const n = pairs.length / 2;
  const ctx = new OfflineAudioContext(2, n, rate);
  const buf = ctx.createBuffer(2, n, rate);
  const l = new Float32Array(n), r = new Float32Array(n);
  for (let k = 0; k < n; k++) { l[k] = pairs[2 * k]; r[k] = pairs[2 * k + 1]; }
  buf.copyToChannel(l, 0); buf.copyToChannel(r, 1);
  const src = ctx.createBufferSource();
  src.buffer = buf;
  const chain = makeMonitorChain(ctx, { limited: mode === "limited" });
  // Out of the page's set, so its frames do not glide this chain's gains while it renders.
  monitorChains.delete(chain);
  if (release !== null && chain.limiter) chain.limiter.release.value = release;
  src.connect(chain.input);
  const reds = [];
  for (let f = every; f < n; f += every) {
    ctx.suspend(f / rate).then(() => { reds.push(chain.limiter ? chain.limiter.reduction : 0); ctx.resume(); });
  }
  src.start(0);
  const out = await ctx.startRendering();
  const a = out.getChannelData(0), b = out.getChannelData(1);
  const o = new Float32Array(2 * n);
  for (let k = 0; k < n; k++) { o[2 * k] = a[k]; o[2 * k + 1] = b[k]; }
  const u = new Uint8Array(o.buffer);
  let s = "";
  for (let i = 0; i < u.length; i += 8192) s += String.fromCharCode.apply(null, u.subarray(i, i + 8192));
  return [btoa(s), reds];
}"""


def main():
    src, dst, rate, every, mode = sys.argv[1], sys.argv[2], float(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
    release = float(sys.argv[6]) if len(sys.argv) > 6 else None
    data = open(src, "rb").read()
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
        page = browser.new_page()
        page.goto("file://" + os.path.abspath(PAGE))
        page.wait_for_function("typeof makeMonitorChain === 'function'")
        out, reds = page.evaluate(RUN, [base64.b64encode(data).decode(), rate, every, mode, release])
        browser.close()
    with open(dst, "wb") as f: f.write(base64.b64decode(out))
    with open(dst + ".json", "w") as f: f.write(json.dumps(reds))


main()
