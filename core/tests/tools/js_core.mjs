/* Lifts a function out of web/scope.html by name and evaluates it, so the
   parity runners hold the C++ port to the page's own text rather than to a
   copy of it that could drift. A function is taken from its `function name(`
   line to the first line after it that is a lone closing brace at column
   nought, which is how every top-level function in the page ends. */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const page = fs.readFileSync(path.join(here, "..", "..", "..", "web", "scope.html"), "utf8");

export function pageFunction(name) {
  const start = page.indexOf("\nfunction " + name + "(");
  if (start < 0) throw new Error("no function " + name + " in scope.html");
  const end = page.indexOf("\n}\n", start);
  // Indirect eval, so the function's own names do not collide with ours.
  return (0, eval)("(" + page.slice(start + 1, end + 2) + ")");
}

/* Several definitions out of the page at once - functions and constants -
   evaluated together in one scope so they can see each other, as they do in
   the page. A `const` runs to the end of its statement: a multi-line array
   or arrow function to its closing line, anything else to its semicolon. */
export function pageScope(names) {
  const parts = names.map((name) => {
    let start = page.indexOf("\nfunction " + name + "(");
    if (start >= 0) return page.slice(start + 1, page.indexOf("\n}\n", start) + 2);
    start = page.indexOf("\nconst " + name + " = ");
    if (start < 0) throw new Error("no definition of " + name + " in scope.html");
    const line = page.slice(start + 1, page.indexOf("\n", start + 1));
    const close = line.endsWith("[") ? "\n];\n" : line.endsWith("{") ? "\n};\n" : ";\n";
    return page.slice(start + 1, page.indexOf(close, start) + close.length);
  });
  return new Function(parts.join("\n") + "\nreturn { " + names.join(", ") + " };")();
}

/* Functions and constants from inside `makeGeneratorCore`, which no page
   function exports: lifted out by name - a function indented two spaces to
   its closing brace at the same depth, a constant to its line's end - and
   evaluated at a sample rate together with the page's helpers they call,
   so they see the closure they were written in. A seeded `Math.random` can
   be put in their scope with `random`, which is how the noise is compared. */
const core = (() => {
  const start = page.indexOf("\nfunction makeGeneratorCore(");
  return page.slice(start, page.indexOf("\n}\n", start));
})();
const OUTER = ["TWO_PI", "DRAWBAR_HARMONICS", "cycleOf", "polyBlep", "polyBlamp", "cycleRead", "waveAt", "svfG", "svfStep"];
export function coreScope(names, rate, random) {
  const outer = OUTER.map((name) => {
    let start = page.indexOf("\nfunction " + name + "(");
    if (start >= 0) return page.slice(start + 1, page.indexOf("\n}\n", start) + 2);
    start = page.indexOf("\nconst " + name + " = ");
    const line = page.slice(start + 1, page.indexOf("\n", start + 1));
    const close = line.endsWith("{") ? "\n};\n" : ";\n";
    return page.slice(start + 1, page.indexOf(close, start) + close.length);
  });
  const inner = names.map((name) => {
    let start = core.indexOf("\n  function " + name + "(");
    if (start >= 0) return core.slice(start + 1, core.indexOf("\n  }\n", start) + 4);
    start = core.indexOf("\n  const " + name + " = ");
    // A `let` too: the shaper reads the core's own shaping variables.
    if (start < 0) start = core.indexOf("\n  let " + name + " = ");
    if (start < 0) throw new Error("no " + name + " in makeGeneratorCore");
    return core.slice(start + 1, core.indexOf(";\n", start) + 2);
  });
  const body = "const Math = Object.create(globalThis.Math); if (random) Math.random = random;\n"
    + outer.join("\n") + "\n" + inner.join("\n")
    // `__set` reaches a `let` in this closure, as the core's own code does.
    + "\nreturn { " + names.join(", ") + ", __set: (name, value) => eval(name + ' = value') };";
  return new Function("rate", "random", body)(rate, random);
}

// mulberry32, as scope::Random has it, so the page's noise draws the same.
export function mulberry32(seed) {
  let a = seed;
  return () => {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

/* The scenario language both runners read, so a scenario is written once.
   One command a line; `#` starts a comment. Commands before the first `at`
   are the setup; `at N ...` runs its command before sample N is stepped;
   `run N` is how many samples to step. */
export function readScenario(file) {
  const setup = [], timed = [];
  let run = 0;
  for (const raw of fs.readFileSync(file, "utf8").split("\n")) {
    const line = raw.replace(/#.*/, "").trim();
    if (!line) continue;
    const words = line.split(/\s+/);
    if (words[0] === "run") run = Number(words[1]);
    else if (words[0] === "at") timed.push({ at: Number(words[1]), words: words.slice(2) });
    else setup.push(words);
  }
  timed.sort((a, b) => a.at - b.at);
  return { setup, timed, run };
}
