# The golden files

What the page's JavaScript answered for each scenario of the core's tests,
recorded while it still ran, so the core can be held to it now that the
JavaScript engine is gone (`plugin/STAGE5-PLAN.md`): one gzipped file a
section, fifteen in all, 6.5 MB. The thirteen of the port-is-the-original job
were written in stage 5's step 2, from the page's engine; `restore.json.gz`,
what the page's own `restore` left in its brain for every setup the restore,
morph, menus, hands, rack, fade and view sections load, was written in step 6,
the day before that brain was deleted. `core/tests/golden_runs.py` writes and
reads them, and the top of that file is the long version of what follows.

## Why they exist

The core began as a port of the page's own engine, and the test that mattered
was whether it was the SAME: a scenario through the page's `makeEnvelope` (and
the generator, keyboard, matrix, clock, level, capture, beam, picture sources,
Scan, hearing, score, setup codec and restore) and through the C++, compared
sample for sample. Once the page's engine went there was nothing to compare
against; these files are that comparison kept on disk - the JavaScript's
answer, proven against the live page on every run until the last, and now the
answer the core is held to. Where `core_tests.py` called the page's runner, it
now asks for the recording (`golden.recorded("envelope", path)`), and holds the
core's own run on the same scenario to it, to 1e-12.

The other two jobs of `core_tests.py` have no recording: the face and the core
agree (the page's controls, bank, sources and codec against the core's panel,
presets, schema and codec, read off the page as it is now), and the engine's
pieces hold by their own numbers (`core/tests/pieces/`).

## What is in a file

A list of runs in the order the tests made them. Each is `{tool, input, hash}`
with either

- `output` - the tool's text exactly, for a run short enough to keep whole
  (and every restore run, which is read field by field as JSON); or
- `sketch` and `chars` - for a long run (the generator's 130 runs alone are
  95 MB of digits). The sketch is, per line, the text with the numbers taken
  out, and per block of 64 numbers three figures: their sum, their sum weighted
  by position, and the largest in size. A number that is not finite is kept
  where it sits, so a NaN is never summed away.

A run is keyed by the tool that recorded it and a hash of the scenario's text
(the checkout's paths removed, so the hash is the same in any checkout), not by
the scenario's file name - the tests reuse names like `one.txt` for hundreds of
runs. The tools are named as they were when they recorded (`envelope_js.mjs`
and the rest, `restore_page.py`), though they were deleted in step 6: the files
did not have to be rewritten when the runners went.

**What the sketch can and cannot see.** One value moved by `g` moves the block
sum by `g`, held to the same `1e-12` tolerance the whole-text comparison uses;
and the weighted sum over the plain sum gives the position, so a mismatch names
the line, the block, the moved value and by how much, as the whole text does.
Two values swapped, or a run a sample late, leave the sum and move the weighted
sum. What it cannot see is two or more values moved within one block so that
both sums cancel - two changes of opposite sign in the ratio of their positions
- which no plausible port fault produces and a deliberate one could. Where a
mismatch has to be exact, the run is kept whole; the sketch is only for the
runs too large to keep whole, and those are bulk renders where a fault moves
thousands of samples, not two in a cancelling pair. A sketched run cannot be
handed to a section's own comparison as text, so there the core's answer is
held to the sketch directly and the section sees the core against itself: the
sketched sections rest wholly on that direct comparison, which is a check of
its own in every section and null-tested at the end of every run.

The NaN rule is the tests' `worst()`: a NaN anywhere is a failure, never
skipped, and the tolerance is `1e-12` relative to the larger of one and the value.

## Running against the files

```
CHROME=/opt/pw-browsers/chromium python3 core/tests/core_tests.py
```

Every section with a file holds the core to it, and closes with two checks of
its own: that the file holds no run the tests no longer ask for, and that the
core's runs against the file directly found nothing (and were made at all). A
scenario the file has no run for fails, naming it.

## Writing them again (when the sound is meant to change)

```
CHROME=/opt/pw-browsers/chromium python3 core/tests/core_tests.py --write-golden --because "what changed in the sound, and why"
```

Until step 6 a rewrite was refused unless the page's JavaScript and the core
agreed on the section, so a new file was never merely believed. With no page
left to confirm the core, the guard is the reason: `--write-golden` refuses to
run without `--because`, and every rewrite appends a line to the log below -
the date, the reason, and which files moved by how many runs - so a
regenerated file is never anonymous and its reason sits beside it in the same
commit. A section is still refused if any check of its own failed (with the
files out of the way, those are the checks of what the sound should be, and
their nulls: a change that breaks one is not the change that was meant). A
section whose runs did not move prints `KEPT` and rewrites nothing, so an
unrelated change leaves the files - and the git diff - alone; for each run that
moved, it prints where it first differs from the old file, since a gzipped
file is not readable as a diff.

"Moved" is the plain run's rule: past the tolerance. A run the core still
answers within it is kept as it was, byte for byte, and the section is handed
the recording, as the plain run hands it; only a run that moved takes the
core's text, and only a file with one is written (16 Nov). Before that the
core's text stood in for every recorded run under `--write-golden`, which
spells numbers its own way (`4000` for `4000.0`) and differs below the
tolerance: six checks that read the recorded text failed on an unchanged core
and refused keyboard, matrix, level and hearing, and functions, picture, scan,
score and restore were rewritten for nothing. Checks that look for a value in a
run's text look for it with every number spelt one way (`has`, `spelt` in
core_tests.py), so a run the core's text has replaced reads as the recording
did. Seen on 16 Nov: on an unchanged core the writer keeps all fifteen files
and refuses none, where the old one rewrote five and refused four; with the
level's attack moved by a millionth and the dyad's top clamp moved to 3999 Hz,
it wrote level alone (seven runs, by about 1.3e-7), logged the reason, refused
keyboard for its clamp check and kept the other thirteen.

Why a reason and not a bound: refusing a rewrite past some size of change
would stop the changes worth making and pass the small wrong ones. A reason
that has to be written down puts the judgement with whoever meant the change,
and leaves it on the record for whoever reads the diff.

The scenarios are built from fixed random seeds, so a rewrite with no change to
the sound writes identical bytes.

## The nulls

The comparison is null-tested every run, at the end: a value in a file moved by
a billionth, and a NaN put in its place, must each fail and name the line and
value, for a run kept whole and a run kept as a sketch; a NaN against a NaN is
no difference; and a value moved by a tenth of the tolerance is none either.
Beyond those, the nulls that broke a copy of the page and ran its JavaScript
(a page that kept a delay line through a switch, read the Key as its gate,
dropped the arpeggiator's strike, walked a long segment whole) break the same
line in a copy of the core now (`mutant` in `core_tests.py`), and the recorded
answer must be told from the broken core's. Step 2's three, seen red by hand as
the files were built: one value changed in a file (red, naming the scenario,
line, value and gap); the core mutated (red in the section's comparison and in
the direct one); and a NaN fed into a file (red, whole and sketch).

## Rendering the instrument offline (render_cpp)

The golden files hold the port to what the page's JavaScript answered. What a
sound *should* do is held by the core's own tests, `core/tests/pieces/`, and
the ones that need the whole instrument playing - a setup with the loop
closed for thirty seconds, a microphone through the effects, a preset held
under a note - render it offline with `core/tests/tools/render_cpp.cpp`
(stage 5, step 3, batch 5). In a piece:

```
rows = kit.render([["make", 48000, CODE, {"pictureAmount": 0}],   # a setup code, fields laid over it
                   ["midi", 0x90, 57, 127],                         # at the sample reached
                   ["every", 0.1, "heard", "stage", "meter"],       # readings each tenth of a second of audio
                   ["to", 30]])                                     # render to thirty seconds
```

Each row is a reading's moment (`t`) and its readings' words. The file's
header lists every command (the hands, an input from a file or a sine,
`record` for the heard pair, the lanes and the grid as float32) and every
reading. A run is the same to the bit every time, and reading does not move
what is rendered; `core/tests/pieces/render.py` proves both, with their
nulls, before anything else stands on it. It is native only, like
instrument_cpp's own readings, so nothing it prints is compared with the
page.

Since stage 5's step 5a the heard pair `record` writes is the limited one,
6 ms late (the limiter's lookahead) and bent at the top, as a host and the
speakers get it. A piece that holds the heard pair to the sample against
something the instrument made - an input passed through, the band split's
sum, the Output's quarter - records `prelimit` instead, the pair as it stood
before the limiter, or switches the limiter off with the harness's
`["control", "limiter", "0"]`. The first golden file regenerated for a
reason of its own was 5a's `picture.json.gz`: one run of eleven, thirty of
the meter's verdicts "wandering" become "settled" (the meter's verdict reads
change over the eye's time since 5a), every number in it unmoved.

## The log

Each rewrite of a file since stage 5's step 6, as `--write-golden --because` writes it.

- 2026-11-16: The split by notes adds three setup fields, splitBy, splitEnd and splitCount, whose defaults are the key split. Rewrote setup (2 of 13 runs: the codec's run, whose every decoded setup gains the three keys at their defaults, and the table of fields, which gains them with their rules; neither differs from its recording in anything else). The rewrite also offered functions, picture, scan, score and restore, which write mode stores afresh wherever the core's digits differ at all; they passed against their recordings to the tolerance before and after, so they were left as recorded.
- 2026-11-16: Every note heard in both ears at the Width, through a heard plane of its own (16 Nov, the owner's, after web/docs/both-ears.md); a dyad's change of interval starting the two phases in step with a 30 ms crossfade (option A of one-to-two-notes.md); and the quarter turn's switch, polyRound, gone (always on, so no setup, default or restored tone names it). Rewrote generator (26 of 26 runs new or changed, 0 dropped); setup (2 of 13 runs new or changed, 0 dropped); restore (53 of 53 runs new or changed, 10 dropped).
- 2026-11-16: A note handed between the dyad's two places without a pop (16 Nov, the owner's): the old right keeps its own pitch through a change of interval, and a note that goes on through one carries its phase into its new place, crossfaded in a straight line. Rewrote generator (1 of 26 runs new or changed, 0 dropped).
- 2026-11-16: The split by notes' Chord window adds one setup field, splitWindow (0 to 15 ms, default 10), additive like the split's other three: the codec's decoded setups gain the key at its default and the table of fields gains it with its rule; nothing else in either differs from its recording. Rewrote setup (2 of 13 runs new or changed, 0 dropped).
- 2026-11-16: The merge of the Chord window (splitWindow) onto every note heard in both ears: the setup recording gains the union of both branches' fields. Rewrote setup (2 of 13 runs new or changed, 0 dropped).
- 2026-11-17: What the Width applies to (widthDrawn) and the sound's own Width (soundWidth), two additive setup fields (16 Nov, the owner's switch): the table of fields and the codec's defaults gain them, and every restored panel the sound's Width's range, which the morph walks. Rewrote setup (2 of 13 runs new or changed, 0 dropped); restore (53 of 53 runs new or changed, 2 dropped).
- 2026-11-17: The rack gained an EQ (17 Nov): its seven setup fields, their seven upper-hand twins and the schema's rules joined the page's defaults, so the codec's answers name them. Additive, nothing heard moves: every gain defaults to nought, which leaves the EQ out of the sum (pieces/eq.py holds that to the bit). Rewrote setup (2 of 13 runs new or changed, 0 dropped).
- 2026-11-17: The owner's picks from the Bass listening page and the voices' budget refit (17 Nov): the Bass under the pad's bass hand reads at Scan 30 rather than 25, which the restore runs drawn from the bank carry; and the governor's model refitted to the core in WebAssembly (drawbars dearer, pink noise and the filter cheaper), so the generator runs whose voices the governor thins give up copies at other loads. Rewrote generator (4 of 26 runs new or changed, 0 dropped); restore (3 of 53 runs new or changed, 3 dropped).
- 2026-11-17: the owner's Width default, 50 (17 Nov), the player's and the sound's own; with the EQ's switch made a field (eqOn) the same day. Rewrote restore (53 of 53 runs new or changed, 0 dropped).
- 2026-11-17: the setup codec at version 12: a version-11 code with a gain off nought comes up with eqOn, the EQ's switch made a field (17 Nov). Rewrote setup (13 of 13 runs new or changed, 0 dropped).
- 2026-11-18: Drawn envelopes (18 Nov, web/docs/mseg-design.md): the setup codec at version 13 with each envelope's delay, hold and shape fields, whose decode pass writes an old code's envelope as the shape that plays it to the bit; the panel's new controls (the envelopes' Delay and Hold, the Shape menus) and its times to 20 s; and the modulation fade's slopes on the drawn envelopes' one bend law, (1 - e^-kt) / (1 - e^-k) for the power of t it had, which moves a fade with a midpoint off a half and leaves one at a half where it was. The amp, filter and Envelope's own sound did not change: every envelope recording passed before the rewrite. Rewrote matrix (2 of 11 runs new or changed, 0 dropped); setup (13 of 13 runs new or changed, 1 dropped); restore (53 of 53 runs new or changed, 5 dropped).
- 2026-11-18: Painting, step 2 (18 Nov, web/docs/painting-design.md): two additive setup fields, screenDraws (trace or paint, default trace) and paintPersistence (the painting's half-life in seconds, 1 to 120, default 16): the table of fields and the codec's defaults gain them. Nothing heard moves: a setup without them draws the trace, and painting runs nothing while the trace is drawn. Rewrote setup (2 of 13 runs new or changed, 0 dropped).
- 2026-11-19: The drawn LFOs (19 Nov, web/docs/lfo-drawn.md): three additive setup fields per LFO (l<i>m, l<i>p, l<i>t) at their defaults, and the panel's Phase slider, Starts menu and drawn Shape option; nothing heard moves, every old setup takes lfoStep's own path; old op lists reproduce the old recordings exactly (checked before the rewrite: all 53 restore runs matched with the old lists and lfoPhase0 left out of the dump, and the setup runs differ only by the six new keys). Rewrote setup (2 of 13 runs new or changed, 0 dropped); restore (53 of 53 runs new or changed, 5 dropped).
- 2026-11-22: The EQ's whole range (22 Nov): setup version 14 turns each band's old place, a hundred over a span of its own, into the same hertz as a place of a thousand over 20 Hz to 20 kHz (the cutoff's law), and the gains reach -16 dB. The setup codec's answers move by the version stamp, the table of fields' new EQ rules and defaults, and 630 new version-14 commands; nothing heard moves: every sound recording and restore were kept untouched on the runs before this one. Rewrote setup (13 of 13 runs new or changed, 1 dropped).
- 2026-11-23: The zoom is only the look (22 Nov, the owner's): the beam lays the grid Scan reads unmagnified at any zoom, so the beam's runs with a zoom other than one lay the whole record and the figure at its own size; and the zoom's slider moved from Scope & measure to the screen's toolbar, so restore's random walks over the page's sliders in markup order touch other view sliders - between old and new only level, position, timebase, holdoff and zoom differ. Rewrote beam (3 of 5 runs new or changed, 1 dropped); restore (2 of 53 runs new or changed, 2 dropped).
