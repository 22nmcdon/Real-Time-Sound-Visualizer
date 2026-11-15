import { WASI } from "node:wasi"; import fs from "node:fs"; import path from "node:path";
const [wasmPath, script] = process.argv.slice(2);
const dir = path.dirname(path.resolve(script));
const wasi = new WASI({ version: "preview1", args: ["budget", "/w/" + path.basename(script)], preopens: { "/w": dir } });
const mod = await WebAssembly.compile(fs.readFileSync(wasmPath));
const inst = await WebAssembly.instantiate(mod, wasi.getImportObject());
wasi.start(inst);
