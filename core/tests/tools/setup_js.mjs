/* The page's setup codes - `DEFAULTS`, `encodeSetup`, `decodeSetup` and
   `migrateSetup` - lifted out of web/scope.html by name and run in strict
   mode, as the page's script is, through the commands in a file, one result
   line per command, as setup_cpp prints them.

     defaults              the defaults, as JSON
     encode JSON           the code for that snapshot, or `throws`
     decode CODE           the setup it reads as, `unreadable`, or `throws`

   Every character past ASCII in a result is written as {u+xxxx}, so a lone
   surrogate reads the same from both sides - and not as \uxxxx, which is how
   JSON.stringify writes one, and would make an escaped half of a pair look
   the same as one written out.
   Usage: node setup_js.mjs <commands> */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
// SCOPE_PAGE names another copy of the page, and WASM_FILE another module,
// for a check that alters one.
const page = fs.readFileSync(process.env.SCOPE_PAGE || path.join(here, "..", "..", "..", "web", "scope.html"), "utf8");

function definition(name) {
  let start = page.indexOf("\nfunction " + name + "(");
  if (start >= 0) return page.slice(start + 1, page.indexOf("\n}\n", start) + 2);
  start = page.indexOf("\nconst " + name + " = ");
  if (start < 0) throw new Error("no definition of " + name + " in scope.html");
  const line = page.slice(start + 1, page.indexOf("\n", start + 1));
  if (/;\s*(\/\/.*)?$/.test(line)) return line + "\n";
  const close = line.endsWith("[") ? "\n];\n" : line.endsWith("{") ? "\n};\n" : ";\n";
  return page.slice(start + 1, page.indexOf(close, start) + close.length);
}

/* With CORE=wasm in the environment the codes are made and read by the
   compiled core's codec (5e), from the module the page carries, as the site
   now makes them; otherwise by the page's own JavaScript. */
const MODE = process.env.CORE || "js";
const LIFTED = ["RISING", "LAG_MIX_DEFAULT", "TIMEBASE_DEFAULT", "DRAWBAR_DEFAULT", "FULL_SCALE_DB", "DEFAULTS",
                "SETUP_VERSION", "encodeSetupHere", "decodeSetupHere", "migrateSetup", "makeWasmSetupCodec"];
const WASM_BYTES = MODE === "wasm" && process.env.WASM_FILE ? new Uint8Array(fs.readFileSync(process.env.WASM_FILE))
  : MODE === "wasm" ? (() => {
  const at = page.indexOf("/* WASM_CORE_BEGIN */\"");
  return Uint8Array.from(Buffer.from(page.slice(at + 22, page.indexOf("\"/* WASM_CORE_END */", at)), "base64"));
})() : null;
const s = new Function("WASM_BYTES", '"use strict";\n' + LIFTED.map(definition).join("\n")
                       + "\nif (WASM_BYTES) { const c = makeWasmSetupCodec(new WebAssembly.Module(WASM_BYTES));"
                       + " return { DEFAULTS, encodeSetup: c.encode, decodeSetup: c.decode }; }"
                       + "\nreturn { DEFAULTS, encodeSetup: encodeSetupHere, decodeSetup: decodeSetupHere };")(WASM_BYTES);
const ascii = (text) => text.replace(/[^\x00-\x7f]/g, (c) => "{u+" + c.charCodeAt(0).toString(16).padStart(4, "0") + "}");

const out = [];
for (const line of fs.readFileSync(process.argv[2], "utf8").split("\n")) {
  if (!line) continue;
  const space = line.indexOf(" ");
  const cmd = space < 0 ? line : line.slice(0, space), rest = space < 0 ? "" : line.slice(space + 1);
  if (cmd === "defaults") out.push(ascii(JSON.stringify(s.DEFAULTS)));
  else if (cmd === "encode") {
    try { out.push("code " + s.encodeSetup(JSON.parse(rest))); } catch (error) { out.push("throws"); }
  } else if (cmd === "decode") {
    try {
      const setup = s.decodeSetup(rest);
      out.push(setup === null ? "unreadable" : "read " + ascii(JSON.stringify(setup)));
    } catch (error) { out.push("throws"); }
  } else throw new Error("unknown command " + cmd);
}
process.stdout.write(out.join("\n") + "\n");
