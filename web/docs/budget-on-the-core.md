# The voices' budget on the core

Written for stage 5, step 3, batch 6 (14 November), when budgettest's numbers
moved off the page's JavaScript and onto the core
(`core/tests/pieces/budget.py`). Nothing here has been changed: it is what
was measured, for the owner to decide on.

## What the governor gives up is the same as before

The governor (`scope::Generator::govern`, a port of the page's) gives things
up by a model of what each voice costs, not by a clock, so the question was
whether the core's model is the page's. It is, exactly. Run side by side on
the same scripts - budgettest's sweep of one to eight notes a layer with
everything on, the chords over five-second releases, the caps, the 4 kHz
drive, the fade, and every one of the 277 setups of the old library and the
bank under a chord of eight a layer and under a chord over releases - the two
gave the same units to the last bit, the same copies, factor and held notes
let go, and cut the same voices, voice for voice. So moving the checks
changes nothing anyone hears, and there are no recordings to compare: there
is no difference to listen to.

## What the model was fitted to

The model's costs were fitted to the page's JavaScript in milliseconds. The
core spends its time differently. Each feature's measured cost over its
modelled cost, as a share of the median of all of them (budgettest's rule,
which divides out the machine's speed):

| | page's JavaScript (node) | the core as WebAssembly (node) | the core, native |
|---|---|---|---|
| a unit of the model, in ms of work a second | 0.89 | 0.46 to 0.50 | 0.40 to 0.55 |
| everything on, one note a layer, ms a second | about 210 | 150 to 170 | 110 to 130 |
| pink noise | 0.71 to 0.73 | 0.58 to 0.69 | 0.35 to 0.47 |
| the filter | 0.66 to 0.67 | 0.57 to 0.58 | 0.40 to 0.50 |
| drawbars with seven copies | 1.00 to 1.13 | **1.68 to 1.78** | 1.03 to 1.27 |
| the dearest otherwise | pulse 1.13 to 1.80 | everything 1.52 to 1.63 | 1.37 to 1.46 |

Two runs of each, on a container busy with other work, so each figure moves by
a tenth or two between runs (the JavaScript's pulse read 1.80 once and 1.13
once). The JavaScript and WebAssembly columns are the page's own
`makeGeneratorCore` and `makeWasmCore` in node, blocks of 128 as the worklet
runs them; native is `core/tests/tools/budget_cpp.cpp`.

Three things follow:

- **The noise and the filter are costed dearer than the core spends on
  them**, by about twice natively. That is the safe side - a feature costed
  dearer than it is gives up a copy early; one costed cheaper is a glitch -
  so the pieces hold the other side (nothing past 1.6 of the median) and name
  these two rather than fail on them.
- **The drawbars with copies are costed cheaper than the WebAssembly spends
  on them**, 1.68 and 1.78 of the median in two runs, where natively and in
  JavaScript they sit near one. That is the side that glitches. It does not
  today, because the budget as a whole is cautious (next point): drawbars at
  seven copies, four notes a layer, the most the governor lets through, come
  to about 280 ms of work a second in WebAssembly, under half of real time.
  The pieces time the core natively and so cannot see it; a WebAssembly
  timing would have to run in node or a browser.
- **The budget is about twice as cautious as it was.** 350 units was about a
  third of a second's work a second in the page's JavaScript; the core does
  the same work in about half the time in WebAssembly and less natively. So the
  instrument gives up copies and notes at loads it could now carry. Raising
  the budget, or refitting the costs to the core, would change what a dear
  chord sounds like - more copies kept, fewer notes let go - and is the
  owner's to hear first. The pieces do not refit anything.

## What the page's checks could not see

- *"A drawn note is let go only once every undrawn one has gone"* had held of
  nothing since P4, which drew the inner voices too: no voice had both gains
  at nought, so the check passed over an empty list. The governor's rule is
  inner before outline; the pieces hold that, on a chord with outline notes
  enough that some do go.
- *"No preset gives anything up under a chord of eight a layer"* copied each
  setup's generator fields into a fresh core and left its routings out, which
  the model costs (a routing onto FM, sync or the shaper). Counted, one setup
  of the old library does give something up: Glass pad, whose
  `env.note>gen.fm` makes both hands' five copies four under sixteen notes -
  on the page's brain as on the core's. The bank gives nothing up either way.
  The check is kept as it was, with a second for the bank with its routings.
