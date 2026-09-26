"""Stage L's new figures and solids, and the route every solid is drawn by.

Against the way each would fail:

- a route that jumps, misses an edge, or does not close: every solid's route
  - the three written out and the four built by `eulerRoute` - is checked
  step by step against the solid's own edges, and must return where it
  began;
- a route that retraces more than it must: each draws exactly its edges plus
  one for every pair of odd corners, which is the least any closed route
  can - 16, 8, 12, 40, 36, 144 and 210 segments;
- a builder that draws something when it cannot draw everything: given a
  shape whose odd corners cannot be paired along its edges, it refuses;
- a figure that jumps or does not close, or leaves the screen: the polygon
  and the butterfly return to where they began without a jump, and stay
  inside full scale while filling it;
- a figure that is some other figure: the polygon's corners are where n
  sides put them, and the butterfly is Temple Fay's formula, computed here
  independently, at points round the curve;
- a menu that does not offer them, or offers a name that draws the cube:
  every new name is in its menu, and on the page each solid draws a picture
  of its own.
"""
import math, os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def butterfly(t):
    """Temple Fay's curve, as the page is meant to draw it."""
    th = t * 12 * math.pi
    r = math.exp(math.cos(th)) - 2 * math.cos(4 * th) - math.sin(th / 12) ** 5
    return (math.sin(th) * r / 2.907, (math.cos(th) * r - 0.661) / 2.907)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()

    print("\n--- the routes ---")
    routes = p.evaluate("""() => MODELS.map((m) => {
      // The three written-out tables carry no edge list; they are regular
      // solids, so their edges are the shortest distances, as the built ones'.
      const edges = m.edges || nearestEdges(m.v);
      const key = (a, c) => (a < c ? a + '-' + c : c + '-' + a);
      const all = new Set(edges.map(([a, c]) => key(a, c)));
      const drawn = new Set();
      let along = true;
      for (let i = 0; i + 1 < m.route.length; i++) {
        const k = key(m.route[i], m.route[i + 1]);
        if (!all.has(k)) along = false;
        drawn.add(k);
      }
      const degree = new Array(m.v.length).fill(0);
      for (const [a, c] of edges) { degree[a]++; degree[c]++; }
      return { name: m.name, edges: edges.length, odd: degree.filter((d) => d % 2).length,
               segments: m.route.length - 1, closed: m.route[0] === m.route[m.route.length - 1],
               along, every: drawn.size === all.size };
    })""")
    for r in routes:
        print("    %-12s %3d edges, %2d odd corners, %3d segments" % (r["name"], r["edges"], r["odd"], r["segments"]))
    check("every solid's route closes, steps only along its edges, and draws every one",
          all(r["closed"] and r["along"] and r["every"] for r in routes) and len(routes) == 7,
          str([(r["name"], r["closed"], r["along"], r["every"]) for r in routes]))
    check("and retraces no more than it must: its edges and one for each pair of odd corners",
          [r["segments"] for r in routes] == [16, 8, 12, 40, 36, 144, 210]
          and all(r["segments"] == r["edges"] + r["odd"] // 2 for r in routes),
          str([r["segments"] for r in routes]))

    refused = p.evaluate("""() => {
      const tries = { star: [[0, 1], [0, 2], [0, 3]], path: [[0, 1], [1, 2]] };
      const out = {};
      for (const [name, edges] of Object.entries(tries)) {
        try { eulerRoute(4, edges); out[name] = 'drawn'; } catch (e) { out[name] = 'refused'; }
      }
      out.square = eulerRoute(4, [[0, 1], [1, 2], [2, 3], [3, 0]]);
      return out;
    }""")
    check("a shape whose odd corners cannot be paired along its edges is refused, and a cycle is drawn once round",
          refused["star"] == "refused" and refused["path"] == "refused" and len(refused["square"]) == 5,
          str(refused))

    # Which knot: (3, 2, 7), computed here on its own and scaled to a unit
    # radius as the page scales every solid. Without this, a knot of any
    # other frequencies was still a closed loop of 210 edges drawing a
    # picture of its own, and the mutation pass could not tell them apart.
    got = p.evaluate("() => MODEL_BY_NAME.get('Knot').v")
    raw = []
    for i in range(210):
        t = i / 210 * 2 * math.pi
        raw.append((math.cos(3 * t + 0.7), math.cos(2 * t + 0.2), math.cos(7 * t)))
    longest = max(math.sqrt(x * x + y * y + z * z) for x, y, z in raw)
    off = max(abs(g - w / longest) for gv, wv in zip(got, raw) for g, w in zip(gv, wv))
    check("the knot is the (3, 2, 7) Lissajous knot, point for point", len(got) == 210 and off < 1e-9,
          "%d points, %.2e from the formula" % (len(got), off))

    print("\n--- the figures ---")
    figs = p.evaluate("""() => {
      const out = {};
      for (const [name, detail] of [['Polygon', 7], ['Butterfly', 5]]) {
        const N = 100000; let worst = 0, most = 0, prev = figureAt(name, 0, detail), outside = 0;
        const first = prev;
        for (let i = 1; i <= N; i++) {
          const at = figureAt(name, (i % N) / N, detail);
          worst = Math.max(worst, Math.hypot(at[0] - prev[0], at[1] - prev[1]));
          most = Math.max(most, Math.abs(at[0]), Math.abs(at[1]));
          if (Math.abs(at[0]) > 1 || Math.abs(at[1]) > 1) outside++;
          prev = at;
        }
        const last = figureAt(name, 1 - 1e-9, detail);
        out[name] = { step: worst, most, outside, gap: Math.hypot(last[0] - first[0], last[1] - first[1]) };
      }
      const corner = (n, k) => figureAt('Polygon', k / n, n);
      const mid = (n, k) => figureAt('Polygon', (k + 0.5) / n, n);
      out.corners = [3, 6, 12].map((n) => {
        let off = 0;
        for (let k = 0; k < n; k++) {
          const c = corner(n, k), m = mid(n, k);
          off = Math.max(off, Math.hypot(c[0] - Math.cos(2 * Math.PI * k / n), c[1] - Math.sin(2 * Math.PI * k / n)),
                        Math.abs(Math.hypot(m[0], m[1]) - Math.cos(Math.PI / n)));
        }
        return off;
      });
      // Two is less than a polygon has, and a fraction is a whole number of sides.
      out.floor = [figureAt('Polygon', 1 / 3, 2), figureAt('Polygon', 1 / 3, 3)];
      out.round = [figureAt('Polygon', 0.2, 5.4), figureAt('Polygon', 0.2, 5)];
      out.fly = [0.013, 0.1, 0.37, 0.5, 0.81].map((t) => figureAt('Butterfly', t, 5));
      out.circle = figureAt('Circle', 0.1, 5);
      return out;
    }""")
    print("    %s" % {k: figs[k] for k in ("Polygon", "Butterfly")})
    check("the polygon and the butterfly close, never jump, and stay inside full scale while filling it",
          all(figs[n]["gap"] < 1e-6 and figs[n]["step"] < 0.005 and figs[n]["outside"] == 0 and figs[n]["most"] > 0.95
              for n in ("Polygon", "Butterfly")),
          str({n: (round(figs[n]["gap"], 9), round(figs[n]["step"], 5), figs[n]["outside"], round(figs[n]["most"], 4))
               for n in ("Polygon", "Butterfly")}))
    check("n sides put the corners on the circle n apart and the sides' midpoints at cos(pi/n)",
          max(figs["corners"]) < 1e-9, str(figs["corners"]))
    check("and two sides is a triangle, and 5.4 is five",
          figs["floor"][0] == figs["floor"][1] and figs["round"][0] == figs["round"][1],
          "%s / %s" % (figs["floor"], figs["round"]))
    want = [butterfly(t) for t in [0.013, 0.1, 0.37, 0.5, 0.81]]
    off = max(math.hypot(a[0] - w[0], a[1] - w[1]) for a, w in zip(figs["fly"], want))
    check("the butterfly is Temple Fay's curve, computed here on its own, and not the circle",
          off < 1e-9 and math.hypot(figs["fly"][1][0] - figs["circle"][0], figs["fly"][1][1] - figs["circle"][1]) > 0.1,
          "%.2e from the formula" % off)

    print("\n--- on the page ---")
    page = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const figures = [...el.figure.options].map((o) => o.value), models = [...el.model.options].map((o) => o.value);
      el.genMode.value = 'wireframe'; el.genMode.dispatchEvent(new Event('change'));
      /* Held still, and measured over exactly four laps. Turning, each window
         caught the solid at a different angle, so two looks at one solid
         differed as much as two solids did - a misspelt name that kept the
         cube passed as a solid of its own. Still, a whole number of laps of
         the same path sums to the same number whenever it is taken. */
      for (const id of ['spinX', 'spinY', 'spinZ']) { el[id].value = '0'; el[id].dispatchEvent(new Event('input')); }
      el.figureRate.value = '40'; el.figureRate.dispatchEvent(new Event('input'));
      const n = Math.round(4 * state.source.sampleRate / 40);
      const prints = {};
      for (const model of ['Cube', 'Dodecahedron', 'Icosahedron', 'Torus', 'Knot']) {
        el.model.value = model; el.model.dispatchEvent(new Event('change'));
        state.source.reswing();
        await wait(300);
        const [l, r] = state.source.getLatestWindow(n);
        let sum = 0, finite = true;
        for (let i = 0; i < l.length; i++) { sum += l[i] * l[i] + r[i] * r[i]; if (!Number.isFinite(l[i] + r[i])) finite = false; }
        prints[model] = finite ? Math.round(sum * 10) / 10 : null;
      }
      // The same solid twice, to show a look is repeatable at this rounding.
      el.model.value = 'Cube'; el.model.dispatchEvent(new Event('change'));
      await wait(300);
      const again = state.source.getLatestWindow(n);
      let sum = 0;
      for (let i = 0; i < again[0].length; i++) sum += again[0][i] ** 2 + again[1][i] ** 2;
      const cubeAgain = Math.round(sum * 10) / 10;
      el.genMode.value = 'wave'; el.genMode.dispatchEvent(new Event('change'));
      return { figures, models, prints, cubeAgain };
    }""")
    print("    %s" % page)
    check("the Figure menu offers the polygon and the butterfly, and the Solid menu the four new solids",
          {"Polygon", "Butterfly"} <= set(page["figures"])
          and {"Dodecahedron", "Icosahedron", "Torus", "Knot"} <= set(page["models"]),
          "%s / %s" % (page["figures"], page["models"]))
    prints = list(page["prints"].values())
    check("and each new solid draws a picture of its own on the page, not the cube",
          None not in prints and len(set(prints)) == len(prints) and min(prints) > 1
          and page["cubeAgain"] == page["prints"]["Cube"],
          "%s, the cube again %s" % (page["prints"], page["cubeAgain"]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
raise SystemExit(1 if fails else 0)
