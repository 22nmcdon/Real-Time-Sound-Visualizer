/* The compiled instrument through the page's own wrapper (`makeWasmBrain`,
   lifted from web/scope.html by name), from the module the page carries,
   through the same script as instrument_cpp, which plays the native one. See
   that file for the language and what comes out.
   Usage: node instrument_js.mjs <script>   (WASM_FILE names another module, SCOPE_PAGE another page) */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const page = fs.readFileSync(process.env.SCOPE_PAGE || path.join(here, "..", "..", "..", "web", "scope.html"), "utf8");
function definition(name) {
  const start = page.indexOf("\nfunction " + name + "(");
  if (start < 0) throw new Error("no definition of " + name + " in scope.html");
  return page.slice(start + 1, page.indexOf("\n}\n", start) + 2);
}
const bytes = process.env.WASM_FILE ? new Uint8Array(fs.readFileSync(process.env.WASM_FILE)) : (() => {
  const at = page.indexOf("/* WASM_CORE_BEGIN */\"");
  return Uint8Array.from(Buffer.from(page.slice(at + 22, page.indexOf("\"/* WASM_CORE_END */", at)), "base64"));
})();
const makeWasmBrain = new Function('"use strict";\n' + definition("makeWasmBrain") + "\nreturn makeWasmBrain;")();
const module = new WebAssembly.Module(bytes);

// %.9g, as the C library writes it, so a float reads the same from both sides.
function g9(v) {
  if (v === 0) return Object.is(v, -0) ? "-0" : "0";
  if (!Number.isFinite(v)) return Number.isNaN(v) ? "nan" : v > 0 ? "inf" : "-inf";
  const e = Math.floor(Math.log10(Math.abs(v)));
  let text = v.toPrecision(9);
  if (/e/.test(text) || e < -4 || e >= 9) {
    text = v.toExponential(8).replace(/\.?0+e/, "e").replace(/e([+-])(\d)$/, "e$10$2");
  } else if (text.includes(".")) text = text.replace(/\.?0+$/, "");
  return text;
}

let brain = null;
const out = [];
for (const line of fs.readFileSync(process.argv[2], "utf8").split("\n")) {
  if (!line) continue;
  const [cmd, ...a] = JSON.parse(line);
  if (cmd === "make") { brain = makeWasmBrain(module, a[0], a[1], a[2]); if (!brain.read) out.push("no"); }
  else if (cmd === "slider") { if (!brain.slider(a[0], a[1])) out.push("no"); }
  else if (cmd === "setup") { if (!brain.setup(a[0])) out.push("no"); }
  else if (cmd === "control") brain.control(a[0], a[1]);
  else if (cmd === "click") brain.click(a[0]);
  else if (cmd === "routings") brain.routings(a[0]);
  else if (cmd === "fade") { if (!brain.fade(a[0])) out.push("no"); }
  else if (cmd === "midi") brain.midi(a);
  else if (cmd === "block") {
    const n = a[0];
    const lanes = [0, 1, 2, 3].map(() => new Float32Array(n));
    const sent = brain.block(n, ...lanes);
    const stride = a[1] >= 1 ? a[1] : 1, all = [];
    for (const lane of lanes) for (const v of lane) all.push(v);
    out.push("block " + all.filter((v, k) => k % stride === 0).map(g9).join(" "));
    if (sent) out.push("out " + sent.map((m) => m.join(" ") + " ;").join(" "));
    const state = brain.state();
    if (state) out.push("state " + state.version + " " + state.code);
  } else throw new Error("unknown command " + cmd);
}
process.stdout.write(out.join("\n") + "\n");
