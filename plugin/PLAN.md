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
- **2c. The setup as the core's state:** the page's flat snapshot and
  `restore`, setup codes and their migrations, and presets. The panel the
  keyboard reads becomes part of it, and so do the macros and the morph -
  which moves the panel's sliders, and so cannot come before them. (It was
  listed after time and the sources until the morph showed why not.)
- **2d. Time:** the key and the clock (the host's transport in the plugin),
  the LFOs locked to it, the arpeggiator, the score.
- **2e. The rest of the sources** that are not the picture's or the
  hearing's: the learned controllers as sources, the note envelope, the level.
- **2f. The hearing sources,** which analyse the sound and so are DSP in the
  core rather than the page.
- **2g. The host's parameters.**

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
a run without its feature. Of 76 mutants, 71 are caught; the five that live
change nothing:

- running status kept after `0xF0`, whose messages do nothing whether the
  data after them is read in pairs or dropped;
- channel pressure taking one data byte or two, for the same reason;
- the early return on a message cut short at the end of the bytes, where the
  loop ends anyway;
- the draw count's ceiling of eight raised to nine, when at most eight notes
  sound to be drawn;
- `setPair`'s own call to work the layers out again, which the `applyNotes`
  after it makes first anyway.

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

What the port leaves to later pieces: the arpeggiator (2d), where the page
asks `arpActive()`; the panel's sliders the keyboard reads and moves, which
are `Panel` until the setup is the core's (2c); and a chord handed to the
generator, which the generator copies and so can allocate on a note, once a
layer, until the brain's state is fixed in size.

**3. The page as a view.** One adapter in the page: the worklet and the
WebAssembly core in a browser, JUCE's bridge in the plugin. The web suite goes
on testing the page against the browser build.

**4. The picture's sources in the core,** so the loops go on with the window
closed.

**5. The site on WebAssembly.** The worklet runs the compiled core, and the
JavaScript engine and brain are retired once parity says there is nothing left
they do that the core does not.

**6. Release.** macOS AU and VST3, signed and notarised; Windows VST3 with
WebView2 linked statically; state saved into the host's project; recording
redone natively or left out.

## Found on the way

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
- **A mutation pass in the working tree is a build of the mutant.** The
  keyboard's first pass rewrote `keyboard.h` in place while the plugin was
  being built beside it, and the plugin's shell test failed - the note-off
  never closed the gate - on a mutant compiled in, not on the port; a backup
  of the header taken then to add a print held a mutant too. Mutants are
  made in a copy of `core/include` now, compiled from there, and the working
  tree is never touched while a pass runs.
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
draw without one (`57,64` holds a fifth), and `SCOPE_REPORT=1` prints the page's reports. With no sound card,
an `~/.asoundrc` of `pcm.!default { type null }` gives the processor a device
to run on.

On Linux the web view needs WebKitGTK 4.1 and GTK 3, and the standalone ALSA:
`libwebkit2gtk-4.1-dev libgtk-3-dev libasound2-dev`, with the X11 and
freetype headers JUCE asks for.
