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

Mutation: 64 mutants of the handlers, 59 caught. Three are equivalent for
every value a menu can send - a law applied to a menu whose law is the
value itself, the draw count's floor of two under a menu that starts at two,
and an LFO's free rate kept on locking when the free rate is its rate
whenever it is free - and two are out of this harness's sight: the score's
notes stopped when its switch goes off, as no score note plays here, and
the threshold disarmed by its menu, as nothing arms it without frames. Six
lived at first and were caught once the dump read what the handlers write
(the keyboard's interval, the LFO's shape as it plays, its phase from a
radian rather than from nought, which a reset to nought could not show) or
the readable runs had a case for them (a key changed with the quantiser on,
a number of voices the menu has not got). The matrix's edits, four of four;
the plugin's hands, nineteen of nineteen, three only after the shell test
learnt to load a preset after the hands, to press both of a set of
buttons, and to hear a button put back; the page's side, nineteen of
nineteen, one only after hosttest.py touched the routings it had just put
back.

**3c: layer B on the panel, LFO 2's rate, and the fade.** Three things 3b
left out, each because the core had no place for it.

Layer B. With the layers on, the page's A and B buttons choose which layer
the voice controls show and write (`showLayerOnPanel`): B shown keeps what
A's controls said and writes B's tone into them, each through its law
back. The core's panel had a layer field that nothing set, so a slider moved
with B shown on the page moved A in the plugin. The keyboard now keeps which
layer is being edited and says so whenever it works the layers out again,
as the page's `syncLayers` does; the brain shows that layer on its panel
(`scope::showLayerOnPanel`, `syncLayerPanel`), the laws back are in
`LAYER_CONTROLS` beside the laws, and the buttons are sent and kept. Its
parity is a section of its own, with a keyboard there - the layers are
only on with one, and the harness's page had none, so 3b's runs could
never have seen this.

LFO 2's rate. Its slider is made when LFO 2 is chosen, so it was not one of
the sliders the page opened with, and the core's panel table, held to the
page's, had no place for it. It is LFO 1's slider again (`rangeSpec`), as
on the page.

The fade. The page keeps it in its own storage, not in a setup, so it was
never going to arrive with a preset. It is sent whole when it is saved
(`hostFade`), kept as a hand, and put back on the page from the plugin's
state - the fade's defaults where the plugin has been told none, since a
project reopened is the plugin's, whatever the page's storage remembers.
`scope::fadeFromPage` reads it as the page's `fadeFromHost` does, a code's
oddities and the fade's old names included.

Mutation: the core's new pieces, 20 of 26 caught. Four are equivalent - a
law back rounded where the slider rounds to its step anyway (the level, the
cutoff, the drawbars), and the flag for A's kept controls, which cannot
differ when it is read - and two are the core holding the panel on A while
a setup is restored, which its restore never needs, as nothing in it asks
the keyboard to work the layers out again before the voice controls are
written; it is kept because the page needs it and the two should not
differ. The plugin's wiring, six of six; the page's, eight of ten by
hosttest.py and two more by parity (the page's hold on A, which is the bug
fix, and the fade's mode checked), with one equivalent left - the fade's
memory set on connecting, which the first state applied has already set.

**4. The picture's sources in the core,** so the loops go on with the window
closed.

**4a: the arithmetic** (`scope/picture.h`). The phosphor grid the photocell
reads - 64 by 64 floats over the graticule, each cell keeping the brighter
of what it held and what is laid on, faded with the canvas - and its
five-point bilinear read; the beam's running moments, for roundness; the
picture meter, with its coverage, change, novelty and verdict; the drawn
pair's direction and edge contact; the photocell's slewed reading; and
`pictureStep`, with boredom's rise and leak and the slew on every value.
The page's grids are Float32Arrays, so these are floats written the same
way, and its `Math.hypot` is V8's (`jsHypot`, from the solids): roundness is
a difference of two nearly equal numbers for a figure that is nearly a
line, and `std::hypot`'s last place made one 2 per cent apart.

What it is not yet is anything the plugin runs. What the grid is given is
the renderer's own segment walk - the X-Y figure, each Y-T polyline, the
peak bars - in canvas pixels, through the view's settings (the display, the
timebase and trigger, the zoom, the channels' scales and offsets, the turn,
persistence). That is the next piece, and the larger one; this one is held
to the page with segments both are handed.

Parity (`picture_js.mjs`, `picture_cpp`): named runs for each piece - a
segment and the reads across a cell's edge, a fade through every
persistence, the beam's steps, roundness of a circle, a two-to-one ellipse
at two turns, a line and a figure shrinking to nothing, the photocell's
slew, each verdict reached (settled, cycling, wandering, and running away
by ink and by the limiter), the drawn pair each way round and to the edge,
a figure under the moments' floor, twenty seconds for the meter's memory to
forget, and frames far enough apart that the window's median lies between
two kinds - and 30 random runs of 200 commands. Mutation: 41 of 42 caught;
the one left clears the photocell's reading when it is turned off, which
the next frame clears anyway before anything reads it. Six lived until the
runs could show them: the moments' floor, a cell over full ink, the
memory's fifteen seconds, the verdict's wait for history, the median of an
even window, and boredom let go when the photocell is.

**4b: the capture** (`scope/capture.h`). One frame of what the screen
draws, from the source's latest samples: the window and the trigger's
search span behind it, giving way in the page's order when the buffer is
short; the AC coupling and the trace's filter over the whole fetch, primed;
the lag lane, interpolated; mid and side; the turn, before the trigger; and
the edge found with its hysteresis and holdoff, the window cut there. The
view's settings are a struct (`View`) where the page reads `state`, and the
automatic lag's lock is handed in. The trace filter's law for the cutoff is
the voice's, so `cutoffHz` moved here from restore.

Parity (`capture_js.mjs`, `capture_cpp`): every timebase at three rates, the
edge at three places and pushed past both ends; the trigger rising and
falling on noise and a ringing square, out of reach and on a constant; full
scale moving the level; the coupling on one lane and the other and on the
input's side; each kind of filter with its resonance and what is pointed at
both; the lag whole and fractional, clamped, locked, and refused three ways;
mid and side and the turn, refused three ways; the buffer giving way;
samples landing exactly on the level and on the band's edge, edges exactly a
holdoff apart and a fraction of a sample short; and 40 random runs.
Mutation: 45 of 47 caught. The two left are equivalent: the search starting
at sample one rather than nought, where no crossing can be, and mid and side
asking that the source has two channels as well as the frame, which it does
whenever the frame does, as mid and side refuses the lag that could add a
lane. Six lived until runs could show them - the band's edge, a level met
exactly, the holdoff's rounding and its equality, a cutoff past what the
rate holds, and a lag that adds to less than nothing. Exact samples needed
a square of a half on an offset of a half, since a float of 0.4 and a
double of 0.4 do not cancel.

**4c: the beam's walk** (`scope/beam.h`). What the renderer lays into the
grid each frame: the X-Y figure, or one per layer while the source asks and
the lag has not taken the lanes, turned when the capture has not turned it,
placed by full scale and offset and magnified, a point in every so many when
the window is long; each Y-T lane on, in its band when stacked, as a bar a
column when there are more samples than pixels and as the polyline
otherwise; and the beam's shading on both - the anchor from a histogram of
the squared lengths, smoothed per display, and a step for each segment - so a
fast stroke deposits less than a slow one. `drawPicture` does a frame: the
fade, then the walk for the display, and the spectrogram clears the grid.
Nothing is drawn; the canvas is handed in as its size, whether it was
resized or wiped, and how wide the widest lane name is, which the page
measures and the core cannot.

Parity (`beam_js.mjs`, `beam_cpp`) runs the page's own `drawMain` and `drawXY`
on a canvas that draws nothing, each frame from the page's own capture, so
what is compared is what the page deposits and not a second reading of it.
Named runs: the figure at each level of the beam and with it off, zoomed,
placed, at the smallest square and resized; a diagonal line turned by the
capture and by the walk; figures the source asks for, one naming a lane that
is not there, refused under the lag; a window long enough to stride; Y-T as
polyline, shaded, magnified, as peak bars and past the beam's limit, and
unlocked; six lanes stacked with the gutter each way, a lane off, offset and
scaled; persistence each way; the anchor set, moved, forgotten; samples that
are not numbers or are infinite; a figure that does not move, the deepest
zoom, and noise past the anchor's histogram; and a circle and a fifth. Then
40 random runs of 40 commands. Not the spectrogram's branch, which clears
the grid: the page's spectrogram needs a canvas that draws, and the plugin
checks that branch in 4d. A circle at 220 Hz lays the same grid with
the beam on as off, and a fifth lays less; the walk turns a rack's pair as
the capture turns a stereo pair; the gutter is the widest name and sixteen
pixels, held to 22 per cent of the screen; the anchor moves 3.1 per cent of
the way to a new figure in a 16 ms frame. Each was seen to fail on a wrong
value first.

Mutation: 48 of 57 caught in the walk. The nine left are equivalent, or
reachable only in states the page never reaches: the floor under a squared
length in the step and the floor at step nought, which no anchor can bring
into play; the percentile's tie, met only when three tenths of the count is
a whole number and the count lands on it; the hysteresis, which never holds
(below); rounding a squared length to a float, which moves a step only
within a float's width of its edge; an anchor that is not finite, which none
is; the first segment's hysteresis, which has no step before it; a figure's Y
lane missing from a frame of more than one lane; and the cap on points,
which the stride's rounding up already keeps. Four lived until something
could show them: the anchor's top bin (the noise past the histogram), the
anchor's smoothing and the lag's refusal of figures (both mutants first
failed to compile and were counted as living), and the gutter's rounding
(a screen whose 22 per cent is not a whole pixel).

The grid's walk gained a cut on the way (below, under *Found on the way*),
in the page and the core together, and its mutants ran through both the
picture's runs and the walk's: 12 of 18 caught, and the one in `jsHypot`.
The six left change how long a walk takes and not what it lights, which is
the cut's whole claim: its threshold, held instead by a check that every
picture run lays the same grid through a copy of the page with the cut
taken out, to the last bit; the grid's far edges a cell further out, past
which every sample is skipped anyway; the two samples' margin at either
end, there for rounding at a grid edge no run lands on; and the bound where
the cut part is walked afresh, brought down to 1e10 steps, which walks the
far run's segments afresh and lights the same cells. Two lived until runs
could show them - a segment lying along the graticule's top edge, and a walk
straying past the part on the grid, which only a segment too long to walk
whole shows, by never finishing.

The plugin runs it from 4d.

**4d: the plugin draws its own picture** (`scope/screen.h`, the view in
`scope/restore.h`). So the loops through the picture go on with the window
closed, the plugin captures from its picture ring, lays the grid, and steps
the photocell and the picture's sources itself, at the page's sixty frames a
second of audio time, in the page's order: the capture, the sources stepped
from the grid the last frame left, the matrix, then the deposits. The score
reads that grid, so it plays in the plugin now, where it used to send
nothing. The sources are registered while the photocell is on, as `setPhoto`
has it, and the view's destinations - rotation, the lag, the filter, the
zoom, the trigger's position, each lane's full scale - always, with the zoom
made again from its step and offset after every matrix pass.

The view is the page's `state` held in the brain (`Brain::ViewState`):
restored from a setup as the page's `restore` leaves it, moved by the view's
sliders, and changed by its menus, switches and buttons and the reticle,
which the page now sends - the display, the trigger's edge, lane and mode,
each lane's switches, mid and side, the lag, the filter, the analysis and
measurement taps, the layout, the beam, persistence, the X-Y pair, the
photocell's button and the Clear button. The page's keyboard shortcuts for the
display and the zoom, and the wheel's zoom, became hands on the button and the
slider, so the plugin hears them; and the trigger's lane buttons have ids.
Held to the page by the restore parity, whose dump now carries the view: every
preset, every random setup and every slider, menu and switch run there
compares it, and a section of its own puts the view's hands between presets,
with lanes the generator has not got and a reticle off the screen. The page
switching to X-Y when the kind menu chooses a drawing was found there.

What differs, said in `screen.h`: the page's verdict reads its monitor
limiters, Web Audio nodes the plugin has not got, so a picture cannot run
away by the limiter here; the automatic lag's lock is not ported, and the
lag is the slider's; the canvas is a fixed 846 by 534, the page's trace at its
usual size, which matters only to Y-T's peak bars, one a pixel; and the
capture is always Auto's.

Checked in the shell test: sixty frames a second and not one a block; the
frame is the page's capture of the ring as the block before left it, at a
timebase that asks for more than the ring holds; with the photocell on its
sources are there, the grid is lit and the reading moves; the loop bends the
figure "Pendulums bent by the light" draws, against the same without its
routings, and the photocell switched off from the page is that null exactly,
picture and sound; the loop reaches the sound in "Brightness opens the
ellipse", the reticle put on its line from the page; switched off mid-run the
sources go, switched on from off the loop starts; Y-T chosen on the page is
drawn in place of the figure; an oscillator on the zoom from the page moves
the picture; infinite persistence keeps everything, the Clear button starts
again and the grid fills again after it; a depth past a source's reach is
held to it; and the view's buttons are kept as hands, a display undoing the
last and every press of the photocell's switch.

Mutation: the view's half of the core, 72 of 75 through the restore parity;
the plugin's wiring and `screen.h`, 26 of 29 through the shell test; the
page's side, 12 of 12 through hosttest.py. The six left are equivalent: the
trigger's lane tested against the lanes after `setTrigSource` has already
held it under them; an offset rounded before a slider of step one rounds it
anyway; the lane rows built again when the lag is switched, which with two
lanes changes nothing the restore's rebuild had not; a frame due a little
early, at the same rate; a fixed sixteen milliseconds for the frame's
elapsed time where the real ones alternate about 16.7; and the turn applied
to the drawn pair's shape, which moves only its edge contact - not offered as
a source - since its direction is the same under any turn. Most of the rest
lived until something could show them, and each named something the runs
did not do: setups that move the view's every field, where the presets
leave the holdoff, the edge, the trigger's mode and the lanes' switches at
their defaults; lanes the generator has not got; an AC corner off its
slider; the kind menu changed with the spectrogram showing; a full scale
halfway between two detents; a reticle with no comma, which the core had
refused and the page reads as a number and a NaN; the frame compared with
the page's own capture of the ring, its length and what it asked for; the
photocell switched mid-run each way; the grid filling again after a Clear;
and a depth past a source's reach. And the restore's last step was found
missing by the first of those: the page builds the lanes' rows again from
what they hold, so a scale slider stands at the detent nearest its
decibels, which the core's panel had left where the setup put it.

**5. The site on WebAssembly.** The worklet runs the compiled core, and the
JavaScript engine and brain are retired once parity says there is nothing left
they do that the core does not.

5a puts the generator in the worklet as WebAssembly, behind a switch:
`?core=wasm` in the address, and the worklet runs the C++ core's
`scope::Generator` where it ran `makeGeneratorCore`, and says which it made.
Everything else stays as it was - the main thread's generator, the effects
worklet, the brain - so the switch changes one thing, and the JavaScript one
is the default until the compiled one has been shown to be the same in every
way the worklet uses it.

The module is built by `core/wasm/build.py` with clang's own wasm32 target
and the WASI libc and libc++, no Emscripten: `-fno-exceptions -fno-rtti -O2`,
as a reactor so `_initialize` runs the static constructors, and stripped. It
imports only the three WASI calls the C library's abort path reaches for,
which the page stubs. The library's `operator new` would throw and a module
without an exception runtime cannot link that, so the bridge has its own, and
an allocation that fails ends the module as it would end the worklet. The
build is deterministic, 187 KB, and goes into the page as base64 between two
marker comments, because the page is one file opened from the disk as often
as served and a worklet cannot fetch from `file://`. `--check` builds it again
and compares; parity runs that, and the web suite does when the toolchain is
there.

The bridge (`core/wasm/scope_wasm.cpp`, and `makeWasmCore` in the page) is
the JavaScript core's interface spelt for a boundary of numbers. A setting
crosses as its field's name and its value as JSON in a scratch buffer, read by
the core's own `jsonParse`; JavaScript writes a number in its shortest
round-trip form, so nothing is lost on the way, and a typed array goes as the
array it holds. Routes go as seven doubles each. The oscillators stay the
worklet's objects and its truth: every number written in before a block and
read back after it, so a restart the worklet makes by setting a phase to
nought is just the phase. The lanes, the input and the readings come back
through views made fresh after every call, since the module's memory can grow
and replace its buffer.

Held three ways. Parity drives the page's `makeWasmCore` over the module the
page carries and the page's `makeGeneratorCore` through the generator runs,
both through the harness's own calls, and compares the samples and what the
worklet reads back - the envelope, the crossings, the budget, the drawing and
each oscillator's phase, held value and value - to 1e-12 in every family; the
effect's runs say so and are left out, as the effect is not the compiled
core's yet. The nulls build the bridge wrong on purpose - a route a
thousandth too strong, the phases not handed back, a setting given as text
dropped - and each fails it, and the page's copy is told from one a character
different. `wasmtest.py` plays the page with the switch and finds the worklet
saying `wasm`, the picture drawn from it and the oscillators coming back, and
without it saying `js`; and runs every one of the 254 generator presets
through both cores with the settings, routes and oscillators the page holds,
through JSON as processorOptions are and then as live objects as a message
brings them, for a quarter of a second: the same to 1e-16, against a route a
hundredth stronger or a tone a cent sharp that is not.

The samples agree to the bit everywhere but the drawing's readings, which
differ in the last place: V8's sine and the WASI libc's are not the same
function, and the native build's libm is a third. A first-run difference in
`figure-path` was not that - see the comparison that skipped NaN, below.

Mutation: the bridge's C++, 45 of 49 through the parity section, and its
page side, 21 of 24. The seven left are equivalent: an oscillator's depth,
which the generator never reads (routes carry their own amounts), written
across or not, on either side; its held value and its value written in,
which only the module itself changes, since a restart sets the phase alone;
the oscillators sized in two steps rather than one; UTF-8's two-byte branch,
which no string the page sends reaches; and `undefined` turned into `null`,
which the page never sends. Five more lived until runs were added that did
what the page does and the runs had not: drawbars on layer B, with a
registration of their own; a drawn cycle, a wavetable bank and a path each
cleared after being set; an oscillator's shape changed under a routing; an
oscillator restarted, by its phase set to nought; and typed arrays handed
over, which JSON writes as objects unless told otherwise. The harness's two
modes hand over typed arrays now, and it has `restart` and `none` for the
other three.

5b gives the effects worklet the compiled core too, and makes it what both
worklets run: the generator's and the effects' on a live input take the
module unless the address says `?core=js`, or the browser has no
WebAssembly. The bridge gained the effect (`scope_effect`: a live pair in the
first two lanes, the plane's result in the next two, the oscillators in and
out as for a block). A worklet that is sent the module and cannot make it -
a version it does not know, memory it will not give - makes the JavaScript
core instead, through `makeWorkletCore`, and says which it made and why; the
page keeps both (`coreKind`, `coreWhy`) for the tone, the rack's lane and the
effects insert, so a refused module is the other core playing rather than
silence. The main thread's generator, which draws the picture while the
sound is off, is still the JavaScript one.

What made the default safe to change is that the whole web suite is now a
test of it: every check that sounds the generator or puts an effect on a
live input runs the compiled core, and passes. On top of that, parity's
effect runs went from one to four - the echo with feedback and ping-pong
under routings and a restart, the kaleidoscope and mirror oversampled with
the radius routed, and nothing on at all - compared through the harness
like every other run, with a null that copies the input to the output
without running the effect, which all four fail (the last by its
oscillators, which the effect steps and the copy does not); and wasmtest.py
puts every preset's effects, as the insert is given them, on a 3:2 stereo
input through both cores, the same to 1e-16, against a twist a hundredth of
a radian further that is not. It plays a stub microphone through the
mirror and finds the insert running the compiled core and the input folded,
and `js` for both worklets with `?core=js`, and gives the page a module of a
version nobody has written and finds both worklets on the JavaScript core,
saying why, and playing.

Mutation: the effect's path through the bridge, 6 of 6 through the parity
section - its lanes swapped either way, the second input written from the
first, the oscillators not written in or not read back; and the worklets'
choice of core and what they say of it, 9 of 9 through wasmtest.py - the
fallback rethrowing, the compiled core called the JavaScript one, the switch
read the wrong way or `&&` as `||`, the effects worklet not sent the module,
its report or the generator's reason not kept, the effects worklet not
saying, and the helper left out of the worklet's module.

5c moves the main thread's generator - the tone source's and the rack lane's,
which draw the picture while the sound is off and whose settings the page
reads back - onto the compiled core, under the same switch and with the same
fallback (`makeMainCore`; `mainCoreKind` and `mainCoreWhy` on the source). The
module is compiled once on the main thread, synchronously, about forty
milliseconds, and each source instantiates its own; a browser that will not
compile a module this size there gets the JavaScript core and says why. So the
generator the page runs is the compiled one everywhere it runs.

The main thread asks more of a core than a worklet does, and three things
were needed. Its settings: the page reads `tone` and `toneB` back, so the
wrapper keeps them on this side by the rules the JavaScript core stores by -
the defaults and the storing are now shared functions (`generatorSettings`,
`storeGeneratorSetting`) that both cores use, so they cannot drift. Its
blocks: the main thread draws without the heard pair, and the lane without
layer B's, and the bridge passes the core none for a pair it was not given,
as the JavaScript core is passed null. And its readings: the pitch, the kick
on the spin and the swing's envelope came across with the rest. What it does
not offer is the voices in detail, which only the tests read, from cores
they make themselves.

Two faults were found on the way, both in the wrapper. A view over the
module's memory made before a call that grew it, which threw the first time a
preset sent a wavetable bank (the same shape was in the state read-back since
5a, and had been lucky); and the cost of JSON for the big settings - the
wavetable bank, the drawn cycle and the path, which every preset sends -
which more than doubled what a preset cost. Those go as numbers now
(`scope_tables`).

Held by: parity's picture-only comparison of every run, the main thread's
call; a module withholding the heard pair from a caller who gave one, which
fails; and in wasmtest.py the main thread saying `wasm` by default and `js`
with the switch, every preset's settings read back the same from the mirror
as from the JavaScript core, every generator preset drawn picture-only the
same through both cores, and a page whose own WebAssembly is refused drawing
from the JavaScript core while its worklet still runs the compiled one. And,
as with 5b, the whole web suite: every check that draws the generator with
the sound off now draws it from the compiled core.

Mutation: the bridge's new paths, 19 of 20 through parity in its three ways
of asking for a block - the tables and the path read or written short or
wrong, a cleared one left set, the readings out of order, the gate not
kept, the pairs' flags confused, the tables not sent; the one left asks for
the heard pair when only B's was wanted, which changes nothing a caller
reads. Two lived until the run on the bank's last slot was added: a bank
arriving a slot short, from either side. And the page's half, 8 of 8
through wasmtest.py: the mirror not kept or not the one handed out, the
switch inverted, the fallback's reason dropped, either source making the
JavaScript core while saying otherwise, the module refused, and the view
over the memory made before the call that grows it.

5d puts the picture's own sources on the site onto the compiled core: the
phosphor grid and its fades, the walks the renderer lays into it, the
photocell, the picture meter and its verdict, roundness from the beam's
moments, the drawn pair's shape, boredom and the slews - the pieces 4a
ported. The page's JavaScript for them is gathered into `makePictureEngine`
and stays, as the fallback and the reference; `makeWasmPictureEngine` is the
same interface over the core's `Phosphor` and `PictureSources`, an instance
of its own from the module the main thread compiled; `pictureEngine` is
whichever the switch chose, with the same fallback and the same report
(`pictureCoreKind`, `pictureCoreWhy`). The renderer still draws to the canvas
and walks the beam in JavaScript, handing each walk's polyline to the engine:
moving the walk itself (4c's `drawPicture`) would put the canvas's and the
grid's walks in two places, which is the drift the renderer's comment says
the grid was built to avoid.

The page's objects stay where they were, because the tests and the readouts
reach into them: `phosphor.grid` is the engine's cells - over the compiled
core, a view into its memory, so a test's write is a write the core reads -
and `photo` and `picture` are plain objects each step reads and writes back.
The core gained what that needs and nothing else: the cells to write into,
`carry` for the slewed values handed back in, and the meter reset alone.

Held three ways. The parity harness's picture runs go through the compiled
engine as well as the page's, and its output is the page's to the character
across all of them (9,538 lines), against runs with every persistence a
hundredth more that are not. wasmtest.py records every call the page makes
to its engine over real frames - every preset that turns the photocell on,
Y-T, the spectrogram over a lit grid, persistence off and infinite, a Clear,
a word and the lag's figure turned and zoomed into the screen's edge, five
seconds with a reset, those five seconds with the limiters held down, and a
still picture - and replays them into a fresh engine of each kind, comparing
the cells, the photocell, every value raw and slewed, the meter, its verdict
and the shape after each call; against persistence a thousandth more and
every walk a step brighter, which are not. And the web suite runs every
picture check on the compiled engine.

Mutation: the bridge's picture exports, 13 of 13, and the compiled engine's
page side, 9 of 10, through the recorded replays; the one left skips a
polyline of two points, which the page never lays. Five of the thirteen
lived until the replays did what the page does and they had not: the
spectrogram over a grid with ink on it (a blank that did nothing cleared
nothing either way); a turn applied backwards, which only the lag's figure
shows (see the README on figures with a mirror in them); the monitor's
limiters held down, which with the sound off they never are; a meter reset
with history behind it; and a verdict other than "listening". And the
page's wrappers - what each frame hands the engine, the meter it reads, the
grid it hands back - 10 of 10 through phototest, shapetest and wasmtest.

5e makes setup codes on the site the compiled core's: `encodeSetup` and
`decodeSetup` on the page call `setupCodec`, `scope/setup.h` compiled, in an
instance of its own, with the page's own kept as `encodeSetupHere` and
`decodeSetupHere`, the fallback and the reference. The core gained a UTF-16
`decodeSetup`, which the UTF-8 one now calls; the bridge, an encode and a
decode over UTF-16 text. `restore` stays the page's: it applies a setup to the
page's state and its controls, and the core's restore applies one to a
`Brain` the site does not run yet - it moves when the brain does.

Held by parity's setup section, whose 804 commands - every kind of snapshot
and code, the throws and the unreadable, numbers V8 writes in exponent form,
lone surrogates - now also go through the compiled codec as the site makes
it, and give the page's lines to the character, against the commands with a
frequency a hertz higher that do not; and by wasmtest.py, where every preset's
snapshot makes the same code through each codec and reads back the same, and
27 awkward codes and snapshots - empty, not base64, base64 of things that are
not setups, old versions, names past Latin-1, null, an array, a number for a
code, a setup longer than the reader's chunk - have the same outcome from
each, a throw as a throw. The cost is the module's size: 211 KB to 371 KB.

Mutation: the bridge's setup exports, 4 of 5 through parity's commands, the
one left reading the code as UTF-8 first, which comes to the same since
anything past Latin-1 makes a code unreadable either way; two error codes the
page could not tell apart were made one. The codec's page side, 7 of 7, three
of them only once wasmtest.py's awkward cases had a null and an array to
encode, a number to decode and a setup longer than the reader's chunk - and
the number found a real difference on the way: the page's own decoder trims
inside its `try`, so a code that is not a string reads as nothing, where the
compiled codec had thrown.

5f puts the brain on the site too, as a second arrangement beside the first:
with `?brain=core` the page is the face of the instrument compiled whole, as
it is the plugin's, rather than the brain driving the compiled engine. Two
halves.

The first lifted the plugin's processor, less JUCE, into the core:
`scope::Instrument` (`scope/instrument.h`) is the hands the page sends and
how they are remembered, a setup loaded, the state code, the block loop with
its once-a-frame work and its events at their samples, and the picture ring.
The processor owns one and keeps what only a host has - the parameters, the
transport, the MIDI in and out, the locks - handing it over through three
hooks (MIDI sent, a slider the page moved, a setup loaded) and the block's
arguments. The SVG path parser threw, as the page's does, and the core builds
without exceptions for WebAssembly, so it keeps the first refusal and stops
at the next command instead, with the same strokes or the same message. Held
by the shell test, all 59 checks unchanged, and parity.

The second compiled it and put it in a worklet. The bridge's `brain_`
exports take the page's hands as the plugin's native functions do, text in
UTF-16; MIDI as messages for the top of the next block, as a host's would be
at sample nought; and hand back the heard pair, the picture pair, what was
sent to a MIDI port, and the state when it changes. In the page,
`makeWasmBrain` wraps them, `brainProcessor` plays them in the audio thread,
and `makeBrainHost` answers the plugin's native functions from it, so
`scopeHost` - the page's bridge to the plugin - is the worklet when there is
no plugin, and the page runs its hosted code unchanged: `toHost`,
`hostConnect`, every hand sent, every state applied. What the site needed
that the plugin did not: the page's notes, passed on as MIDI from the four
places they enter (a port's bytes once, as they came, and not again as the
notes the page makes of them); the instrument's MIDI out sent from the page's
port on the page's channel, with the page's own brain kept from sending
beside it; the generator's switch opening the instrument's way to the
speakers through the page's monitor chain, the instrument playing either
way, as in a host; and a press. A browser runs no blocks until something on
the page has been pressed, which a plugin never waits for, so the processor
posts its state from its constructor - the page shows the instrument at once
- and the credit line says it is waiting until the first press starts it.

Found on the way: a hosted page had no generator. `genSettings` and `genSet`
asked whether the source was a tone, and a hosted source never is, so inside
the plugin the generator's whole section was missing from the panel - no
kind, no frequency, no shape - and the plugin's tests, which send hands from
code, never looked. A hosted source now carries a mirror of the generator's
settings (`makeGeneratorMirror`, by the cores' own rules), kept by the page's
handlers and restored from the instrument's state, and the two ask whether
the source carries settings rather than what it is. And while hosted the
source switch is disabled: a microphone chosen there would be drawn while the
instrument went on taking the panel's hands.

What it has not got, and why it is a second mode rather than the first: live
inputs, files, the rack and recording, none of which the plugin's view of the
page has either; the effects on a live input with them; and the page's own
analyses that drive the generator in the first arrangement (the hearing of a
live input, the automatic lag's lock), which the instrument's own hearing
replaces for its own sound only. The module is the price everyone pays: 371
KB to 764 KB, in one module rather than two, since a second would carry the
generator twice.

Held by parity's instrument section: seven scripts through the native
instrument and the compiled one, through the page's own wrapper - notes and
the pedal, the page's hands of every kind, refusals, every preset in turn
with a note held through each, the arpeggiator on MIDI clock and what it
sends, a photocell loop over five hundred blocks, and blocks of every size
from one frame to 2,048 - every sample, state and message the same to the
bit, against the comparison one line out of step, the native run with one
hand a step away, and modules with the page's MIDI dropped, the heard pair
handed back as the picture pair, a state never published and a switch read
as off. By braintest.py, in the browser: the page draws the instrument and
shows its state; a note from the page is heard at its pitch and not a
semitone up, with silence either side; a slider halves the picture; a preset
is the setup the instrument loaded and not another; the kind menu moves the
panel, the view and the instrument; a port's bytes go once; MIDI out leaves
by the page's port and channel and the page's brain stays quiet; the switch
opens and closes; a module that will not make leaves the website; and an
unpressed page plays nothing until pressed. And by hosttest.py, which now
looks for the generator's panel inside the plugin.

Mutation: the bridge's `brain_` exports, 14 of 15 through parity's scripts;
the one left prepares the instrument for blocks of 64 rather than 128, which
only changes how a block is cut into pieces, and the pieces add up to the
same samples. One lived until a run had a note nought held: a message padded
to three bytes is a clock byte and two zeros, which under a note's running
status is a note-on for note nought at velocity nought, and only a held note
nought can hear that. The page's side, 30 of 30: 27 through braintest.py and
hosttest.py and three in the page's wrapper through parity, which drives that
wrapper lifted from the page - a switch read the wrong way, the MIDI padding,
and the heard pair handed back as the picture. Two lived until braintest.py
looked: the picture's lanes posted the wrong way round, which on Harmonic
tone, its lanes a quarter-cycle apart, reads a quarter where the website's
reads three quarters; and the instrument made on the defaults rather than on the setup the
page opened on, which the page then restored without complaint, until a check
asked for Harmonic tone's timebase of 3 where the default's is 4.

5g gives the instrument an input, which on the site is your microphone or
line input in `?brain=core` and in the plugin is an input bus, so the plugin
can be an effect as well as a synth. A block may carry an input pair, and the
instrument draws one of two sources, chosen by the page's Tone and Mic
buttons, which are hands now (`srcTone`, `srcMic`). Drawing the input, the
input goes through the plane - `Generator::effect`, the page's effects
worklet, which steps the oscillators itself - and what comes out is both the
picture and what is heard, as the page's analysers and monitor chain both
hang off the insert's output; the hearing stops counting what it hears as a
loop, since it is not the instrument's own sound. Drawing the generator, the
input is the generator's, for its live-input modes (the FM, the ride and the
clock), as one channel - the two summed and halved, as the page's worklet
takes it - and in the instrument it reaches the generator heard or not,
where the page's own needs the generator to be heard, the input reaching its
generator only inside the worklet. Which source is drawn is not a hand on
the setup: a setup has never said which source is playing, and a preset
lands on whatever is. So a preset loaded leaves it where it is, and the
state carries it beside the setup as `pluginInput`, for a project reopened.

On the site, Mic in `?brain=core` asks the page for the live stream - the
same one, from the same code, that the generator's live-input modes open -
and connects it to the worklet's input; the page's own rule says what is
heard: a line input you have asked to hear, never a microphone. The plugin's
input bus is off until a host turns it on, mono or stereo, and is copied out
of the buffer before anything is written into it, since a host hands the
input over where the output goes back. Not carried across: the band split,
which is the page's own four filters and has no place in the instrument yet,
and the device chooser inside the plugin, where the input is the host's.

Held by parity: a run through every part of it - the input drawn, through
the kaleidoscope and a routing on the twist, a preset loaded meanwhile, back
to the generator with each of its three input modes, a mono input and none -
and one that opens from a state with the input drawn, the compiled
instrument the native one to the bit, against modules with the input's lanes
swapped and a stereo input taken as mono; and, since two sides that ignored
the input would agree perfectly, the samples read against what was fed: the
input drawn with nothing on the plane comes out exactly as it went in, from
the reopened state's first block too, and not once folded or under the
generator - against the same reading a sample late. By the shell test: the
input bus on, the generator's sound and not the input; Mic from the page,
the input heard and drawn sample for sample, left as left; folded by the
kaleidoscope; a state saved and reopened drawing its input through the same
plane; Tone back to the generator with the state saying nothing of an input;
and the generator's FM moving a figure from the input, where with the mode
off the input changes nothing at all. By braintest.py, with a stereo stream
of known pitches standing in for the microphone: the input drawn at its
pitches, left as left, against the lanes the other way round; a microphone
not heard, a line input heard when asked; the plane folding it; Tone letting
the stream go; and the generator's FM taking it unheard. And by hosttest.py:
inside the plugin Mic and Tone are sent, the device is the host's, and a
state puts the source back on the page.

Mutation: the instrument's input and the plugin's bus, 13 of 13, twelve
through the shell test and one through parity - the heard pair left unwritten
while the input is drawn, which in the plugin changes nothing because the
host's buffer already holds the input in place, and which only a harness that
hands the instrument its own empty lanes can see. Three lived at first and
named something no check did: a stereo input reaching the generator as its
left channel alone, caught once a mono bus carrying the halved sum had to
sound the same; the instrument prepared again, as a host changing its rate
does, forgetting that what it hears is not a loop; and a mono input drawn on
one side only. The page's side, 20 of 20 through braintest.py, hosttest.py
and, for the plain site's generator taking an input only while heard,
inputtest.py; one line was found doing nothing, monitoring reset on a change
of source that asks again for it anyway, and was taken out.

5h plays a file through the instrument on the site. A file is only an input:
the page decodes it in the instrument's own audio context and plays it into
the worklet's input, the instrument draws its input as it does for a
microphone, and it is heard, as a file always is on the site. The transport
- play, pause, seek, loop, where it is - was the file source's, and is now
`makeBufferPlayer`, which the file source and the instrument's file both
use; the band split keeps a copy of its own, wired into its four lanes. The
microphone's stream and a file are never both the input: choosing a file
lets the stream go, and Mic or Tone lets the file go, while a state from the
instrument saying what is already so leaves a playing file alone. Inside the
plugin File stays off: the host plays files there. Nothing in the core
changed, so parity has nothing new to hold; braintest.py does it, with a WAV
made in the page - 441 Hz on the left, 661.5 Hz on the right - drawn at its
pitches, left as left, against the lanes the other way round; heard; the
stream let go; paused silent, seeking, looping past its end; and Tone
letting it go. hosttest.py checks File is off inside the plugin.

Mutation: the page's side, 13 of 13 through braintest.py and hosttest.py.
One lived until the check started from the generator: a file that never told
the instrument to draw its input, which a check that pressed Mic first could
not tell from one that did; and the guard that keeps a playing file through a
state from the instrument was caught only once a check applied such a state
while one played.

5i gives the instrument a rack. A third source beside its generator and its
input: up to six lanes, one signal each, which it draws, triggers on and
hears. Its picture ring keeps six lanes rather than a pair; the capture
already took a source of lanes, as a rack is on the page. A lane is the
input's lane of the same number, or - the generator's lane - the generator's
picture left channel, one signal as the page's generator lane is, and what
the instrument then sends out is that lane alone on both sides. The
generator runs with or without a lane, since its block steps the
oscillators every modulation reads. The level and the hearing read the
trigger's lane, and the hearing's width the pair's other lane, as the page
reads a rack; and what it hears is a loop through its own sound only while
the trigger is on the generator's lane. A rack is told by count and the
generator's place (`srcLanes`, "4,0"); like a rack's files, it is not kept
in the state.

On the site the rack's audio stays the page's own - `makeRackSource`, now
able to build in a context it is handed and to take its generator lane from
its owner: stems decoded and started together, a microphone's lane, the
mixer that plays the stems. Each lane is tapped where its analyser hangs,
before the mixer turns it, into the worklet's input - an analyser passes its
input through, so the tap is one connection and nothing about how a lane is
built changed - and the generator's lane is the instrument's, its mixer
level turning the instrument's output. Not carried across: the band split,
which is its own four filters; the alignment for playing along, which reads
a lane further back on the page where the instrument takes it as it plays;
and in the plugin a rack at all, where the host plays the files.

Held by parity, a rack run - four lanes of the page's, five with the
generator's first and a note in it, the trigger and the pair moved, a preset
loaded, back to the generator - the compiled instrument the native one to the
bit, and the lanes read off the samples: each fed lane at its own place, the
generator's lane the generator, nothing past the count, two lanes again
after - against the reading a lane along, and a module handing the lanes over
a place along - and, back at the generator for longer than the ring holds,
no lane of the rack's left behind in rows the pair wrote again. By the shell
test: the hearing a loop only with the trigger on the generator's lane; its
pitch and level read from the trigger's lane and its width from the X-Y
pair's other lane; all three lanes drawn, and a lag asked for in a rack not
taken; a setup loaded over a rack keeping its lanes; Mic, into a rack and
out, back at the generator; and a generator's lane past the count unheard.
By braintest.py, with two stems made in the page and
the generator's lane, each drawn at its pitch; the stems heard through the
mixer and the generator's lane through the instrument as the mixer and its
switch say; the lanes fitted and the pair started again at the first two,
the instrument told; a lane not yet posted read as silence; the trigger
reaching the instrument; paused, the stems quiet and
the generator drawing on; the band split saying it is not the instrument's;
and Tone leaving the rack and stopping its stems. And by hosttest.py, Lanes
off inside the plugin.

The width check found a bug that parity could not. The core's panel checks
a menu's value against the menu's options, as a browser does, and it held
the X-Y pair's two menus to the options they have before a rack: lanes 0
and 1. On the page they are built again with one option per lane. So in a
rack, a pair on lane 2 or later became lane 0 inside the instrument. The
compiled instrument and the native one made the same mistake, so parity's
rack run, which sets the pair on lane 3, agreed with itself. The lane menus
now take a lane count, which a rack sets. A related gap was on the page: a
rack in `?brain=core` started the page's pair again at the first two lanes
and never told the instrument, so the picture showed one pair while the
instrument heard the width of another. The page now sends it.

Mutation, the instrument's side: 18 of 18. Fifteen were caught by the shell
test. The other three are about lane contents the plugin has no input to
fill, and were caught by parity's readings: a lane past the count left
unzeroed, Tone not leaving the rack, and the pair leaving a rack's lanes in
the ring. At first the shell test caught 6 of 16, and parity's readings 3
more. The checks for the rest were written against what each survivor
broke, and one of them found the menu bug above. Two guards that covered
each other lived as a pair: entering a rack cleared "draws the input", and
the state refused to say input during a rack. The second guard was removed.
The ring's mutant lived until the rack run went back to the generator for
longer than the ring holds. Before that, every row it read had only ever
been written by the pair.

The page's side: 20 of 22 caught, one equivalent and one living. The brain
source reading an unposted lane as silence lived until the check read back
over the frames three lanes wrote. A window of the last two lanes' frames
found nothing stale in a ring that had not come round yet. Fitting the
channels when a rack is adopted proved equivalent: `buildLaneRows` fits them
itself, so that call is gone. One mutant lives: the worklet dropping a
part-filled chunk when the lane count changes. Without the drop, the new
lane's first chunk starts with up to 512 frames of silence. With it, those
frames are lost from the old lanes. No reading at the screen's rate tells
the two apart, and the drop is kept because it never mixes two counts in one
chunk.

5j moves the band split into the instrument: the input it draws, split by
the page's four crossovers into a rack of four lanes. Each lane is one
signal, the band of the two channels halved together, as the page's
analysers take a stereo band. What is heard is the bands' two channels
summed, each at the gain the page's mixer gives it (`laneMix`), so a band
soloed is the part you are looking at. It is asked for and let go by
`srcBands`, ends with Mic, Tone or a rack, and is kept in the state as
`pluginBands`: a host's input split is how that project is played, as the
input itself is.

The filters had to be the page's BiquadFilterNodes rather than its
JavaScript biquad, since the page's band split is made of the nodes. The
cookbook in doubles came within 2.5e-6 of Chromium. Trying each float
rounding in turn found the two that close the gap: Q is an AudioParam, so a
float, and the browser works out the resonance as a float as well.
`biquadNodeCoefficients` holds them. The memory is doubles fed back float
samples, as the browser's is.

On the site, Into bands under Mic and a file split from Lanes go to the
instrument in `?brain=core`, the file played into it as 5h plays one. Its
band lanes (`makeHostBandLanes`) are what the page's mixer and lane rows
turn, and they send the gains as one message once the mixer has set all
four. In the plugin, Into bands splits the host's input. The plugin's
picture now serves as many lanes as the picture has, interleaved, and the
page reads the count off the length, since it already knows the frame
count. Two lanes are byte for byte what they were. A state putting the
split back is applied without a word sent back, as every state is.

Held by parity: a band-split run and a state that opens split, the compiled
instrument the native one to the bit. Each lane and what is heard are read
against a Python copy of the browser's arithmetic, again to the bit, at
even gains and with a mix. The memory starts fresh each time the split
begins, the input is whole between, and nothing lies past four lanes. These
readings fail against a crossover at 130 Hz and a split read a block late.
braintest.py holds the strongest check: the compiled instrument fed a
stereo signal a block at a time, against the page's BANDS rendered offline
through real BiquadFilterNodes. Every lane and what is heard agree to zero,
and the comparison fails against the bands one place along. braintest.py
also covers:

- the live split in its order, kept in the state and not heard;
- a solo sent as one mix, and Whole;
- Into bands chosen over the generator waiting for Mic;
- a state saying so not sent back;
- a file split of 60 Hz and 2 kHz drawn at each pitch and heard, its
  lanes not removable one by one;
- Tone letting it go;
- Tone or Mic pressed while a file is decoding letting the file go.

The shell test plays the host's input split: four lanes served, the Low the
60 Hz and the High mid the 2 kHz, and what is heard the four summed, to
1.5e-8. It also checks a solo heard as that band alone, the split kept in
the project and reopened, Mic whole again, and a rack chosen over the split
letting it go. hosttest.py checks the same
inside the plugin's page: Into bands sent, the four served lanes drawn
exactly, a solo sent as one mix, a lane not yet served read as silence,
Tone letting the split go, and the state putting it back quietly.

The page's bands do not add back up, by about 3 dB at 60 Hz (0.207 RMS
from 0.3). That is the page's behaviour, carried across exactly. The
comment at `BANDS` used to call the difference small, and now gives the
number.

A gap in 5h's file path came out too. Under `?brain=core`, Tone and Mic
returned before marking a file still decoding as no longer wanted, so a
file finished decoding after Tone was pressed and was played over the
generator. That was true of a file split as well. `playFile` now asks
whether it is still wanted once the file has decoded, and Tone and Mic
mark any build in flight as stale in the host's path, as they always did
on the page's own.

Mutation, the instrument's side: 18 of 19, and the nineteenth equivalent.
Nine were caught by the shell test and nine by parity's readings. The
comparison of compiled with native does not count as a catch here, since
a mutant changes only the native side. Rounding Q to a float before the
resonance is worked out cannot be told apart for the one Q the bands use,
because rounding the resonance absorbs the difference. It stays, because
it is what the browser does. Four of the 18 lived at first:

- a rack chosen over the split, until a check chose one;
- the clamp on a mix gain below nought, which the page's mixer never sends.
  That clamp is gone;
- the lanes past four not cleared during a split. This lived until parity
  ran the split after a six-lane rack for longer than the ring holds, as
  5i's ring mutant had needed. That run also found the native harness
  handing a pair to a rack as no lanes, where the bridge hands it as two,
  and the harness now does as the bridge does;
- the band memory and gain resets, which were caught only once parity's
  readings were counted apart from its comparison.

The page's side: 28 of 28, through braintest.py and hosttest.py. Eleven
lived at first, and each now has a check:

- a mix sent again unchanged;
- a state applied while already split, which could not show whether it
  was sent back;
- a band split's lanes left removable;
- the plugin's file split guard;
- the decode race above, from Tone and from Mic.


5k moves the alignment for playing along into the instrument. Each of a
rack's lanes goes through a delay line, written every sample whatever its
delay, so moving the alignment reads further back at once, as the page's
analysers let it. Each lane is read as many samples back as the page says
(`laneDelay`): the track's lanes and the generator's held back to meet a
late input, or the input held back instead. As on the page, only the
picture moves; what is heard is not held back. The lines reach 200 ms, as
far as the page's slider does. A new rack starts at nought, with nothing
behind it, as the page's new lanes do. The page's `applyAlignment` still
decides which lanes and how far, and in `?brain=core` it tells the
instrument, and the alignment row is shown there.

On the way, the page itself was found losing the alignment when a
play-along was built again, for example with the generator ticked in. The
new lanes start at 0, and the alignment was applied only when the
context's guess was taken, so the slider went on reading 40 ms over lanes
held back by nothing. `alignRack` takes the guess the first time and
applies the alignment every time, on the page and in the instrument.

Held by parity: a play-along run, the generator's lane first and three fed
lanes, the compiled instrument the native one to the bit. Read off the
samples, each fed lane is its saw from as far back as it was told, and the
generator's lane is what was heard that far back. Moving the delay to the
live lane takes effect at once, a new rack reads from now, and a new rack
held back at once has silence behind it, not the old rack. The readings
fail a sample further back. The shell test checks that the
plugin's generator lane held back 480 samples is what it played 480
samples before, to the sample, and is now again once let go. It also
checks that a lane asked for from further back than 200 ms is drawn from
200 ms back and no further.
braintest.py, in `?brain=core`, checks that the row shows for a stem and
you, that the instrument is told the stem's delay and yours, and that it
is told again for the new rack when the generator is ticked in. It also
checks that the same alignment is not sent twice, and that a rack of the
same shape in its place is told it again.
alongtest.py checks the same rebuild on the page's own rack.

Mutation, the instrument's side: 9 of 9. Seven were caught by the shell
test and two by parity's readings, not counting its comparison of compiled
with native. One lived until parity held a new rack back at once:
clearing the delay lines when a rack is made. Without that clearing, the
first moment of a new rack aligned at once showed the old rack.

The page's side: 9 of 9, through braintest.py and alongtest.py. One lived
until the rebuild check trimmed the alignment to 70 ms rather than 40.
This browser's guess is 40 ms, so a rebuild that took the guess again
passed a check at 40.

5l is recording in `?brain=core`, and is all on the page's side. Measured
first, a clip already carried the generator heard and a file, through the
instrument's monitor chain, but two things were wrong. A microphone and
the band split were silent: a clip takes a live input nobody hears from
the source's `unheard`, and the brain source named none. And every clip
said the sound was what the speakers played, a silent one included,
because the instrument's monitor chain is always there.

The chain now says when it is silent (its gain is nought), and a clip
takes it only while it is not. `unheard` answers as the page's sources
do:

- for the input drawn, the instrument's output before its silent way out,
  which is the input through the plane, as the page's insert gives it;
- for the input split into bands, the input whole, as the page's band
  split gives it;
- for a rack, its live lane;
- for a file, or a line input monitored, nothing, since the speakers have
  them already.

Held by recordtest.py, on a second page with `?brain=core`:

- a generator nobody hears makes a silent clip that says why, and heard,
  its note is at its pitch;
- a live input unheard is in the clip, the note saying so;
- folded both ways by the instrument's plane, the input is an octave up,
  so what is taken is after the plane;
- split, with the Low band soloed, the input is still whole and loud;
- monitored, the input is in the clip once, through the speakers;
- a file is what the speakers played;
- playing along, the clip has the track and your input.

The fold was first read by the clip's lowest sample, which said no fold:
the codec takes a folded wave's DC away, about 0.32 of it, so the reading
is now the octave.

Mutation, 8 of 8 through recordtest.py.

5m is making `?brain=core` the site's default, with `?brain=js` as the
way back. It is not one step. Flipping the default and running the whole
web suite gave 1436 checks passed, 159 failed and 20 suites crashed, in
57 of the 74 suites. The failures are of two kinds, and only the first is
the instrument's to fix:

- Behaviour you would see. The first was the biggest: on the site, with
  nothing plugged in, the screen was blank until a note.
- Tests that reach into the JavaScript brain's own objects (the
  generator's worklet driver, `state.source.reswing`, the envelope's gate
  flag), which a source that is the instrument has no reason to have.

The JavaScript brain does not go away. `parity.py` holds the core to the
page's own functions, lifted out of `scope.html` by name, so the
JavaScript is the reference the core is a port of, as well as the way
back. The suites that test that reference will run on `?brain=js`. What
the default has to pass is everything you would see.

5m-i is the blank screen. The instrument gated its generator from the
start, because the plugin's host is always a keyboard. The page gates
only while there is a keyboard to wait for (`keyboardPresent`: a MIDI
port or the screen's keys), since a shut gate with nothing to open it is
a blank screen with nothing on the panel to explain it. The instrument
now takes `keyboardPresent` as a control, and the site's brain host sends
it from `midiApplyGate`: asked every frame, as the page asks it of its
own generator, and sent when the answer moves.

It is not a hand on the setup. It says where the instrument is playing,
not what it plays, so it is not remembered in the state, and the plugin
never sends it. An instrument told nothing is the plugin's: gated until a
note.

With the fix, the flipped suite went to 1493 passed, 109 failed and 18
suites crashed. The 109 that remain, read one by one, are in these
groups:

- The fade's dot and readouts.
- Layer B's drawbars, morph and pulse width written from the panel.
- A learned controller on a generator control.
- The readouts that explain a quiet screen or a budget.
- The picture's loop into the sound (boredom, the photocell's pitch).
- Tests that drive the page's LFOs by hand, which the page steps itself
  when the instrument is the source.

Held by:

- parity.py: with no keyboard the generator plays with no note, is gated
  the moment one is there and freed when it goes. Told nothing, it waits
  for a note. Nulled against a keyboard there from the start.
- braintest.py: with no keyboard and nothing played, the site's
  instrument draws its generator. The note check now opens the screen's
  keys first, because it was written against the plugin's assumption that
  a keyboard is always there.

Mutation: 4 of 4 in the core through parity's reading, and 3 of 4 on
the page's side through braintest.py. The one that lived sends the
answer every frame rather than when it moves, which sounds the same and
costs a message a frame. A fifth mutant lived too, and the code it
mutated has gone. It removed a guard against sending before the worklet
was ready, but the worklet builds the instrument in its constructor,
before it reads a message, so the guard did nothing.

**6. Release.** macOS AU and VST3, signed and notarised; Windows VST3 with
WebView2 linked statically; state saved into the host's project; recording
redone natively or left out.

## Found on the way

- **A comparison that skipped NaN called NaN and a number the same.**
  `worst` in the parity harness took the largest difference with Python's
  `max`, which never takes a NaN after a number. The generator's path fixture
  had a time more than it had points, so the page drew NaN for the last
  stretch of every cycle and the core read past the end of its vector - and
  the run passed, as did the same path in `figureAt`'s rows, until the
  WebAssembly build read different memory there and disagreed with the
  native one. NaN against a number is infinitely far now, and checked to be;
  the core reads a missing point as the page's undefined, NaN; the fixture
  has its sixth point, and the short path is held at `figureAt`, where no
  clamp stands between it and the comparison. Not in a generator run: the
  output clamps are `fmin` and `fmax` in the core, which give the bound for
  a NaN, and `Math.min` and `Math.max` on the page, which keep it, so a NaN
  sample is full scale in one and NaN in the other. The core's is the safer
  for a host, and nothing the page builds makes a NaN to reach it; the same
  difference stands wherever else the core uses `fmin` and `fmax` for the
  page's `Math.min` and `Math.max`, and parity holds those for finite
  values only.

- **Every button the plugin did not name was in the keyboard's set.** The
  hands a state keeps are compacted by set - pressing Dyad undoes an earlier
  Poly - and a button outside the four sets 3b knew was put in the
  keyboard's. Nothing reached it while those were the only buttons sent; the
  view's would have, and the photocell's button would have erased a Dyad
  press. Each set is named now, the photocell's switch keeps every press,
  and the Clear button, which leaves nothing behind, is not kept.
- **A check that claimed more than the preset does.** The first check that
  the loop reached the sound with the window closed used "Pendulums bent by
  the light", and found the sound unchanged by its routings: they bend the
  figure the pendulums draw, which is what the preset is for, and the heard
  pendulums do not carry the ratio. The check reads the picture for that
  preset now, and the sound for "Brightness opens the ellipse", whose phase
  is heard.

- **One loud sample stopped the page.** The grid's segment walk samples every
  half cell of the whole segment, so a sample far past full scale - a float
  of 1e39 is 3.4e38 - asked for some 10^40 steps, and an infinite one asked
  for infinitely many; the page stopped answering, and a plugin would have
  stopped its host. The port went looking because a host cannot be allowed
  to stop, and both the page and the core now walk a segment longer than two
  grid widths only where it crosses the grid - the samples the whole walk
  takes there, so the cells are the same to the bit, which a check holds
  against a copy of the page without the cut - and lay nothing for a point
  that is not a number. The first cut walked the cut part afresh, at another
  phase, and lit other cells on an ordinary diagonal; parity passed, both
  sides having changed together, and a surviving mutant (the cut's
  threshold, caught when it should have been equivalent) said so. The parity runs found both halves: a lane of
  infinities set the core writing to a cell from a NaN index where the page
  laid nothing - two ends at the same infinity are a NaN only in their
  difference, which `std::fmax` dropped, so the core now asks the
  differences - and a lane of 1e39 then hung both sides.
- **The beam's hysteresis never holds a step.** `strokeBeam` keeps the old
  step when the new step's centre is within a fifth of a step of the old
  one's edges, and a neighbouring step's centre is half a step out, so the
  condition is never met and a segment's step is exactly `beamStep`'s. Its
  comment says noise near an edge would otherwise shred a run; it does. The
  core keeps the dead branch so the two stay together, and a mutant widening
  the margin is caught, so changing the page will show. Not fixed here: it
  changes every shaded picture, which is a decision about how the beam looks.
- **A circle is not always the same with the beam on.** The page says that,
  with the anchor at the thirtieth percentile, a figure of even speed
  saturates at the ink, so a circle draws the same with the beam on or off.
  The anchor is the centre of a histogram bin 0.78 wide in log2 of the
  squared length, and a speed in the upper half of its bin reaches step 6 of
  8: a circle at 800 Hz lays less with the beam on. At 220 Hz, and at 14 of
  15 frequencies tried, it lays the same; the parity check uses 220 and says
  so. Not fixed here, for the same reason.
- **`jsHypot` let a NaN beat an infinity.** JavaScript's `Math.hypot` is
  infinite if any argument is, wherever a NaN stands; the port returned at
  whichever came first. Nothing had handed it both until a segment ran to
  (NaN, infinity); one does now.

- **An envelope that was an array.** The page asks whether each envelope it
  is handed is an object with `typeof`, to which an array is one, with
  nothing in it, so the envelope stays as it was; the core asked whether it
  was a JSON object, and gave an array the defaults. The fade's random runs
  never made an envelope that was not an object; a surviving mutant that
  dropped the check said so, and they make arrays, numbers and nulls now.

- **The fade held a copy where the page holds the routing.** A routing
  fading out is the page's routing object itself, so a depth changed and the
  routing taken off before the next frame fades out at the new depth. The
  core's fade copied the routing once a frame and faded the stale one. The
  matrix's random runs had `amount` and `unroute` from the start and never
  put them on one pair without a frame between; the edits' runs, which
  replace the whole list, did it at once. The copy is now brought up to
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
python3 core/wasm/build.py                   # the core compiled into the page, after any change to it
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

The WebAssembly build needs clang with the wasm32 target, the WASI libc and
the wasm32 libc++ (Ubuntu: `wasi-libc libc++-18-dev-wasm32
libc++abi-18-dev-wasm32 libclang-rt-18-dev-wasm32`); parity needs it too, to
check the page's copy and run it.

On Linux the web view needs WebKitGTK 4.1 and GTK 3, and the standalone ALSA:
`libwebkit2gtk-4.1-dev libgtk-3-dev libasound2-dev`, with the X11 and
freetype headers JUCE asks for.
