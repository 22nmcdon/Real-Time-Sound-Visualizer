// The page's envelope through a scenario, one value per line, as the C++
// runner prints them. Usage: node envelope_js.mjs <scenario>
import { pageFunction, readScenario } from "./js_core.mjs";

const makeEnvelope = pageFunction("makeEnvelope");
const { setup, timed, run } = readScenario(process.argv[2]);
let rate = 48000, reset = null;
const tone = { attackMs: 5, decayMs: 200, sustain: 1, releaseMs: 200 };
const apply = (words, env) => {
  if (words[0] === "rate") rate = Number(words[1]);
  else if (words[0] === "tone") tone[words[1]] = Number(words[2]);
  else if (words[0] === "reset") { if (env) env.reset(Number(words[1])); else reset = Number(words[1]); }
  else if (words[0] === "gate") env.gate(words[1] === "1", Number(words[2] || 1));
  else throw new Error("unknown command " + words.join(" "));
};
for (const words of setup) apply(words, null);
const env = makeEnvelope(rate, tone);
if (reset !== null) env.reset(reset);
const out = [];
let k = 0;
for (let i = 0; i < run; i++) {
  while (k < timed.length && timed[k].at === i) apply(timed[k++].words, env);
  out.push(env.step().toPrecision(17));
}
process.stdout.write(out.join("\n") + "\n");
