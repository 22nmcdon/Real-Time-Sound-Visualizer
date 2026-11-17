# What reaches the sound

The owner noticed on 17 Nov that the Zoom changes the sound a great deal. It should not have been
a surprise: Scan and the three reads take in the light as it is drawn on the 64 by 64 grid, so
anything that changes how the figure is drawn - where it sits, how large, how long a window, how
it is turned, how bright - changes what they read, and through them the sound. This is that
measured for every control on the face rather than guessed, by `web/tools/reach_audit.py`.

## How it was measured

Two passes. In the browser, the page opened as a player opens it with the worklet running, and
every message the page posts to the instrument caught on its way (as `braintest.py` catches them);
on each figure every control was moved to two other values, one at a time, and what it sent was
kept, with the setup code the page would save after it. The plugin's editor sends the same
messages, so this is what the plugin hears too. A control that sends nothing and leaves the code
as it was cannot reach the instrument at all, and is *look-only* by construction.

Then the core. For each control and value that sent anything, the instrument was rendered offline
(`core/tests/tools/render_cpp.cpp`) from the figure's code with the messages handed over before the
first note - and again loaded from the code the change left, where that differs - with a chord held
4.5 seconds, against the figure rendered without them. The held part, 1.5 to 4.5 s, is compared:
the spectrum's distance (`honestytest.py`'s fifth-octave band shares, window against window, a
mean; 0.02 is about what a Breathing preset moves in a quarter second), and the difference's RMS
against the sound's in dB. The engine is deterministic, so the null under every reading is the
base rendered twice, which reads the same to the bit; and a control that cannot reach the sound
reads exactly nothing, which the look-only rows below are.

The figures: a Settled preset (Tine piano), a Breathing one (Slow pad) and a two-hands split (Bass
under the pad), each at Scan 60 and Picture 80, each in X-Y and in Y-T. Six figures, two values a
control. *Measured change* is the largest of those readings, with the figure and the value it was
found at; *figures* lists every figure on which the control changed the sound at all.

The classes:

- **sound by design** - a control of the sound (the Generator, the envelopes, the rack, the
  Picture section), which changes it as it should.
- **REACHES THE SOUND THROUGH THE PICTURE** - a control of the view or the look (the screen's
  toolbar, Scope & measure, the Beam, Enlarge's options, This window) that measurably changes the
  sound, because it changes what is drawn on the grid Scan reads.
- **look-only** - a view or face control that reads nought on every figure: it sends the
  instrument nothing, or nothing it acts on.
- **idle here** - a sound control that sent its message but changed nothing on these six figures
  (a module's knob while the module is off, the second hand's controls with one hand).
- **face only** - sends nothing and changes no code, and is not a view control: it arranges the face.
- **not moved** - each with why: it loads a sound, needs a device, or is not a setting.

The host's parameters (`kKnobs` in `plugin/src/PluginProcessor.h`) are the sliders marked *(host)*:
each is the slider by its id, so its row is its measure.

## The table

<!-- table: written by web/tools/reach_audit.py -->

354 controls. REACHES THE SOUND THROUGH THE PICTURE 45; sound by design 102; idle here 81; look-only 69; face only 9; not moved 48. The null: each figure's base rendered twice, the same to the bit on all six.

| id | control | home | class | measured change (most, held part) | figures | info line now | right? |
|---|---|---|---|---|---|---|---|
| `rotate` | Turn | bench/plane | REACHES THE SOUND THROUGH THE PICTURE | 0.363 spectrum, &minus;3 dB difference (split-xy at -25) | breathing xy, breathing yt, settled xy, settled yt, split xy | Turns the figure on the screen, and Scan reads it turned, so the sound changes with it whatever Speakers get is set to. | yes, since 17 Nov: before it did not say the sound moves |
| `acCorner` | AC corner | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.148 spectrum, &minus;10 dB difference (breathing-xy at 54) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Where AC coupling starts taking things away, 0.5 to 20 Hz, in what Scan reads too. Ten removes a drift; twenty thins a bass note’s bottom. | yes, since 17 Nov: before it did not say the sound moves |
| `ch1Ac` | AC | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.160 spectrum, &minus;9 dB difference (breathing-xy at true) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Blocks what is not moving, so a DC offset cannot push this lane off the screen. Scan reads the lane coupled, so the sound changes too. | yes, since 17 Nov: before it did not say the sound moves |
| `ch1Offset` | Offset | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.516 spectrum, &minus;0 dB difference (settled-yt at -50) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Moves this lane’s trace up or down the screen, and in X–Y the figure along its axis. Scan reads it where it is drawn, so the sound moves too. | yes, since 17 Nov: before it did not say the sound moves |
| `ch1On` | Show | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.631 spectrum, 4 dB difference (split-yt at false) | breathing yt, settled yt, split yt | Draws this lane in Y–T and gives it a row in the readouts. In Y–T Scan reads only the lanes drawn, so the sound changes too. | yes, since 17 Nov: before it did not say the sound moves |
| `ch1Scale` | Full scale | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.590 spectrum, &minus;1 dB difference (split-yt at 6) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | The level that reaches the top of the screen, 0 to −50 dBFS. Lower opens up a quiet signal; Scan reads the larger figure, so the sound changes. | yes, since 17 Nov: before it did not say the sound moves |
| `ch2Ac` | AC | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.187 spectrum, &minus;8 dB difference (breathing-xy at true) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Blocks what is not moving, so a DC offset cannot push this lane off the screen. Scan reads the lane coupled, so the sound changes too. | yes, since 17 Nov: before it did not say the sound moves |
| `ch2Offset` | Offset | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.580 spectrum, &minus;1 dB difference (split-yt at 60) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Moves this lane’s trace up or down the screen, and in X–Y the figure along its axis. Scan reads it where it is drawn, so the sound moves too. | yes, since 17 Nov: before it did not say the sound moves |
| `ch2On` | Show | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.607 spectrum, 2 dB difference (split-yt at false) | breathing yt, settled yt, split yt | Draws this lane in Y–T and gives it a row in the readouts. In Y–T Scan reads only the lanes drawn, so the sound changes too. | yes, since 17 Nov: before it did not say the sound moves |
| `ch2Scale` | Full scale | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.593 spectrum, &minus;0 dB difference (split-yt at 6) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | The level that reaches the top of the screen, 0 to −50 dBFS. Lower opens up a quiet signal; Scan reads the larger figure, so the sound changes. | yes, since 17 Nov: before it did not say the sound moves |
| `edgeFalling` | Falling | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.154 spectrum, &minus;8 dB difference (breathing-yt at on) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Starts the trace where the signal crosses the level going down. Scan reads the trace from there, so the edge changes the sound too. | yes, since 17 Nov: before it did not say the sound moves |
| `edgeRising` | Rising | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.154 spectrum, &minus;8 dB difference (breathing-yt at on); on in every figure, so measured as the change back from edgeFalling | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Starts the trace where the signal crosses the level going up. Scan reads the trace from there, so the edge changes the sound too. | yes, since 17 Nov: before it did not say the sound moves |
| `filterCutoff` | Cutoff | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.556 spectrum, &minus;3 dB difference (split-yt at 250) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Where the trace filter acts, 20 Hz to 20 kHz. Lower on a low pass rounds the trace’s corners and what Scan reads; a source on it sweeps. | yes, since 17 Nov: before it did not say the sound moves |
| `filterOn` | Filter the trace | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.274 spectrum, &minus;6 dB difference (split-yt at true) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Filters the trace, and so what Scan reads from it: a low pass rounds a square towards a sine. Heard directly only on Shaped. | yes |
| `filterRes` | Resonance | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.661 spectrum, 2 dB difference (split-yt at 80) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | A peak at the cutoff, in what Scan reads too: nought is gentle, a hundred rings. High, it can push the trace past full scale: Clipping. | yes, since 17 Nov: before it did not say the sound moves |
| `filterType` | Type | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.638 spectrum, 3 dB difference (split-yt at highpass) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Which part the trace filter keeps, and so what Scan reads: low pass the bottom, high pass the top, band pass a band; a notch carves one out. | yes, since 17 Nov: before it did not say the sound moves |
| `holdoff` | Holdoff | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.262 spectrum, &minus;3 dB difference (breathing-yt at 40) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Ignores an edge with another close behind it, up to 5 ms, which settles a wave that crosses the level twice a cycle. Scan reads the trace it settles. | yes, since 17 Nov: before it did not say the sound moves |
| `lag` | Delay | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.276 spectrum, &minus;4 dB difference (split-xy at 320) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How far behind the delayed copy is, 0.1 to 40 ms; Scan reads the loop it draws. Only on Set; on Auto it shows what the lock found. | yes, since 17 Nov: before it did not say the sound moves |
| `lagAuto` | Delay | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.312 spectrum, &minus;2 dB difference (split-xy at on); on in every figure, so measured as the change back from lagManual | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Sets the delay to a quarter of the note’s period, locked slowly: a pure tone draws a circle, vibrato turns it, and Scan reads it so. | yes, since 17 Nov: before it did not say the sound moves |
| `lagManual` | Delay | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.312 spectrum, &minus;2 dB difference (split-xy at on) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Holds the delay where its knob puts it, whatever the note. Scan reads the loop it draws, so the sound changes too. | yes, since 17 Nov: before it did not say the sound moves |
| `lagOn` | Lag X–Y | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.785 spectrum, 2 dB difference (split-yt at true) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Plots the signal against itself a moment later: one input draws a loop shaped by its harmonics, and Scan reads that loop, so the sound changes. | yes, since 17 Nov: before it did not say the sound moves |
| `layOver` | Layout | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.791 spectrum, 1 dB difference (split-yt at on) | split yt | In Y–T, every lane on one graticule: how the lanes line up against each other. Scan reads them as drawn, so the sound changes too. | yes, since 17 Nov: before it did not say the sound moves |
| `layStack` | Layout | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.791 spectrum, 1 dB difference (split-yt at on); on in every figure, so measured as the change back from layOver | split yt | In Y–T, each lane in its own strip with its name: what each part is doing. Scan reads the strips as drawn, so the sound changes too. | yes, since 17 Nov: before it did not say the sound moves |
| `level` | Trigger level | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.323 spectrum, &minus;5 dB difference (split-yt at -500) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How high the signal must cross to start the trace, as a share of full scale: the dashed rose line. Scan reads the trace from there, so the sound too. | yes, since 17 Nov: before it did not say the sound moves |
| `midSide` | Mid / side | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.234 spectrum, &minus;5 dB difference (breathing-xy at true) | breathing xy, breathing yt, settled xy, settled yt | Draws the sum and the difference of a stereo pair in place of left and right: the figure turned 45°, as Scan reads it. Turns Lag X–Y off. | yes, since 17 Nov: before it did not say the sound moves |
| `position` | Position | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.214 spectrum, &minus;6 dB difference (breathing-yt at 80) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How much of the screen shows what came before the trigger. At 10%, a tenth. Scan reads the window it frames, so the sound changes too. | yes, since 17 Nov: before it did not say the sound moves |
| `seeDry` | Screen reads | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.274 spectrum, &minus;6 dB difference (split-yt at on) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | The screen, and so Scan, reads the signal as it came in, before the filter, the AC coupling and the turn. The readout says so. | yes, since 17 Nov: before it did not say the sound moves |
| `seeWet` | Screen reads | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.274 spectrum, &minus;6 dB difference (split-yt at on); on in every figure, so measured as the change back from seeDry | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | The screen, and so Scan, reads the signal after the filter, the AC coupling and the turn. | yes, since 17 Nov: before it did not say the sound moves |
| `trigSource0` | Source | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.149 spectrum, &minus;10 dB difference (breathing-xy at on); on in every figure, so measured as the change back from trigSource1, trigSource2, trigSource3 | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Takes the trigger from the first lane. Every lane is cut at that lane’s edge, so they stay in step, and Scan reads them cut there. | yes, since 17 Nov: before it did not say the sound moves |
| `trigSource1` | Source | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.149 spectrum, &minus;10 dB difference (breathing-xy at on) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Takes the trigger from the second lane. Every lane is cut at that lane’s edge, so they stay in step, and Scan reads them cut there. | yes, since 17 Nov: before it did not say the sound moves |
| `xyX` | X–Y pair | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.188 spectrum, &minus;7 dB difference (breathing-xy at 1) | breathing xy, settled xy | Which lane is drawn across, the figure’s X, and so what Scan reads. The goniometer follows the same pair. | yes, since 17 Nov: before it did not say the sound moves |
| `xyY` | X–Y pair | measure/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.188 spectrum, &minus;7 dB difference (breathing-xy at 0) | breathing xy, settled xy | Which lane is drawn upward, the figure’s Y, and so what Scan reads. One lane against itself draws a diagonal line. | yes, since 17 Nov: before it did not say the sound moves |
| `beamLevel` | Intensity | picture/pictureBar | REACHES THE SOUND THROUGH THE PICTURE | 0.224 spectrum, &minus;7 dB difference (split-xy at off) | breathing xy, settled xy, split xy | How much the trace dims where it moves fast, as a real beam does: bright at the turns, faint in the sweeps. Scan reads the dimming too. | yes |
| `beamXY` | X–Y | picture/pictureBar | REACHES THE SOUND THROUGH THE PICTURE | 0.224 spectrum, &minus;7 dB difference (split-xy at false) | breathing xy, settled xy, split xy | Lets Intensity dim the X–Y figure where it moves fast. Unticked, the whole figure is full ink, and Scan reads it that way. | yes |
| `beamYT` | Y–T waveform | picture/pictureBar | REACHES THE SOUND THROUGH THE PICTURE | 0.147 spectrum, &minus;9 dB difference (breathing-yt at true) | breathing yt, settled yt, split yt | Lets Intensity dim the waveform where it moves fast, and Scan reads the dimming. Off to start: dimming a square’s steep edge hides what Y–T shows. | yes, since 17 Nov: before it did not say the sound moves |
| `clearButton` | Clear | -/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.104 spectrum, &minus;11 dB difference (breathing-xy at pressed); pressed two seconds into the chord | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Wipes the screen and the light Scan and the photocell read, so the picture builds up again from nothing. Persistence stays as set. | yes |
| `dispSpect` | Spect | -/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.678 spectrum, 0 dB difference (split-yt at on) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Frequency up, time running right to left, loudness as ink. Scan and the picture read nothing here, so the tone keeps its last wave. | yes |
| `dispXY` | X–Y | -/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.918 spectrum, 2 dB difference (split-yt at on) | breathing yt, settled yt, split yt | The left channel against the right, drawn as one figure: the picture Scan is made to read. Turns Persistence on if it was off. | yes |
| `dispYT` | Y–T | -/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.918 spectrum, 1 dB difference (split-xy at on) | breathing xy, settled xy, split xy | Each channel drawn against time, as a waveform. Scan reads the waveform as it is drawn, so the timebase moves the tone too. | yes |
| `modeAuto` | Auto | -/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.677 spectrum, 0 dB difference (split-yt at on); on in every figure, so measured as the change back from modeNormal, modeSingle | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Draws whatever arrives, triggered or not, so the trace never stops and Scan reads it all. A grey trace is free-running, not a fault. | yes, since 17 Nov: before it did not say the sound moves |
| `modeNormal` | Normal | -/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.677 spectrum, 0 dB difference (split-yt at on) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Holds the last triggered picture while nothing crosses the level, rather than drawing an untriggered one. Scan reads the held picture. | yes, since 17 Nov: before it did not say the sound moves |
| `modeSingle` | Single | -/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.042 spectrum, &minus;15 dB difference (settled-xy at on) | settled xy | Waits for one edge, draws it and stops: how to catch a transient. Scan reads the stopped picture, so the tone stands. Run arms it again. | yes, since 17 Nov: before it did not say the sound moves |
| `run` | Stop | -/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.677 spectrum, 0 dB difference (split-yt at pressed) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Holds the trace and the picture the sound reads, so the tone stands while notes sound on. Also silences the score and ends every MIDI note sent. | yes |
| `timebase` | Timebase | -/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.359 spectrum, &minus;2 dB difference (breathing-yt at 2) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How much time the screen holds, from a millisecond to half a second across. Scan reads what it holds, in X–Y as in Y–T, so the sound changes too. | yes, since 17 Nov: before it did not say the sound moves |
| `zoom` | Zoom | -/bench | REACHES THE SOUND THROUGH THE PICTURE | 0.646 spectrum, 0 dB difference (split-yt at 19) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Magnifies: in Y–T a slice around the trigger, in X–Y the figure, on the spectrogram the band. Scan reads it as drawn, so the sound changes too. | yes, since 17 Nov: before it did not say the sound moves |
| `amp` (host) | Level | bench/bench | sound by design | 0.753 spectrum, 1 dB difference (split-yt at 112) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How loud the generator plays, and so how large it draws its figure and what Scan reads. Each hand’s, or both while the Generator is linked. | - |
| `barsUse` | Use drawbars | bench/bench | sound by design | 0.902 spectrum, 4 dB difference (breathing-yt at pressed) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Puts the Shape on Drawbars, so the bars below are heard. Until then they are greyed and move nothing. | - |
| `chorusMix` | Mix | bench/chorus | sound by design | 0.397 spectrum, &minus;4 dB difference (split-xy at 80) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How much chorus you hear; nought is off. A late copy of the pair whose lateness swings, so the figure breathes and turns. | - |
| `delayFeedback` | Feedback | bench/delay | sound by design | 0.157 spectrum, &minus;11 dB difference (split-yt at 72) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How many times each repeat comes back. Stops at 0.9, so it always dies away, and no source can be patched onto it. | - |
| `delayLowCut` | Low cut | bench/delay | sound by design | 0.164 spectrum, &minus;9 dB difference (breathing-xy at 80) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Thins each repeat on its way round, up to 1 kHz, so each comes back thinner than the last. At nought it is off. | - |
| `delayMix` (host) | Mix | bench/delay | sound by design | 0.590 spectrum, &minus;2 dB difference (split-xy at 80) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How loud the repeats are; nought is off. In X–Y they are ghost figures trailing the live one. | - |
| `delayMs` | Time | bench/delay | sound by design | 0.292 spectrum, &minus;6 dB difference (split-yt at 1602) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How long before each repeat, up to two seconds. Greyed while Sync follows the tempo; a source on it bends the repeats’ pitch, like tape. | - |
| `delayPingPong` | Ping-pong | bench/delay | sound by design | 0.137 spectrum, &minus;11 dB difference (breathing-xy at true) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Sends each repeat to the other side, so the ghost figures alternate between the figure and its reflection across the diagonal. | - |
| `delaySync` | Sync | bench/delay | sound by design | 0.300 spectrum, &minus;6 dB difference (breathing-yt at 1/4) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Free, or the time as a note value of the tempo in Perform, following it when it moves. While it is synced, Time is greyed. | - |
| `delayTone` | Tone | bench/delay | sound by design | 0.139 spectrum, &minus;10 dB difference (breathing-xy at 80) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Darkens each repeat on its way round, so each comes back duller than the last. At the top it is open and changes nothing. | - |
| `delayWidth` | Width | bench/delay | sound by design | 0.153 spectrum, &minus;8 dB difference (breathing-xy at 160) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How far apart the repeats are heard. At nought they collapse to a line on the diagonal; at 100% as played; at 200% twice as wide. | - |
| `delayWow` | Wow | bench/delay | sound by design | 0.257 spectrum, &minus;7 dB difference (split-yt at 80) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Drifts the delay time slowly, as a tape’s speed drifts, so each repeat is a little off pitch and its ghost figure turns. | - |
| `envAttack` | Attack | bench/bench | sound by design | 0.154 spectrum, &minus;9 dB difference (breathing-xy at 50) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How long a note takes to reach full level once its key goes down, and the figure grows with it. Between notes the generator is silent. | - |
| `envDecay` | Decay | bench/bench | sound by design | 0.131 spectrum, &minus;10 dB difference (breathing-xy at 251) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How long a note takes to fall from its peak to the sustain level. Short, with a low sustain, is a pluck. | - |
| `envSustain` | Sustain | bench/bench | sound by design | 0.711 spectrum, 2 dB difference (split-yt at 25) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | The level a note holds while its key stays down, as a share of its peak. At nought every note dies away on its own. | - |
| `eqHigh` | High | bench/eq | sound by design | 0.132 spectrum, &minus;11 dB difference (breathing-xy at 72) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Lifts or cuts everything above the high shelf’s corner, up to 12 dB either way: air over the sound, or a darker one with softer corners. |  |
| `eqLow` | Low | bench/eq | sound by design | 0.415 spectrum, &minus;0 dB difference (breathing-yt at 72) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Lifts or cuts everything below the low shelf’s corner, up to 12 dB either way: weight under the sound, the figure longer at its lowest notes. |  |
| `eqMid` | Mid | bench/eq | sound by design | 0.440 spectrum, &minus;4 dB difference (settled-yt at 72) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Lifts or cuts a band around Mid at, as wide as Width, up to 12 dB either way: a boost brings that part forward, a cut hollows it out. |  |
| `glide` | Glide | bench/bench | sound by design | 0.512 spectrum, &minus;1 dB difference (settled-xy at 125) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How long each new note slides from the last note's pitch rather than stepping; off at nought. In Poly every note of a chord slides from there. | - |
| `linkAmpEnv` | Amp envelope’s link | bench/bench | sound by design | 0.128 spectrum, &minus;13 dB difference (split-yt at pressed) | split xy, split yt | Whether the amp envelope is the same in both hands or this hand’s own. Unlinking starts the other hand as a copy; linking copies this one over it. | - |
| `linkDelay` | Delay’s link | bench/delay | sound by design | 0.068 spectrum, &minus;18 dB difference (split-yt at pressed) | split xy, split yt | Whether the delay is the same in both hands or this hand’s own. Unlinking starts the other hand as a copy; linking copies this one over it. | - |
| `linkGen` | Generator’s link | bench/bench | sound by design | 0.133 spectrum, &minus;12 dB difference (split-yt at pressed) | split xy, split yt | Whether the Generator is the same in both hands or this hand’s own. Unlinking starts the other hand as a copy; linking copies this one over it. | - |
| `linkPhaser` | Phaser’s link | bench/phaser | sound by design | 0.015 spectrum, &minus;28 dB difference (split-yt at pressed) | split xy, split yt | Whether the phaser is the same in both hands or this hand’s own. Unlinking starts the other hand as a copy; linking copies this one over it. | - |
| `linkPlane` | Plane’s link | bench/plane | sound by design | 0.025 spectrum, &minus;23 dB difference (split-yt at pressed) | split xy, split yt | Whether the Plane is the same in both hands or this hand’s own. Unlinking starts the other hand as a copy; linking copies this one over it. | - |
| `linkVcf` | Voice filter’s link | bench/bench | sound by design | 0.532 spectrum, &minus;1 dB difference (split-yt at pressed) | split xy, split yt | Whether the voice filter is the same in both hands or this hand’s own. Unlinking starts the other hand as a copy; linking copies this one over it. | - |
| `midiDrawCount` | Outline | bench/bench | sound by design | 0.220 spectrum, &minus;5 dB difference (breathing-yt at 4) | breathing xy, breathing yt, settled xy, settled yt | How many held notes make the figure's outline, for the hand being edited. The rest are drawn along the diagonal. | - |
| `midiDrawWhich` | Outline | bench/bench | sound by design | 0.200 spectrum, &minus;7 dB difference (breathing-xy at lowest) | breathing xy, breathing yt, settled xy, settled yt | Which notes make the outline: bass and melody, the lowest, the highest or the most recent. The lowest leans onto X, the rest onto Y. | - |
| `midiDyad` | Dyad | bench/bench | sound by design | 1.068 spectrum, 4 dB difference (split-yt at on) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Two held notes are the two channels, the lower on X, so the interval you play is the figure: a fifth stands still, a third walks. | - |
| `midiKindKey` | Key | bench/bench | sound by design | 0.766 spectrum, &minus;0 dB difference (breathing-yt at on) | breathing xy, breathing yt, settled xy, settled yt | Splits at a key: under it the lower hand, from it up the upper. Press a key on the strip to split there. | - |
| `midiKindLayer` | Layer | bench/bench | sound by design | 0.769 spectrum, 1 dB difference (breathing-yt at on) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Every note plays in both hands, A and B, so each is two voices at once. | - |
| `midiKindNotes` | Notes | bench/bench | sound by design | 0.659 spectrum, 1 dB difference (breathing-yt at on) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Splits by the notes held: the lowest (or highest) few are one hand, the rest the other, wherever you play them. | - |
| `midiLayerPair` | How the two hands are drawn | bench/bench | sound by design | 0.821 spectrum, 2 dB difference (split-yt at against) | split xy, split yt | A figure each, overlaid in their own inks, or A against B: one figure, A's notes on X and B's on Y. Every note is heard in both ears. | - |
| `midiLayers` | Layers | bench/bench | sound by design | 0.958 spectrum, 3 dB difference (split-yt at off) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Whether a second sound plays: one, a split at a key or by the notes held, or layered. The strip's Two hands and Key, Notes, Layer set it. | - |
| `midiMono` | Mono | bench/bench | sound by design | 1.182 spectrum, 3 dB difference (split-yt at on) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | The newest note sets the pitch and the Interval menu puts the second channel above it, so one finger plays the whole figure. | - |
| `midiPoly` | Poly | bench/bench | sound by design | 1.182 spectrum, 3 dB difference (split-yt at on); on in every figure, so measured as the change back from midiDyad, midiMono | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Every held note sounds, up to eight, each with its own envelope. Outline chooses which of them make the figure's outline. | - |
| `midiPolyJust` | Tune a chord | bench/bench | sound by design | 0.354 spectrum, &minus;1 dB difference (settled-yt at true) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Tunes each chord to whole-number ratios of its lowest note, so a major triad is 4:5:6 and its figure closes. Notes move a few cents to get there. | - |
| `midiSplitBy` | Split by | bench/bench | sound by design | 0.486 spectrum, 2 dB difference (split-yt at notes) | split xy, split yt | How a split gives each note its hand: at a key, or by the notes held, counted from one end. The strip's Key and Notes set it. | - |
| `midiTwoHands` | Two hands | bench/bench | sound by design | 0.958 spectrum, 3 dB difference (split-yt at pressed) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | In Poly, a second sound: Key, Notes or Layer on the strip then says how the hands share the notes. Off, every note plays the one sound. | - |
| `midiVelocityTo` | Velocity | bench/bench | sound by design | 0.617 spectrum, 2 dB difference (split-yt at fm) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How hard you play always sets a note's level and how brightly it strikes the screen. With FM, a harder note is also brighter in tone. | - |
| `oscBend` (host) | Warp | bench/bench | sound by design | 0.607 spectrum, 3 dB difference (split-yt at -50) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Bends the wave at one point of its cycle: up pinches it there, down swells it. The figure bulges or sharpens there and the tone brightens, in tune. | - |
| `oscFm` | FM | bench/bench | sound by design | 0.869 spectrum, 2 dB difference (split-xy at 80) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How far the second oscillator swings the voice's phase: pure at nought, then brighter, then bells and clangour. The figure gets busier with it. | - |
| `oscRatio` | Ratio | bench/bench | sound by design | 0.972 spectrum, 3 dB difference (settled-xy at 1.25) | settled xy, settled yt | The voice's second oscillator, as a ratio to the note, heard only through FM and Ring. A 3:2 sounds harmonic for the reason a 3:2 figure closes. | - |
| `oscRing` | Ring | bench/bench | sound by design | 0.646 spectrum, 4 dB difference (split-xy at 80) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Multiplies the voice by the second oscillator instead: at full the note itself goes, leaving the sum and difference tones. | - |
| `oscSub` | Sub | bench/bench | sound by design | 1.039 spectrum, 3 dB difference (settled-yt at 80) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How much of a square or sine an octave or two under the note is mixed in. It deepens the sound without making it louder. | - |
| `oscSync` | Sync | bench/bench | sound by design | 1.128 spectrum, 0 dB difference (breathing-xy at 660) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Runs the shape faster than the note and restarts it every note cycle, so the pitch stays and the tone tears. For the saw and square; off at 1×. | - |
| `oscUnison` | Unison | bench/bench | sound by design | 0.589 spectrum, 0 dB difference (breathing-yt at 3) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Stacks detuned copies of each note, so the sound thickens and the figure shimmers in place. | - |
| `phaserDepth` | Range | bench/phaser | sound by design | 0.024 spectrum, &minus;23 dB difference (split-yt at 25) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How far the sweep reaches, up to two and a half octaves either side of 700 Hz. At nought the notches stand still. | - |
| `phaserFeedback` | Resonance | bench/phaser | sound by design | 0.020 spectrum, &minus;23 dB difference (breathing-yt at 19) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Feeds the phaser back on itself to sharpen its two notches. Stops at 0.75 so it never rings on, and takes no source. | - |
| `phaserMix` (host) | Mix | bench/phaser | sound by design | 0.451 spectrum, &minus;3 dB difference (split-yt at 80) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How much phaser you hear; nought is off. It opens a line into a loop that widens and closes, and twists a figure unevenly. | - |
| `phaserRate` | Sweep | bench/phaser | sound by design | 0.028 spectrum, &minus;22 dB difference (split-yt at 129) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How fast the notches sweep, one channel on a sine and the other on its cosine: the pace at which the loop widens and closes. | - |
| `planeLimit` | Radial | bench/plane | sound by design | 0.444 spectrum, &minus;3 dB difference (breathing-xy at 2) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | What happens where the figure meets a circle of the Radius. Clip rounds loud parts off without bending the stereo image; Fold reflects them back in. | - |
| `planeMirror` | Mirror | bench/plane | sound by design | 0.799 spectrum, &minus;1 dB difference (split-xy at 1) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Folds the figure onto one half of itself; to the ear, the octave-up pedal, every harmonic even. The folded wave sits above zero. | - |
| `planeOS1` | Oversampling (1×) | bench/plane | sound by design | 0.162 spectrum, &minus;0 dB difference (breathing-xy at on) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | The bending ones at the sample rate: cheapest, and what they add above half of it folds back as stray notes out of the key. | - |
| `planeOS2` | Oversampling (2×) | bench/plane | sound by design | 0.636 spectrum, 1 dB difference (split-yt at on); on in every figure, so measured as the change back from planeOS1, planeOS4 | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | The bending ones at twice the sample rate, the default, so most of the stray tones they add are filtered off rather than folded back. | - |
| `planeOS4` | Oversampling (4×) | bench/plane | sound by design | 0.636 spectrum, 1 dB difference (split-yt at on) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Four times the sample rate: cleaner still on a hard clip or a high note, at twice the cost of 2×. Fold and Snap stay rough at any rate. | - |
| `planeScaleX` | Scale X | bench/plane | sound by design | 0.506 spectrum, &minus;1 dB difference (split-yt at 50) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | The left channel’s level, and the figure’s width. At nought the figure is an upright line and the left is silent; at two, double. | - |
| `planeScaleY` | Scale Y | bench/plane | sound by design | 0.502 spectrum, &minus;1 dB difference (split-yt at 160) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | The right channel’s level, and the figure’s height. At nought the figure lies flat and the right is silent; at two, double. | - |
| `planeShear` | Shear | bench/plane | sound by design | 0.460 spectrum, &minus;2 dB difference (split-yt at -50) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Leans the figure by feeding some of the right channel into the left; below nought it leans the other way. Exact, and adds no delay. | - |
| `planeSnap` | Snap | bench/plane | sound by design | 0.227 spectrum, &minus;6 dB difference (settled-xy at 5) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Puts both channels on a grid: a bitcrusher to the ear and pixels on the screen. Five bits is the coarser. | - |
| `planeTwist` (host) | Twist | bench/plane | sound by design | 0.546 spectrum, 2 dB difference (split-yt at -50) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Turns each point by more the further it is from the middle, so loud parts swirl and the quiet centre stays still: a stereo turn that follows level. | - |
| `reverbMix` (host) | Mix | bench/reverb | sound by design | 0.471 spectrum, &minus;5 dB difference (breathing-xy at 80) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How loud the tail is; nought is off. Past 0.2 it keeps a held chord moving: the screen goes on drawing the tail and Scan reading it. | - |
| `shape` | Shape | bench/bench | sound by design | 0.589 spectrum, 4 dB difference (breathing-yt at sine) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | The wave each note is made of. A sine is pure and draws smooth curves; sharper shapes are brighter and put corners in the figure. | - |
| `shpBits` | Crush | bench/bench | sound by design | 0.133 spectrum, &minus;10 dB difference (breathing-xy at 6) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Fewer levels for each sample, the stepped grit of a bitcrusher: the trace turns to a staircase. Off keeps every level. | - |
| `shpDrive` | Drive | bench/bench | sound by design | 0.630 spectrum, 3 dB difference (split-yt at 80) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Pushes the wave into a soft ceiling: a sine rounds towards a square, and so does its figure. The reading is how much quiet parts are lifted. | - |
| `shpFold` | Fold | bench/bench | sound by design | 0.880 spectrum, 3 dB difference (split-xy at 80) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Bends the wave back each time it would pass full scale: on Y–T the peaks fold inward, and in X–Y the figure grows petals. | - |
| `shpOS` | Oversampling | bench/bench | sound by design | 0.037 spectrum, &minus;22 dB difference (split-xy at 4) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How finely Drive and Fold are worked. Four times is cleaner for a hard drive on a high note and costs twice as much for every voice. | - |
| `shpRate` | Rate | bench/bench | sound by design | 0.147 spectrum, &minus;9 dB difference (breathing-xy at 11025) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Holds each sample longer, as a lower sample rate would, for the folded-back whine of a lo-fi sampler. Off is the full rate. | - |
| `vcfAtk` | Attack | bench/bench | sound by design | 0.053 spectrum, &minus;18 dB difference (split-xy at 250) | split xy, split yt | How long the filter's sweep takes to reach its height once a key goes down. Moves nothing while Envelope is at nought. | - |
| `vcfCut` (host) | Cutoff | bench/bench | sound by design | 0.923 spectrum, &minus;1 dB difference (settled-yt at 250) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Where the filter starts taking the top off. Lower is darker, and the figure gets rounder, since the harmonics that put corners in it go first. | - |
| `vcfDec` | Decay | bench/bench | sound by design | 0.063 spectrum, &minus;17 dB difference (split-xy at 1600) | split xy, split yt | How long the sweep takes to fall from its height to its sustain. Short gives each note a pluck or a wah. | - |
| `vcfEnvAmt` | Envelope | bench/bench | sound by design | 0.415 spectrum, &minus;2 dB difference (split-yt at -20) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How many octaves the filter's own envelope sweeps the cutoff, up or down, as each note starts. | - |
| `vcfRes` | Resonance | bench/bench | sound by design | 0.716 spectrum, 0 dB difference (settled-yt at 80) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How sharply the filter peaks at its cutoff. Higher rings at that pitch, and a sweep of the cutoff draws its ringing in the figure. | - |
| `vcfSus` | Sustain | bench/bench | sound by design | 0.266 spectrum, &minus;2 dB difference (split-yt at 80) | split xy, split yt | Where the sweep holds while the key is down, as a share of Envelope's octaves. At nought each note opens and closes again. | - |
| `vcfTrack` | Key track | bench/bench | sound by design | 0.752 spectrum, 2 dB difference (split-yt at 80) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How far the cutoff follows the note, from middle C. At 100 per cent a high note is as bright as a low one; at nought, high notes are duller. | - |
| `vcfType` | Type | bench/bench | sound by design | 0.711 spectrum, 1 dB difference (split-yt at 2) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Which filter is in every note: low pass darkens, high pass thins, band pass keeps a middle, notch takes one out. Off, the knobs below are idle. | - |
| `trigSource2` |  | measure/bench | sound by design | 0.078 spectrum, &minus;17 dB difference (split-yt at on) | split xy, split yt |  | - |
| `trigSource3` |  | measure/bench | sound by design | 0.078 spectrum, &minus;17 dB difference (split-yt at on) | split xy, split yt |  | - |
| `arpMode` | Arp | perform | sound by design | 0.689 spectrum, 3 dB difference (split-yt at down) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Plays a held chord a note at a time at the tempo: up, down, up and back, as played or at random. Letting go stops it. | - |
| `pictureFeel` | Rise, fall | picture/pictureBar | sound by design | 0.157 spectrum, &minus;9 dB difference (breathing-xy at slow) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How quickly the push comes and how slowly it goes: Snappy, Smooth or Slow, or Custom with a knob for each. | - |
| `pictureMovesA` | Pictures (Lower) | picture/pictureBar | sound by design | 0.210 spectrum, &minus;10 dB difference (split-xy at B) | split xy | Whose sound the lower hand’s picture moves through the Amount: its own, the upper’s, or both. A sound hearing two takes their average. | - |
| `pictureMovesB` | Pictures (Upper) | picture/pictureBar | sound by design | 0.180 spectrum, &minus;8 dB difference (split-xy at A) | split xy | Whose sound the upper hand’s picture moves through the Amount: its own, the lower’s, or both. Shown only while each hand draws a figure. | - |
| `pictureResponds` | Responds to | picture/pictureBar | sound by design | 0.269 spectrum, &minus;5 dB difference (breathing-xy at both) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | What the Amount’s push follows: Change flares at a new or harder gesture and settles; Level follows how much is lit; Both is a base with a flare. | - |
| `pictureSwell` | Swell | picture/pictureBar | sound by design | 0.376 spectrum, &minus;3 dB difference (split-yt at false) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | The picture breathing by itself while a chord is held, smoothly, at a rate the Persistence sets: slower as the light lingers. Off, a held chord rests. | - |
| `scanReadsA` | Reads (Lower) | picture/pictureBar | sound by design | 0.098 spectrum, &minus;14 dB difference (split-xy at B) | split xy | Whose picture the lower hand’s Scan reads: its own, the upper’s, or both averaged. Crossed, each hand’s tone comes from the other’s figure. | - |
| `scanReadsB` | Reads (Upper) | picture/pictureBar | sound by design | 0.099 spectrum, &minus;13 dB difference (split-xy at A) | split xy | Whose picture the upper hand’s Scan reads: its own, the lower’s, or both averaged. Shown only while each hand draws a figure of its own. | - |
| `scoreOn` | Play the picture | picture/pictureBar | sound by design | 0.674 spectrum, 1 dB difference (settled-yt at true) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Plays the screen as a score: a playhead crosses it at the tempo, low on the screen low in pitch, and the brightest points are the notes. | - |
| `fadeMode` | Fade | routings/bench | sound by design | 0.090 spectrum, &minus;12 dB difference (settled-yt at in) | settled xy, settled yt | Whether modulation eases in and out rather than arriving at once: a routing patched or taken off, a note struck or let go. | - |
| `linkPicture` | Picture’s link | -/pictureBar | sound by design | 0.161 spectrum, &minus;10 dB difference (split-yt at pressed) | split xy, split yt | Whether Amount, Scan and Strike are the same in both hands or each hand’s own. Softness and Persistence are the screen’s, shared. | - |
| `menvFollow` | Follows the amp envelope | -/bench | sound by design | 0.372 spectrum, &minus;5 dB difference (settled-yt at on); on in every figure, so measured as the change back from menvItsOwn | settled xy, settled yt | The Envelope rises and falls with Play’s amp envelope, whose curve it draws greyed: set it on Play. | - |
| `menvItsOwn` | Its own | -/bench | sound by design | 0.372 spectrum, &minus;5 dB difference (settled-yt at on) | settled xy, settled yt | Gives the Envelope four times of its own, one swell for the notes held, drawn over its knobs. | - |
| `menvOwn` | Its own | -/bench | sound by design | 0.372 spectrum, &minus;5 dB difference (settled-yt at true) | settled xy, settled yt | Gives the Envelope four times of its own, one swell for the notes held. Off, it follows Play’s amp envelope. | - |
| `oscScan` (host) | Scan | -/pictureBar | sound by design | 0.562 spectrum, &minus;2 dB difference (split-yt at 25) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How much of the voice’s wave is read off the screen, up to 80 per cent. A moving picture moves the tone; a still one is a still tone. | - |
| `output` (host) | Output | -/pictureBar | sound by design | 0.016 spectrum, &minus;1 dB difference (split-xy at 25) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How loud you hear it, after everything, and nothing else: the picture, Scan and the loop are the same at any setting. No preset changes it. | - |
| `persistence` | (hidden menu) | - | sound by design | 0.471 spectrum, &minus;2 dB difference (split-yt at 0) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Never shown, so never pointed at: the plugin's panel names it. The Persistence knob in the Picture section is the one people turn. | - |
| `pictureAmount` (host) | Amount | -/pictureBar | sound by design | 0.425 spectrum, &minus;2 dB difference (breathing-yt at 25) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How far the picture moves the sound by itself: its glow folds it, its motion echoes it, its memory turns it. At nought, a plain synthesiser. | - |
| `scanMemory` (host) | Persistence | -/pictureBar | sound by design | 0.441 spectrum, &minus;2 dB difference (split-yt at 55) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How long a stroke takes to fade to half, from off to infinite. Longer, and the tone, the picture’s reads and the score remember more. | - |
| `scanSoft` (host) | Softness | -/pictureBar | sound by design | 0.325 spectrum, &minus;4 dB difference (split-yt at 48) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How much the light is blurred before Scan reads it. At nought thin lines read as spikes and buzz; higher is rounder. Only while Scan is on. | - |
| `scanStrike` (host) | Strike | -/pictureBar | sound by design | 0.127 spectrum, &minus;11 dB difference (breathing-xy at 25) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How brightly each note lights the screen where Scan reads it. Higher, and every new note flares in the tone, then settles as the light fades. | - |
| `srcDetail-add` | Add a destination | -/bench | sound by design | 0.821 spectrum, 2 dB difference (breathing-xy at gen.freq) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | Puts this source on another control, from every one it can reach. Dragging its card onto a knob does the same. | - |
| `stereoWidth` (host) | Width | -/pictureBar | sound by design | 0.369 spectrum, &minus;0 dB difference (settled-yt at 25) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | How wide each note is heard: at nought every note the same in both ears, at a hundred each its own ring. No note moves as others join it. | - |
| `widthDrawn` | Drawn too | -/pictureBar | sound by design | 0.323 spectrum, &minus;5 dB difference (split-xy at on) | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | The Width is the sound's: the screen draws every note at it, so the speakers are the screen again, Scan reads it, and the setup keeps it. | - |
| `widthHeard` | Heard | -/pictureBar | sound by design | 0.323 spectrum, &minus;5 dB difference (split-xy at on); on in every figure, so measured as the change back from widthDrawn | breathing xy, breathing yt, settled xy, settled yt, split xy, split yt | The Width is yours and only how wide you hear: the screen draws the notes against each other, and the picture and Scan never hear it. | - |
| `bar0` | 16′ | bench/bench | idle here | nought (the same to the bit) | - | An octave under the note, the organ's deepest bar. Out at all, the wave repeats only every other cycle of the note, and so does the figure. | - |
| `bar1` | 5⅓′ | bench/bench | idle here | nought (the same to the bit) | - | A fifth above the note. Out at all, as with the 16′, the wave repeats only every other cycle of the note. | - |
| `bar2` | 8′ | bench/bench | idle here | nought (the same to the bit) | - | The note you play, as a sine. This bar alone at eight is a full-scale sine; adding others changes the colour, not the level. | - |
| `bar3` | 4′ | bench/bench | idle here | nought (the same to the bit) | - | An octave above the note, the second harmonic. Each bar draws out from nought to eight, about three decibels a step. | - |
| `bar4` | 2⅔′ | bench/bench | idle here | nought (the same to the bit) | - | An octave and a fifth above the note, the third harmonic. Upper bars brighten the tone and put finer turns in the figure's line. | - |
| `bar5` | 2′ | bench/bench | idle here | nought (the same to the bit) | - | Two octaves above the note, the fourth harmonic. | - |
| `bar6` | 1⅗′ | bench/bench | idle here | nought (the same to the bit) | - | Two octaves and a major third above the note, the fifth harmonic, which gives the organ its reedy edge. | - |
| `bar7` | 1⅓′ | bench/bench | idle here | nought (the same to the bit) | - | Two octaves and a fifth above the note, the sixth harmonic. | - |
| `bar8` | 1′ | bench/bench | idle here | nought (the same to the bit) | - | Three octaves above the note, the eighth harmonic. On the highest notes it is left out rather than folded back. | - |
| `chorusDepth` | Depth | bench/chorus | idle here | nought (the same to the bit) | - | How far the copy’s lateness swings either side of Centre. More is a wider wobble in pitch and a figure that breathes further. | - |
| `chorusFeedback` | Feedback | bench/chorus | idle here | nought (the same to the bit) | - | Feeds the copy back into itself, which makes the chorus a flanger: with a short Centre it rings at a pitch of its own. | - |
| `chorusRate` | Rate | bench/chorus | idle here | nought (the same to the bit) | - | How fast the copy’s lateness swings, one channel on a sine and the other on its cosine: the pace the figure breathes and turns at. | - |
| `chorusTime` | Centre | bench/chorus | idle here | nought (the same to the bit) | - | How late the copy sits, from 1 to 30 ms. Short, with Feedback up, it rings as a flanger; longer is a looser doubling. | - |
| `envRelease` | Release | bench/bench | idle here | nought (the same to the bit) | - | How long a note takes to fade once you let go of its key. The figure shrinks with it. | - |
| `eqHighFreq` | High at | bench/eq | idle here | nought (the same to the bit) | - | Where the high shelf turns, 1 to 16 kHz, four octaves on the knob: its middle is 4 kHz. The gain is half its full amount there. |  |
| `eqLowFreq` | Low at | bench/eq | idle here | nought (the same to the bit) | - | Where the low shelf turns, 40 to 640 Hz, four octaves on the knob: its middle is 160 Hz. The gain is half its full amount there. |  |
| `eqMidFreq` | Mid at | bench/eq | idle here | nought (the same to the bit) | - | The middle of the mid band, 125 Hz to 8 kHz, six octaves on the knob: its middle is 1 kHz. |  |
| `eqMidWidth` | Width | bench/eq | idle here | nought (the same to the bit) | - | How wide the mid band is, from a fifth of an octave, a narrow notch or peak, to four octaves, a broad tilt of the middle. |  |
| `freq` | Frequency | bench/bench | idle here | nought (the same to the bit) | - | The pitch: a note in Dyad or Mono sets it, and a turn moves the note held. On Y–T, higher puts more cycles on the screen. | - |
| `fxOrder` | Rack order | bench/bench | idle here | nought (the same to the bit) | - | Which of the phaser, chorus and delay comes first. Drag a module by its handle, or the arrow keys; the Plane and EQ stay first, the Reverb last. | - |
| `interval` | Interval | bench/bench | idle here | nought (the same to the bit) | - | The second channel against the first, in Mono; in Dyad the notes you play set it. Small whole-number ratios close the figure: a fifth is a still 2:3. | - |
| `linkChorus` | Chorus’s link | bench/chorus | idle here | nought (the same to the bit) | - | Whether the chorus is the same in both hands or this hand’s own. Unlinking starts the other hand as a copy; linking copies this one over it. | - |
| `linkEq` | EQ’s link | bench/eq | idle here | nought (the same to the bit) | - | Whether the EQ is the same in both hands or this hand’s own. Unlinking starts the other hand as a copy; linking copies this one over it. |  |
| `linkOsc` | Oscillator’s link | bench/bench | idle here | nought (the same to the bit) | - | Whether the oscillator is the same in both hands or this hand’s own. Unlinking starts the other hand as a copy; linking copies this one over it. | - |
| `linkReverb` | Reverb’s link | bench/reverb | idle here | nought (the same to the bit) | - | Whether the reverb is the same in both hands or this hand’s own. Unlinking starts the other hand as a copy; linking copies this one over it. | - |
| `linkShp` | Shaping’s link | bench/bench | idle here | nought (the same to the bit) | - | Whether the shaping is the same in both hands or this hand’s own. Unlinking starts the other hand as a copy; linking copies this one over it. | - |
| `midiBendRange` | Pitch bend | bench/bench | idle here | nought (the same to the bit) | - | How far the bend wheel takes every note, either way, in semitones. All the notes bend together, so the figure keeps its shape. | - |
| `midiEndHigh` | High | bench/bench | idle here | nought (the same to the bit) | - | By notes, counts from the top: the highest notes held are the upper hand, the rest the lower. | - |
| `midiHold` | Hold the interval | bench/bench | idle here | nought (the same to the bit) | - | In Dyad, a single note keeps the last interval above it, so one finger walks a figure up a melody. Off, one note is a unison. | - |
| `midiPressureTo` | Pressure | bench/bench | idle here | nought (the same to the bit) | - | What pressing harder on a held key moves, if your keyboard sends it: a vibrato, the Picture amount, Scan's depth, or nothing. | - |
| `midiSplitCount` | How many | bench/bench | idle here | nought (the same to the bit) | - | By notes, how many the counted hand takes, one to six. A press on the strip's places sets it. With fewer held, every note is its own. | - |
| `midiSplitEnd` | Counted | bench/bench | idle here | nought (the same to the bit) | - | By notes, which end is counted: the lowest notes held for the lower hand, or the highest for the upper. The strip's low and high set it. | - |
| `midiWheelTo` | Mod wheel | bench/bench | idle here | nought (the same to the bit) | - | What the mod wheel moves: a vibrato of up to a third of a semitone, the Picture amount, Scan's depth, or nothing. | - |
| `morph` | Morph | bench/bench | idle here | nought (the same to the bit) | - | One knob through sine, triangle, saw and square, crossfading each pair. Put a source on it and the tone and the figure change as you play. | - |
| `oscBendAt` | Warp at | bench/bench | idle here | nought (the same to the bit) | - | Where in the cycle Warp bends the wave, in degrees. Moves nothing while Warp is off; in X–Y, pulling the figure sets it. | - |
| `oscSpread` | Spread | bench/bench | idle here | nought (the same to the bit) | - | How far apart Unison's copies are tuned, in cents either way. Wider beats faster and smears the figure further. Idle while Unison is off. | - |
| `oscSubOct` | Sub octave | bench/bench | idle here | nought (the same to the bit) | - | Whether the sub sits one octave or two under the note. Idle while Sub is off. | - |
| `oscSubShape` | Sub shape | bench/bench | idle here | nought (the same to the bit) | - | The sub's wave: a square fills out the bottom with a buzz, a sine is a plain deep tone. Idle while Sub is off. | - |
| `phase` | Phase | bench/bench | idle here | nought (the same to the bit) | - | Where the second channel starts in its cycle against the first. At a unison, 0° draws a diagonal line and 90° a circle. Not for Poly's chords. | - |
| `planeRadius` | Radius | bench/plane | idle here | nought (the same to the bit) | - | Where the clip or fold acts, as a part of full scale. Smaller, and more of the figure meets the circle: quieter and more distorted. | - |
| `planeTurn` | Turn (upper) | bench/plane | idle here | nought (the same to the bit) | - | The upper hand’s own turn, in the Turn’s place while the Plane is that hand’s own: it turns the upper figure, and the lower’s stays. | - |
| `reverbPre` | Pre-delay | bench/reverb | idle here | nought (the same to the bit) | - | How long before the tail starts, up to 100 ms, so a note’s attack is heard clear of it. | - |
| `reverbSize` | Size | bench/reverb | idle here | nought (the same to the bit) | - | How long the tail takes to fall away, from 0.3 to 9 seconds. Longer leaves a longer trail of where the figure has been. | - |
| `reverbSpread` | Spread | bench/reverb | idle here | nought (the same to the bit) | - | At nought both channels get the same tail and the figure survives it. Up, each gets its own, an ordinary stereo reverb, and the figure clouds over. | - |
| `reverbTone` | Tone | bench/reverb | idle here | nought (the same to the bit) | - | How dark the tail is: lower takes more of the top off it, down to 500 Hz. At the top it is open. | - |
| `table` | Position | bench/bench | idle here | nought (the same to the bit) | - | Where the wavetable sits among its four drawn cycles, crossfading the two either side. Put a source on it and the timbre travels. | - |
| `tuneEqual` | Equal | bench/bench | idle here | nought (the same to the bit) | - | Takes the keys as an equal-tempered piano has them, a little off the ratios, so the figure turns at the rate the interval beats. | - |
| `vcfRel` | Release | bench/bench | idle here | nought (the same to the bit) | - | How long the cutoff takes to come back once you let go of the key. | - |
| `width` | Width | bench/bench | idle here | nought (the same to the bit) | - | How much of each cycle the pulse is up, 5 to 95 per cent. At 50 it is the square; narrower is thinner and more nasal. | - |
| `arpOctaves` | Arp octaves | perform | idle here | nought (the same to the bit) | - | How many octaves the arpeggio spreads the chord over, from one to three. | - |
| `arpRate` | Arp step | perform | idle here | nought (the same to the bit) | - | How long each step of the arpeggio is, at the tempo: from a crotchet (1/4) to a semiquaver triplet (1/16t). | - |
| `keyRoot` | Key | perform | idle here | nought (the same to the bit) | - | The page’s one key, which the quantiser and the score play in. | - |
| `keyScale` | Scale | perform | idle here | nought (the same to the bit) | - | Which notes of the key count: Chromatic (every semitone), major, minor or one of the modes. The quantiser and the score use it. | - |
| `morphPos` (host) | Morph | perform | idle here | nought (the same to the bit) | - | Slides the whole sound between the two stored ends: pitch by octaves, every other knob in a straight line. Menus, switches and the scope’s view stay. | - |
| `morphStoreA` | Morph · store A | perform | idle here | nought (the same to the bit) | - | Stores every knob as the fader’s left end, and puts the fader there. Store, change the sound, store the other end, then slide. | - |
| `morphStoreB` | Morph · store B | perform | idle here | nought (the same to the bit) | - | Stores every knob as the fader’s right end, and puts the fader there, so storing moves nothing you hear. | - |
| `quantise` | Quantise | perform | idle here | nought (the same to the bit) | - | Moves the generator’s pitch, after everything patched onto it, to the nearest note of the key: an LFO on the frequency plays a melody. | - |
| `quantiseGlide` | Glide | perform | idle here | nought (the same to the bit) | - | How long the quantised pitch takes to slide to each new note, up to 300 ms; off, it steps. Only while Quantise is on. | - |
| `tempo` | Tempo | perform | idle here | nought (the same to the bit) | - | The page’s one tempo, 30 to 300 BPM: the arpeggiator, the score and every synced LFO or delay play at it. | - |
| `transportPlay` | Bar | perform | idle here | nought (the same to the bit) | - | Stops the bar and silences the score; pressed again, starts it from the one and restarts the synced oscillators with it. | - |
| `pictureFall` | Fall | picture/pictureBar | idle here | nought (the same to the bit) | - | How long the push takes to go when the picture asks for less. Longer, and a swell outlasts the playing that made it. | - |
| `pictureRise` | Rise | picture/pictureBar | idle here | nought (the same to the bit) | - | How long the push takes to come when the picture asks for more. Shown with Custom. | - |
| `scoreLow` | From | picture/pictureBar | idle here | nought (the same to the bit) | - | The note at the bottom of the screen. The rows go up from it in the page’s key. | - |
| `scoreOctaves` | Octaves | picture/pictureBar | idle here | nought (the same to the bit) | - | How many octaves the screen’s height covers, up from the bottom note. More octaves, wider leaps from the same picture. | - |
| `scoreStep` | Step | picture/pictureBar | idle here | nought (the same to the bit) | - | How long the playhead stays on each column of the screen, as a note value at the tempo. Shorter, and the melody runs faster. | - |
| `scoreVoices` | Notes a step | picture/pictureBar | idle here | nought (the same to the bit) | - | The most notes a step plays: the brightest points in the column, loudest first. One note is a melody; more are chords. | - |
| `fadeLoop` | Loop | routings/bench | idle here | nought (the same to the bit) | - | Sends the fade’s attack and decay round again and again for as long as a note is held. | - |
| `fadeRestart` | Restart | routings/bench | idle here | nought (the same to the bit) | - | Runs the fade’s envelope again, from where it is, on every note you strike. | - |
| `inputDepth` |  | settings | idle here | nought (the same to the bit) | - |  | - |
| `inputMode` |  | settings | idle here | nought (the same to the bit) | - |  | - |
| `midiSplitWindow` | Chord window | settings | idle here | nought (the same to the bit) | - | Split by notes, every note waits this many ms so a chord struck at once is dealt by pitch. 0 plays at once. | - |
| `keysVelocity` | Velocity | -/screenKeys | idle here | nought (the same to the bit) | - | How hard the on-screen keys and the typed letters play: louder, and a brighter strike on the screen where Scan reads. | - |
| `lfoRate0` | Rate | -/bench | idle here | nought (the same to the bit) | - | How fast the LFO sweeps, from 0.01 to 8 cycles a second. Greyed while Sync locks it to the tempo. | - |
| `lfoShape0` | Shape | -/bench | idle here | nought (the same to the bit) | - | The wave the LFO sweeps with. Ramp rises and drops back; Random jumps to a new level each cycle and holds it. | - |
| `lfoSync0` | Sync | -/bench | idle here | nought (the same to the bit) | - | Free runs at Rate; a note value locks the LFO to the tempo, and it starts again on the beat. | - |
| `menvAtk` | Attack | -/bench | idle here | nought (the same to the bit) | - | How long the Envelope takes to rise when it starts, up to two seconds. Greyed while it follows the amp envelope. | - |
| `menvDec` | Decay | -/bench | idle here | nought (the same to the bit) | - | How long it takes to fall from the top to Sustain, up to four seconds. Greyed while it follows the amp envelope. | - |
| `menvRel` | Release | -/bench | idle here | nought (the same to the bit) | - | How long it takes to fall to nought after the last key lifts, up to four seconds. Greyed while it follows the amp envelope. | - |
| `menvSus` | Sustain | -/bench | idle here | nought (the same to the bit) | - | Where it rests while notes are held, from nought to the top. Greyed while it follows the amp envelope. | - |
| `photoButton` | On | -/bench | idle here | nought (the same to the bit) | - | Puts a light sensor on the screen, landing on the figure; drag its reticle there to aim it. Off, it reads nought. | - |
| `soundWidth` | Width | -/pictureBar | idle here | nought (the same to the bit) | - | The sound's own Width, saved with it, while the Width is on what's drawn too: the screen draws every note at it, and you hear what's drawn. | - |
| `midiStripDown` | Down an octave | bench/bench | look-only | nought (the same to the bit) | - | Moves the strip's view down an octave, to see or split at a lower key. It changes what is shown, never the sound. | yes |
| `midiStripUp` | Up an octave | bench/bench | look-only | nought (the same to the bit) | - | Moves the strip's view up an octave, to see or split at a higher key. It changes what is shown, never the sound. | yes |
| `midiWindowGo` | Chord window | bench/bench | look-only | nought (the same to the bit) | - | Goes to the Chord window, in Settings' MIDI: how long every note waits, split by notes, so a chord is dealt by pitch. | yes |
| `ch3Ac` |  | measure/bench | look-only | nought (the same to the bit) | - |  | yes |
| `ch3On` |  | measure/bench | look-only | nought (the same to the bit) | - |  | yes |
| `ch4Ac` |  | measure/bench | look-only | nought (the same to the bit) | - |  | yes |
| `ch4On` |  | measure/bench | look-only | nought (the same to the bit) | - |  | yes |
| `cursorsOn` | Cursors | measure/bench | look-only | nought (the same to the bit) | - | Two time and two level cursors to drag on the Y–T screen; the readout gives each pair’s difference, and Δt as a frequency. | yes |
| `hearDry` | Speakers get | measure/bench | look-only | nought (the same to the bit); on in every figure, so measured as the change back from hearWet | - | The speakers get the signal as it came in: the filter, the AC coupling and the turn change the picture, and the sound only through Scan. | yes, since 17 Nov: before it did not say the sound moves |
| `hearWet` | Speakers get | measure/bench | look-only | nought (the same to the bit); measured with the trace filter on: the generator's sound is the same to the bit; a live input was not played | - | The speakers get the trace after the filter, the AC coupling and the turn, all after the instrument's limiter, so a resonant trace can be loud. | no: measured nought on the generator with the filter on (see below) |
| `lagMix` | Heard | measure/bench | look-only | nought (the same to the bit); measured with Lag X-Y on: the same to the bit; a live input was not played | - | How much of the delayed copy reaches the right speaker when the speakers get Shaped: a comb that follows the pitch. Up to 50%. | no: measured nought on the generator with Lag X-Y on (see below) |
| `measurePost` | Numbers read | measure/bench | look-only | nought (the same to the bit) | - | The numbers read the signal after the Plane’s Turn, as the screen shows it. The level meter and Clipping stay on the signal. | yes |
| `measurePre` | Numbers read | measure/bench | look-only | nought (the same to the bit); on in every figure, so measured as the change back from measurePost | - | The numbers read the signal as it arrived, before the Plane’s Turn. | yes |
| `midiFollow` | … and the timebase | measure/bench | look-only | nought (the same to the bit); sends nothing when a note moves the page's timebase (measured with a note held): the instrument's stays | - | Also sets the timebase from the note: about four periods of the lowest note held, so the wave keeps its size as you play. | half: the screen's timebase follows, the instrument's does not (see below) |
| `midiTruth` | Lag and tuner from the note | measure/bench | look-only | nought (the same to the bit) | - | Takes the pitch from the key you play, for the Auto lag and the tuner, rather than estimating it from the sound. | yes |
| `readoutsOn` | Readouts under the screen | measure/bench | look-only | nought (the same to the bit) | - | Shows the numbers under the screen, a row per lane: peak, RMS, frequency, the nearest note, THD. Off to start. | yes |
| `bInk` | The upper hand’s ink | picture/pictureBar | look-only | nought (the same to the bit) | - | The colour of the upper hand’s figure while each hand draws one: its lane’s ink to start, or one you choose. Only the look. | yes |
| `beamGoni` | Goniometer | picture/pictureBar | look-only | nought (the same to the bit) | - | Lets Intensity dim the goniometer’s trace where it moves fast, as on the main screen. Only the look. | yes |
| `graticuleOn` | Graticule | picture/pictureBar | look-only | nought (the same to the bit) | - | Rules the screen’s divisions over the paper, or leaves it bare. Only the look: Scan never reads the grid. | yes |
| `inkAccent` | Ink: Rose | picture/pictureBar | look-only | nought (the same to the bit); on in every figure, so measured as the change back from inkCh1, inkCh2, inkCh3, inkCh4, inkCh5 | - | Draws the X–Y figure in rose, the accent. Only the look: Scan reads the light, not its colour, and Y–T lanes keep their own inks. | yes |
| `inkCh1` | Ink: Charcoal | picture/pictureBar | look-only | nought (the same to the bit) | - | Draws the X–Y figure in charcoal. Only the look: Scan reads the light, not its colour. | yes |
| `inkCh2` | Ink: Slate | picture/pictureBar | look-only | nought (the same to the bit) | - | Draws the X–Y figure in slate. Only the look: Scan reads the light, not its colour. | yes |
| `inkCh3` | Ink: Olive | picture/pictureBar | look-only | nought (the same to the bit) | - | Draws the X–Y figure in olive. Only the look: Scan reads the light, not its colour. | yes |
| `inkCh4` | Ink: Sage | picture/pictureBar | look-only | nought (the same to the bit) | - | Draws the X–Y figure in sage. Only the look: Scan reads the light, not its colour. | yes |
| `inkCh5` | Ink: Plum | picture/pictureBar | look-only | nought (the same to the bit) | - | Draws the X–Y figure in plum. Only the look: Scan reads the light, not its colour. | yes |
| `traceWidth` | Thickness | picture/pictureBar | look-only | nought (the same to the bit) | - | How thick the trace is drawn. Only the look: Scan reads where the beam went, not how wide it was drawn. | yes |
| `fadeEditA` | Fade · Lower (A) | routings/bench | look-only | nought (the same to the bit) | - | Shows the lower hand’s fade envelope to draw, the upper’s faint behind. Each hand’s sound follows its own; only with two hands. | yes |
| `fadeEditB` | Fade · Upper (B) | routings/bench | look-only | nought (the same to the bit) | - | Shows the upper hand’s fade envelope to draw, the lower’s faint behind. Each hand’s sound follows its own; only with two hands. | yes |
| `infoLineOn` | Info line | settings | look-only | nought (the same to the bit) | - | Shows a line like this one along the foot, saying what the control you rest on does. Off hides it; this browser remembers. | yes |
| `monitorLive` | Hear it through the page | settings | look-only | nought (the same to the bit) | - | Plays a line input through the page, tens of milliseconds late. Only for a line, never a band split; wear headphones the first time. | yes |
| `size100` | Size | settings | look-only | nought (the same to the bit) | - | Everything on the face at its own size, whatever the window. This browser remembers it. | yes |
| `size125` | Size | settings | look-only | nought (the same to the bit) | - | Everything on the face at 125%, whatever the window. This browser remembers it. | yes |
| `size90` | Size | settings | look-only | nought (the same to the bit) | - | Everything on the face at 90%, whatever the window. This browser remembers it. | yes |
| `sizeAuto` | Size | settings | look-only | nought (the same to the bit); on in every figure, so measured as the change back from size90, size100, size125 | - | 90% in a window under 1100 wide or 680 tall, 100% otherwise, so the plugin’s smallest window fits. Only the look changes. | yes |
| `autoset` | Autoset | -/bench | look-only | nought (the same to the bit); sends only Run; the timebase, full scales and level it picks stay the page's (measured with a note held) | - | Reads the signal and picks a timebase, a full scale for each lane and a trigger level to fit it, then runs in Auto. | half: the screen's settings change, the instrument's do not (see below) |
| `benchTab-ink` |  | -/bench | look-only | nought (the same to the bit) | - |  | yes |
| `benchTab-play` |  | -/bench | look-only | nought (the same to the bit) | - |  | yes |
| `benchTab-space` |  | -/bench | look-only | nought (the same to the bit) | - |  | yes |
| `editHandA` | Editing: Lower | - | look-only | nought (the same to the bit); on in every figure, so measured as the change back from editHandB | - | Puts the lower hand on the face: its own sections show and write its values. Named A when layered. Only with a split or layers. | yes |
| `editHandB` | Editing: Upper | - | look-only | nought (the same to the bit) | - | Puts the upper hand on the face: its own sections show and write its values. Named B when layered. Only with a split or layers. | yes |
| `enlargeButton` | Enlarge | -/bench | look-only | nought (the same to the bit) | - | Fills the window with the screen; Esc or this again brings the face back. Nothing it does changes the sound or is a step in undo. | yes |
| `enlargeTrail` | Trail | -/bench | look-only | nought (the same to the bit) | - | How long the enlarged screen keeps a stroke: as heard, half as long, or short. Only the look: Scan reads the Persistence's trail. | yes |
| `goniOn` | Goniometer & correlation | -/pictureBar | look-only | nought (the same to the bit) | - | A pane beside the screen: left against right turned 45°. Upright is mono, a circle is wide, flat means the channels fight. | yes |
| `handsA` | Which hands: Lower (A) | -/bench | look-only | nought (the same to the bit) | - | Draws only the lower hand’s figure (A’s, layered), so two figures piled into one cloud can be seen apart. Only the look. | yes |
| `handsB` | Which hands: Upper (B) | -/bench | look-only | nought (the same to the bit) | - | Draws only the upper hand’s figure (B’s, layered), so two figures piled into one cloud can be seen apart. Only the look. | yes |
| `handsBoth` | Which hands: Both | -/bench | look-only | nought (the same to the bit); on in every figure, so measured as the change back from handsA, handsB | - | Draws both hands' figures. Only the look: Scan reads both however many are drawn. | yes |
| `harmonicsOn` | Harmonics & THD | -/pictureBar | look-only | nought (the same to the bit) | - | A pane of the fundamental and its partials as bars, with the distortion they add up to. Needs a tone; noise gets no number. | yes |
| `infoMore` |  | -/pictureBar | look-only | nought (the same to the bit) | - |  | yes |
| `loopButton` | Loop | -/pictureBar | look-only | nought (the same to the bit) | - | Draws over the screen where Scan reads, the wave it is playing and the picture’s verdict. Only the look; nothing shows until Scan is on. | yes |
| `measureButton` | Scope & measure | -/bench | look-only | nought (the same to the bit) | - | Opens the oscilloscope’s own tools over the screen: run, trigger, timebase, scale, the trace filter and the readouts. | yes |
| `measureClose` | Close | -/bench | look-only | nought (the same to the bit) | - | Closes Scope & measure. Its settings stay as you left them, and the readouts stay if you switched them on. | yes |
| `menuButton` | Settings | - | look-only | nought (the same to the bit) | - | Opens what is set once and left: MIDI, the modulation fade, this window’s size, the input and the audio device. | yes |
| `menuClose` | Close | - | look-only | nought (the same to the bit) | - | Closes Settings. What is set here stays set when you load another sound. | yes |
| `modEditorClose` | Close | -/bench | look-only | nought (the same to the bit) | - | Closes the editor and brings the tab back. The source keeps moving everything it is on. | yes |
| `panesButton` | Panes | -/pictureBar | look-only | nought (the same to the bit) | - | Chooses the panes shown beside the screen in Enlarge: goniometer, spectrum, harmonics and tuner, and the spectrogram’s span. Only the look. | yes |
| `panesClose` | Close | -/pictureBar | look-only | nought (the same to the bit) | - | Closes the list of panes; the ones ticked show beside the enlarged screen. | yes |
| `performButton` | Perform | - | look-only | nought (the same to the bit) | - | Opens what is set at the start and played over: the arpeggiator, the clock, the key and tempo, and the morph. | yes |
| `performClose` | Close | - | look-only | nought (the same to the bit) | - | Closes Perform; the arpeggiator and the clock keep running. | yes |
| `photoPlace` | Place it on the figure | -/bench | look-only | nought (the same to the bit) | - | Moves the reticle to the nearest bright part of the figure, as switching it on does. Off, it switches it on. | yes |
| `pictureClose` | Close | -/pictureBar | look-only | nought (the same to the bit) | - | Closes Advanced. Everything set in it stays set, the loop overlay and the panes included. | yes |
| `pictureMore` | Advanced | -/pictureBar | look-only | nought (the same to the bit) | - | Opens what Scan reads and the score, and the screen’s look: the beam, its inks, the panes and the loop overlay. | yes |
| `pictureOnly` | Picture only | -/bench | look-only | nought (the same to the bit) | - | Hides all that is drawn over the trace: the graticule and its labels, the reticle, the loop, the hand's mark, the verdict and the panes. | yes |
| `routingsButton` | Routings | -/modRow | look-only | nought (the same to the bit) | - | Opens every routing in one place, by source or by destination, with a switch per source and the fade. The number is how many. | yes |
| `routingsByDest` | By destination | -/bench | look-only | nought (the same to the bit) | - | Lists every routing under the control it moves, to see all that is on one knob. | yes |
| `routingsBySource` | By source | -/bench | look-only | nought (the same to the bit); on in every figure, so measured as the change back from routingsByDest | - | Lists every routing under the card it comes from, each source with its switch. | yes |
| `routingsClose` | Close | -/bench | look-only | nought (the same to the bit) | - | Closes Routings and brings the tab back. Every routing and switch stays as set. | yes |
| `spectroSpan` | Span | -/pictureBar | look-only | nought (the same to the bit) | - | How many seconds the spectrogram shows across the screen, two to thirty. Only in the Spect display. | yes |
| `spectrumOn` | Spectrum | -/pictureBar | look-only | nought (the same to the bit) | - | A pane beside the screen showing how much of the sound is at each frequency. | yes |
| `tunerOn` | Tuner | -/pictureBar | look-only | nought (the same to the bit) | - | A pane naming the nearest note, with a needle for how many cents off; against the key you play, if there is one. | yes |
| `barsGo` | Drawbars | bench/bench | face only | nought (the same to the bit) | - | The registration, bar by bar from 16′ to 1′, as an organist writes it. Press it to go to the nine drawbars on the Ink tab. | - |
| `cycleGo` | Cycle | bench/bench | face only | nought (the same to the bit) | - | Opens the drawn cycle on the Ink tab, where you draw one period of the wave with the pointer and hear it as you draw. | - |
| `cycleGrab` | Grab | bench/bench | face only | nought (the same to the bit) | - | Takes one cycle of what is playing as the drawn wave. Hold the same note on the keyboard and the period is exact; without one it is measured. | - |
| `cycleSine` | Sine | bench/bench | face only | nought (the same to the bit) | - | Starts the drawing again from a sine. With the wavetable, only the slot chosen beside it. | - |
| `cycleSmooth` | Smooth | bench/bench | face only | nought (the same to the bit) | - | Rounds the corners of what you drew, a little each press: the top harmonics soften, and the figure's sharp turns with them. | - |
| `midiEndLow` | Low | bench/bench | face only | nought (the same to the bit); on in every figure, so measured as the change back from midiEndHigh | - | By notes, counts from the bottom: the lowest notes held are the lower hand, the rest the upper. | - |
| `tuneJust` | Just | bench/bench | face only | nought (the same to the bit); on in every figure, so measured as the change back from tuneEqual | - | Snaps the interval to its whole-number ratio, so a fifth is exactly 2:3 and its figure stands still. Poly's chords have their own tick. | - |
| `menvEvery` | Every note | -/bench | face only | nought (the same to the bit) | - | Starts its attack again on every new note, from where it has got to, so a run is a row of rises. Only with its own envelope. | - |
| `menvPhrase` | Each phrase | -/bench | face only | nought (the same to the bit); on in every figure, so measured as the change back from menvEvery | - | Starts when you play after silence; notes played while it is open join the same swell. Only with its own envelope. | - |
| `midiSplitLearn` | Learn from a key | bench/bench | not moved: waits for a key | - | - | Splitting at a key, takes the split point from the next key played, on your keyboard or, in the plugin, your host's. | - |
| `clearReference` | Clear | measure/bench | not moved: clears the reference | - | - | Takes the saved reference trace off the screen. | - |
| `saveReference` | Save reference | measure/bench | not moved: stores a reference trace | - | - | Freezes the trace on screen and keeps it dashed behind the live one in Y–T, so you can see what a change did. | - |
| `tempoTap` | Tap tempo | perform | not moved: taps a tempo over real seconds | - | - | Sets the tempo from your last four taps, and starts the synced oscillators on the beat you tapped. | - |
| `device` | Device | settings | not moved: needs a device | - | - | Which input Mic draws. The site’s choice only: in the plugin, the host’s input is used. | - |
| `helpFirst` | Help sheet at first | settings | not moved: the help sheet | - | - | Opens the help sheet over the instrument the first time it opens, in a browser or a host. The ? in the header opens it any time. | - |
| `keysOpen` | On-screen keys | settings | not moved: the on-screen keys | - | - | Two octaves of keys along the foot of the window, played by pointer or computer keyboard. M opens and shuts them from anywhere. Not in the plugin. | - |
| `kindLine` | Input is | settings | not moved: needs an input | - | - | Says a line input is plugged in, a keyboard or an interface, which has no ear, so it may be heard through the page. | - |
| `kindMic` | Input is | settings | not moved: needs an input | - | - | Says a microphone is plugged in, so it is never sent to the speakers: it would hear them and feed back. | - |
| `micBands` | Split | settings | not moved: needs a microphone | - | - | Splits the input into four bands by pitch, so one instrument down one input draws four lanes and a figure that moves as you play. | - |
| `micWhole` | Split | settings | not moved: needs a microphone | - | - | Draws the input as it arrives: one pair, left against right. | - |
| `midiConnect` | MIDI in | settings | not moved: asks for MIDI devices | - | - | Asks the browser for MIDI, then listens to every keyboard connected. Needs a secure page; Safari has no Web MIDI. | - |
| `midiOut` | MIDI out | settings | not moved: a MIDI port | - | - | A port to send the score’s and the arpeggiator’s notes to. With a synth on Local Off, the picture plays it. | - |
| `midiOutCh` | MIDI out channel | settings | not moved: a MIDI port's channel | - | - | The MIDI channel those notes go out on, one to sixteen. Changing it ends every note already sent. | - |
| `srcMic` | Source | settings | not moved: needs a microphone | - | - | Draws what comes in at the audio input instead of the generator, a microphone or a line. Choose the device under Audio. | - |
| `srcTone` | Source | settings | not moved: the source: an input needs a device | - | - | Draws and plays the instrument’s own generator, the one your keys play. Where the instrument starts. | - |
| `benchSearch` | Find a control | -/bench | not moved: a search box | - | - | Finds any control by name, and by a few other words (adsr, lfo). Choosing a result opens whatever it is behind. Press / from anywhere. | - |
| `helpButton` | How this works | - | not moved: the help sheet | - | - | Opens the help sheet: what each part of the instrument does to the sound and the picture, and where to find it. | - |
| `helpClose` |  | - | not moved: the help sheet | - | - |  | - |
| `keysClose` | Hide the keyboard | -/screenKeys | not moved: the on-screen keys | - | - | Hides the keys and lets go of every note they hold. The letters and the space bar go back to their usual jobs. | - |
| `keysDown` | Down an octave | -/screenKeys | not moved: the on-screen keys | - | - | Moves the on-screen keys down an octave; Z does the same from the computer keyboard. | - |
| `keysLatch` | Tap to hold | -/screenKeys | not moved: the on-screen keys | - | - | Each tap holds its note until you tap it again, so a mouse can hold a chord. Unticking lets go of every note it held. | - |
| `keysPedal` | Pedal | -/screenKeys | not moved: the on-screen keys' pedal | - | - | The sustain pedal: press to hold every note after you let go, press again to lift. Holding the space bar does the same. | - |
| `keysUp` | Up an octave | -/screenKeys | not moved: the on-screen keys | - | - | Moves the on-screen keys up an octave; X does the same from the computer keyboard. | - |
| `preset` | Plain sine | - | not moved: opens the browser | - | - | The sound loaded now, with its heading above it, and edited once you change it; Custom for a code pasted. Press to open the preset browser. | - |
| `presetBrowse` | Browse | - | not moved: opens the browser | - | - | Opens the preset browser: the bank under Settled and Breathing, and your saved sounds. Choosing a card there loads nothing. | - |
| `presetClose` | Close | - | not moved: closes the browser | - | - | Closes the browser and keeps what is loaded. Choosing a card loads nothing; Load or a double-click does. | - |
| `presetCode` | Setup code | - | not moved: a code to paste | - | - | The whole setup as text: copy it to send a sound to someone, or paste one in and press Paste to load it. | - |
| `presetCopy` | Copy | - | not moved: copies the code | - | - | Copies the setup code of the sound as it is now, for a message, another browser or the plugin. | - |
| `presetDelete` | Delete saved | - | not moved: deletes a saved sound | - | - | Deletes the saved sound chosen, or the saved one loaded, from this browser, without asking. The bank’s own cannot be deleted. | - |
| `presetLoad` | Load | - | not moved: loads a sound | - | - | Loads the chosen sound and leaves the browser open, to compare it with another. Enter or a double-click loads and closes. | - |
| `presetName` | Save this sound as | - | not moved: a saved sound's name | - | - | The name to keep the sound under; Enter saves. A name already saved is replaced without asking. | - |
| `presetNew` | New · a still sine | - | not moved: loads the base | - | - | Loads the still sine the instrument opens on, with the picture at nought, and closes the browser: a start for a sound of your own. | - |
| `presetNext` | The next preset | - | not moved: loads another sound | - | - | Loads the next sound in the bank, in the browser’s order, without opening anything. Your saved sounds are not stepped through. | - |
| `presetPaste` | Paste | - | not moved: loads a code | - | - | Loads the code pasted into the field, or else the one on the clipboard if the browser hands it over. | - |
| `presetPrev` | The previous preset | - | not moved: loads another sound | - | - | Loads the previous sound in the bank, in the browser’s order, without opening anything. Your saved sounds are not stepped through. | - |
| `presetSave` | Save | - | not moved: saves | - | - | Keeps the sound under Saved in this browser, with what is sounding now as its figure. The setup code takes it elsewhere. | - |
| `presetSaveHead` | Save | - | not moved: saves | - | - | Opens the preset browser at its save field, to keep the sound as it is now under a name of your own, in this browser. | - |
| `presetSaveOpen` | Save this sound… | - | not moved: opens saving | - | - | Opens a field to name the sound as it is now and keep it under Saved, in this browser, with its figure as the thumbnail. | - |
| `redoButton` | Redo | - | not moved: a step on | - | - | Puts back a change Undo took away. Any new change clears what was left to redo; Ctrl or ⌘ Shift Z does the same. | - |
| `routingsAllOff` | Switch all off | -/bench | not moved: silences every routing | - | - | Silences every source’s routings and keeps them; pressed again, it puts them all back. | - |
| `routingsClear` | Clear every routing | -/bench | not moved: clears every routing | - | - | Takes every routing off, from every source. Undo puts them back. | - |
| `tabKeys` |  | - | not moved: the help sheet | - | - |  | - |
| `tabMeasure` |  | - | not moved: the help sheet | - | - |  | - |
| `tabScreen` |  | - | not moved: the help sheet | - | - |  | - |
| `tabSignal` |  | - | not moved: the help sheet | - | - |  | - |
| `tabTrigger` |  | - | not moved: the help sheet | - | - |  | - |
| `undoButton` | Undo | - | not moved: a step back | - | - | Takes back your last change, up to a hundred. A knob turned counts once, after it has rested; Ctrl or ⌘ Z does the same. | - |

<!-- end of table -->

Since the audit (17 Nov), by hand rather than measured, in the table's JSON with a note each:
the EQ's switch became a field (`eqOn`, pressed by the rack's switch and by the editor's own,
`eqEditorOn`), *sound by design*; and its editor came, opened by the curve on its line
(`eqThumb`) and shut by its Close (`eqEditorClose`), both *face only*. The EQ's gains were
measured when a gain off nought put the EQ in: with the switch a field, a gain moved from code
while the EQ is off is *idle here*, and moved by a hand it switches the EQ on.

## The ones that reach the sound through the picture

<!-- reaches: written by hand from the table -->

Forty-five, and on most figures every one of them. The grid Scan reads is the screen's own
deposit (`walkXY` and `walkYT` in `core/include/scope/beam.h`, from the frame
`captureInto` cuts in `capture.h`), so everything that decides where the beam lands on the
screen, or how bright, decides what Scan reads. Sizes are the spectrum's distance at the
largest reading (0.02 is a quarter second of a Breathing preset's movement; a change of
display reads about 0.9, which is a different sound).

Then for each, the question asked: could Scan read the figure *before* the control is
applied, and what would it cost. One answer covers most of X-Y: Scan could read a second
deposit made from the frame's lanes at unit scale, centred, unturned and undimmed - its own
picture beside the shown one. What that costs, every time: a second walk of the beam a frame
(the walk is the larger part of a frame's drawing); the screen stops being what the sound
hears, which is the instrument's premise (`making-it-one-instrument.md`); the routings onto
`view.zoom`, `view.rotate`, `trig.position` and the lane scales, which exist to move the
picture and the sound together, would move only the picture; and every preset was voiced, and
measured by `honestytest.py`, with the view reaching the sound, so the bank would be heard and
measured again. In Y-T the window *is* the figure: a waveform drawn against time has no shape
before a timebase, a trigger and a position say which stretch of time it is, so Scan could
only read "before" them by fixing a window of its own (four periods of the lowest note, as
*Follow* picks one) - the cost there is that the Y-T screen and Scan read different stretches.

**The display and the run.** `dispXY`, `dispYT` (0.92: X-Y and Y-T are different pictures,
by design of the loop), `dispSpect` (0.68: Scan reads nothing, the tone keeps its last wave),
`run` (0.68: Stop holds the picture), `modeNormal`, `modeAuto` (0.68), `modeSingle` (0.04,
on one figure), `clearButton` (0.10, pressed mid-chord). *Before?* No: these choose what the
picture is, or whether it moves; there is no earlier figure for Scan to read. Their lines
already said so, but for the three modes.

**Where it sits and how large.** `zoom` (0.65), `ch1Scale` and `ch2Scale` (0.59),
`ch1Offset` and `ch2Offset` (0.52, 0.58). *Before?* In X-Y, yes, as above: Scan's grid at
unit scale and no offset. Of all of them the cheapest to take out of the sound and the most
surprising to have in it - the help sheet called zoom and full scale "where the trace sits and
how big it is". The cost beyond the general one: zoom routed from an LFO is a way of playing
(the help sheet's oscillators "that move the picture") that would go quiet. In Y-T the zoom is
a slice about the trigger and the full scale the strip's height, both part of the window.

**The turn and the pair.** `rotate` (0.36; not on split-yt, where Y-T draws lanes rather than
a pair), `midSide` (0.23), `xyX`, `xyY` (0.19, X-Y only). *Before?* The turn, yes in X-Y, and
its line said the sound turned only on *Shaped*: on *Input* it reaches through Scan on every
figure but one. Mid and side and the pair choose which signals make the figure, so "before"
means only "always left against right", which is what they exist to change.

**The window.** `timebase` (0.36, in X-Y too: the window is how much of the sound the figure
traces), `level` (0.32), `position` (0.21), `holdoff` (0.26), `edgeRising`/`edgeFalling`
(0.15), `trigSource0`/`trigSource1` (0.15). *Before?* In Y-T no - the window is intrinsic. In
X-Y the trigger decides only where the window starts, and it still measured on every X-Y
figure; Scan could read the latest window untriggered, at the cost of a figure that slides on
the screen while the sound holds still.

**The lanes in Y-T.** `ch1On`, `ch2On` (0.63, 0.61, Y-T only), `layOver`/`layStack` (0.79,
split-yt only, where there are four lanes to stack). *Before?* Only by reading lanes Scan
cannot see, which is no picture at all.

**The trace's shaping.** `filterOn` (0.27), `filterType` (0.64), `filterCutoff` (0.56),
`filterRes` (0.66), `seeDry`/`seeWet` (0.27), `ch1Ac`, `ch2Ac` (0.16, 0.19), `acCorner`
(0.15), `lagOn` (0.79), `lag` (0.28), `lagManual`/`lagAuto` (0.31). *Before?* Yes in X-Y:
`seeDry` already is "before" for the filter, the coupling and the turn, and the measurement
shows it working (0.27 against `seeWet`); the cost of making it the rule is that the trace
filter, which `filterOn`'s line sells as "and so what Scan reads", stops being a way to voice
the loop. The lag is the figure itself (one signal against itself later): there is no figure
before it.

**The beam.** `beamLevel` (0.22), `beamXY` (0.22, X-Y only), `beamYT` (0.15, Y-T only).
*Before?* Yes: Scan could take the undimmed strokes, which is the help's open question 3
answered by measurement. The cost is small (the dimming is a weight on the deposit, and
undimmed is the deposit without it) and the change to the sound is the size above.

And four that change the screen and not the sound when they should arguably change both:
*Follow* (`midiFollow`) and *Autoset* move the page's timebase, full scales and level and send
the instrument nothing (measured with a note held: Follow sent no message at all, Autoset only
Run), so after either the screen's settings and the ones Scan reads part ways until the next
setup is sent; and a split's third and fourth lanes' full scale and offset (`ch3Scale` and
the rest) are refused by the instrument, which has no such sliders. Nothing here changes
them; they are for the owner.

*Since, the same day* (claude/page-review-fixes): Follow and Autoset send the instrument
each control they move, as a hand on it would (`hostSendAsHand`; Autoset is one undo step,
Follow's timebase is a note's and none), and the page no longer offers a full scale or an
offset for a lane past the second, which it draws at full scale and centred as the
instrument does (`HOST_LANES`). Taking them in the instrument would have been new setup
fields and the core's restore. `followtest.py` holds all three. The table above is as
measured before; a fresh `reach_audit.py` run will show the four lanes' rows gone.

## Info lines that are wrong

<!-- wrong: written by hand from the table -->

Thirty-eight lines did not say the sound moves with their control, and were fixed in the words
on 17 Nov (`what-each-control-says.md`, then `write_words.py`): `zoom`, `timebase`, `level`,
`position`, `holdoff`, `edgeRising`, `edgeFalling`, `trigSource0`, `trigSource1`, `layStack`,
`layOver`, `modeAuto`, `modeNormal`, `modeSingle`, `xyX`, `xyY`, `midSide`, `lagOn`, `lag`,
`lagManual`, `lagAuto`, `ch1On`, `ch2On`, `ch1Scale`, `ch2Scale`, `ch1Offset`, `ch2Offset`,
`ch1Ac`, `ch2Ac`, `acCorner`, `filterType`, `filterCutoff`, `filterRes`, `seeDry`, `seeWet`,
`beamYT`; and two that said the opposite: `rotate` ("the sound turns with it only while
Speakers get is on Shaped") and `hearDry` ("the filter, the AC coupling and the turn change
only the picture"). The help sheet's Zoom entry gained a sentence to match. `reachtest.py` was
red on the old lines and is green on the new.

Not fixed, because the fix is a decision rather than words:

- `hearWet` (*Speakers get: Shaped*) says the speakers get the trace after the filter, the
  coupling and the turn. On the generator, with the filter on, it measures the same to the bit
  as *Input*: in the instrument the speakers never get the shaped trace. `lagMix` (*Heard*)
  likewise measures nought with Lag X-Y on. Both may act on a live input, which this audit did
  not play; the help sheet's "The generator is always heard" makes the same claim. This is the
  help's open question 2, now measured. Decided 17 Nov (the owner's): both rows are shown only
  while a live input plays, and hidden on the generator, their values and ids kept.
- `midiFollow` and `autoset` say what they do to the screen truly, and the instrument is not
  told (above). Since fixed: it is told.
- `ch3Scale`, `ch3Offset`, `ch4Scale`, `ch4Offset`: the page sends them and the instrument
  refuses them. Since fixed: the page no longer offers them.
