/* What the instrument's worklet allocates while it plays (the outside review,
   17 Nov), run the way a worklet runs it - the module's text, evaluated with
   the globals a worklet has - in Node, where the garbage collector can be
   watched (v8.GCProfiler). An audio thread that allocates on every block is
   one the collector stops now and then, and a stop longer than a block is a
   click.

   Usage: node workletalloc.mjs <module.js> <core.wasm> <setup code> <seconds>
   Prints a JSON report: the bytes allocated on the heap per simulated second
   (each collection's heap before it, less the heap after the one before),
   the typed arrays' bytes and views made a second (counted as made), the
   collections, and the chunks posted, so a quiet worklet that posted nothing
   is not taken for a frugal one. */
import fs from "node:fs";
import v8 from "node:v8";

const [, , modulePath, wasmPath, code, secondsText] = process.argv;
const seconds = Number(secondsText) || 10;
globalThis.sampleRate = 48000;
globalThis.currentTime = 0;
globalThis.currentFrame = 0;
let Processor = null;
globalThis.registerProcessor = (name, cls) => { if (name === "scope-brain") Processor = cls; };
const posted = { chunks: 0, other: 0, errors: [] };
// The page's answers, delivered before the next block: a worklet takes its messages between blocks.
const answers = [];
let processor = null;
globalThis.AudioWorkletProcessor = class {
  constructor() {
    this.port = {
      onmessage: null,
      /* The page's side, as makeBrainHost answers: a chunk's lanes are copied
         into its ring and, where the worklet asks for them back (recycle),
         handed back. Nothing is cloned here, so what is counted is what the
         worklet made, not what a page would make receiving it. */
      postMessage: (m, transfer) => {
        if (m && m.error) posted.errors.push(m.error);
        if (m && m.lanes) {
          posted.chunks++;
          // NO_RECYCLE, the null: a page that never sends the buffers back.
          if (processor && processor.wantsBack && !process.env.NO_RECYCLE) answers.push(m.lanes.map((lane) => lane.buffer));
        } else posted.other++;
      },
    };
  }
};
/* Every typed array the module makes, counted as it is made: the bytes of a
   new buffer, and a view onto one that exists (the core's memory, a lane
   handed back). A typed array's bytes are not on the heap, so the
   collector's figures above do not see a lane or a grid made a chunk;
   this does. Subclasses, so a subarray (made by its species) is counted
   as the view it is. */
const made = { bytes: 0, views: 0, counting: false };
for (const name of ["Float32Array", "Float64Array", "Uint8Array", "Uint16Array", "Int16Array", "Int32Array"]) {
  const Real = globalThis[name];
  globalThis[name] = class extends Real {
    constructor(...args) {
      super(...args);
      if (!made.counting) return;
      if (args[0] instanceof ArrayBuffer || (typeof SharedArrayBuffer !== "undefined" && args[0] instanceof SharedArrayBuffer)) made.views++;
      else made.bytes += this.byteLength;
    }
  };
}
(0, eval)(fs.readFileSync(modulePath, "utf8"));
const bytes = fs.readFileSync(wasmPath);
const module = new WebAssembly.Module(bytes);
// What the page hands over: the module where the worklet takes one, the bytes where it compiled its own.
try {
  processor = new Processor({ processorOptions: { wasm: module, code } });
  if (posted.errors.length) throw new Error(posted.errors[0]);
} catch (error) {
  posted.errors.length = 0;
  processor = new Processor({ processorOptions: { wasm: bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), code } });
}
processor.wantsBack = typeof processor.spare !== "undefined";
// A chord held, so the instrument has work in every block.
for (const note of [48, 55, 64]) processor.port.onmessage({ data: { op: "midi", bytes: [0x90, note, 100] } });
const out = [[new Float32Array(128), new Float32Array(128)]];
const blocks = Math.round(seconds * sampleRate / 128);
const run = (n) => {
  for (let i = 0; i < n; i++) {
    while (answers.length) processor.port.onmessage({ data: { recycle: answers.shift() } });
    currentTime += 128 / sampleRate; currentFrame += 128;
    processor.process([[]], out);
  }
};
run(Math.round(sampleRate / 128));          // a second to settle: first-use allocations are not the steady state
const before = { chunks: posted.chunks };
const profiler = new v8.GCProfiler();
profiler.start();
made.counting = true;
const heap0 = v8.getHeapStatistics();
run(blocks);
const heap1 = v8.getHeapStatistics();
made.counting = false;
const { statistics } = profiler.stop();
let allocated = 0, last = heap0.used_heap_size;
for (const gc of statistics) {
  allocated += Math.max(0, gc.beforeGC.heapStatistics.usedHeapSize - last);
  last = gc.afterGC.heapStatistics.usedHeapSize;
}
allocated += Math.max(0, heap1.used_heap_size - last);
console.log(JSON.stringify({
  seconds, blocks, chunks: posted.chunks - before.chunks, errors: posted.errors,
  bytesPerSecond: Math.round(allocated / seconds),
  arrayBytesPerSecond: Math.round(made.bytes / seconds), viewsPerSecond: Math.round(made.views / seconds), collections: statistics.length,
  collectionsPerSecond: +(statistics.length / seconds).toFixed(2),
  recycled: processor.wantsBack,
}));
