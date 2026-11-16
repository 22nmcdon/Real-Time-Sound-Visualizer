# How the both-ears listening page was made

Scratch scripts, kept so the takes and numbers on `../index.html` can be made
again. They were run from a scratch directory holding them, a `bin/` of builds
beside it and an `out/` for the renders (`rend.py` finds both from where it
sits); nothing here is read by any suite, and nothing in `core/include` was
changed.

- `heard_patch.py INCLUDE` turns a copy of `core/include` into one with the two
  ways as compile-time switches, every one off by default. Each build is
  `render_cpp` against that copy (`g++ -std=c++17 -O2 -Wall -Wextra -Werror -I
  COPY core/tests/tools/render_cpp.cpp`):
  - `render_cpp`: the real core, today
  - `r-null`: the copy with no switches, which `proof.py` requires to be the core to the bit
  - `r-w1a`, `r-w1b`, `r-w1c`: `-DOPT_HEARD=1 -DOPT_K=0.0`, `0.5`, `1.0` (Way 1's three widths)
  - `r-w2`: `-DOPT_W2=1 -DOPT_K=1.0` (Way 2)

  Way 1 is written for Poly (every voice, any oscillator) and for Dyad's plain
  wave and Scan (`waveAt`), which is Harmonic tone's path; Dyad's oscillator and
  noise paths fall back to the drawn pair, and layer B is not covered.
- `proof.py` renders both phrases through every build and compares each with the
  core byte for byte: the drawn lanes, the shown grid, the loop's readings and,
  apart, the heard pair and the limiter. Writes `proof.json`.
- `build.py` renders every take (with its base64 beside it), measures each note
  in each ear by lock-in, the release sweep and the limiter's share, and writes
  `numbers.json`; the copy kept here has the figures' points taken out, which
  `build.py` writes again. `page.py` writes the page from `page.tmpl`.
  `bank.py` reads the bank out of `presets.h`.
