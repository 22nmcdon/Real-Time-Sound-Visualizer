# The Scan experiment

Stage P2 of `../making-it-one-instrument.md`: before Scan is built, find out whether a
scanned phosphor can sound good at all. Offline; nothing in the app changes.

## How it was run

```
CHROME=/path/to/chromium python3 capture.py grids/   # six presets, 180 frames of the 64x64 grid each
python3 scan.py grids/ out/                           # tables, renders and metrics.json
```

`capture.py` loads each preset in the page and records `pictureEngine.cells`, one grid
per engine frame, for three seconds. That grid is the C++ core's too (parity holds them
equal), so it is the one Scan would read. `scan.py` reads each frame along a closed path,
with the grid blurred first by a *softness* in cells, into a 2048-point table with its
average removed and its level evened. Each table is band-limited to the note and
crossfaded into the next frame's, and the result played at A2, E3 and A3 for a second
each, every file at the same loudness.

The loop is open (what Scan plays is not drawn back) and nothing of the preset's own sound
is mixed in, so these are the hardest case. The real Scan would add both, and would slew
the table's harmonics rather than crossfading whole tables.

Four paths: a circle round the figure's centre at its RMS radius (*wide*), the same at
half the radius (*tight*), a 2:3 Lissajous path (*lissajous*), and a circle displaced from
the centre (*offset*). Three softnesses: 0, 1.5 and 3 cells.

## What the tables say

*Heard* is the lowest harmonic carrying a tenth of the energy: what the ear takes for the
pitch, so 1 is in tune and 3 is three times the note. *dB/oct* is how fast the harmonics
fall: a saw falls 6. *Fund.* is the fundamental's share of the energy. *Motion* is the mean
change in the table's spectrum between frames.

| Variant | Heard | dB/oct | Fund. | Motion |
|---|---|---|---|---|
| reference: sine | 1 | -18.9 | 1.00 | 0.000 |
| reference: saw | 1 | -6.0 | 0.61 | 0.000 |
| harmonograph · wide · raw | 2 | -3.0 | 0.04 | 0.000 |
| harmonograph · wide · soft 3 | 2 | -14.2 | 0.00 | 0.000 |
| harmonograph · offset · soft 1.5 | 1 | -12.9 | 0.54 | 0.008 |
| harmonograph · offset · soft 3 | 1 | -19.5 | 0.71 | 0.005 |
| kaleidoscope · wide · raw | 1 | -9.0 | 0.28 | 0.043 |
| kaleidoscope · wide · soft 3 | 1 | -12.8 | 0.48 | 0.015 |
| kaleidoscope · offset · soft 1.5 | 1 | -12.2 | 0.95 | 0.011 |
| kaleidoscope · offset · soft 3 | 1 | -11.3 | 0.96 | 0.004 |
| morphing-rose · wide · raw | 3 | -3.1 | 0.04 | 0.198 |
| morphing-rose · wide · soft 3 | 1 | -14.9 | 0.49 | 0.199 |
| morphing-rose · offset · soft 1.5 | 1 | -13.7 | 0.43 | 0.168 |
| morphing-rose · offset · soft 3 | 1 | -15.0 | 0.73 | 0.121 |
| perfect-fifth-equal · wide · raw | 2 | -4.7 | 0.09 | 0.256 |
| perfect-fifth-equal · wide · soft 3 | 2 | -17.3 | 0.09 | 0.083 |
| perfect-fifth-equal · offset · soft 1.5 | 1 | -13.7 | 0.24 | 0.088 |
| perfect-fifth-equal · offset · soft 3 | 1 | -17.3 | 0.23 | 0.054 |
| perfect-fifth-just · wide · raw | 2 | -0.7 | 0.00 | 0.054 |
| perfect-fifth-just · wide · soft 3 | 4 | -14.1 | 0.00 | 0.055 |
| perfect-fifth-just · offset · soft 1.5 | 1 | -12.9 | 0.14 | 0.024 |
| perfect-fifth-just · offset · soft 3 | 1 | -17.8 | 0.20 | 0.019 |
| rose · wide · raw | 3 | -1.6 | 0.00 | 0.001 |
| rose · wide · soft 3 | 3 | -9.7 | 0.00 | 0.001 |
| rose · offset · soft 1.5 | 2 | -14.9 | 0.08 | 0.001 |
| rose · offset · soft 3 | 2 | -17.6 | 0.07 | 0.001 |

## Findings

1. **Softness works.** Raw, the thin lit lines give spiky tables falling 1 to 5 dB an
   octave: buzzy, as predicted. Softened by three cells they fall 10 to 17 dB an octave.
2. **A centred path plays a symmetric figure out of tune.** A figure with k-fold symmetry
   read from its centre repeats k times a lap, so the note sounds k times too high: the
   three-petalled rose read from its centre gives harmonic 3 as its lowest, and the just
   fifth harmonic 4. This was not foreseen, and it breaks the plan's promise that the
   picture cannot put you out of tune unless Scan is designed around it.
3. **An off-centre path fixes it for five of the six.** Their fundamental becomes the
   strongest harmonic, at 14-95% of the energy. The rose, the most symmetric, still leans
   on its second harmonic: Scan needs either a larger offset or a correction that divides
   the read rate by the symmetry it detects.
4. **A still picture gives a still table.** The just fifth, the rose and the harmonograph
   change by under 6% between frames; the equal fifth and the morphing rose by 5-30%. The
   pictures that move are the ones that sound alive, as the plan expected.

## Round one, heard

All six pictures have potential, and every one was jarring. Raw it was terrible (the
morphing rose raw and softened especially); the off-centre, softer takes had the right
feel, the moving ones most, and the jarring carried over into them. The kaleidoscope was
the most promising.

## Round two: where the jarring comes from

```
python3 scan2.py grids/ out2/
```

Two causes were in how round one made the sound, not in the pictures. Each frame's table
was crossfaded whole into the next sixty times a second, and evened in level on its own,
so any change in the picture stepped the note at 60 Hz. And a path across thin lit lines
reads sharp pulses, which stand the harmonics in a jagged comb. `scan2.py` plays each
picture's off-centre, softer reading four ways, each adding one fix: **A** as round one
made it; **B** eased, every harmonic's level gliding to the picture's over 150 ms at a
fixed phase on a bank of oscillators; **C** B with the comb smoothed across neighbouring
harmonics and 3 dB an octave more fall; **D** C at equal level with the default tone.
Each plays A2 for a second, then an A minor chord for two.

*Grain* is how much the sound's spectrum steps from one picture frame to the next while
the single note is held; the default tone alone reads 0.0007.

| Picture | A | B | C | D |
|---|---|---|---|---|
| Morphing rose | 0.153 | 0.030 | 0.020 | 0.012 |
| Perfect fifth, equal | 0.067 | 0.020 | 0.014 | 0.009 |
| Kaleidoscope | 0.013 | 0.001 | 0.001 | 0.001 |
| Harmonograph | 0.013 | 0.006 | 0.005 | 0.003 |
| Perfect fifth, just | 0.026 | 0.004 | 0.003 | 0.002 |
| Rose | 0.004 | 0.002 | 0.002 | 0.002 |

Easing cuts the grain two to eight times on every picture, most on the two that move.
Whether that is the jarring the owner heard is for the second listening page.

## The decision

The numbers say a softened, off-centre scan makes tables in a musical range, in tune for
most figures. Whether they *sound* good is a judgement for ears, not numbers: the renders
are on a listening page made for the owner, and the go or no-go is recorded in the plan
once they have been heard.
