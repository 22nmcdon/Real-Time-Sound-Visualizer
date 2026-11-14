# The golden files

What the page's JavaScript answered for each parity scenario, so the core can
be held to it once the JavaScript engine is gone (stage 5 of
`plugin/STAGE5-PLAN.md`, step 2). One gzipped file a parity section; 5.3 MB in
all. `core/tests/golden_runs.py` writes and reads them, and the top of that file
is the long version of what follows.

## Why they exist

Parity does two jobs (`plugin/STAGE5-PLAN.md`, section 2). One is *the port is
the same as the original*: a scenario through the page's `makeEnvelope` (and
the generator, keyboard, matrix, clock, level, capture, beam, picture sources,
Scan, hearing, score, setup codec) and through the C++, compared sample for
sample. The other is *the face and the core agree*, which compares the page's
controls with the core's panel and has no JavaScript engine under it.

When the engine goes, the first job has nothing to compare against. These files
are that comparison kept on disk: the JavaScript's answer, recorded while both
still exist and proven against the live page every run, so the core can be held
to it after the page's engine is deleted. Only the thirteen port-is-the-original
sections have a file; the face-and-core sections have none and do not change.

## What is in a file

A list of runs in the order parity made them. Each is `{tool, input, hash}`
with either

- `output` - the tool's text exactly, for a run short enough to keep whole; or
- `sketch` and `chars` - for a long run (the generator's 130 runs alone are
  95 MB of digits). The sketch is, per line, the text with the numbers taken
  out, and per block of 64 numbers three figures: their sum, their sum weighted
  by position, and the largest in size. A number that is not finite is kept
  where it sits, so a NaN is never summed away.

A run is keyed by its tool and a hash of the scenario's text (the checkout's
paths removed, so the hash is the same in any checkout), not by the scenario's
file name - parity reuses names like `one.txt` for hundreds of runs.

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
thousands of samples, not two in a cancelling pair.

The NaN rule is parity's `worst()`: a NaN anywhere is a failure, never skipped,
and the tolerance is `1e-12` relative to the larger of one and the value.

## Regenerating a file (when the sound is meant to change)

```
CHROME=/opt/pw-browsers/chromium python3 core/tests/parity.py --write-golden
```

One command, and it **refuses to overwrite a section's file unless every check
in that section passed** - that is, unless the page's JavaScript and the C++
core agreed on it, the same `1e-12`. So a regenerated file is never merely
believed: it is the JavaScript's answer, confirmed by the core, recorded. A
section with a failure prints `REFUSED` and keeps its old file. A section whose
runs are unchanged prints `KEPT` and rewrites nothing, so an unrelated change
leaves the files - and the git diff - alone. Because the files are gzipped and
not readable as a diff, `--write-golden` prints, for each run that moved, where
it first differs from the old file.

The scenarios are built from fixed random seeds, so a regeneration with no
intended change writes identical bytes. Commit the changed `.json.gz` with the
code that changed the sound, and say in the commit why the sound moved.

## Running against the files

```
CHROME=/opt/pw-browsers/chromium python3 core/tests/parity.py            # all three
CHROME=/opt/pw-browsers/chromium python3 core/tests/parity.py --golden   # the core against the files, no page
```

With no flag, parity runs all three: the page's JavaScript as before, the core
as before, the two compared as before, *and* each run checked against its
golden file and the core checked against the file directly. This is what proves
the files still match the live page, and it is what runs before a push while
the JavaScript is still here.

`--golden` is what parity becomes once the engine is gone: the JavaScript is not
run, the files stand in for it, and the core is held to them. A run kept whole
is handed to parity's own comparison as the JavaScript's text would have been; a
run kept as a sketch cannot be (a sketch is not text), so for those the core's
answer is compared with the sketch here, and parity's own comparison sees the
core against itself. `--golden` needs the C++ tools built, which parity does.

## The nulls

The comparison is null-tested every run (in `--golden` and the three-way
default, at the end): a value in a file moved by a billionth, and a NaN put in
its place, must each fail and name the line and value, for a run kept whole and
a run kept as a sketch; a NaN against a NaN is no difference; and a value moved
by a tenth of the tolerance is none either. Beyond those standing nulls, the
three the plan asked for were seen red by hand as the mode was built: one value
changed in a file (the golden comparison goes red naming the scenario, line,
value and gap); the core mutated (both the JS-vs-core comparison and the
core-vs-file comparison go red); and a NaN fed into a file (red, whole and
sketch).

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
