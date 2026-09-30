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
