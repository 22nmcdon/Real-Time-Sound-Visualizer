# Becoming a plugin

The instrument as a VST3 and AU plugin (and a standalone app), with the page as
its UI. Decided: **one C++ core, shared.** The sound engine and, in time, the
brain are written once in C++, built natively for the plugin and to WebAssembly
for the website, and the page becomes the UI for both. The website on GitHub
Pages goes on working throughout; nothing here may break it.

## Why the brain has to move, not only the engine

A standalone app could keep the brain in the page - the modulation matrix, the
sources, the keyboard's notes, the arpeggiator, the score, the fade envelopes,
presets - and send the engine the same one message a frame that the page sends
its worklet now. A plugin cannot. A host closes the plugin's window whenever it
likes, and closing it destroys the web view: everything the page runs stops,
and a patch that should go on playing in the host's timeline goes silent. So in
the plugin the page is a view of state held in C++, and a closed window
changes nothing about the sound.

That is most of the logic in `web/scope.html`, which is why the shared core
matters: two brains, one in JavaScript for the site and one in C++ for the
plugin, would drift apart in the way the README records again and again. One
brain, compiled twice, cannot.

## The boundary

```
  the page (UI)  <-- state snapshots, picture frames --  core (C++)
                 --- commands: set, patch, load, note -->  engine + brain
```

- **The page** draws and edits. It no longer owns state: it asks the core to
  change something and redraws from what the core says. In the browser the core
  is WebAssembly in the worklet; in the plugin it is native, behind JUCE.
- **The picture** is drawn by the page from sample windows the core hands over:
  in the plugin through JUCE's resource provider (`/picture.bin`, binary, one
  fetch a frame), in the browser straight from the worklet.
- **The picture's own sources** - the phosphor grid, the photocell, the picture
  meter - move into the core too, since they drive the sound and must go on
  when the window is closed.

## Stages

**0. The spike** (done). A JUCE plugin that builds on Linux here, loads the
page from inside its binary, plays notes through the first ported piece of the
core, and serves the samples it played; the page finds JUCE's bridge, asks the
plugin what it is (`scopeHost`), and draws the plugin's output instead of its
own generator - one fetch of `/picture.bin` a frame, never two at once - and
reports back how the picture is getting through (`scopeReport`). And the method
the port lives by: `core/tests/parity.py` holds each ported piece to the page's
own JavaScript, sample for sample; `web/tests/hosttest.py` holds the page's
side to a fake bridge serving a known stereo signal.

Measured in the standalone on a virtual display here, with software rendering
and no real sound card (an ALSA null device):

| | frames a second | fetch, mean | worst |
|---|---|---|---|
| no audio device (nothing to play) | 62 | 13 ms | 43 ms |
| device running, silent | 59 | 13 ms | 48 ms |
| device running, A3 held | 46 | 16 ms | 134 ms |

Serving the picture costs the plugin's main thread about 1.5 per cent. The
drop with a note held is the page drawing a real waveform in WebKitGTK's
software renderer while the null device's audio thread spins a whole core
(it never blocks, so the processor runs flat out) - not the transport. A real
machine with GPU compositing and a real device will do better; that is a
reasonable expectation, not a measurement, and the first run on one should
check it. The answer to the spike's question is yes: the path holds the
picture at frame rate with room to spare, and the brain can move.

**1. The engine.** `makeGeneratorCore` (about 1,900 lines) to C++: voices and
layers with their pushes, the voice's oscillator, shaping and filter, drawbars,
wavetables and drawn cycles, the harmonograph and the solids, the plane, the
delay and chorus, the quantiser, the governor. Each piece held to the page by
the parity harness before the next is started, with scenarios written so the
fixture can show the effect.

**Stage 1 is ported.** The whole of `makeGeneratorCore` is in the core,
leaves first, each piece held to the page before the next was started:

- the envelope (`scope/envelope.h`);
- the waveforms and the functions under them (`scope/wave.h`): `cycleOf`, the
  two bleps, the drawbars' gain and weights, the intervals, the
  state-variable filter, the drawn cycle's read, and `waveAt` for every shape;
- the four noises (`scope/noise.h`) and the LFOs (`scope/lfo.h`);
- the voice's oscillator (`scope/osc.h`), with unison, FM, ring, hard sync
  and its band-limited reset, and the sub; and what follows it in a voice
  (`scope/voice.h`): the filter with its cached coefficient, drive and fold
  with their oversampler, and the crush;
- the chord's voices (`scope/voices.h`): the quantiser, `reconcileVoices` with
  its release tails, and `sound`;
- the plane (`scope/plane.h`): every shape of it at one, two and four times
  the rate, then the chorus and the echo, for each of the three pairs;
- the drawings: the figures (`scope/figures.h`), and the solids as the page
  builds them, routes and all, with the beam walked round them
  (`scope/wireframe.h`);
- and the generator itself (`scope/generator.h`): the routings summed into
  each layer's pushes, the governor, the dyad, the chord on two layers, the
  figure, the solid, the pendulums plucked and swung, the second generator,
  the input three ways, the crossings and the score's voices, and the effect
  a live input goes through - with the calls the worklet makes between
  blocks.

The pieces are held by about 18,000 calls written by `parity.py` and answered
by both (`functions_js.mjs`, `functions_cpp`). The functions inside
`makeGeneratorCore`, which the page does not export, are lifted out by name
(`coreScope`) and run in the closure they were written for. The whole is held
by 71 runs through the page's own `makeGeneratorCore` and `scope::Generator`
alike (`generator_js.mjs`, `generator_cpp`), driven as the worklet drives
it: blocks of 128 into float arrays, with the routings, the chord, the gate,
strikes, kicks and resets landing between blocks while things sound. The
page's side is assembled from the names `generatorModuleSource` binds, read
out of its own text, so the runner has exactly what the worklet has. Each run
must show what it is for - the governor taking copies away, both crossings
firing, layer B drawing, the heard pair differing from the picture in a
chord, a solid still spinning from a kick - and each of those checks was seen
to fail on a wrong value before it was believed.

Nearly every number agrees to the last bit, and none by more than 6e-15. Of
277 mutants of the ports, 263 are caught. The fourteen that live change
nothing that can happen, and each was looked at:

- a voice's phase folded back up from below nought, which `cycleOf` and `sin`
  read as the same point of the cycle;
- a compiled path's span between neighbours, which is never nought; a test
  for a corner that no list holds; a solid's leg, which no model projects to
  nothing; and an exact tie, which the beam's walk never lands on;
- heard left and right, which are equal for every role;
- a governor's rank, which never ties, since every voice is born at its own
  count; and the rule never to cut the last voice, which no setting can make
  cost more than the budget alone;
- a score voice's age, which only matters while all four are sounding;
- a store into a float array, which rounds whether or not it is told to;
- the guard against a `NaN` in the accumulator, which nothing sends;
- the drawbars' weights worked out only when a level moves, which is economy:
  worked out every sample they come out the same;
- the filter envelope's reset when the core is made, and the level an
  envelope is left at when ungated, neither of which is read before
  `setGated` resets it again.
`Math.hypot` is held to the last bit, because V8 computes it by an algorithm
the port copies (scaled by the largest, the sum compensated) and a solid's
corners are divided by it.

The plugin plays it. `ScopeProcessor` runs `scope::Generator` in place of
the spike's sine - its heard pair to the speakers, its picture pair to the
page - with the host's notes reaching it as the page's keyboard reaches a
gated dyad, each at its own sample. The shell test holds what the plugin
plays to the generator driven directly with the same calls, and they are
equal to the last bit; the same note a sample late would be 0.03 out. With
A3 held, the standalone's page reads 220 Hz on both channels, the right a
quarter-cycle on from the left, the harmonic's third partial in the spectrum,
and a peak of 0.362 - the page's default dyad, made in C++.

Then stage 2, below.

The plane's delay lines are made with it, not the first time the echo or the
chorus is wanted as in the page, and its oversamplers are emptied in place
when the factor changes rather than made again: allocating on the audio
thread is how a plugin glitches. A line made early holds noughts until it is
written, which is what one made late starts with, so nothing played differs.

A voice's envelopes hold their tone by pointer, not by copy and not by
reference: the page's envelope reads `tone.attackMs` every sample, so a slider
moved mid-note is heard mid-note, and a copy would freeze the tone at the
note's birth. A reference would do that job but makes a voice unmovable, and
voices live in a vector that is erased from. The mutant that freezes the tone
is caught by a scenario that moves the sliders while notes sound.

JavaScript's `Math.round` is `jsRound` in the core, not `std::round` (which
takes a half away from nought) and not `floor(x + 0.5)` (which rounds the
double just under a half up); the crush's quantiser is where it shows.

The noise draws from a `scope::Random` it is handed (mulberry32), not from
`Math.random`; the harness hands the page the same generator, so the two are
compared exactly. In use the plugin's noise and the site's are different
sequences of the same noise.

**2. The brain.** The modulation matrix and every source, the fade envelopes,
notes, layers, the arpeggiator, the score, the clock (the host's transport in
the plugin), presets and setup codes as the core's state. The host's automation
gets a curated set of parameters - the macros, the morph position, the main
knobs - rather than every control.

In pieces, as the engine went, each held to the page before the next:

- **2a. The keyboard** (ported): the stack, the pedal, controllers, bytes, and
  what notes tell the generator.
- **2b. The matrix** (ported): destinations, routings and their text, the
  reach and loop rules, the compiled routes each block with their fades, and
  events.
- **2c. The setup as the core's state** (ported, but for the snapshot): the
  page's flat snapshot and `restore`, setup codes and their migrations, and
  presets. The panel the keyboard reads becomes part of it, and so do the
  macros and the morph - which moves the panel's sliders, and so cannot come
  before them. (It was listed after time and the sources until the morph
  showed why not.)
- **2d. Time** (ported): the key and the clock (the host's transport in the
  plugin), the LFOs locked to it, the arpeggiator, the score and the MIDI out
  they share.
- **2e. The rest of the sources** (ported) that are not the picture's or
  the hearing's: the learned controllers as sources, the note envelope, the
  level, the drawings' six, and the threshold.
- **2f. The hearing sources** (ported), which analyse the sound and so are
  DSP in the core rather than the page.
- **2g. The host's parameters** (built), and the plugin's state as a setup
  code.

**2a is ported.** `scope/keyboard.h` is the page's `midi` functions: the
held stack and its rules (a velocity of nought is a release, a note does not
stack twice, a panic empties it), the sustain pedal and half-pedal, learned
controllers with their smoothing and names, `midiBytes` with running status
and a real-time byte taken wherever it lands - and what the stack tells the
generator: the dyad's interval with Hold, mono, the chord on one layer or two
(split with its learned point, layered, each layer's draw rule, A against B),
just chords, the gate, the drawings' rates and the rose's petals, a pitched
harmonograph struck by a key, and how the figures are laid out. And its
sources: Key, Sustain, Notes, Spread, Melody, Inner.

It is held to the page's own functions, lifted by name from `scope.html`
(`keyboard_js.mjs`) and run against a stand-in generator that writes down
every call; `keyboard_cpp` plays a real `scope::Generator` through a target
that writes down the same calls first. 24 named runs and 40 seeded random
sequences of 80 commands agree call for call, with the sources, the readout,
the panel, the stack and the controllers after every command. Each named run
must show what it is for, and each of those checks was seen to fail against
a run without its feature. Of 78 mutants, 72 are caught; the six that live
change nothing:

- running status kept after `0xF0`, whose messages do nothing whether the
  data after them is read in pairs or dropped;
- channel pressure taking one data byte or two, for the same reason;
- the early return on a message cut short at the end of the bytes, where the
  loop ends anyway;
- the draw count's ceiling of eight raised to nine, when at most eight notes
  sound to be drawn;
- `setPair`'s own call to work the layers out again, which the `applyNotes`
  after it makes first anyway;
- a count below two told apart before or after it is made whole, when below
  two only ever means one note sounding.

The plugin plays the host's MIDI through it, byte for byte as the page's
port does, and the shell test holds a dyad through the plugin - the second
key mid-block in another block, released by a note-on at velocity nought -
to a keyboard and generator told the same notes by name: equal to the last
bit, with the second key a sample late 0.011 out, and the picture's right
channel crossing three times to the left's two. In the standalone, with A3
and E4 held, the page reads 220 Hz and 330 Hz - "E4 +2", the just fifth.

**2b is ported.** `scope/matrix.h` is the page's modulation matrix: sources
and destinations by id, routings with their depth, `routingAllowed` (an event
reaches only what is struck, and never from the picture), the reach a picture
source may move a destination - stored within it, except for a source whose
reach depends on what is playing - and the one total the loop may push into a
destination; the fades, with each layer's envelope and its clamps, a routing
eased in and out, ghosts heard while they fade and then forgotten, and the
stepped sources through delay, attack, decay, sustain, release, loop and
restart; the routes compiled once per change and read and faded once a block,
the loop's routes into one slot combined and bounded; events fired once for
each new count and never for the count a routing found; and the picture's
destinations summed into an offset and held to their range. A routing's text
is the page's: `scope/text.h` has JavaScript's `toFixed`, which rounds an
exact tie away from nought where `printf` rounds it to even (0.0625 is
"0.063" in a browser), and its `Number`, which reads "1.2.3" as nothing where
`strtod` reads 1.2.

It is held to the page's own functions the same way (`matrix_js.mjs`,
`matrix_cpp`): the page's text lifted by name - the picture's loop out of
`applyModMatrix` itself - with stand-in sources whose values the run sets,
the page's own `GEN_DESTS`, and the run's clock for `performance.now()`. 19
named runs and 40 seeded random sequences of 120 commands agree on every
route, event and offset, with the stored depths and what is heard and fading
after each command; each named run shows what it is for, and each of those
checks was seen to fail on a run without it - one, that a preset's pair does
not dip, passed on a run with no preset in it, since all of nothing is true,
and requires its frames now. The generator's destinations are a table in the
port, and are held to `GEN_DESTS` id by id, slot by slot. Of 72 mutants (67
of the matrix, 5 of the number text), 66 are caught; the six that live change
nothing:

- the half of the event rule that refuses a level to something struck, which
  nothing else reads for such a pair;
- a fade's end taken as past one rather than at it, where `pow(1, x)` is one;
- layer B's depths worked out while fading is off, when every gain is one;
- a held value written for an LFO's route, which is never set;
- the decay's last instant, which lands on the sustain either way;
- a ghost's routes recompiled while fading only in, when no ghost is heard.

The port found one thing the page does that a reading of it would miss: its
fades are a `Map`, so two routings of the same pair share one entry, where
the first of them stood. The random sequences found it, on a pair routed
twice.

The plugin compiles its routes from it at the top of every block, from the
sources ported so far (`scope/sources.h`: the LFOs, the keyboard's six, and
Swing again, Kick and Pluck to strike), and the shell test holds a routed
dyad - an LFO on the pitch, the key's velocity on the level - to a matrix,
keyboard and generator driven directly: equal to the last bit, and 0.61 from
the same notes unrouted. The page opens with no routings, so the plugin sounds
as it did until a setup gives it some.

**2c has begun with the codes.** `scope/setup.h` is the page's setup as it
keeps it - one flat object, `DEFAULTS` key for key, and the code that carries
what differs from them: `encodeSetup`, `decodeSetup`, and the migrations from
versions one, two and three. A code is `btoa(JSON.stringify(diff))`, so
`scope/json.h` is JSON and base64 as V8 has them: UTF-16 strings, numbers
printed as `Number.prototype.toString` prints them (shortest digits, "1e+21",
"1e-7", minus nought as "0"), keys in V8's order (array indices first,
ascending), `JSON.stringify`'s escapes, and `btoa`, which refuses a character
past 0xFF as the browser throws, and the forgiving `atob`. The migrations read
an old code with JavaScript's coercions - a lane of "1" or [1] is lane one, a
full scale of "3" the fourth detent, a level given as text multiplied as a
number - and in strict mode, as the page is, so a code that reads as a bare
number or string throws where the page throws. A code that reads as `null` is
one the page cannot load.

It is held to the page's own functions in node (`setup_js.mjs`, `setup_cpp`):
the defaults, about 300 snapshots with every kind of number, string and
nesting encoded to the same characters, and about 500 codes - old versions
with fields of every type, codes cut, padded, spaced and corrupted, JSON's
corners - decoded to the same setup, or refused or thrown on as the page
refuses or throws. Of 61 mutants, 58 are caught; the three that live change
nothing: the second of `toString`'s placements at exactly 21 digits, which a
double never reaches; two arrays compared as equal, where `DEFAULTS` holds
none; and the text an object turns into as a trigger lane, which is never on a
detent whatever it says.

Three of the first fixtures could not see what they were for. The old codes'
levels are only migrated while their lane sits on a detent other than nought,
which random codes seldom did, so most of JavaScript's reading of a number was
never read; a code on the -40 dB detent has a gain of exactly a hundred, and
every reading shows there. Whitespace inside a code was only ever a space, the
tabs being at its ends where the trim takes them first. And the runners wrote
a character past ASCII as \u and four digits - which is how `JSON.stringify`
writes a lone surrogate, so a port that escaped half of a good pair printed
what the page printed. They write `{u+xxxx}` now.

**Then `restore`, and the presets.** `scope/restore.h` is what the page's
`restore` does to the instrument: both layers of the generator, the keyboard,
the LFOs, the routings (or the old two-oscillator enum, for a code from before
them), the key, the quantiser and the tempo, the crossings, the plane and the
echo - and the settings it keeps for pieces still to come: the score, the
arpeggiator, the threshold, the macros, the morph's ends, the photocell.
`restore` writes each value into one of the page's controls and fires the
control's handler, so the port is two things. `Controls` is the browser's
part: a slider takes a value as the browser does - a valid number or its
middle, clamped to its range, snapped to its step half-way up (all 92 step in
whole numbers) - and a menu given a value it has not got has nothing chosen and
reads "". The sliders and menus are a table written out from the page
(`scope/panel_controls.h`) and held to its DOM control for control.
`restoreSetup` is the handlers' part, in `restore`'s order, each with its law.
The library is `scope/presets.h`, every section and preset the page ships,
held to the page's `PRESETS` character for character, and the plugin now opens
as the page does, on "Harmonic tone", loaded through the core.

This is the one piece held in a browser, because the page's `restore` needs a
DOM: `restore_page.py` runs it in Chromium and writes out what it left behind,
and `restore_cpp` writes the same from the port. All 281 presets, and 500
random setups - every field in and out of range, of every type, junk - load to
the same instrument, field for field, each loaded on top of the last as the
page loads them. The checks that the runs reach every kind, both layers, the
old enum, the morph, the controllers and the tempo, and that a slider snaps a
half up and takes its middle for junk, were each seen to fail on data without
it. The shell test holds a preset loaded in the plugin - "Wah", a ramp through
a resonant filter an LFO sweeps - to the core told the same preset and notes
directly, equal to the last bit. Of 88 mutants of the port, 76 are caught.
Ten of the twelve that live change nothing: a slider's minus nought, which no
snap makes; a ninth digit past eight, clamped again downstream; layer B's
fallback for the morph, which names itself; the morph's and the width's own
clamps and vcfDec's lower bound, which their sliders apply anyway; a draw
count of nought against the floor of two; an input mode, an interval and a
macro's bar, which no menu or split can hand over. The other two are what
`restore` does to motion rather than to settings - the reswing it ends with,
and the notes it applies a second time - which a comparison of settings cannot
see, and which are the generator's and the keyboard's own, held by their own
parity.

The comparison found two things a reading would not. A clamp of a value that
may not be a number - where the photocell sits - must carry the NaN through as
`Math.min` does, where `std::fmin` drops it and answers the bound. And a draw
rule's count is not rounded by the page: a setup can give 2.35 and the page
keeps it, its `slice` then truncating, so the keyboard's count is a number now,
read as `slice` reads it; the keyboard's random sequences give fractional
counts too.

What the port of `restore` leaves to later pieces: a MIDI clock overriding
the tempo; and
three fields the page passes on raw - a mode it has not got, a `just` that is
not a boolean, an LFO shape it does not know - which the core takes by their
name or their truth while the page also keeps the raw value for its panel.
The view's half of a setup - the timebase, the trigger, the traces' scales and
offsets, the lag, the rotation, the picture's filter, the zoom - is written
into the panel's sliders as the page writes it, so the morph can walk them;
what the page then does with them is the page's.

**Then the macros and the morph.** A hand on a slider is `moveSlider`: the
value taken as the browser takes it, then `sliderInput`, which is every
slider's handler that reaches the sound or a setting a setup carries, each
with its law - and the morph walks sliders through the same handlers, so it
could not come before them. `morphStore` keeps an end and puts the fader at
it, so storing moves nothing; `morphStep` runs once a frame after the matrix
and, only when where the fader stands has moved by a ten-thousandth, walks
each slider that differs between the ends to its blend - frequency in ratio,
so half way from 220 to 880 is 440 - and fires its handler only if the
browser's value moved. The macros are sources (`BrainSources`, which also
registers the fader as the matrix's destination `morph.pos`), set by their
knobs. The plugin steps the morph after the matrix each block, and the shell
test holds LFO 1 sweeping the fader through the matrix to the core doing the
same written out, equal to the last bit, with the fader left at B as the
null.

Held in the browser like `restore`, as operations rather than setups: 1,642
of them - hands on every slider in and out of range and with junk, ends
stored, the fader moved by hand, pushed by the matrix for a frame and held
there across a store, the macros by their knobs and their sliders - on top of
presets and the defaults, and every one leaves the same instrument. The made
lines read: a quarter of the way puts amp a quarter of the way and tells the
generator, frequency walks in ratio and the keyboard's panel follows, a push
under the threshold moves nothing, a hand on a slider at rest stays, a synced
LFO's rate slider sets its free rate, a synced delay's slider goes on showing
the beat, storing A from half way puts the fader at A, and B stored under a
held push moves nothing until the push changes. Each was seen to fail against
a wrong value, and the count of walks leaves out the fader's own slider,
because with it in, a morph that walked nothing passed.

Two things the comparison found. The page's morph does not walk its sliders
in the order the page lays them out: `MORPH_IDS` is taken when the script
runs, before the Bench has moved its sections, and leaves out the sliders made
later (the traces' scales, the LFO's rate); an end is written in that order,
so a code's text depended on it. It is a table of its own now
(`kMorphIds`), held to the page. And the page's own frames ran between one
batch of the harness's lines and the next, stepping the morph there - where
the C++ runner has no frame, and where a batch happened to end. The page now
runs under Playwright's clock, paused, so its frames run only when told, and
both runners put one frame (the matrix's push, then the morph's step) before
every line. A bare install of the clock is not enough: time flows under it,
and the frames with it, until it is paused.

Of 66 mutants of the handlers, the macros and the morph, 58 are caught. The
first pass caught 53 and its survivors were runs missing, not equivalents:
nothing moved a synced LFO's rate or a synced delay's time, stored A away
from A, held a push across a store, or pushed between the step's threshold
and ten times it - which on sliders that snap to whole numbers only one two
thousand steps wide can show. Each is a made line now. Six of the eight that
live change nothing: a macro's own clamp and rounding, and the tempo's
rounding, which their sliders already apply; the plane's panel refreshed
after a plane slider, which already shows the value; and a handler fired
when the browser's value did not move, which sets what is already set. The
other two are layer B, below.

Not yet: the panel showing layer B. The page swaps the voice controls'
values when the editing layer changes (`showLayerOnPanel`), and its sliders
then write layer B; the port has `panelLayer` and the handlers honour it, but
nothing in the core yet moves it, so no run edits B and the two mutants that
send a slider to layer A whatever the panel shows both live. The morph's walk
allocates (a slider's value is the text the browser would hold) and runs on
the audio thread for now; its place is the message thread once the page is
the plugin's face.

**And the drawn cycles and the figures made of strokes,** which finish the
setup. `scope/cycles.h` is the four slots' points, their defaults, their text
in a code, and `cycleTables`, the resynthesis that turns 256 points into
eight band-limited tables; restore decodes the slots, builds the tables, and
hands the drawn cycle to both layers and the bank to the wavetable.
`scope/strokes.h` is the page's single-stroke font, its SVG path reader, the
compiler that turns strokes into what the figure reads, and a drawing's text;
restore sets the word, the path and the drawing, and sends the figure the one
it shows. A word is upper-cased first, and JavaScript's upper case is
Unicode's - "ß" draws as two letters and a Greek letter with its accents as
three spaces - so the 104 characters whose upper case is not one non-ASCII
character are a table, written out from V8. Tables are built again only for a
slot whose points have changed, which gives the same tables and saves some
25 ms a slot.

Held to the page as part of `restore`: all 281 presets and the random
setups, now with cycles of 256 bytes and of the wrong length, with white
space `atob` forgives and characters it does not; words that upper-case into
more letters, past twenty-four units, with line breaks a text input drops;
SVG paths of every command, numbers run together, arcs' flags, junk; and
drawings with junk in their pairs. Each line carries every slot's points, the
tables the generator holds (by two sums a table and two of its values), the
cycles' codes written back, the three compiled paths in full and the one the
figure was sent, and the panel's note on a path it could not read. The made
lines read: a default slot written out a byte at a time is written back as
no cycle; "straße" draws as STRASSE; a path refused leaves the last one
drawing; and a path past six thousand points is too detailed. A preset with
one character of its cycle changed, one letter of its word, one number of
its path or one point of its drawing is each a null. The shell test plays "A
drawn cycle" through the plugin, equal to the core to the last bit, where
before this the core had no tables and played a sine.

Of 88 mutants of the cycles, the strokes and their part of restore, 81 are
caught. The first pass left fifteen, and eight of them were fixtures that
could not show the effect: the Greek letters that upper-case into three were
in a word of nothing the font draws, which compiles to no path at all, so
how many characters it made could not matter - every one of the 104 is now a
made line between two letters; and nothing had a `+` on a number, a drawing
whose points all coincide, a drawing past three thousand points, a path of
only spaces, or a slot within a step of its default but not half a step.
The seven that live change nothing: a placeholder for a character the font
never draws, which the font does not draw either way; a guard against a
glyph's part of one point, which no glyph has; a vertical line's offset
written two ways that are one; two guards against a path whose box is not a
number, and one against a path of one point, which all end in no path
either way; and a trim before a split that drops what the trim would have.

Two things found on the way, one in each direction. The core's tables were
`float`, on the word of a comment that the page's were Float32Arrays; they
are plain arrays, and the generator's parity fed both sides float tables of
multiples of a sixty-fourth, exact in either, so nothing could show it.
They are doubles now. And reading the page's path reader to port it showed
that a number after a Z hung the page: Z takes no numbers, so the cursor
stayed where it was and read the same number as another Z, for ever. A
pasted path or a shared setup code could freeze the tab, and no check had a
path that was not well formed. The page refuses it now, with a check that
runs the reader in a worker under a time limit (web/README.md has it).

What the setup still leaves: a snapshot of the core's state as a setup (the
page's `snapshot`, the other direction from `restore`), which waits for the
page to be the plugin's face (stage 3) - the host's saved state did not need
it after all (2g); and grabbing a cycle from what is playing, which listens,
and can now be built on the hearing (2f).

What the port leaves to later pieces: the arpeggiator (2d, since ported),
where the page asks `arpActive()`; the panel's sliders the keyboard reads and moves, which
are `Panel` until the setup is the core's (2c); and a chord handed to the
generator, which the generator copies and so can allocate on a note, once a
layer, until the brain's state is fixed in size.

**2d has begun with the clock.** `scope/clock.h` is the page's `transport`:
the tempo in force (the slider's, a tap's, or a MIDI clock's, the mean of the
last two dozen gaps), the bar worked out from the time it is asked about
rather than stepped - re-based when the tempo changes, so it never jumps, and
under a MIDI clock a twenty-fourth a tick, guessing ahead between ticks but
never past the next - Start, Stop and Continue, a MIDI Start that holds the
bar a tick short so the first tick is the one, and the step once a frame that
lets a quiet clock go and sets every locked oscillator's rate. The Brain holds
it where it held a bare tempo, restore sets the tempo and steps it as the page
does, and a delay in note values is sent again when the tempo moves it.

Held to the page by its own harness (`clock_js.mjs` against `clock_cpp`): 13
named runs and 60 random ones, 7,650 lines, every field of the clock and both
oscillators each line. The made runs read: a tempo changed mid-bar leaves the
bar where it was; a MIDI clock at 120 reads 120 and moves the bar a
twenty-fourth a tick, never guessing past the next; a quiet clock is let go
after half a second and the slider's tempo comes back; a Start with no clock
after it does not hold the bar short for ever; taps, stopped and running; the
locked oscillators following the tempo and the clock and restarting on Start;
the delay sent only when it moves. Four nulls. Of 44 mutants, 42 are caught:
the two left are the tap's rounding before a `setTempo` that rounds anyway,
and a guard on an empty list of ticks no state reaches while the clock is a
MIDI clock's. The first pass left two more that were runs missing - time never
went backwards, though a MIDI tick is stamped when it arrived and can come a
little before the frame that reads it; and the harness could not tell a delay
sent again unchanged from one not sent - and the fuzz steps back now and then,
and `clockFrame` says whether it sent.

In the plugin, the clock steps first in every block, as in the page's frame.
A host's transport, which the page has not got, is the clock's while the host
gives one: its tempo in force with the slider's kept, its play and stop as
Start and Stop, its position as the bar; a host gone quiet gives the tempo
back to the slider, as a stopped MIDI clock does. MIDI's real-time bytes
reach the clock through the keyboard at the time of their own sample. The
shell test plays "Wobble" (LFO 1 locked to a quaver) under a stand-in host at
90 and finds the oscillator at three cycles a second against four with no
host, the bar at the host's position, stopped where the host stopped, and the
slider's tempo back once it goes; and a MIDI clock at 150 sent as bytes reads
150, where stamping the ticks at the block's top read 152.

**Then the arpeggiator,** inside the keyboard, where the page has it: the
hands' stack stays the hands' (the sources and the pedal go on reading it)
and the generator is shown the arpeggio's note instead, swapped in for as
long as it takes to apply - nothing, then the step, so every note is struck.
The patterns, the dyad's pairing of the lowest held note with the arpeggio's,
the steps counted on the clock from the first key so they cannot drift, the
rate at the clock's tempo, and the MIDI out each step's note goes to. The
page strikes the first step on a timer, 25 ms after the first key so a chord
spread over a few milliseconds is gathered before it starts; the core has no
timers, so the keyboard keeps its wakes and its owner fires each at its time.
The page's random walk asks `Math.random`; the core's draws from its own
seeded generator, and the parity seeds the page's alike.

Held to the page through the keyboard's own harness, which now lifts the
arpeggiator too, with a stand-in timer, tempo and out: nine named runs and
forty random ones on the clock, among the keyboard's 14,500 lines. The made
runs read: a chord struck over 12 ms starts on its lowest note 25 ms after
the first key, not on the key that came first; each step after falls on the
first frame after its quaver; the dyad pairs and the other modes do not; each
step is struck; down, up-and-down and played; the step at the tempo in force;
switched off with keys down the generator gets the whole chord at once;
letting go stops it; not driving the generator, it does not step; a random
walk stays among what is held. Three nulls. Of 38 mutants, 34 are caught; the
four left are a check of the gather the step count already makes, two
orderings of timers that do nothing when they fire, a guard on a loop that
cannot run, and an index already reset. The first pass's one other survivor
was a run missing: keys let go while the generator's kind takes no notes, so
nothing tells the arpeggiator, and the kind changed back - the next frame
finds it running with nothing held, and must stop it.

In the plugin the arpeggiator steps once a block after the keyboard's frame,
at the clock's tempo; a key is stamped with its own sample's time; and the
first step, the page's timer, is struck at the sample its time falls on. The
shell test holds a chord in "Intervals in turn" and hears the first sound 25
ms after the first key to the sample - 1,300 where the next block's top
would have been 1,536.

**And the score, with the MIDI out.** `scope/score.h` is the page's score -
the phosphor grid read as a graphical score, the playhead crossing its 64
columns on the clock's bar, a step a semiquaver, quaver or crotchet, and the
brightest few pitches of the key in a column struck in the generator's score
voice - and the out it shares with the arpeggiator, the crossings and the
pluck: one port and one channel, forty note-ons a second at most and every
note-off sent whatever the count, a note already sounding ended before it is
struck again, a new port or channel letting go on the old one first, and the
panic. The crossings' notes, ended a tenth of a second on, and the pluck's,
150 ms on, came with it, since they are the out's other callers. The score's
brightness is kept in single precision, as the page's `Float32Array` keeps
it, or a tie between two bands breaks the other way; and its step is the
bar's over the step's beats plus a billionth, because six twenty-fourths of a
MIDI clock come to 0.24999999999999997 and the step due on that tick would
otherwise be a tick late.

Held to the page by its own harness (`score_js.mjs` against `score_cpp`, the
latter on a Brain linked as `linkClock` links it): 10 named runs and 50
random ones, 7,400 lines - the strikes and every byte sent each command,
then the playhead, the chord, what is sounding, the rate limit's count and
the note-offs due. The made runs read: one lit cell a column - the bottom row
the key's lowest pitch, the top its highest, a dim cell no note and one at the
floor a note; the brightest few over the floor loudest first; a step every
semiquaver, and a frame two steps late playing only the newest, not a flam;
Stop letting go, Start back to the first column, the scope stopped playing
nothing; a tie going to the lower pitches; the bar's one leaving the chord
sounding until the next step; after a MIDI Start nothing until the next tick,
and the seventh tick the second step despite its rounding; note-offs due on a
frame's own millisecond going on it; the rate limit; a note struck twice and a
channel changed; the crossings, counts going up and down. Four nulls. Of 48
mutants of the score, 43 are caught; four of those left are guards that cannot
change what is picked (an empty key, a dark cell, a band under the floor, the
brightness array's initial value), and the fifth - a bar below nought - cannot
happen on the page, where the bar is never less than a tick short of nought,
and is held by the shell test, where a host's count-in makes one. Five more
mutants of `linkClock`'s hooks are all caught. What restore does when a setup
turns the score off - let it go there and then - is what the score's next
frame would do anyway, a frame later, and nothing in the harnesses can tell
the two apart.

In the plugin the out writes into the host's MIDI buffer at the sample of
whatever sent the note: an arpeggio's first step at its own sample, a step
after it at the block's top as the page steps it in its frame, a note-off from
letting go at the release's sample, and the crossings, the score and the
pluck's note-offs at the block's top, once a block as the page's once a frame.
The grid is still the page's, so the score's playhead runs on the bar and
plays nothing until stage 4. The pluck is struck at the setup's pluck note,
where the core's own stand-in strikes middle C and sends nothing. The shell
test reads what comes back from the host's buffer: the arpeggio's steps at
1,300 and then every 12,000 samples to the block's top, each ending the last;
"Three against two" sending both lines' notes together at velocity 102 and
ending each 100 ms on, and the boot preset sending nothing; a routing firing
the pluck at C5 in "Pendulums ring a bell"; and "A sine, sung" under a host
two beats into its count-in, the playhead waiting until the one and then
following the bar. Eleven mutants of the plugin's wiring, every one caught.

**2e: the rest of the sources.** The learned controllers (`cc.N`, each
registered the frame after the keyboard learns it), the note envelope
(`env.note`), the drawings' six (Swing, Pendulum, Tilt, Turn, Roll, Facing),
the level (`env.live`, `scope/level.h`) and the threshold (`threshold`, the
Brain's, a value source made into an event by rising through a level, with
0.05 of hysteresis and 80 ms between firings). Whether a source is the
picture's is now asked of it rather than read from a field, because the
page's answer is a getter for the threshold - and will be for the hearing,
which is a loop only while it hears the generator.

The port found two bugs in the page, fixed there first (web/README.md): a
routing from a controller that had not moved yet was skipped and never
compiled again once it had, so a preset's mod wheel was never heard; and a
setup code with the threshold watching itself overflowed the stack, a bug the
core had copied and its random runs found.

Held to the page three ways. The level and the threshold by their own
harness (`signal_js.mjs` against `signal_cpp`): 9 named runs and 60 random
ones, 9,200 lines, the follower and the threshold's whole state each command,
with runs at each edge - the stride's, the cap at full scale, the level itself,
80 ms exactly, the hysteresis's 0.24999999999999997, a watched source
forgotten and brought back, and the threshold's part of restore run on both
sides. The envelope and the drawings by the generator's harness, which now
reads the page's own registrations of them over its generator against the
core's sources, with runs that can show each: a solid's three turns apart, a
key held at the end, an ungated run where the generator says one and the
source must say nought. Four nulls. Mutation: 10 of 11 of the level (the one
left chooses attack or release when the two are equal, where the step is
nought either way), 18 of 18 of the threshold, 7 of 7 of the sources. The
harness's first mutation pass caught everything, because both comparisons -
the parity's and the mutation runner's - took minus infinity against itself
for a difference, their difference being NaN; both now take identical text as
the same before doing any arithmetic.

In the plugin the level reads the last 2048 frames of the picture's left
channel at the top of each block - the page reads its screen's fetch, which
follows the timebase - and the threshold steps before the events fire, in the
page's frame's order, which the crossings and the score now keep too. The
shell test hears "Wheel wah"'s wheel from its first move and not a sample
before; "Envelope sync sweep" as the core plays it, and unlike it without its
routing; and "Pendulums ring a bell" plucking C5 at the top of the block its
level reaches 0.40 - the pendulums swing from the start, so that is a few
blocks in - with the level equal to a scope::Level's own over the picture the
page would be handed, exactly. Eight mutants of the wiring, all caught; the
two that read the wrong channel or the oldest of the ring were caught only
once that last check was added.

**2f: the hearing.** `scope/hearing.h` is the page's `hearingStep`: a window
of 4096 samples through a Hann window and an FFT, the four bands by
Parseval, the flux and the onset it fires, the brightness from the centroid,
the pitch from a held key or else YIN's period estimator past its confidence
gate on a steady window, and the width from the X-Y pair's correlation; and
the nine sources, which are the picture's - a loop, with its reach - while
what is heard is the generator. Its owner says whether it is, whenever that
changes, because the page's answer is a getter asked live, stopped or not;
only the recompile it asks for waits for a step, as the page's does. A window
whose length is not a power of two is not heard at all: the page's never are,
and its FFT would read past its arrays on one.

Held to the page by its own harness (`hearing_js.mjs` against `hearing_cpp`):
10 named runs and 100 random ones, 7,100 lines, every value the hearing
keeps each command, sounds made of sines and noise in a window that slides
with the frames' elapsed time. The made runs read: a full-scale sine in each
band reads near one there; 220 Hz named with nothing held, the pitch slewing
there at four a second; a held key outranking it, a chord's lowest note the
key; silence holding the pitch, brightness and width while the bands and flux
let go; the width for channels alike, inverted, in quadrature, the same lane
twice and one lane; an onset out of silence once, none for a note stopping,
none within 80 ms and one at exactly 80; the loop flag and reach following
the generator, and the routes touched as it flips; the lane the trigger
watches; windows too short, the shortest and the longest; and the
estimator's corners - no room to double, a period at the end of its range,
no dip under the threshold, an offset with a trace on it, the decimated pass
over 32,768 samples, and a window not steady. Four nulls.

The parity found one bug of mine: the page's doubling search moves its own
upper bound as it finds deeper dips, the bound being re-read each time round
the loop, and I had fixed it at the start. It showed only on a noisy tone at
a window of 1024, as 160 Hz against 155. Of 58 mutants, 49 are caught; the
nine left are each equivalent where the core uses them, and say why: a
conjugated FFT has the same magnitudes; the estimator's shortest period is
clamped to the pitch's top either way; two guards cannot be reached at the
window sizes heard; the parabola is only ever taken through a point no higher
than its neighbours, so its clamp never acts; an aperiodicity only gates;
the rise can never exceed the total; the decimated pass at exactly 16384 is
the same pass; and an energy scaled by a ten-thousandth is the same gate.

In the plugin the hearing reads the last 4096 frames of the picture each
block, left as the trigger's lane and the pair for the width, its held key
the lowest the hands hold. The shell test holds every value to a
scope::HearingSources of its own over the picture the page would be handed,
exactly, and hears "Brightness swirls it" against the same without its
routing; and "Hits restart the pendulums" plays as without its routing though
the onset fires, because an event that hears the generator it would strike is
refused. ("Brightness adds points" was the first choice and showed nothing,
rightly: a star's points are whole, and the brightness its reach allows adds
less than half of one.) Seven mutants of the wiring, all caught. Its period
estimator allocates as it goes, which is not yet fit for an audio thread and
moves with the morph's walk.

**2g: the host's parameters, and the state.** Eight parameters, a curated
few rather than every control: the four macros, the morph's fader, and the
level, the cutoff and the echo, each one of the panel's sliders by id and in
its units, so a parameter moved by the host is a hand on that slider - its
value written as the browser would hold it, its handler run - and a
parameter applies when the host moves it and not again, so a slider moved
since by something else stays where it was put. Loading a setup reads them
back from the panel, so the host shows what the preset set.

The state is a setup code, the thing the page shares, and not a snapshot of
everything. The page's `snapshot` reads the view's half of a setup - the
display, the trigger, the channels, the filter, the panes - from controls the
core does not keep, so it cannot be ported whole until the page is the
plugin's face (stage 3); and until then what can change the plugin's state is
narrow: the setup it was loaded with, the host's parameters, and the
controllers it has learned. So the state is the setup as loaded, and over it
each parameter's slider as the page's snapshot writes it and the learned
controllers' names; a state handed back is restored as a preset is, before
the first block if it comes before `prepareToPlay` and at the top of the next
block if it comes while it plays - that block, and any the message thread
holds the lock for, being silence rather than a wait. What it loses, and
says so here: anything moved by a hand that is not a parameter, of which
there is none until stage 3.

The shell test: eight parameters named and read back from "Stretched
echoes"; Macro 1 and the cutoff automated in "Brighten, grit, space, swirl"
heard from the block they are moved in and not a sample before; a state
round trip, with Macro 2 and the echo moved and the wheel learned, into a
fresh plugin that then plays the same notes sample for sample, with the same
parameters and the wheel learned, where the same plugin without it does not;
a state handed over mid-play loaded at the next block; and a slider moved
after its parameter staying put. Eight mutants of the wiring, all caught,
two only once the last two checks were added - a state left for the first
block instead of loaded by `prepareToPlay`, and parameters applied again
every block, which nothing heard until something else moved their sliders.

**3. The page as a view.** One adapter in the page: the worklet and the
WebAssembly core in a browser, JUCE's bridge in the plugin. The web suite goes
on testing the page against the browser build.

**3 has begun with the channel.** Three native functions: `scopeSlider` (a
slider moved on the page, by id and value), `scopeSetup` (a setup loaded on
the page, a preset or a code, as a code) and `scopeState` (the plugin's state
for the page). The first two wait in a queue for the top of the next block
and are done there as the morph's walk is: a slider is `moveSlider`, the
page's handler ported, and the host's parameter for it follows; a setup is
loaded as a preset is. The plugin's state is the setup code it would save -
the setup loaded, the sliders moved since as `pluginSliders` ("id=value;..."),
the controllers learned - published by the audio thread whenever it changes,
with a count of the changes that came from the host (a load, a parameter
moved) rather than the page. The page asks for it four times a second and
applies it only when that count moves, so it never hands its own drag back
to itself, and applying it sends nothing. The saved state is the same code,
so a slider moved on the page survives a project saved and reopened, and the
host parameters' sliders ride in it rather than beside it.

What it did not do, and why: a menu, a switch or a routing changed on the
page did not reach the plugin. Sending the whole setup on every change was
the simple design and was measured first - restoring even the setup already
playing moves the sound at that sample by 0.2 to 1.2, on five presets of
seven, where one control turned does not - so each of those controls waited
for its handler in the core, as the sliders' was ported, with parity. That
is 3b.

The shell test: a slider moved on the page is, sample for sample, the same
move made directly, at the next block's top and not before, with its
parameter following; the state the page is shown carries it without counting
it as the host's, while a parameter the host moves is counted; a preset's
code loaded from the page is loaded as the plugin loads a preset, and a bad
code refused. hosttest.py, against the fake bridge's log: the page shows the
plugin's state on load, the slider moved since included, and sends nothing
back, not even the preset it opened on before it knew it was hosted; a slider
moved is sent once; a newer state is applied, one no newer is not, and
applying it sends nothing; a preset loaded is sent whole and reads back as
that preset. Nine mutants of the page's side, eight caught; the ninth drops
the first pull on connecting, which the next pull, a quarter of a second
later, makes up for - the ordering it exists for (the state shown before
anything is sent) is real but too brief for a check to see.

**3b: the menus, the switches, the buttons and the routings.** The page's
"change" handler for every menu, switch and text box that reaches the sound
or what a setup carries - fifty-seven of them, from the kind and the shape
to the keyboard's switches, the arpeggiator, the score, the LFOs' menus, the
threshold's and the macros' names - is `scope::controlChange`, its buttons
(the tuning, the keyboard's mode, the plane's oversampling) are
`controlClick`, and an edit to the routings is `Matrix::setRoutings`: the
list as the edit left it, a routing kept being the same routing, its serial
kept, so an event on it fires on the next count where a preset's would not.
The page sends them from two capture-phase listeners and after any edit to
the routings, each depth to its last digit; the plugin queues them like a
slider and keeps each that did something in `pluginHands`, the saved state's
list of every hand since the setup was loaded, in order, which replaced
3a's `pluginSliders` (a state saved with that still loads). A hand on a
control already in the list replaces the earlier one at the end, unless a
hand between them reads it or is read by it - the keyboard's drive is for
the kind chosen at the time, an LFO's rate moved while it is synced is its
free rate - since the earlier one would then be put back in a different
place.

Not sent, each for a reason given where `HOST_CONTROLS` is: the view's
menus; the fade's, which the page keeps in its own storage and not in a
setup; layer B's editing, which swaps the panel between the layers where
the core's panel always writes A; the MIDI out's port, the host's in the
plugin; and LFO 2's rate, a slider made when LFO 2 is chosen and so not one
the core's panel table has. A depth dragged reaches the plugin when the drag
ends, as the page only counts it an edit then.

Parity, in a new section of `parity.py`: 1,300-odd hands through the page's
own handlers and the core's - presets, sliders, every menu with values it has
and some it has not, switches, text, buttons - each leaving the same
instrument, field by field; the readable ones (a path drawn under the Path
figure is what the figure sends, an echo synced to a quarter at 120 is
500 ms, C major quantised is the mask 2741, an LFO locked to a quarter runs
at 2 Hz from a phase of nought); every one of the sixty-five controls seen to
move something; and nulls. The dump grew what the new handlers write that it
did not read: the arpeggiator the keyboard plays as well as its menus, the
LFOs' phase and epoch, the threshold's arming, and the keyboard's copy of
the interval. The matrix's runs gained `edit` and a run that shows the
serial kept. The shell test: a menu, a switch and a button sent are their
handlers at the next block's top, what the plugin does not know is not
kept, and a fresh plugin given the state plays the same sample for sample;
a control moved twice is kept once while the drive keeps its place between
two kinds; the routings keep every digit; an old state's sliders load.
hosttest.py: each kind is sent once, the view's menu and an unported button
not at all, the routings whole and only when changed, and a state's hands
put back in order with nothing sent back.

**4. The picture's sources in the core,** so the loops go on with the window
closed.

**5. The site on WebAssembly.** The worklet runs the compiled core, and the
JavaScript engine and brain are retired once parity says there is nothing left
they do that the core does not.

**6. Release.** macOS AU and VST3, signed and notarised; Windows VST3 with
WebView2 linked statically; state saved into the host's project; recording
redone natively or left out.

## Found on the way

- **The fade held a copy where the page holds the routing.** A routing
  fading out is the page's routing object itself, so a depth changed and the
  routing taken off before the next frame fades out at the new depth. The
  core's fade copied the routing once a frame and faded the stale one. The
  matrix's random runs had `amount` and `unroute` from the start
  and never put them on one pair without a frame between; the edits' runs,
  which replace the whole list, did it at once. The copy is now brought up to
  date by serial whenever the routings change, and a named run shows it.
- **The arpeggiator's mode read two menus a restore leaves stale.** The
  page's `arpSet` reads the rate and octaves menus; the core's panel has
  copies of them that `restoreSetup` does not write, keeping the values in
  the brain instead, so the ported handler read the menus as they were
  before the preset. It reads the brain's now. Found by the first run of the
  menus' parity, at the 173rd hand.

- **JUCE 8.0.9's Linux web view could not serve the page.** It runs WebKit in
  a child process and passes each resource over a pipe, reading without
  blocking; a message bigger than the pipe's buffer arrived in pieces, the
  reader dropped the first piece at the first gap, and read the next as a
  length - `std::bad_alloc` a few seconds after the window opened. JUCE fixed
  the reader later; the plugin is pinned to 8.0.15. (Tags sorted as text put
  8.0.9 last, which is how the old one was chosen.)
- **WebKitGTK read the page as Latin-1** through JUCE's custom scheme whatever
  the page's meta or the Content-Type said. The markup was unharmed, being
  ASCII with entities; the script's forty-odd other characters were not. The
  plugin serves the page as pure ASCII (`asciiPage`): escapes in the script,
  entities in the markup. The site's file is unchanged.
- **The envelope ported bit for bit.** The same scenarios through
  `makeEnvelope` and `scope::Envelope` differ by exactly nought, not merely by
  less than the 1e-12 allowed. One of the mutants tried on it cannot be caught
  by any scenario: the one-sample floor on a stage's time, because a stage's
  pole is built to land on its end in exactly that many steps, so any shorter
  time overshoots and is clamped to the same value. The scenario says so.

- **The fake bridge's first fixture could not show a pile-up.** It answered
  each fetch in 8 ms, faster than a frame, so fetches never overlapped whether
  the page waited for one before the next or not, and a page that did not
  wait passed. It answers in 40 ms now, longer than two frames, and a page
  that does not wait has four in flight.
- **Two of the waveform calls could not see the mistakes they were for.** A
  null for the pulse's width took the first pulse call it found, which was at
  the top of a cycle - where a pulse narrower than a half is 0.9 whatever its
  width - and could not tell 0.3 from 0.31; it takes one from the low part of
  the cycle now. And the drawbars were only ever called with steps that put
  every partial wholly under or wholly over Nyquist, so their fade band could
  have been twice as wide; they have steps that put each partial in it. One
  mutant is equivalent and cannot be caught: the blep's window taken as
  `t <= dt`, since the blep is nought at its edge either way.
- **Three more fixtures that could not see their mistake,** each found by a
  mutant that survived: every unison count in the oscillator's sweep was a
  whole number, so rounding half a copy down passed (a run with 2.5 copies
  catches it); the stepped noise steps when its phase goes back, which only
  a phase standing still can tell from "on or back" (a run at 0 Hz); and the
  pulse and drawbars ones above.
- **The voice's chain had two more,** caught the same way: no filter run
  moved the tone's filter settings while the envelope held still, so a cache
  that ignored the envelope amount or the tracking passed (each run now moves
  one setting part-way, alone); and no fold fell between a quarter and a
  half turn, the one range where the fold's normalising limit shows.
- **The whole core found two things the pieces could not.** Its first run
  through every mode found the morph's default at nought where the page
  starts it at one and a half - `VoiceTone` was written for the oscillator's
  tests, and its defaults were the tests'. And the plane's `step` threw away
  what the echo and chorus returned; the plane's own runs found that one,
  but only at two and four times, since no run at one had the echo on.
- **The whole core's first runs could not see a third of their mutants.** 36
  of 123 lived at first. Ten were mutants that did not compile and had
  counted as caught in an earlier pass's tally, which is why the tally now
  requires a failing comparison by name. The rest were runs that could not
  show the effect: releases too long to finish inside a run, so idle tails
  were never swept; a filter on a unison dyad, so its right channel's pitch
  was its left's; bars out of range on bars nothing pushed back; the
  governor's costs read after the unison that used them had been taken
  away; tails never cut because nothing was over the budget at one copy; a
  clock input that always went negative, so its hysteresis was never in
  play; a crossing line no beam ever hovered under. Each has a run now.
- **The outputs are float and the loop reads them back.** The crossings and
  the heard pair read the picture from the output array, so they see it
  rounded to float as the page does. A port that kept the double would
  differ in the last place of a float, and on a crossing line that is a
  note on one side and none on the other.
- **A runner edited while a pass compiles it is a pass that counts nothing.**
  The restore pass compiled its runner from the tree, and an include added to
  the runner mid-pass left thirteen mutants failing to build against the
  pass's copied headers. The pass copies its runner as well as its headers
  now.
- **A mutation pass in the working tree is a build of the mutant.** The
  keyboard's first pass rewrote `keyboard.h` in place while the plugin was
  being built beside it, and the plugin's shell test failed - the note-off
  never closed the gate - on a mutant compiled in, not on the port; a backup
  of the header taken then to add a print held a mutant too. Mutants are
  made in a copy of `core/include` now, compiled from there, and the working
  tree is never touched while a pass runs.
- **A page's own frames run between a harness's calls.** The browser runner
  evaluated its lines fifty at a time, and between two batches the page's
  animation frame ran as it would for anyone - stepping the morph, and with
  it any slider the last line had left between its ends. The C++ runner had
  no frame there, so whether a run agreed depended on where a batch ended.
  The page runs under Playwright's clock now, paused (a bare install leaves
  time flowing, and the frames with it), and a frame happens where both
  runners say.
- **The null device spins.** ALSA's `null` output accepts everything at once,
  so the standalone's audio thread runs the processor as fast as it can and
  takes a core. Fine for checking the picture end to end; not a measure of
  anything the processor costs.

## Building and testing

```
python3 core/tests/parity.py                 # the core against the page
cmake -S plugin -B plugin/build -G Ninja [-DSCOPE_JUCE_DIR=/path/to/JUCE]
cmake --build plugin/build
plugin/build/ScopeShellTest_artefacts/Release/ScopeShellTest
python3 web/tests/run.py host                # the page's side, against a fake bridge
```

To see it: run the standalone (`plugin/build/ScopeInstrument_artefacts/
Release/Standalone/Scope`). Two switches for the spike, read once at start:
`SCOPE_HOLD_NOTE=57` holds A3 through the keyboard so there is something to
draw without one (`57,64` holds a fifth), `SCOPE_PRESET=Wah` opens on a preset
by name, and `SCOPE_REPORT=1` prints the page's reports. With no sound card,
an `~/.asoundrc` of `pcm.!default { type null }` gives the processor a device
to run on.

On Linux the web view needs WebKitGTK 4.1 and GTK 3, and the standalone ALSA:
`libwebkit2gtk-4.1-dev libgtk-3-dev libasound2-dev`, with the X11 and
freetype headers JUCE asks for.
