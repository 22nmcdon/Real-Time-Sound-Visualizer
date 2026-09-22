/* The mapping, pulled out of the page and exercised on the inputs that broke
   the naive form. Run: node beam.test.mjs */
import { readFileSync } from "node:fs";

const src = readFileSync(new URL("check.js", import.meta.url), "utf8");
// Lift just the pure pieces, so this tests the shipped text rather than a copy.
const grab = (name) => {
  const at = src.indexOf("function " + name + "(");
  if (at < 0) throw new Error("not found: " + name);
  let depth = 0, i = src.indexOf("{", at);
  for (let j = i; j < src.length; j++) {
    if (src[j] === "{") depth++;
    else if (src[j] === "}" && --depth === 0) return src.slice(at, j + 1);
  }
  throw new Error("unbalanced: " + name);
};
const consts = src.match(/^const BEAM_(?:K|R|EPS2|HIST_LO|HIST_HI|HIST_BINS) = [^;\n]+;/gm).join("\n");
const mod = new Function(consts + "\n" + grab("beamStep") + "\nreturn { beamStep: (a,b) => beamStep(a,b,2.3), BEAM_K };")();
const { beamStep, BEAM_K } = mod;

let failures = 0;
const check = (name, cond, detail = "") => {
  if (!cond) failures++;
  console.log((cond ? "  ok  " : " FAIL ") + name + (detail ? "   " + detail : ""));
};

const log2 = Math.log2;

console.log("-- degenerate input: the cases the naive form got wrong --");
{
  // A cusp in a live frame: zero-length segment, healthy anchor.
  const s = beamStep(0, log2(16));
  check("cusp (len2=0, live anchor) is finite and brightest",
        Number.isFinite(s) && s === BEAM_K - 1, `step=${s}`);
}
{
  // Silence: every segment zero, so the anchor is zero too. 0/0 was NaN here,
  // and buckets[NaN] threw. This is the app's default screen.
  const s = beamStep(0, log2(1e-6));
  check("silence (len2=0, anchor=0) is finite, no NaN",
        Number.isFinite(s) && Number.isInteger(s), `step=${s}`);
  check("silence is finite and uniform (all segments equal -> full ink)",
        s === BEAM_K - 1, `step=${s}`);
}
{
  // Every step must be a usable array index for any input at all.
  let worst = null;
  for (const len2 of [0, 1e-30, 1e-6, 1e-3, 1, 16, 1e3, 1e6, 1e9, Infinity]) {
    for (const ref2 of [1e-6, 1e-9, 1, 1e9]) {
      const s = beamStep(len2, log2(ref2));
      const good = Number.isInteger(s) && s >= 0 && s < BEAM_K;
      if (!good && worst === null) worst = `len2=${len2} ref2=${ref2} -> ${s}`;
    }
  }
  check("every (len2, ref2) pair yields a valid index 0..K-1", worst === null, worst || "");
}
{
  const s = beamStep(NaN, log2(16));
  check("NaN length still yields a valid index",
        Number.isInteger(s) && s >= 0 && s < BEAM_K, `step=${s}`);
}

console.log();
console.log("-- the shading itself --");
{
  // A circle traced at a constant angular rate has constant speed, so every
  // segment is the anchor. This is the null test: it must be uniform, and at
  // mid-ramp rather than pinned to an end.
  const mid = beamStep(16, log2(16));
  check("circle (s == anchor) is uniform at FULL ink", mid === BEAM_K - 1, `step=${mid}`);

  let uniform = true;
  for (const s of [0.01, 1, 16, 1e4]) {         // any trace rate, any timebase
    if (beamStep(s, log2(s)) !== mid) uniform = false;
  }
  check("...and identical at every trace rate and timebase", uniform);
}
{
  const fast = beamStep(16 * 36, log2(16));     // 6x the anchor speed
  const slow = beamStep(16 / 36, log2(16));     // 6x slower than the anchor
  check("6x faster than the anchor is the dimmest step", fast === 0, `step=${fast}`);
  check("slower than the anchor saturates at full ink, never brighter", slow === BEAM_K - 1, `step=${slow}`);
  check("brightness falls monotonically with speed", (() => {
    let prev = Infinity;
    for (let e = -8; e <= 8; e++) {
      const s = beamStep(16 * Math.pow(4, e), log2(16));
      if (s > prev) return false;
      prev = s;
    }
    return true;
  })());
}

console.log();
console.log(failures === 0 ? "BEAM MAPPING PASS" : `BEAM MAPPING FAIL (${failures})`);
process.exit(failures === 0 ? 0 : 1);
