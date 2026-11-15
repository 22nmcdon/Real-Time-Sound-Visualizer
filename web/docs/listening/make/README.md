# How the listening page was made

Scratch scripts, kept so the numbers on `../index.html` can be made again. They
were run from a scratch directory holding a `bin/` of builds, not from here, and
nothing in them is read by any suite.

- `measure.py` runs `core/tests/tools/honesty_cpp.cpp` (built as `bin/honesty_cpp`)
  at 48 kHz with the key at sixteen places, 0.900 s to 1.134 s after the load, a
  sixty-fourth of a second apart, and summarises each run as
  `web/tests/honestytest.py`'s `summary` and `RULES` do.
- `phrase.py` renders a phrase through `render_cpp` (`record heard`) and writes the
  left channel as a 16-bit, 44.1 kHz WAV.
- `gov.py` holds the two budget cases and reads the governor through a scratch
  `render_cpp` with a `budget` reading (`render_gov.patch`), built against a
  copy of `core/include` with the budget as a macro: `-DSCRATCH_BUDGET=350` or `45`,
  as it is or with `fit.patch`'s four fitted terms.
- `wasmcost.py` times `budget.py`'s twenty cases in the core as WebAssembly: a WASI
  build of `budget_cpp` (`budget_wasm.patch`: no `ifstream`, which the WASI libc++
  lacks, blocks of 128 as the worklet runs, and the exception stubs
  `core/wasm/scope_wasm.cpp` uses) run in node by `runwasm.mjs`. Its two runs are
  `wasmcost-1.json` and `wasmcost-2.json`.
- `build.py` makes every number and take into `numbers.json` and the WAVs, with
  each WAV's base64 beside it; `page.py` writes the page from `numbers.json`.
