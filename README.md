# Real-Time Sound Visualizer

A synthesiser that plays its own picture. It is a JUCE plugin (VST3 and a standalone
app) whose sound is drawn on an oscilloscope's screen and read back off it, so what you
see is part of what you hear:

> **You play → the beam draws → the screen remembers → it is read back → you hear it →
> the beam draws.**

Notes light the screen where they land (*Strike*), the light lingers (*Persistence*),
and *Scan* reads the brightness round a circle as the voice's own wave, at the pitch you
hold - so a figure that moves is a tone that moves, and a held chord either settles or
keeps breathing. The *Picture amount* lets what the screen is doing (how much is lit,
how fast it changes, how much it repeats) push the sound further.

Where it is going next is a screen that paints rather than traces: a picture that looks
like a painting, true to the sound, that the instrument then plays back
([`web/docs/painting-the-sound.md`](web/docs/painting-the-sound.md)). The plan behind all
of it, and its first rule - a feature has to act on the loop above - is
[`web/docs/making-it-one-instrument.md`](web/docs/making-it-one-instrument.md).

## Trying it

The plugin is the product; its face is a web page, and the same page with the same
engine (compiled to WebAssembly) runs on the site as its demo:

**https://22nmcdon.github.io/Real-Time-Sound-Visualizer/**

Work in progress is published beside it, at
https://22nmcdon.github.io/Real-Time-Sound-Visualizer/testing/, and reaches the
page above only when it has been tried there.

It starts silent until a note: show the keys under the screen and play A to K, or connect
a MIDI keyboard in Settings (Chromium or Firefox; Safari has no Web MIDI). Then open the
preset browser and try a sound under each heading: *Settled* sounds move as each note
strikes the screen and come to rest while held; *Breathing* ones keep moving while held.

Building the plugin: [`plugin/`](plugin/) (`cmake -B build -G Ninja plugin && ninja -C
build`; Linux needs WebKitGTK 4.1 and GTK 3). There are no signed builds yet.

## What is here

| | |
|---|---|
| [`plugin/`](plugin/) | The instrument as a JUCE plugin, with the page as its interface. Its staged history and what is left is [`plugin/PLAN.md`](plugin/PLAN.md). |
| [`core/`](core/) | The instrument in C++, shared by the plugin and (as WebAssembly) the site, held to the page sample for sample by `core/tests/parity.py`. |
| [`web/`](web/) | `scope.html`: the face, one file, which still carries an engine of its own in JavaScript that the core is checked against - retiring it so the core is the only engine is the next simplification. |
| [`DESIGN.md`](DESIGN.md) | How it looks: which parts are the house it shares with the jazz and guitar learning apps, and which are the instrument's own. |
| [`CLAUDE.md`](CLAUDE.md) | How work is done here: the tests, the house style, and the layout decisions already made. |
| [`web/docs/`](web/docs/) | The plans and studies, each dated, including the [handoff](web/docs/handoff-p8.md) written at P8, kept as history. |

## Working on it

```
python3 web/extract.py && node --check web/tests/check.js   # the page's syntax, seconds
python3 web/tests/run.py                                    # every check on the page
python3 core/tests/parity.py                                # the C++ core against the page
python3 core/wasm/build.py                                  # after any change to core/
```

The page's suites need Playwright with a Chromium (point `CHROME` at it if the default
path is wrong). [`web/README.md`](web/README.md) lists the suites and, more usefully, the
things this page has already got wrong once, each written down with the reason.

A native desktop build in Python and Qt lived in `oscilloscope-poc/` until it was retired
in the plan's first stage; it is in the history.
