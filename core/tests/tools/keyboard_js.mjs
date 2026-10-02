/* The page's keyboard - its note stack, pedal, controllers and bytes, and what
   it tells the generator - lifted out of web/scope.html by name and driven
   through the runs in a file, one result line per command, as keyboard_cpp
   prints them.

   The generator it plays is a stand-in that writes down every call the
   keyboard makes of it (`set`, the chord, the gate, `setGated`, `reswing`,
   the layout) and keeps the settings those calls change, which is all the
   keyboard reads back. The panel's sliders the keyboard reads and writes are
   stand-ins too, holding strings as an input element does. Everything else
   - the functions that decide - is the page's own text.

   A file is runs of `run key=value ...`, then one command a line, then `end`:
     on NOTE VEL   off NOTE   pedal V   panic   cc N RAW   name N [WORDS_WITH_UNDERSCORES]   bytes b,b,...
     mode dyad|mono|poly   draw LAYER COUNT WHICH   just 0|1
     layers off|split|layer   learn   pair each|against   hold 0|1
     drive 0|1   play 0|1   gen FIELD VALUE   panel FIELD VALUE
     frame MS   undrive   present 0|1
     arp MODE RATE OCTAVES   bpm BPM   at MS   tick   out 0|1
   `at` moves the clock, firing first any timer due by then at its own time;
   `tick` is the frame's arpTick; `out` opens or closes the MIDI out.
   A run's head may say present=0 for a page with no keyboard.
   Usage: node keyboard_js.mjs <runs> */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { mulberry32 } from "./js_core.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const page = fs.readFileSync(path.join(here, "..", "..", "..", "web", "scope.html"), "utf8");

function definition(name) {
  let start = page.indexOf("\nfunction " + name + "(");
  if (start >= 0) return page.slice(start + 1, page.indexOf("\n}\n", start) + 2);
  start = page.indexOf("\nconst " + name + " = ");
  if (start < 0) throw new Error("no definition of " + name + " in scope.html");
  const line = page.slice(start + 1, page.indexOf("\n", start + 1));
  // One line with a comment after its semicolon is one line.
  if (/;\s*(\/\/.*)?$/.test(line)) return line + "\n";
  const close = line.endsWith("[") ? "\n];\n" : line.endsWith("{") ? "\n};\n" : ";\n";
  return page.slice(start + 1, page.indexOf(close, start) + close.length);
}

const LIFTED = [
  "POLY_VOICES", "MIDI_ROOT", "CC_SMOOTH", "CC_INKS", "NORD_CC", "INTERVALS", "midiHz", "midi", "screenKeys",
  "intervalRatio", "keyboardPresent", "midiPitch", "midiNoteOn", "midiNoteOff", "midiSetPedal", "midiPanic",
  "polyHz", "layersOn", "layerNotes", "polyVoices", "polyWanted", "midiApplyPoly", "syncPoly", "syncLayers",
  "midiUndrawn", "midiPair", "midiInterval", "midiDrivesGenerator", "midiApplyGate", "midiGateNotes",
  "midiApplyNotes", "midiApplyNotesTo", "roseDetail", "midiUndrive", "midiControl", "midiLearn", "midiSmooth",
  "midiRegisterKey", "midiBytes", "setMidiMode", "syncPlay", "genLane", "genSettings", "genSet", "genReswing",
  "ARP_RATES", "ARP_GATHER", "arp", "arpActive", "arpStepMs", "arpSequence", "arpApply", "arpStep", "arpStop", "arpHeld",
  "arpTick", "arpSet",
];

/* The page's surroundings, as little as the lifted functions reach for: the
   clock and its timers, the tempo, and a MIDI out that writes down what it is
   sent while it is open. */
const STUBS = `
let midiRunning = 0;
const log = [];
const show = (v) => v === null ? "null" : v === true ? "1" : v === false ? "0"
  : typeof v === "number" ? v.toPrecision(17)
  : Array.isArray(v) ? (v.length ? v.map((n) => n.note + "/" + n.freq.toPrecision(17) + "/" + n.velocity.toPrecision(17) + "/" + n.role).join("+") : "none")
  : String(v);
const settings = { mode: "wave", figure: "Circle", just: true, pitched: false, voices: null, inputFrom: "live" };
const settingsB = { voices: null };
let gatedNow = false, layoutNow = "one";
const toneSource = {
  kind: "tone",
  get settings() { return settings; }, get settingsB() { return settingsB; },
  get layout() { return layoutNow; },
  setLayout(next) { log.push("layout " + next); layoutNow = next; },
  set(field, value, layer) { log.push("set " + field + " " + show(value) + " " + (layer || 0)); (layer === 1 ? settingsB : settings)[field] = value; },
  reswing() { log.push("reswing"); },
  gate(open, velocity) { log.push("gate " + show(open) + " " + show(velocity)); },
  setGated(on) { log.push("setGated " + show(on)); gatedNow = on; },
  get gated() { return gatedNow; },
  describe() { return ""; },
};
const state = { source: toneSource };
const genInput = { from: "live" };
let clock = 0;
const performance = { now: () => clock };
const timers = [];
function setTimeout(fn, ms) { timers.push({ due: clock + ms, fn }); }
const transport = { bpm: 120 };
let outOpen = false;
function midiOutNote(note, velocity, now) {
  if (!outOpen) return false;
  log.push("out " + note + " " + show(velocity) + " " + show(now));
  return true;
}
function midiOutOff(note) { log.push("outoff " + note); }
const sources = new Map();
function registerSource(entry) { sources.set(entry.id, entry); return entry; }
const MOD_SOURCES = sources;
function midiRealtime(status) { log.push("realtime " + status); }
const noop = () => {};
const syncMidi = noop, midiSayMonitor = noop, syncLayerPanel = noop, buildLaneRows = noop,
      paintScreenKeys = noop, buildSourceChips = noop, buildMidiRows = noop;
const element = () => ({ value: "", textContent: "", checked: false, hidden: false, disabled: false, setAttribute: noop });
const elements = { interval: Object.assign(element(), { value: "0" }), freq: Object.assign(element(), { value: "220" }),
                   figureRate: Object.assign(element(), { value: "40" }), detail: Object.assign(element(), { value: "5" }),
                   arpMode: Object.assign(element(), { value: "off" }), arpRate: Object.assign(element(), { value: "1/8" }),
                   arpOctaves: Object.assign(element(), { value: "1" }) };
const el = new Proxy(elements, { get: (t, k) => (k in t ? t[k] : (t[k] = element())) });
`;

const source = STUBS + LIFTED.map(definition).join("\n") + `
return { midi, screenKeys, settings, settingsB, sources, log, show, el, genInput, toneSource,
         midiNoteOn, midiNoteOff, midiSetPedal, midiPanic, midiControl, midiBytes, midiSmooth, midiApplyGate,
         midiApplyNotes, midiUndrive, midiRegisterKey, midiLearn, setMidiMode, syncLayers, syncLayerPanel, syncPlay, genSettings,
         POLY_VOICES, layersOn, arp, arpSet, arpTick, timers, transport,
         setClock: (ms) => { clock = ms; }, setOut: (on) => { outOpen = on; },
         setPresent: (on) => { midi.access = on ? {} : null; } };`;

function run(head, commands) {
  const p = Object.fromEntries(head.map((kv) => kv.split("=")));
  // One seeded Math.random for the arpeggiator's random walk, as the core seeds its own.
  const k = new Function("Math", source)(Object.assign(Object.create(globalThis.Math), { random: mulberry32(1) }));
  let now = 0;
  k.setPresent(p.present !== "0");
  k.midiRegisterKey();
  const lines = [];
  for (const words of commands) {
    const [cmd, ...a] = words;
    k.log.length = 0;
    if (cmd === "on") k.midiNoteOn(Number(a[0]), Number(a[1]));
    else if (cmd === "off") k.midiNoteOff(Number(a[0]));
    else if (cmd === "pedal") k.midiSetPedal(Number(a[0]));
    else if (cmd === "panic") k.midiPanic();
    // A name from a setup code, as `decodeCC` hands one over; none is a bare learn.
    else if (cmd === "name") k.midiLearn(Number(a[0]), a[1] === undefined ? undefined : a[1].replace(/_/g, " "));
    else if (cmd === "cc") k.midiControl(Number(a[0]), Number(a[1]));
    else if (cmd === "bytes") k.midiBytes(a[0].split(",").map(Number));
    else if (cmd === "mode") k.setMidiMode(a[0]);
    // The panel's handlers, as the page has them: thin, and each ends in
    // `midiApplyNotes`, which is the part that decides.
    else if (cmd === "draw") {
      k.midi.draws[Number(a[0])].count = Math.max(2, Math.min(k.POLY_VOICES, Number(a[1]) || 2));
      k.midi.draws[Number(a[0])].which = a[2];
      k.midiApplyNotes();
    } else if (cmd === "just") { k.midi.polyJust = a[0] === "1"; k.midiApplyNotes(); }
    else if (cmd === "layers") {
      k.midi.layers.mode = a[0]; k.midi.layers.learning = false;
      k.syncLayers(); k.syncLayerPanel(); k.midiApplyNotes();
    } else if (cmd === "learn") k.midi.layers.learning = !k.midi.layers.learning;
    else if (cmd === "pair") { k.midi.layers.pair = a[0]; k.syncLayers(); k.midiApplyNotes(); }
    else if (cmd === "hold") k.midi.hold = a[0] === "1";
    else if (cmd === "drive") {
      const tone = k.genSettings();
      k.midi.drive[tone.mode] = a[0] === "1";
      if (a[0] === "1") k.midiApplyNotes(); else k.midiUndrive();
      k.syncPlay();
    } else if (cmd === "play") {
      const tone = k.genSettings();
      if (tone.mode in k.midi.play) {
        k.midi.play[tone.mode] = a[0] === "1";
        k.syncPlay();
        if (k.midi.play[tone.mode]) k.midiApplyNotes(); else k.midiUndrive();
      }
    } else if (cmd === "gen") {
      // Straight onto the generator, as another section of the panel would.
      const v = a[1] === "true" ? true : a[1] === "false" ? false : Number.isNaN(Number(a[1])) ? a[1] : Number(a[1]);
      k.settings[a[0]] = v;
      if (a[0] === "inputFrom") k.genInput.from = v;
    } else if (cmd === "panel") k.el[a[0]].value = a[1];
    else if (cmd === "frame") { k.midiSmooth(Number(a[0])); k.midiApplyGate(); }
    else if (cmd === "undrive") k.midiUndrive();
    else if (cmd === "present") k.setPresent(a[0] === "1");
    else if (cmd === "arp") {
      k.el.arpMode.value = a[0]; k.el.arpRate.value = a[1]; k.el.arpOctaves.value = a[2];
      k.arpSet();
    } else if (cmd === "bpm") k.transport.bpm = Number(a[0]);
    else if (cmd === "at") {
      const until = Number(a[0]);
      for (;;) {
        let next = -1;
        k.timers.forEach((t, i) => { if (t.due <= until && (next < 0 || t.due < k.timers[next].due)) next = i; });
        if (next < 0) break;
        const t = k.timers.splice(next, 1)[0];
        k.setClock(t.due);
        t.fn();
      }
      now = until;
      k.setClock(now);
    } else if (cmd === "tick") k.arpTick(now);
    else if (cmd === "out") k.setOut(a[0] === "1");
    else throw new Error("unknown command " + cmd);

    // And what the keyboard says of itself afterwards: its sources, its readout,
    // the panel it writes, and the stack.
    const m = k.midi, s = (id) => k.show(k.sources.get(id).value());
    const cc = [...m.cc.values()].map((e) => e.number + "/" + e.name.replace(/ /g, "_") + "/" + e.raw + "/" + k.show(e.value) + "/" + k.show(k.sources.get("cc." + e.number).value())).join("+") || "-";
    const state = ["|", "key", s("midi.key"), "pedal", s("midi.pedal"), "count", s("notes.count"), "spread", s("notes.spread"),
      "top", s("notes.top"), "inner", s("notes.inner"), "poly", m.poly.sounding, m.poly.drawn, m.poly.held,
      "split", m.layers.point, k.show(m.layers.learning), "sustain", k.show(m.sustain), "strikes", m.strikesBy[0], m.strikesBy[1],
      "interval", m.interval.index, m.interval.octaves, "panel", k.el.interval.value, k.el.freq.value,
      "layout", k.toneSource.layout, "gated", k.show(k.toneSource.gated), "layers", k.show(k.layersOn()),
      "notes", m.notes.map((h) => h.note + "/" + k.show(h.velocity)).join("+") || "-",
      "sustained", [...m.sustained].join("+") || "-", "cc", cc,
      "arp", k.arp.mode, k.arp.index, k.arp.start === null ? "-" : k.show(k.arp.start), k.arp.steps,
      k.arp.current.map((h) => h.note + "/" + k.show(h.velocity)).join("+") || "-", k.arp.sent.join("+") || "-"];
    lines.push([cmd, ...k.log.flatMap((l) => ["::", l]), ...state].join(" "));
  }
  return lines.join("\n");
}

const text = fs.readFileSync(process.argv[2], "utf8").split("\n");
const out = [];
for (let i = 0; i < text.length; i++) {
  const words = text[i].trim().split(/\s+/);
  if (words[0] !== "run") continue;
  const commands = [];
  for (i++; i < text.length && text[i].trim() !== "end"; i++) {
    const w = text[i].trim().split(/\s+/);
    if (w[0]) commands.push(w);
  }
  out.push(run(words.slice(1), commands));
}
process.stdout.write(out.join("\n") + "\n");
