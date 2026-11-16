# How the one-to-two listening page was made

Scratch scripts, kept so the takes and numbers on `../index.html` can be made
again. They were run from a scratch directory beside a `bin/` of builds, and the
paths at the top of `build.py` and `rend.py` are that directory's; nothing here
is read by any suite.

- `options_patch.py INCLUDE` turns a copy of `core/include` into one with the
  options as compile-time switches, every one off by default (and the copy with
  all of them off was checked to render the same to the bit as the core, Dyad
  and Poly). The builds, each `render_cpp` against that copy:
  - `r-instep`: `-DOPT_XF_MS=30 -DOPT_DYAD_INSTEP=1` (A)
  - `r-lean`: `-DOPT_XF_MS=30 -DOPT_DYAD_INSTEP=1 -DOPT_DYAD_LEAN=0.5` (B)
  - `r-turn`: `-DOPT_POLY_TURN_OUTER=1` (C)
  - `r-nolean`: `-DOPT_POLY_NOLEAN=1` (D)
  - measured and not rendered: `r-xf` (`-DOPT_XF_MS=30`, the crossfade without
    putting the right back in step) and `r-slow` (`-DOPT_ROLE_MS=30`, Poly's roles
    glided over 30 ms rather than 4).

  The Dyad options are written for the plain wave and Scan only (`waveAt`), which
  is the path Harmonic tone plays; the oscillator's path (`oscStep`) would need
  the same crossfade.
- `rend.py` renders the phrase through a `render_cpp` with readings; `meas.py`
  tracks each ear's level, side over mid, correlation and the bass's own
  harmonics in each ear by lock-in; `summ.py` summarises a run; `bank.py` reads
  the bank out of `presets.h`; `plot.py` draws a run against the bass held alone
  (the figures the investigation was read from, not on the page).
- `build.py` makes every take (with its base64 beside it) and `numbers.json`;
  `page.py` writes the page from `page.tmpl` and `numbers.json`. `sweep.py` is the
  first form of the release sweep that `build.py` now carries.
