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

Ported so far, leaves first: the envelope (`scope/envelope.h`); the
waveforms and the functions under them (`scope/wave.h`) - `cycleOf`, the two
bleps, the drawbars' gain and weights, the intervals, the state-variable
filter, the drawn cycle's read, and `waveAt` for every shape; the four noises
(`scope/noise.h`); the voice's oscillator (`scope/osc.h`) - unison, FM,
ring, hard sync with its band-limited reset, and the sub-oscillator; and what
follows it in a voice (`scope/voice.h`) - the filter's cutoff and its cached
coefficient, the drive and fold with their oversampler, and the crush; and the
chord's voices (`scope/voices.h`) - the quantiser, `reconcileVoices` with its
release tails and their limit of eight, and `sound`, a layer's voices summed a
sample at a time with the governor's cut and the gains gliding between roles;
and the plane (`scope/plane.h`) - mirror, twist, kaleidoscope, the clip or fold
at a radius and the snap, at one, two and four times the rate, then the chorus
and the echo, one of each for each of the three pairs.
They are held to the page by a list of about 14,000 calls written by
`parity.py` and answered by both (`functions_js.mjs`, `functions_cpp`); the
functions inside `makeGeneratorCore`, which the page does not export, are
lifted out by name (`coreScope`) and run in the closure they were written for,
with the layers' tones handed in. The voices are run as scenarios of events -
chords, roles changed under held notes, a key pressed again inside its own
release, fifteen tails at once, the layer switched off, the cut, a retune, a
tie at the quantiser, sliders moved mid-note - through every shape and the
whole voice chain on both layers; the plane, every stage alone at every
factor, all of them together, and changed under the pairs. Every call agrees
to the last bit or within 6e-15 - the oscillators' sync and the oversamplers
accumulate a little - and 111 of 112 mutants of the ports are caught. The one
that lives is
the voice's phase folded back up from below nought, which only a pitch bent
past nought reaches, and which changes nothing: `cycleOf` and `sin` read a
phase below nought as the same point of the cycle.
Next: the governor, the crossings and the score's voices, then the
per-sample loop that sums the layers - the routings into each layer's pushes,
the dyad, the drawings - held to the page's own `makeGeneratorCore` whole.

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
`SCOPE_HOLD_NOTE=57` holds A3 so there is something to draw without a
keyboard, and `SCOPE_REPORT=1` prints the page's reports. With no sound card,
an `~/.asoundrc` of `pcm.!default { type null }` gives the processor a device
to run on.

On Linux the web view needs WebKitGTK 4.1 and GTK 3, and the standalone ALSA:
`libwebkit2gtk-4.1-dev libgtk-3-dev libasound2-dev`, with the X11 and
freetype headers JUCE asks for.
