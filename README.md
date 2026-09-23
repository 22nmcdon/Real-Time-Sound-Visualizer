# Real-Time Sound Visualizer

Two implementations of one instrument: an oscilloscope that behaves like a bench
scope rather than like a plotting library, and that is meant to be **played**
as much as read.

| | |
|---|---|
| [`web/`](web/) | `scope.html` — the whole application in one file. No build step, no dependencies. This is where work lands first. |
| [`oscilloscope-poc/`](oscilloscope-poc/) | A native Python/PyQt6 build of the same instrument. |

## Seeing it

The web build is served from this repository by GitHub Pages:

**https://22nmcdon.github.io/Real-Time-Sound-Visualizer/**

Or open `web/scope.html` in a browser — it runs from disk. Chromium or Firefox:
some of what it does (microphone input, and MIDI when that lands) needs APIs
Safari does not have.

## What it does

A test tone is synthesised in the page, so it draws something the moment it
opens. From there it takes a **microphone or line input**, an **audio file**, or
several files at once as separate **lanes** — and it will put a backing track
and your live playing on one graticule, aligned to the sample.

The scope half is the ordinary one done properly: a real trigger with hysteresis
and holdoff, calibrated 1‑2‑5 timebases, pre-trigger position, persistence, and
a beam whose brightness goes as one over its speed, the way a cathode-ray tube's
does.

The instrument half is the reason it exists. **X‑Y** draws one channel against
another, so an interval becomes a Lissajous figure and a stereo field becomes a
shape. **Lag X‑Y** plots a signal against a delayed copy of itself, which gives a
single mono input a second axis and turns one instrument into a moving picture.
A **modulation matrix** lets oscillators and your own playing level drive almost
any control on the page — the filter, the rotation, the zoom, the generator —
additively, several sources at once.

## Working on it

```
python3 web/tests/run.py            # every check
python3 web/tests/run.py lag cap    # just those
```

Needs Playwright with a Chromium, and node for the one non-browser suite. See
[`web/README.md`](web/README.md) for the suites and — more usefully — for the
things this page has already got wrong once, each written down with the reason.

The desktop build has its own instructions in
[`oscilloscope-poc/README.md`](oscilloscope-poc/README.md).

## Designed, written down, not built

| note | what it covers |
|---|---|
| [`web/docs/midi-and-the-audio-path.md`](web/docs/midi-and-the-audio-path.md) | MIDI in from a Nord Electro 6D; giving the generator a real audio path; letting the picture's own transforms shape the sound; two visualisers at once |
| [`oscilloscope-poc/docs/z-axis-lane.md`](oscilloscope-poc/docs/z-axis-lane.md) | brightness as a third axis, and why the desktop build is the place for it |

Also recorded and not built: **band-limited waveforms**. The generator's `waveAt`
is not band-limited, which is correct for a silent generator drawing a *picture*
of a square wave and wrong the moment the generator is audible — this app ships a
"Harmonics and THD" preset that would report the foldover as content.
