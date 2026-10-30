# Real-Time Sound Visualizer

An oscilloscope you play. It draws sound the way a bench scope does, phosphor and
all, and it is becoming an instrument whose sound is made from its own picture:

> **You play → the beam draws → the screen remembers → it is read back → you hear it →
> the beam draws.**

That loop is where it is going rather than all of where it is. Today the picture can
already shape the sound, through the photocell, the picture's readings and a score read
off the screen; the plan that makes it the heart of the instrument, and says what goes to
make room, is [`web/docs/making-it-one-instrument.md`](web/docs/making-it-one-instrument.md).
Read it before adding anything: its first rule is that a feature has to act on one of the
arrows above.

## Seeing it

The site is served from this repository by GitHub Pages:

**https://22nmcdon.github.io/Real-Time-Sound-Visualizer/**

Or open `web/scope.html` in Chromium or Firefox; it runs from disk. Safari has no Web
MIDI, so a MIDI keyboard does not reach it there; the keys on screen still do.

## What is here

| | |
|---|---|
| [`web/`](web/) | `scope.html`: the whole page in one file, the instrument's face on the site and inside the plugin. Work lands here first. |
| [`core/`](core/) | The instrument in C++, held to the page sample for sample by `core/tests/parity.py`, and compiled to WebAssembly so the site runs it too. |
| [`plugin/`](plugin/) | The instrument as a JUCE plugin, with the page as its interface. The plugin is the product; the site is its demo. Its staged history is [`plugin/PLAN.md`](plugin/PLAN.md). |
| [`DESIGN.md`](DESIGN.md) | How it looks: which parts are the house it shares with the jazz and guitar learning apps, and which are the oscilloscope's own. |
| [`CLAUDE.md`](CLAUDE.md) | How work is done here: the tests, the house style, and the layout decisions already made. |

## What it does now

A scope done properly: a real trigger with hysteresis and holdoff, calibrated 1-2-5
timebases, persistence, and a beam whose brightness goes as one over its speed, laid on a
64-by-64 phosphor grid that remembers it.

**X-Y** draws one channel against another, so an interval becomes a Lissajous figure.
**Lag X-Y** plots a signal against a delayed copy of itself, which gives a mono sound a
figure of its own. A generator draws figures and plays them, from a MIDI keyboard or the
keys on screen, and the picture's transforms (mirror, fold, twist, kaleidoscope) shape
the sound as well as the image. The **photocell** and the picture's readings feed back
into the sound, and the **score** plays notes read off the screen.

It also does a good deal the plan intends to cut, because it grew into three instruments
sharing one screen: a synth, an image generator and a visualizer. The plan says which is
which.

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
