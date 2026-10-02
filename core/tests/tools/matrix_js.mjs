/* The page's modulation matrix - its routings, their reach and the loop's
   total, the fades that ease a routing in and out and the stepped sources
   through their envelopes, the routes compiled for the generator each block,
   the events fired once a frame and the picture's destinations summed - lifted
   out of web/scope.html by name and driven through the runs in a file, one
   result line per command, as matrix_cpp prints them.

   The sources and the picture's and the events' destinations are stand-ins
   whose values the run sets, since the real ones are later pieces of the
   port; the generator's destinations are the page's own `GEN_DESTS`. The
   clock is the run's: `performance.now()` reads what `at` last said.

   A file is runs of `run`, then one command a line, then `end`:
     source ID [event] [picture] [stepped] [varies] [reach=R] [index=I]
     value ID V   count ID N   visual ID SPAN MIN MAX BASE   event ID
     route SRC DEST AMOUNT   unroute SRC DEST   amount SRC DEST A
     load SRC>DEST@A;...   edit SRC>DEST@A;...   forget ID   fade MODE [SECONDS]
     env LAYER key=value...   layers 0|1   strike LAYER   at MS   frame   routes   encode   dests
   Usage: node matrix_js.mjs <runs> */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const page = fs.readFileSync(path.join(here, "..", "..", "..", "web", "scope.html"), "utf8");

function definition(name) {
  let start = page.indexOf("\nfunction " + name + "(");
  if (start >= 0) return page.slice(start + 1, page.indexOf("\n}\n", start) + 2);
  start = page.indexOf("\nconst " + name + " = ");
  if (start < 0) start = page.indexOf("\nlet " + name + " = ");
  if (start < 0) throw new Error("no definition of " + name + " in scope.html");
  const line = page.slice(start + 1, page.indexOf("\n", start + 1));
  if (/;\s*(\/\/.*)?$/.test(line)) return line + "\n";
  const close = line.endsWith("[") ? "\n];\n" : line.endsWith("{") ? "\n};\n" : ";\n";
  return page.slice(start + 1, page.indexOf(close, start) + close.length);
}
// A statement the page runs at the top level, taken as it stands.
function statement(text) {
  if (page.indexOf(text) < 0) throw new Error("no statement " + text);
  return text + "\n";
}
// The picture's destinations, as `applyModMatrix` sums them once a frame.
function visualLoop() {
  const body = page.slice(page.indexOf("\nfunction applyModMatrix("));
  const from = body.indexOf("  const heard = routingsHeard();");
  const to = body.indexOf("  // After the matrix, so a source on the fader is already counted.");
  if (from < 0 || to < from) throw new Error("no visual loop in applyModMatrix");
  return "function applyVisual() {\n" + body.slice(from, to) + "}\n";
}

const LIFTED = [
  "CUTOFF_STEPS", "DRAWBARS", "DRAWBAR_SLOT", "MORPH_SLOT", "RADIUS_SLOT", "TWIST_SLOT", "FM_SLOT", "SYNC_SLOT",
  "DRIVE_SLOT", "FOLD_SLOT", "VCF_SLOT", "ECHO_SLOT", "ECHO_TIME_SLOT", "SWING_SLOT", "WIDTH_SLOT", "TABLE_SLOT",
  "SPIN_SLOT", "MOD_SOURCES", "MOD_DESTS", "registerSource", "registerDest", "routingAllowed", "LOOP_TOTAL",
  "clampLoop", "routingAmount", "GEN_DESTS",
  "FADE_MODES", "FADE_LIMITS", "ENV_DEFAULT", "fade", "routeKey", "fadesIn", "fadesOut", "fadeLayered",
  "fadeTravel", "rampMs", "rampAt", "rampDone", "rampTo", "rampStill", "gatePhase", "gateSet", "fadeGain",
  "routingsHeard", "fadeStep", "stepFade", "sourceNow", "setFadeEnvelope", "setFade",
  "eventSeen", "fireEvents", "genMod", "genRoutes", "modDirty", "repaintQueued", "touchRoutings", "compileRoutes",
  "stepRoutes", "workletRoutes", "encodeRoutings", "decodeRoutings",
];

const STUBS = `
let clock = 0;
const performance = { now: () => clock };
const log = [];
const state = { modRoutings: [] };
const midi = { strikesBy: [0, 0] };
let layered = false;
function layersOn() { return layered; }
const noop = () => {};
// The page in the plugin sends its routings after an edit; this harness is no plugin.
const saveFade = noop, paintRoutings = noop, hostRoutings = noop;
const requestAnimationFrame = (f) => f();
`;

const source = STUBS + LIFTED.map(definition).join("\n")
  + statement('for (const dest of GEN_DESTS) registerDest(Object.assign({ kind: "audio" }, dest));')
  + visualLoop() + `
return { state, midi, log, fade, MOD_SOURCES, MOD_DESTS, registerSource, registerDest, touchRoutings, setFade,
         setFadeEnvelope, fadeStep, fireEvents, applyVisual, workletRoutes, encodeRoutings, decodeRoutings,
         routingsHeard, routeKey,
         setClock: (ms) => { clock = ms; }, setLayered: (on) => { layered = on; }, dirty: () => modDirty };`;

const show = (v) => (v === undefined ? "u" : v === true ? "1" : v === false ? "0" : Number(v).toPrecision(17));

function run(commands) {
  const m = new Function(source)();
  const values = new Map(), counts = new Map();
  const lines = [];
  for (const words of commands) {
    const [cmd, ...a] = words;
    m.log.length = 0;
    let said = [];
    if (cmd === "source") {
      const flags = new Set(a.slice(1));
      const entry = { id: a[0], value: () => values.get(a[0]) || 0 };
      if (flags.has("event")) { entry.event = true; Object.defineProperty(entry, "count", { get: () => counts.get(a[0]) || 0 }); }
      if (flags.has("picture")) entry.fromPicture = true;
      if (flags.has("stepped")) entry.stepped = true;
      if (flags.has("varies")) entry.reachVaries = true;
      for (const f of flags) {
        if (f.startsWith("reach=")) entry.reach = Number(f.slice(6));
        if (f.startsWith("index=")) entry.index = Number(f.slice(6));
      }
      m.registerSource(entry);
      m.touchRoutings();
    } else if (cmd === "value") values.set(a[0], Number(a[1]));
    else if (cmd === "count") counts.set(a[0], Number(a[1]));
    else if (cmd === "visual") {
      const [id, span, min, max, base] = a;
      m.registerDest({ id, kind: "visual", span: Number(span), min: Number(min), max: Number(max),
                       base: () => Number(base), set: (offset) => m.log.push("visual " + id + " " + show(offset)) });
    } else if (cmd === "event") {
      m.registerDest({ id: a[0], kind: "event", fire: (amount) => m.log.push("fire " + a[0] + " " + show(amount)) });
    } else if (cmd === "route") {
      m.state.modRoutings.push({ sourceId: a[0], destId: a[1], amount: Number(a[2]) });
      m.touchRoutings();
    } else if (cmd === "unroute") {
      m.state.modRoutings = m.state.modRoutings.filter((r) => !(r.sourceId === a[0] && r.destId === a[1]));
      m.touchRoutings();
    } else if (cmd === "amount") {
      const r = m.state.modRoutings.find((x) => x.sourceId === a[0] && x.destId === a[1]);
      if (r) r.amount = Number(a[2]);
      m.touchRoutings();
    } else if (cmd === "load") {
      // A preset: every routing a new object, as `restore` makes them.
      m.state.modRoutings = m.decodeRoutings(a[0] || "");
      m.touchRoutings();
    } else if (cmd === "edit") {
      // The list as an edit on the page leaves it - one added, dropped or
      // given a new depth - which the page in the plugin sends whole: a pair
      // already there is the same object with its depth, the rest are new.
      m.state.modRoutings = m.decodeRoutings(a[0] || "").map((r) => {
        const had = m.state.modRoutings.find((x) => x.sourceId === r.sourceId && x.destId === r.destId);
        if (!had) return r;
        had.amount = r.amount;
        return had;
      });
      m.touchRoutings();
    } else if (cmd === "forget") {
      // A source unregistered, as forgetting a controller does it.
      m.MOD_SOURCES.delete(a[0]);
      m.touchRoutings();
    } else if (cmd === "fade") m.setFade(a[0], a[1] === undefined ? undefined : Number(a[1]));
    else if (cmd === "env") {
      const part = {};
      for (const kv of a.slice(1)) {
        const [k, v] = kv.split("=");
        part[k] = v === "true" ? true : v === "false" ? false : Number(v);
      }
      m.setFadeEnvelope(part, Number(a[0]));
    } else if (cmd === "layers") m.setLayered(a[0] === "1");
    else if (cmd === "strike") m.midi.strikesBy[Number(a[0])]++;
    else if (cmd === "at") m.setClock(Number(a[0]));
    else if (cmd === "frame") {
      // In the order the page's frame has them, then the routes as the
      // worklet's message takes them.
      m.fadeStep();
      m.fireEvents();
      m.applyVisual();
      const routes = m.workletRoutes();
      said = ["routes", routes.map((r) => [show(r.index), show(r.held), show(r.heldB), r.slot, show(r.amount), show(r.amountB), show(r.unipolar)].join("/")).join("+") || "-"];
    } else if (cmd === "routes") {
      // The routes alone, before the frame's fades have stepped, as the page
      // takes them when the sound is switched on.
      const routes = m.workletRoutes();
      said = ["routes", routes.map((r) => [show(r.index), show(r.held), show(r.heldB), r.slot, show(r.amount), show(r.amountB), show(r.unipolar)].join("/")).join("+") || "-"];
    } else if (cmd === "encode") said = ["code", m.encodeRoutings(m.state.modRoutings) || "-"];
    // The generator's destinations as the page registers them.
    else if (cmd === "dests") said = ["dests", [...m.MOD_DESTS.values()].filter((d) => d.kind === "audio")
      .map((d) => d.id + "/" + d.slot + "/" + show(d.unipolar === true)).join("+")];
    else throw new Error("unknown command " + cmd);

    const amounts = m.state.modRoutings.map((r) => show(r.amount)).join("+") || "-";
    lines.push([cmd, ...m.log.flatMap((l) => ["::", l]), "|", ...said, "amounts", amounts,
                "heard", m.routingsHeard().length, "gains", m.fade.gains.size, "dirty", show(m.dirty())].join(" "));
  }
  return lines.join("\n");
}

const text = fs.readFileSync(process.argv[2], "utf8").split("\n");
const out = [];
for (let i = 0; i < text.length; i++) {
  if (text[i].trim().split(/\s+/)[0] !== "run") continue;
  const commands = [];
  for (i++; i < text.length && text[i].trim() !== "end"; i++) {
    const w = text[i].trim().split(/\s+/);
    if (w[0]) commands.push(w);
  }
  out.push(run(commands));
}
process.stdout.write(out.join("\n") + "\n");
