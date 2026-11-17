/* The compiled core's generator, for the web suites that render it in the
   page (stage 5, step 6). Until then they built the page's own JavaScript
   generator, `makeGeneratorCore`, inside a default page and read its numbers;
   step 6 deleted it with the rest of the page's engine, and these suites now
   hold the core itself, through the bridge the page's worklets drove it by
   (`makeWasmCore`, moved here from the page whole, with the interface the
   JavaScript core had: `set`, `setRoutes`, the gate, `strike`, `reswing`,
   `setInput`, `block`, `effect` and the readings). parity held the two to
   1e-12 on every scenario while both existed (its "generator in WebAssembly"
   section), so a check that passed on the one passes on the other for the
   same reason.

   Loaded by `page.add_init_script(path=...)` before the page: it reaches for
   nothing until called, and then for the page's own `wasmModule`,
   `generatorSettings` and `storeGeneratorSetting`. Noise is seeded (`seed`),
   where the JavaScript core drew from Math.random. */
function compiledGenerator(rate, slots, lfos, seed) {
  const core = makeWasmCore(wasmModule(), rate, slots, lfos, seed || 1);
  /* At a Width of one, where these suites' checks were written and a lone
     note is heard as drawn: the instrument opens at a half since 17 Nov (the
     owner's), which widthtest.py holds, and a suite that wants another sets it. */
  core.set("stereoWidth", 1); core.set("drawnWidth", 1);
  return core;
}

function makeWasmCore(bytes, rate, slots, lfos, seed) {
  // The bytes, or the module already compiled from them (the main thread's).
  const module = bytes instanceof WebAssembly.Module ? bytes : new WebAssembly.Module(bytes);
  // The three calls the C library's abort path imports; there is nothing to write to here.
  const wasi = { fd_close: () => 0, fd_seek: () => 0, fd_write: () => 0 };
  const x = new WebAssembly.Instance(module, { wasi_snapshot_preview1: wasi }).exports;
  x._initialize();
  x.scope_make(rate, slots, lfos.length, seed >>> 0);

  const utf8 = (text) => {
    const out = [];
    for (const ch of String(text)) {
      const c = ch.codePointAt(0);
      if (c < 0x80) out.push(c);
      else if (c < 0x800) out.push(0xc0 | (c >> 6), 0x80 | (c & 63));
      else if (c < 0x10000) out.push(0xe0 | (c >> 12), 0x80 | ((c >> 6) & 63), 0x80 | (c & 63));
      else out.push(0xf0 | (c >> 18), 0x80 | ((c >> 12) & 63), 0x80 | ((c >> 6) & 63), 0x80 | (c & 63));
    }
    return out;
  };
  const write = (...parts) => {
    const total = parts.reduce((n, b) => n + b.length, 0);
    const at = x.scope_text(total);
    const into = new Uint8Array(x.memory.buffer, at, total);
    let k = 0;
    for (const b of parts) { into.set(b, k); k += b.length; }
  };
  const plain = (key, value) => (ArrayBuffer.isView(value) ? Array.from(value) : value);
  const shapes = lfos.map(() => null);
  let input = null, envelope = 0, envelopeStage = 0, envelopeVelocity = 1;
  let budget = { units: 0, asked: [1, 1], unison: [1, 1], askedFactor: 2, factor: 2, silenced: 0, most: 0 };
  let pitch = 0, gated = false;
  const scanHead = [-1, -1];
  /* The settings, kept on this side as the JavaScript core keeps its own, by
     the same rules (`storeGeneratorSetting`): the main thread reads them back
     - the panel, `genSettings`, what a worklet is sent - and the module has
     no way to hand them over. Everything that changes them goes through
     `set`, so the mirror is never behind. */
  const { tone, toneB } = generatorSettings();
  // The worklet's oscillators written in before a call, their shape only
  // when it has changed, and everything the worklet reads read back after.
  const oscillatorsIn = () => {
    lfos.forEach((lfo, i) => {
      if (lfo.shape !== shapes[i]) {
        const b = utf8(lfo.shape);
        write(b);
        x.scope_lfo_shape(i, b.length);
        shapes[i] = lfo.shape;
      }
      x.scope_lfo(i, lfo.rate, lfo.depth, lfo.phase, lfo.held, lfo.value);
    });
  };
  const afterwards = () => {
    // Asked for before the memory is read, for the reason sendTables gives.
    const at = x.scope_state();
    const s = new Float64Array(x.memory.buffer, at, 21 + 3 * lfos.length);
    envelope = s[0];
    budget = { units: s[1], asked: [s[2], s[3]], unison: [s[4], s[5]], askedFactor: s[6], factor: s[7],
               silenced: s[8], most: s[9] };
    /* 10 to 15 were the drawings' readings, and 17 and 18 a solid's kick and
       the pendulums' swing, none read since G2. Left where they were rather
       than closed up: the layout is the core's (scope_state), and a page that
       read it shifted against a core that had not moved would read the
       budget for the pitch. Since 11 Nov 10 and 11 are the envelope's stage
       and velocity, for the Envelope card's dot. */
    envelopeStage = s[10]; envelopeVelocity = s[11];
    pitch = s[16];
    lfos.forEach((lfo, i) => { lfo.phase = s[19 + 3 * i]; lfo.held = s[20 + 3 * i]; lfo.value = s[21 + 3 * i]; });
    scanHead[0] = s[19 + 3 * lfos.length]; scanHead[1] = s[20 + 3 * lfos.length];
  };

  /* The drawn cycle and the wavetable bank go as numbers
     (scope_tables): as JSON a bank is over a megabyte, the page sends it with
     every preset, and the text cost a tenth of a second each time. Counted
     first, then written straight into the module's buffer. */
  const listOf = (v) => (v && typeof v.length === "number" ? v : []);
  const tableSize = (t) => 2 + listOf(t && t.levels).reduce((n, level) => n + 1 + listOf(level).length, 0);
  const putList = (into, k, list) => { into[k++] = list.length; for (let i = 0; i < list.length; i++) into[k++] = list[i]; return k; };
  const putTable = (into, k, t) => {
    const levels = listOf(t && t.levels);
    into[k++] = t && typeof t.most === "number" ? t.most : 0;
    into[k++] = levels.length;
    for (const level of levels) k = putList(into, k, listOf(level));
    return k;
  };
  const sendTables = (which, value) => {
    const object = value !== null && typeof value === "object";
    const size = !object ? 0 : which === 0 ? tableSize(value)
      : Array.isArray(value) ? 1 + value.reduce((n, t) => n + tableSize(t), 0) : 0;
    // The space asked for before the memory is read: asking can grow it,
    // which replaces the buffer an earlier read would have held.
    const at = x.scope_numbers(size);
    const into = new Float64Array(x.memory.buffer, at, size);
    if (size && which === 0) putTable(into, 0, value);
    else if (size) { into[0] = value.length; value.reduce((k, t) => putTable(into, k, t), 1); }
    x.scope_tables(which, size);
  };
  // Table 2 was a figure's path, until G2.
  const TABLES = { cycle: 0, wavetable: 1 };
  // A layer's Scan table (P7a), or none: scope_scan copies it into one the generator is not reading.
  const sendScan = (value, layer) => {
    const size = value !== null && typeof value === "object" ? tableSize(value) : 0;
    const at = x.scope_numbers(size);
    if (size) putTable(new Float64Array(x.memory.buffer, at, size), 0, value);
    x.scope_scan(layer === 1 ? 1 : 0, size);
  };

  return {
    tone, toneB,
    set(field, value, layer) {
      storeGeneratorSetting(tone, toneB, field, value, layer);
      /* Scan's table as numbers, as the drawn cycle goes: as JSON a table a
         frame would be three thousand numbers written out and parsed sixty
         times a second. */
      if (field === "scanTable") { sendScan(value, layer); return; }
      if (field in TABLES) { sendTables(TABLES[field], value); return; }
      const f = utf8(field), v = utf8(JSON.stringify(value === undefined ? null : value, plain));
      write(f, v);
      x.scope_set(f.length, v.length, layer || 0);
    },
    setRoutes(list) {
      const at = x.scope_numbers(7 * list.length);
      const into = new Float64Array(x.memory.buffer, at, 7 * list.length);
      list.forEach((r, i) => {
        into.set([r.index === undefined ? -1 : r.index, r.held || 0,
                  r.heldB === undefined ? r.held || 0 : r.heldB, r.slot, r.amount,
                  r.amountB === undefined ? r.amount : r.amountB,
                  (r.unipolar === true ? 1 : 0) + (r.loop === true ? 2 : 0)], 7 * i);
      });
      x.scope_routes(list.length);
    },
    gate(open, velocity) { x.scope_gate(open ? 1 : 0, velocity); },
    noteDown() { x.scope_noteDown(); },
    setGated(on) { gated = on; x.scope_gated(on ? 1 : 0); },
    strike(hz, velocity) { x.scope_strike(hz, velocity); },
    reswing() { x.scope_reswing(); },
    setInput(samples) { input = samples || null; },
    block(pictL, pictR, n, outL, outR, pictBL, pictBR) {
      oscillatorsIn();
      const at = x.scope_lanes(n);
      if (input) new Float32Array(x.memory.buffer, at + 24 * n, n).set(input.subarray(0, n));
      x.scope_block(n, (input ? 1 : 0) | (outL && outR ? 2 : 0) | (pictBL && pictBR ? 4 : 0));
      const lanes = new Float32Array(x.memory.buffer, at, 7 * n);
      pictL.set(lanes.subarray(0, n));
      pictR.set(lanes.subarray(n, 2 * n));
      if (outL) outL.set(lanes.subarray(2 * n, 3 * n));
      if (outR) outR.set(lanes.subarray(3 * n, 4 * n));
      if (pictBL) pictBL.set(lanes.subarray(4 * n, 5 * n));
      if (pictBR) pictBR.set(lanes.subarray(5 * n, 6 * n));
      afterwards();
    },
    // The effects worklet's call: a live pair in, the pair through the plane out.
    effect(inL, inR, outL, outR, n) {
      oscillatorsIn();
      const at = x.scope_lanes(n);
      const into = new Float32Array(x.memory.buffer, at, 2 * n);
      into.set(inL.subarray(0, n));
      into.set(inR.subarray(0, n), n);
      x.scope_effect(n);
      const lanes = new Float32Array(x.memory.buffer, at, 4 * n);
      outL.set(lanes.subarray(2 * n, 3 * n));
      outR.set(lanes.subarray(3 * n, 4 * n));
      afterwards();
    },
    get envelope() { return envelope; },
    get envelopeStage() { return envelopeStage; },
    get envelopeVelocity() { return envelopeVelocity; },
    get budget() { return budget; },
    get gated() { return gated; },
    get pitch() { return pitch; },
    get scanHead() { return scanHead; },
  };
}

// An init script runs in a scope of its own: the two are made the page's globals by name.
globalThis.compiledGenerator = compiledGenerator;
globalThis.makeWasmCore = makeWasmCore;
