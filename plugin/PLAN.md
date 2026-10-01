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
