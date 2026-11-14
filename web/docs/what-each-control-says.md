# What each control says

The info line's sentence for every control on the face (G3b of
[the second pass](the-face-second-pass.md)), drafted 9 Nov for the owner to read before
it ships. The line on the face shows the control's name, its value, a gold dot when a host
can automate it and the hand it applies to; the sentence here comes after them. At most
150 characters each. *Paragraph* marks the controls whose card (opened from *More*) needs
more than the line can carry, with what it should say.

324 controls: 324 lines, none marked as removed by a later stage, 77 wanting a paragraph
(counted again in G5a, which added the Routings panel's, the Photocell's editor's and the
Envelope's two switches, and moved the fade to Routings; in G5b, which added a depth's
three - its slider, its number and its cross - wherever a row of depths is, and whose
right-click menu has no controls of its own to describe: its items are its words, and
*What is this?* in it opens a control's card; and in G6, which took Edit A / B, the rack's
Together / A / B and B's turn on a row of its own, gave the turn the Turn's place, and
added the header's Editing and a link on eleven sections; on 11 Nov, which added the five
of *How the picture responds*; and on 12 Nov, with the constellation's prototype, Draw's way,
its place, its hands and Reseed; and again on 12 Nov, the Width beside the Output; and on
14 Nov, which took those four away again with the prototype, in stage 5's step 4).
Each line was checked against the control's code, its section's notes and the help sheet.

## Questions for the owner

Seven are about the instrument rather than the words - the drafting found them by reading
what each control actually does:

1. ~~**Glide does nothing in Poly**~~ - settled 9 Nov: fixed. Each new note slides from the
   last note's pitch, a chord's notes together, out of silence too; page and core, with
   parity. Still open: **Interval**, **Phase** and **Tuning** are idle in Poly (chords play
   at their keys, tuned by *Tune a chord*); say so in the line, or grey them in Poly?
2. **The Plane's Turn is not heard by default.** The speakers turn with the figure only
   while *Speakers get* (Scope & measure › Filter) is on *Shaped*, and it starts on
   *Input*; the help sheet says the Turn turns the sound with the figure. The same holds
   for the trace filter and AC coupling. Which is meant, and does the plugin turn the sound
   at all?
3. **The Beam is under "Only the look" but reaches the sound.** With Intensity above Off,
   the dimmed strokes are what goes into the light Scan, the reads, the photocell and the
   score read (page and core alike). Move the Beam out of *Only the look*, or have the
   grid take undimmed strokes?
4. **Stop may not hold the tone in the compiled instrument.** The help sheet says Stop
   holds the screen and so the tone; the core does not hear Run. Should Stop hold Scan's
   tone in the plugin, as it does in the page?
5. ~~**The Photocell can be switched on but not routed by hand**~~ - settled in G5a: it
   is a card, routed as the others are, and its switch is *On* in its editor.
6. ***A against B* puts layer A in the left ear only and B in the right.** Nothing on the
   face says so. Intended?
7. **Kind has one choice once G2 takes the drawings.** Keep a one-item menu, or let it go
   with them? *Answered in G2: it went with them, and its row with it.*

And about the words:

8. **Strike's** agreed line does not say it does nothing while Scan is at nought; Softness's
   does. Add it to Strike's (it would need shortening), or leave it to the card?
9. **The scope's tools change what Scan reads** (the filter, AC, full scale, zoom and the
   rest feed the grid). Only the filter's line says so. Say it for the family?
10. ~~**Lines name today's A and B**~~ - settled in G6: the hands are *Lower* and *Upper*
    on a split and *A* and *B* layered, on the face as in these lines.
11. **Plugin-only differences**: MIDI and the audio device are the host's in the plugin.
    The device line says so; should the MIDI lines?
12. **Loose words**: what FM, Resonance and the upper drawbars do to the figure ("busier",
    "draws its ringing", "finer turns") - sharper wording welcome.
13. **The drawbars' note** says 5⅓′ is a fifth above the 16′; it is a fifth above the note.
    The line says the latter, and the note goes when the cards replace the notes.

## Controls with no id

The pointer rests on these as often as on anything, and the table of words needs a key for
them; G3b gives each a `data-say` with the key in the first column:

| key | what | line | chars |
|---|---|---|---|
| fx-switch | A rack module's switch | Takes the module's Mix to nought and keeps it for this sound; on puts it back, from silence. The Plane's switch rests its shaping and its Turn. | 143 |
| fx-arrow | A rack module's arrow | Opens the rest of this module under it, one module at a time. | 61 |
| fx-handle | A rack module's handle | Drag to move the module up or down the rack, or give it the keyboard and use the arrows. The Plane stays first, the Reverb last. | 128 |
| mod-card | A modulation card | Drag it onto a knob to move that knob with this source; press it to open its editor and show its ring on every knob it is on. | 125 |
| route-switch | A source’s switch in Routings | Off silences every routing from this source and keeps them; on puts them back as they were. A silence is kept with the sound. | 125 |
| tab-play | The Play tab | What you play: the keyboard and its expression, the generator and its envelope, the voice filter. | 97 |
| tab-ink | The Ink tab | What the beam draws with: the oscillator, the shaping, the drawbars and a drawn cycle. | 86 |
| tab-space | The Space & Memory tab | What happens to the drawing after it is made: the Plane, the phaser, chorus and delay, and the reverb, in that order. | 117 |
| mod-depth | A source’s depth | How far this source moves the control, filling out from the middle: right is more, left a minus. Alt-drag the knob, or its ring, for the same. | 142 |
| mod-depth-typed | A depth, typed | The depth as a number: type one, with or without its sign and per cent, and press Enter. As far as the source can reach and no further. | 135 |
| mod-remove | Take it off | Takes this source off this control. The source goes on moving everything else it is on. | 87 |

## Play

### Keyboard

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| keysOpen | On screen | Puts two octaves of keys along the foot of the window, played by pointer or computer keyboard. Nothing sounds until a note, keys or none. | 137 | yes: the computer keyboard plays as music software lays it out (A is C, W C sharp, S D, along two rows), Z and X for octaves, Space a held pedal; letters play notes rather than shortcuts while open; Tap to hold for a mouse |
| midiDyad | Dyad | Two held notes are the two channels, the lower on X, so the interval you play is the figure: a fifth stands still, a third walks. | 129 | yes: the two most recent notes, ordered by pitch whichever landed first; a third note replaces the older; one note alone is a unison unless Hold is ticked |
| midiMono | Mono | The newest note sets the pitch and the Interval menu puts the second channel above it, so one finger plays the whole figure. | 124 | - |
| midiPoly | Poly | Every held note sounds, up to eight, each with its own envelope. Draw chooses which of them make the figure's outline. | 118 | yes: outline notes lean to their side and still sound in both ears, the rest drawn along the diagonal; Glide, Phase and Interval do nothing to a chord; the voice budget |
| midiLayers | Layers | Whether a second sound plays: one, a split at a key with low notes one sound and high another, or layered, every note both. | 123 | yes: Poly only; kept but not applied while your input is drawn, and the note under it says so |
| midiSplitLearn | Split point | The key the upper layer starts from. Press it, then play that key on your keyboard or the screen's. | 99 | - |
| midiLayerPair | How the two layers are drawn | A figure each, overlaid in their own inks, or A against B: one figure, A's notes on X and B's on Y, heard left and right. | 121 | yes: with a figure each, each figure is a picture of its own that moves a sound (Pictures, in the Picture section's Advanced); A against B puts A in the left ear only and B in the right |
| midiDrawCount | Draw | How many held notes make the figure's outline, for the hand being edited. The rest are drawn along the diagonal, heard in both ears. | 132 | - |
| midiDrawWhich | Draw | Which notes make the outline: bass and melody, the lowest, the highest or the most recent. The lowest leans onto X, the rest onto Y. | 132 | yes: with two notes held it is the dyad whatever is chosen; the readout says how many make the outline and what interval it is |
| midiPolyJust | Tune a chord | Tunes each chord to whole-number ratios of its lowest note, so a major triad is 4:5:6 and its figure closes. Notes move a few cents to get there. | 145 | yes: every note moves by a different amount depending on what is under it, so a held melody note retunes as the chord under it changes; not the Tuning switch |
| polyRound | Quarter turn | In Poly, a lone note or an inner voice is heard a quarter-cycle later on the right, so it draws a ring rather than a diagonal line. | 131 | yes: what it costs - summed to mono, the even harmonics of a rich wave cancel, as a dyad's lone note's already do |
| midiHold | Hold the interval | In Dyad, a single note keeps the last interval above it, so one finger walks a figure up a melody. Off, one note is a unison. | 125 | - |

### Expression

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| midiBendRange | Pitch bend | How far the bend wheel takes every note, either way, in semitones. All the notes bend together, so the figure keeps its shape. | 126 | - |
| midiWheelTo | Mod wheel | What the mod wheel moves: a vibrato of up to a third of a semitone, the Picture amount, Scan's depth, or nothing. | 113 | yes: on the Picture amount or Scan's depth the wheel sets that knob outright, so moving it replaces where the knob was left |
| midiPressureTo | Pressure | What pressing harder on a held key moves, if your keyboard sends it: a vibrato, the Picture amount, Scan's depth, or nothing. | 125 | - |
| midiVelocityTo | Velocity | How hard you play always sets a note's level and how brightly it strikes the screen. With FM, a harder note is also brighter in tone. | 133 | - |

### Generator

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| linkGen | Generator’s link | Whether the Generator is the same in both hands or this hand’s own. Unlinking starts the other hand as a copy; linking copies this one over it. | 143 | yes — linked, a knob moved on either hand moves both, and a routing on it moves both; unlinked, the hand being edited alone, and its routings say which hand; the drawbars and the morph are the Generator’s |
| shape | Shape | The wave each note is made of. A sine is pure and draws smooth curves; sharper shapes are brighter and put corners in the figure. | 129 | yes: the gist of each - pulse, the noises, stepped, drawbars, morph, drawn cycle, wavetable - and which of them bring a row of their own |
| morph | Morph | One knob through sine, triangle, saw and square, crossfading each pair. Put a source on it and the tone and the figure change as you play. | 138 | - |
| width | Width | How much of each cycle the pulse is up, 5 to 95 per cent. At 50 it is the square; narrower is thinner and more nasal. | 117 | - |
| table | Position | Where the wavetable sits among its four drawn cycles, crossfading the two either side. Put a source on it and the timbre travels. | 129 | - |
| cycleGo | Cycle | Opens the drawn cycle on the Ink tab, where you draw one period of the wave with the pointer and hear it as you draw. | 117 | - |
| barsGo | Drawbars | The registration, bar by bar from 16′ to 1′, as an organist writes it. Press it to go to the nine drawbars on the Ink tab. | 122 | - |
| glide | Glide | How long each new note slides from the last note's pitch rather than stepping; off at nought. In Poly every note of a chord slides from there. | 142 | yes: one Glide for both hands; a note out of silence slides from the last note however long ago; a sliding note does not land in step with the chord, so its figure turns a little before it settles; under a held note in Mono it glides a turn of Frequency too |
| interval | Interval | The second channel against the first, in Mono; in Dyad the notes you play set it. Small whole-number ratios close the figure: a fifth is a still 2:3. | 149 | yes: the menu shows what the notes set; Poly's chords ignore it; at a unison Phase decides between line and circle |
| tuneJust | Just | Snaps the interval to its whole-number ratio, so a fifth is exactly 2:3 and its figure stands still. Poly's chords have their own tick. | 135 | yes: how fast tempered intervals turn - a fifth about three quarters of a turn a second, a major third nearly nine, a blur under persistence |
| tuneEqual | Equal | Takes the keys as an equal-tempered piano has them, a little off the ratios, so the figure turns at the rate the interval beats. | 128 | - |
| amp | Level | How loud the generator plays, and so how large it draws its figure and what Scan reads. Each hand’s, or both while the Generator is linked. | 139 | yes — in the Picture section’s corner until G7, where it read as a master volume it never was; the Output there now is how loud you hear, and leaves the picture alone |

### Amp envelope

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| linkAmpEnv | Amp envelope’s link | Whether the amp envelope is the same in both hands or this hand’s own. Unlinking starts the other hand as a copy; linking copies this one over it. | 146 | - |
| envAttack | Attack | How long a note takes to reach full level once its key goes down, and the figure grows with it. Between notes the generator is silent. | 134 | yes: a second key over a held one changes the pitch without starting the envelope again; until 10 Nov, on the site with no keyboard and the keys on screen shut, the level was the knob's and nothing else |
| envDecay | Decay | How long a note takes to fall from its peak to the sustain level. Short, with a low sustain, is a pluck. | 104 | - |
| envSustain | Sustain | The level a note holds while its key stays down, as a share of its peak. At nought every note dies away on its own. | 115 | - |
| envRelease | Release | How long a note takes to fade once you let go of its key. The figure shrinks with it. | 85 | - |

### Voice filter

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| linkVcf | Voice filter’s link | Whether the voice filter is the same in both hands or this hand’s own. Unlinking starts the other hand as a copy; linking copies this one over it. | 146 | - |
| vcfType | Type | Which filter is in every note: low pass darkens, high pass thins, band pass keeps a middle, notch takes one out. Off, the knobs below are idle. | 143 | yes: not the Filter in Scope & measure, which is on the whole trace and for looking |
| vcfCut | Cutoff | Where the filter starts taking the top off. Lower is darker, and the figure gets rounder, since the harmonics that put corners in it go first. | 142 | - |
| vcfRes | Resonance | How sharply the filter peaks at its cutoff. Higher rings at that pitch, and a sweep of the cutoff draws its ringing in the figure. | 130 | - |
| vcfTrack | Key track | How far the cutoff follows the note, from middle C. At 100 per cent a high note is as bright as a low one; at nought, high notes are duller. | 140 | - |
| vcfEnvAmt | Envelope | How many octaves the filter's own envelope sweeps the cutoff, up or down, as each note starts. | 94 | yes: its four times below; it opens from where Cutoff is; on the dyad each channel is filtered at its own pitch |
| vcfAtk | Attack | How long the filter's sweep takes to reach its height once a key goes down. Moves nothing while Envelope is at nought. | 118 | - |
| vcfDec | Decay | How long the sweep takes to fall from its height to its sustain. Short gives each note a pluck or a wah. | 104 | - |
| vcfSus | Sustain | Where the sweep holds while the key is down, as a share of Envelope's octaves. At nought each note opens and closes again. | 122 | - |
| vcfRel | Release | How long the cutoff takes to come back once you let go of the key. | 66 | - |

### Drawn cycle

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| cycleSine | Sine | Starts the drawing again from a sine. With the wavetable, only the slot chosen beside it. | 89 | - |
| cycleSmooth | Smooth | Rounds the corners of what you drew, a little each press: the top harmonics soften, and the figure's sharp turns with them. | 123 | - |
| cycleGrab | Grab | Takes one cycle of what is playing as the drawn wave. Hold the same note on the keyboard and the period is exact; without one it is measured. | 141 | yes: it grabs from the trigger lane - your input, or the generator's own output; the reading beside it says which, and why a grab failed |

### Drawbars

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| barsUse | Use drawbars | Puts the Shape on Drawbars, so the bars below are heard. Until then they are greyed and move nothing. | 101 | - |
| bar0 | 16′ | An octave under the note, the organ's deepest bar. Out at all, the wave repeats only every other cycle of the note, and so does the figure. | 139 | yes: nought to eight, about three decibels a step; with the 16′ or 5⅓′ out the readout's frequency is an octave under the key, and the tuner can be told to read the key |
| bar1 | 5⅓′ | A fifth above the note. Out at all, as with the 16′, the wave repeats only every other cycle of the note. | 105 | - |
| bar2 | 8′ | The note you play, as a sine. This bar alone at eight is a full-scale sine; adding others changes the colour, not the level. | 124 | - |
| bar3 | 4′ | An octave above the note, the second harmonic. Each bar draws out from nought to eight, about three decibels a step. | 116 | - |
| bar4 | 2⅔′ | An octave and a fifth above the note, the third harmonic. Upper bars brighten the tone and put finer turns in the figure's line. | 128 | - |
| bar5 | 2′ | Two octaves above the note, the fourth harmonic. | 48 | - |
| bar6 | 1⅗′ | Two octaves and a major third above the note, the fifth harmonic, which gives the organ its reedy edge. | 103 | - |
| bar7 | 1⅓′ | Two octaves and a fifth above the note, the sixth harmonic. | 59 | - |
| bar8 | 1′ | Three octaves above the note, the eighth harmonic. On the highest notes it is left out rather than folded back. | 111 | - |

### Oscillator

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| linkOsc | Oscillator’s link | Whether the oscillator is the same in both hands or this hand’s own. Unlinking starts the other hand as a copy; linking copies this one over it. | 144 | - |
| freq | Frequency | The pitch: a note in Dyad or Mono sets it, and a turn moves the note held. On Y–T, higher puts more cycles on the screen. | 121 | yes: Poly's chords leave it where it is; it is clamped to 30 Hz to 4 kHz, so the top of the keyboard stops at 4 kHz |
| phase | Phase | Where the second channel starts in its cycle against the first. At a unison, 0° draws a diagonal line and 90° a circle. Not for Poly's chords. | 142 | - |
| oscRatio | Ratio | The voice's second oscillator, as a ratio to the note, heard only through FM and Ring. A 3:2 sounds harmonic for the reason a 3:2 figure closes. | 144 | - |
| oscFm | FM | How far the second oscillator swings the voice's phase: pure at nought, then brighter, then bells and clangour. The figure gets busier with it. | 143 | yes: above about ten on a sharp shape the top folds back; Velocity's FM rides on this |
| oscBend | Warp | Bends the wave at one point of its cycle: up pinches it there, down swells it. The figure bulges or sharpens there and the tone brightens, in tune. | 147 | yes: in X–Y you can take hold of the figure and pull, which sets Warp and Warp at; it is FM at one to one, so it stays in tune |
| oscBendAt | Warp at | Where in the cycle Warp bends the wave, in degrees. Moves nothing while Warp is off; in X–Y, pulling the figure sets it. | 120 | - |
| oscRing | Ring | Multiplies the voice by the second oscillator instead: at full the note itself goes, leaving the sum and difference tones. | 122 | - |
| oscSync | Sync | Runs the shape faster than the note and restarts it every note cycle, so the pitch stays and the tone tears. For the saw and square; off at 1×. | 143 | - |
| oscSub | Sub | How much of a square or sine an octave or two under the note is mixed in. It deepens the sound without making it louder. | 120 | - |
| oscUnison | Unison | Stacks detuned copies of each note, so the sound thickens and the figure shimmers in place. | 91 | yes: the copies are not spread left and right, since in X–Y that would smear one axis into the other; a big chord gives copies up first |
| oscSpread | Spread | How far apart Unison's copies are tuned, in cents either way. Wider beats faster and smears the figure further. Idle while Unison is off. | 137 | - |
| oscSubOct | Sub octave | Whether the sub sits one octave or two under the note. Idle while Sub is off. | 77 | - |
| oscSubShape | Sub shape | The sub's wave: a square fills out the bottom with a buzz, a sine is a plain deep tone. Idle while Sub is off. | 110 | - |

### Shaping

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| linkShp | Shaping’s link | Whether the shaping is the same in both hands or this hand’s own. Unlinking starts the other hand as a copy; linking copies this one over it. | 141 | - |
| shpDrive | Drive | Pushes the wave into a soft ceiling: a sine rounds towards a square, and so does its figure. The reading is how much quiet parts are lifted. | 140 | - |
| shpFold | Fold | Bends the wave back each time it would pass full scale: on Y–T the peaks fold inward, and in X–Y the figure grows petals. | 121 | - |
| shpBits | Crush | Fewer levels for each sample, the stepped grit of a bitcrusher: the trace turns to a staircase. Off keeps every level. | 118 | - |
| shpRate | Rate | Holds each sample longer, as a lower sample rate would, for the folded-back whine of a lo-fi sampler. Off is the full rate. | 123 | - |
| shpOS | Oversampling | How finely Drive and Fold are worked. Four times is cleaner for a hard drive on a high note and costs twice as much for every voice. | 132 | yes: a chord too big for four times is worked at twice anyway, which the readout says; a shaped voice is 0.7 ms later either way |

## Space & Memory

### The rack

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| fxOrder | Rack order | Which of the phaser, chorus and delay comes first. Drag a module by its handle, or the arrow keys; the Plane stays first, the Reverb last. | 138 | yes — what the order changes (phaser before the delay keeps each repeat’s sweep; after, the repeats are swept with what you play now); one order for both hands; the sound changes on letting go |

### Plane

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| linkPlane | Plane’s link | Whether the Plane is the same in both hands or this hand’s own. Unlinking starts the other hand as a copy; linking copies this one over it. | 139 | - |
| planeTwist | Twist | Turns each point by more the further it is from the middle, so loud parts swirl and the quiet centre stays still: a stereo turn that follows level. | 147 | yes — the reading is the turn at full scale; a source swirls it half a turn at most; with Picture above nought, Memory pushes it when the figure stops moving |
| rotate | Turn | Turns the figure on the screen. The sound turns with it only while Speakers get, in Scope & measure, is on Shaped. | 114 | yes — worth most with a source on it; on a band split or the lag lane it turns the figure only; Numbers read decides whether the readings follow it |
| planeTurn | Turn (upper) | The upper hand’s own turn, in the Turn’s place while the Plane is that hand’s own: it turns the upper figure, and the lower’s stays. | 132 | - |
| planeMirror | Mirror | Folds the figure onto one half of itself; to the ear, the octave-up pedal, every harmonic even. The folded wave sits above zero. | 128 | yes — which half each choice folds; the offset reaches the speakers unless AC coupling, under Vertical, takes it off |
| planeLimit | Radial | What happens where the figure meets a circle of the Radius. Clip rounds loud parts off without bending the stereo image; Fold reflects them back in. | 148 | - |
| planeRadius | Radius | Where the clip or fold acts, as a part of full scale. Smaller, and more of the figure meets the circle: quieter and more distorted. | 131 | yes — marked at 0.2, where the owner found the clip quieter and distorted in a way worth keeping; two taps land there; shown only while Radial is on |
| planeSnap | Snap | Puts both channels on a grid: a bitcrusher to the ear and pixels on the screen. Five bits is the coarser. | 105 | - |
| planeOS1 | Oversampling (1×) | The bending ones at the sample rate: cheapest, and what they add above half of it folds back as stray notes out of the key. | 123 | yes — the bending ones are Mirror, Radial, Twist and Snap; while any is on the picture and sound are 0.7 ms later; the clip’s worst stray tone at 4 kHz is 27, 55 and 108 dB down at 1×, 2× and 4× |
| planeOS2 | Oversampling (2×) | The bending ones at twice the sample rate, the default, so most of the stray tones they add are filtered off rather than folded back. | 133 | yes — as 1× |
| planeOS4 | Oversampling (4×) | Four times the sample rate: cleaner still on a hard clip or a high note, at twice the cost of 2×. Fold and Snap stay rough at any rate. | 135 | yes — as 1× |
| planeScaleX | Scale X | The left channel’s level, and the figure’s width. At nought the figure is an upright line and the left is silent; at two, double. | 129 | - |
| planeScaleY | Scale Y | The right channel’s level, and the figure’s height. At nought the figure lies flat and the right is silent; at two, double. | 123 | - |
| planeShear | Shear | Leans the figure by feeding some of the right channel into the left; below nought it leans the other way. Exact, and adds no delay. | 131 | - |

### Phaser

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| linkPhaser | Phaser’s link | Whether the phaser is the same in both hands or this hand’s own. Unlinking starts the other hand as a copy; linking copies this one over it. | 140 | - |
| phaserMix | Mix | How much phaser you hear; nought is off. It opens a line into a loop that widens and closes, and twists a figure unevenly. | 122 | yes — with Picture above nought, Memory brings it in on a figure that has stopped moving; a source on it runs the phaser from nought |
| phaserRate | Sweep | How fast the notches sweep, one channel on a sine and the other on its cosine: the pace at which the loop widens and closes. | 124 | - |
| phaserDepth | Range | How far the sweep reaches, up to two and a half octaves either side of 700 Hz. At nought the notches stand still. | 113 | - |
| phaserFeedback | Resonance | Feeds the phaser back on itself to sharpen its two notches. Stops at 0.75 so it never rings on, and takes no source. | 116 | - |

### Chorus

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| linkChorus | Chorus’s link | Whether the chorus is the same in both hands or this hand’s own. Unlinking starts the other hand as a copy; linking copies this one over it. | 140 | - |
| chorusMix | Mix | How much chorus you hear; nought is off. A late copy of the pair whose lateness swings, so the figure breathes and turns. | 121 | - |
| chorusRate | Rate | How fast the copy’s lateness swings, one channel on a sine and the other on its cosine: the pace the figure breathes and turns at. | 130 | - |
| chorusDepth | Depth | How far the copy’s lateness swings either side of Centre. More is a wider wobble in pitch and a figure that breathes further. | 125 | - |
| chorusTime | Centre | How late the copy sits, from 1 to 30 ms. Short, with Feedback up, it rings as a flanger; longer is a looser doubling. | 117 | - |
| chorusFeedback | Feedback | Feeds the copy back into itself, which makes the chorus a flanger: with a short Centre it rings at a pitch of its own. | 118 | - |

### Delay

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| linkDelay | Delay’s link | Whether the delay is the same in both hands or this hand’s own. Unlinking starts the other hand as a copy; linking copies this one over it. | 139 | - |
| delayMix | Mix | How loud the repeats are; nought is off. In X–Y they are ghost figures trailing the live one. | 93 | yes — a source on it brings repeats in from none, and the delay keeps listening at nought; with Picture above nought, Motion pushes it; near full it keeps a held chord moving |
| delayMs | Time | How long before each repeat, up to two seconds. Greyed while Sync follows the tempo; a source on it bends the repeats’ pitch, like tape. | 136 | - |
| delayFeedback | Feedback | How many times each repeat comes back. Stops at 0.9, so it always dies away, and no source can be patched onto it. | 114 | - |
| delayTone | Tone | Darkens each repeat on its way round, so each comes back duller than the last. At the top it is open and changes nothing. | 121 | - |
| delayLowCut | Low cut | Thins each repeat on its way round, up to 1 kHz, so each comes back thinner than the last. At nought it is off. | 111 | - |
| delayWidth | Width | How far apart the repeats are heard. At nought they collapse to a line on the diagonal; at 100% as played; at 200% twice as wide. | 129 | - |
| delayWow | Wow | Drifts the delay time slowly, as a tape’s speed drifts, so each repeat is a little off pitch and its ghost figure turns. | 120 | - |
| delaySync | Sync | Free, or the time as a note value of the tempo in Perform, following it when it moves. While it is synced, Time is greyed. | 122 | - |
| delayPingPong | Ping-pong | Sends each repeat to the other side, so the ghost figures alternate between the figure and its reflection across the diagonal. | 126 | - |

### Reverb

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| linkReverb | Reverb’s link | Whether the reverb is the same in both hands or this hand’s own. Unlinking starts the other hand as a copy; linking copies this one over it. | 140 | - |
| reverbMix | Mix | How loud the tail is; nought is off. Past 0.2 it keeps a held chord moving: the screen goes on drawing the tail and Scan reading it. | 132 | yes — its switch gives 0.15, which keeps every preset under its heading; the loudest settings are bounded, not forbidden, the owner’s call over a defence that would make Scan’s knob lie |
| reverbSize | Size | How long the tail takes to fall away, from 0.3 to 9 seconds. Longer leaves a longer trail of where the figure has been. | 119 | - |
| reverbTone | Tone | How dark the tail is: lower takes more of the top off it, down to 500 Hz. At the top it is open. | 96 | - |
| reverbPre | Pre-delay | How long before the tail starts, up to 100 ms, so a note’s attack is heard clear of it. | 87 | - |
| reverbSpread | Spread | At nought both channels get the same tail and the figure survives it. Up, each gets its own, an ordinary stereo reverb, and the figure clouds over. | 147 | yes — two identical networks, one per channel, alike to the last coefficient at nought; turned up, the cloud is what Scan reads and the loop hears |

## The picture and the modulation

### The screen's toolbar

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| dispYT | Y–T | Each channel drawn against time, as a waveform. Scan reads the waveform as it is drawn, so the timebase moves the tone too. | 123 | yes — in Y–T Scan and the three reads read the lanes as drawn, so timebase and zoom reach the sound |
| dispXY | X–Y | The left channel against the right, drawn as one figure: the picture Scan is made to read. Turns Persistence on if it was off. | 126 | yes — switching in with Persistence off sets it to a short fade, once; change it after and it stays |
| dispSpect | Spect | Frequency up, time running right to left, loudness as ink. Scan and the picture read nothing here, so the tone keeps its last wave. | 131 | yes — the photocell reads nothing too, and Persistence is greyed |
| clearButton | Clear | Wipes the screen and the light Scan and the photocell read, so the picture builds up again from nothing. Persistence stays as set. | 130 | - |
| enlargeButton | Enlarge | Fills the window with the screen; Esc or this again brings the face back. Nothing it does changes the sound or is a step in undo. | 129 | yes — added in G4: it replaced the Scope view; the panes show only in it; the light Scan reads is kept as it opens and closes, the canvas redrawn from blank |

### The screen's toolbar › Enlarge

Shown only while the screen is enlarged (G4). All of them are the look's alone.

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| pictureOnly | Picture only | Hides all that is drawn over the trace: the graticule and its labels, the reticle, the loop, the hand's mark, the verdict and the panes. | 136 | yes — what it hides is drawn apart from the light Scan reads, so the sound is the same either way |
| handsBoth | Which hands: Both | Draws both hands' figures. Only the look: Scan reads both however many are drawn. | 81 | - |
| handsA | Which hands: Lower (A) | Draws only the lower hand’s figure (A’s, layered), so two figures piled into one cloud can be seen apart. Only the look. | 120 | - |
| handsB | Which hands: Upper (B) | Draws only the upper hand’s figure (B’s, layered), so two figures piled into one cloud can be seen apart. Only the look. | 120 | - |
| enlargeTrail | Trail | How long the enlarged screen keeps a stroke: as heard, half as long, or short. Only the look: Scan reads the Persistence's trail. | 129 | yes — Half halves the half-life, Short is the Persistence menu's Short; an infinite Persistence's Half is Long's |

### The Picture section

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| linkPicture | Picture’s link | Whether Amount, Scan and Strike are the same in both hands or each hand’s own. Softness and Persistence are the screen’s, shared. | 129 | yes — unlinking starts the other hand as a copy of this one and linking copies this one over it; the title says the hand while it is its own; a host’s Amount and Strike move both while linked, the hand being edited otherwise |
| pictureMore | Advanced | Opens what Scan reads and the score, and the screen’s look: the beam, its inks, the panes and the loop overlay. | 111 | - |
| pictureAmount | Amount | How far the picture moves the sound by itself: its glow folds it, its motion echoes it, its memory turns it. At nought, a plain synthesiser. | 140 | yes — the three reads and their meters; a keyboard’s expression pedal (CC 11) sets it; every preset sets it; it shares half a control’s reach with the photocell |
| oscScan | Scan | How much of the voice’s wave is read off the screen, up to 80 per cent. A moving picture moves the tone; a still one is a still tone. | 133 | yes — read sixty times a second round a circle by the figure; the pitch holds; reined in to a quarter while the loop runs away; with a split, the hand being edited, or both while the Picture is linked |
| scanStrike | Strike | How brightly each note lights the screen where Scan reads it. Higher, and every new note flares in the tone, then settles as the light fades. | 141 | yes — only while Scan is above nought; each note at its own place round the circle, as hard as it was played |
| scanSoft | Softness | How much the light is blurred before Scan reads it. At nought thin lines read as spikes and buzz; higher is rounder. Only while Scan is on. | 139 | - |
| scanMemory | Persistence | How long a stroke takes to fade to half, from off to infinite. Longer, and the tone, the picture’s reads and the score remember more. | 133 | yes — the screen’s, shared by both hands; the photocell’s memory too; the same setting as the menu over the screen |
| output | Output | How loud you hear it, after everything, and nothing else: the picture, Scan and the loop are the same at any setting. No preset changes it. | 139 | yes — both hands’, on what is heard alone, like a monitor’s volume; −6 dB at 71, −12 dB at 50, unity at the top; no preset, code, undo step or morph moves it; this browser remembers it, and in the plugin the project keeps it and a host can automate it; its meter is what is heard |
| stereoWidth | Width | How wide you hear it: nought puts the middle in both ears, a hundred is the pair as drawn. The picture and Scan are the same at any setting. | 140 | yes — both hands’, on what is heard alone, before the Output; the side of the pair scaled by it, so nought is mono and a hundred the sound as it was; nothing above a hundred, where the limiter would do the widening; no preset, code, undo step or morph moves it; this browser remembers it, and in the plugin the project keeps it and a host can automate it |

### Picture › Advanced

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| pictureClose | Close | Closes Advanced. Everything set in it stays set, the loop overlay and the panes included. | 89 | - |

### Picture › Advanced › What Scan reads

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| scanReadsA | Reads (Lower) | Whose picture the lower hand’s Scan reads: its own, the upper’s, or both averaged. Crossed, each hand’s tone comes from the other’s figure. | 139 | yes — shown only while each hand draws a figure; crossed loops are reined in together when either runs away |
| scanReadsB | Reads (Upper) | Whose picture the upper hand’s Scan reads: its own, the lower’s, or both averaged. Shown only while each hand draws a figure of its own. | 136 | - |
| pictureMovesA | Pictures (Lower) | Whose sound the lower hand’s picture moves through the Amount: its own, the upper’s, or both. A sound hearing two takes their average. | 134 | - |
| pictureMovesB | Pictures (Upper) | Whose sound the upper hand’s picture moves through the Amount: its own, the lower’s, or both. Shown only while each hand draws a figure. | 136 | - |

### Picture › Advanced › How the picture responds

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| pictureResponds | Responds to | What the Amount’s push follows: Change flares at a new or harder gesture and settles; Level follows how much is lit; Both is a base with a flare. | 145 | yes — each hand’s own on the Picture’s link, or both while it is linked; Change is the start until the owner has heard the three; the read is the hand’s own picture’s, so with *Pictures* crossed a hand’s response goes with its picture to the other’s sound; on a fixed scale, so a held chord settles rather than swelling by itself |
| pictureSwell | Swell | The picture breathing by itself while a chord is held, smoothly, at a rate the Persistence sets: slower as the light lingers. Off, a held chord rests. | 150 | - |
| pictureFeel | Rise, fall | How quickly the push comes and how slowly it goes: Snappy, Smooth or Slow, or Custom with a knob for each. | 106 | - |
| pictureRise | Rise | How long the push takes to come when the picture asks for more. Shown with Custom. | 82 | - |
| pictureFall | Fall | How long the push takes to go when the picture asks for less. Longer, and a swell outlasts the playing that made it. | 116 | - |

### Picture › Advanced › Score

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| scoreOn | Play the picture | Plays the screen as a score: a playhead crosses it at the tempo, low on the screen low in pitch, and the brightest points are the notes. | 136 | yes — in the page’s key, in the generator’s voice and out to MIDI; heard, not drawn; silent while the scope is stopped |
| scoreStep | Step | How long the playhead stays on each column of the screen, as a note value at the tempo. Shorter, and the melody runs faster. | 124 | - |
| scoreVoices | Notes a step | The most notes a step plays: the brightest points in the column, loudest first. One note is a melody; more are chords. | 118 | - |
| scoreLow | From | The note at the bottom of the screen. The rows go up from it in the page’s key. | 79 | - |
| scoreOctaves | Octaves | How many octaves the screen’s height covers, up from the bottom note. More octaves, wider leaps from the same picture. | 118 | - |

### Picture › Advanced › Only the look

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| loopButton | Loop | Draws over the screen where Scan reads, the wave it is playing and the picture’s verdict. Only the look; nothing shows until Scan is on. | 136 | - |
| panesButton | Panes | Chooses the panes shown beside the screen in Enlarge: goniometer, spectrum, harmonics and tuner, and the spectrogram’s span. Only the look. | 139 | - |
| panesClose | Close | Closes the list of panes; the ones ticked show beside the enlarged screen. | 74 | - |

### Picture › Advanced › Beam

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| beamLevel | Intensity | How much the trace dims where it moves fast, as a real beam does: bright at the turns, faint in the sweeps. Scan reads the dimming too. | 135 | yes — under “Only the look”, yet the dimmed light is what Scan and the reads take in (see Questions) |
| inkAccent | Ink: Rose | Draws the X–Y figure in rose, the accent. Only the look: Scan reads the light, not its colour, and Y–T lanes keep their own inks. | 129 | - |
| inkCh1 | Ink: Charcoal | Draws the X–Y figure in charcoal. Only the look: Scan reads the light, not its colour. | 86 | - |
| inkCh2 | Ink: Slate | Draws the X–Y figure in slate. Only the look: Scan reads the light, not its colour. | 83 | - |
| inkCh3 | Ink: Olive | Draws the X–Y figure in olive. Only the look: Scan reads the light, not its colour. | 83 | - |
| inkCh4 | Ink: Sage | Draws the X–Y figure in sage. Only the look: Scan reads the light, not its colour. | 82 | - |
| inkCh5 | Ink: Plum | Draws the X–Y figure in plum. Only the look: Scan reads the light, not its colour. | 82 | - |
| bInk | The upper hand’s ink | The colour of the upper hand’s figure while each hand draws one: its lane’s ink to start, or one you choose. Only the look. | 123 | - |
| traceWidth | Thickness | How thick the trace is drawn. Only the look: Scan reads where the beam went, not how wide it was drawn. | 103 | - |
| graticuleOn | Graticule | Rules the screen’s divisions over the paper, or leaves it bare. Only the look: Scan never reads the grid. | 105 | - |
| beamXY | X–Y | Lets Intensity dim the X–Y figure where it moves fast. Unticked, the whole figure is full ink, and Scan reads it that way. | 122 | - |
| beamYT | Y–T waveform | Lets Intensity dim the waveform where it moves fast. Off to start, since dimming a square wave’s steep edge hides what Y–T shows. | 129 | - |
| beamGoni | Goniometer | Lets Intensity dim the goniometer’s trace where it moves fast, as on the main screen. Only the look. | 100 | - |

### A modulation card’s editor

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| modEditorClose | Close | Closes the editor and brings the tab back. The source keeps moving everything it is on. | 87 | - |
| routingsButton | Routings | Opens every routing in one place, by source or by destination, with a switch per source and the fade. The number is how many. | 125 | - |

### A modulation card’s editor › LFO 1 and LFO 2

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| lfoShape0 | Shape | The wave the LFO sweeps with. Ramp rises and drops back; Random jumps to a new level each cycle and holds it. | 109 | - |
| lfoSync0 | Sync | Free runs at Rate; a note value locks the LFO to the tempo, and it starts again on the beat. | 92 | - |
| lfoRate0 | Rate | How fast the LFO sweeps, from 0.01 to 8 cycles a second. Greyed while Sync locks it to the tempo. | 97 | - |
| srcDetail-add | Add a destination | Puts this source on another control, from every one it can reach. Dragging its card onto a knob does the same. | 110 | - |

### A modulation card’s editor › The Envelope

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| menvOwn | Its own | Gives the Envelope four times of its own, one swell for the notes held. Off, it follows Play’s amp envelope. | 108 | yes — its own ignores how hard you play; Play’s, in poly, is the loudest note’s; it moves only while a keyboard plays the generator |
| menvFollow | Follows the amp envelope | The Envelope rises and falls with Play’s amp envelope, whose curve it draws greyed: set it on Play. | 99 | - |
| menvItsOwn | Its own | Gives the Envelope four times of its own, one swell for the notes held, drawn over its knobs. | 93 | - |
| menvPhrase | Each phrase | Starts when you play after silence; notes played while it is open join the same swell. Only with its own envelope. | 114 | - |
| menvEvery | Every note | Starts its attack again on every new note, from where it has got to, so a run is a row of rises. Only with its own envelope. | 124 | - |
| menvAtk | Attack | How long the Envelope takes to rise when it starts, up to two seconds. Greyed while it follows the amp envelope. | 112 | - |
| menvDec | Decay | How long it takes to fall from the top to Sustain, up to four seconds. Greyed while it follows the amp envelope. | 112 | - |
| menvSus | Sustain | Where it rests while notes are held, from nought to the top. Greyed while it follows the amp envelope. | 102 | - |
| menvRel | Release | How long it takes to fall to nought after the last key lifts, up to four seconds. Greyed while it follows the amp envelope. | 123 | - |

### The on-screen keyboard

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| keysDown | Down an octave | Moves the on-screen keys down an octave; Z does the same from the computer keyboard. | 84 | - |
| keysUp | Up an octave | Moves the on-screen keys up an octave; X does the same from the computer keyboard. | 82 | - |
| keysLatch | Tap to hold | Each tap holds its note until you tap it again, so a mouse can hold a chord. Unticking lets go of every note it held. | 117 | - |
| keysPedal | Pedal | The sustain pedal: press to hold every note after you let go, press again to lift. Holding the space bar does the same. | 119 | - |
| keysVelocity | Velocity | How hard the on-screen keys and the typed letters play: louder, and a brighter strike on the screen where Scan reads. | 117 | - |
| keysClose | Hide the keyboard | Hides the keys and lets go of every note they hold. The letters and the space bar go back to their usual jobs. | 110 | - |

## Around the instrument

### Header

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| editHandA | Editing: Lower | Puts the lower hand on the face: its own sections show and write its values. Named A when layered. Only with a split or layers. | 127 | yes — a section linked is both hands whichever is chosen; the hand’s figure’s ink on its dot; the tab cards say where the hands differ |
| editHandB | Editing: Upper | Puts the upper hand on the face: its own sections show and write its values. Named B when layered. Only with a split or layers. | 127 | - |
| presetPrev | The previous preset | Loads the previous sound in the bank, in the browser’s order, without opening anything. Your saved sounds are not stepped through. | 130 | - |
| preset | Plain sine | The sound loaded now, with its heading above it; Custom once you change it. Press to open the preset browser. | 109 | - |
| presetNext | The next preset | Loads the next sound in the bank, in the browser’s order, without opening anything. Your saved sounds are not stepped through. | 126 | - |
| presetBrowse | Browse | Opens the preset browser: the bank under Settled and Breathing, and your saved sounds. Choosing a card there loads nothing. | 123 | - |
| presetSaveHead | Save | Opens the preset browser at its save field, to keep the sound as it is now under a name of your own, in this browser. | 117 | - |
| undoButton | Undo | Takes back your last change, up to a hundred. A knob turned counts once, after it has rested; Ctrl or ⌘ Z does the same. | 120 | yes — what counts as a step (400 ms at rest, only after your own hand; a host’s automation is never one), and that only what a setup code holds is undone (not the fade, the size or the input) |
| redoButton | Redo | Puts back a change Undo took away. Any new change clears what was left to redo; Ctrl or ⌘ Shift Z does the same. | 112 | - |
| performButton | Perform | Opens what is set at the start and played over: the arpeggiator, the clock, the key and tempo, and the morph. | 109 | - |
| helpButton | How this works | Opens the help sheet: what each part of the instrument does to the sound and the picture, and where to find it. | 111 | - |
| menuButton | Settings | Opens what is set once and left: MIDI, the modulation fade, this window’s size, the input and the audio device. | 111 | - |
| persistence | (hidden menu) | Never shown, so never pointed at: the plugin's panel names it. The Persistence knob in the Picture section is the one people turn. | 130 | - |

### Perform

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| performClose | Close | Closes Perform; the arpeggiator and the clock keep running. | 59 | - |

### Perform › Arpeggiator

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| arpMode | Arp | Plays a held chord a note at a time at the tempo: up, down, up and back, as played or at random. Letting go stops it. | 117 | yes — in the dyad each step pairs your lowest note with the next; switching off with keys down gives the generator the chord; its notes go out through MIDI out |
| arpRate | Arp step | How long each step of the arpeggio is, at the tempo: from a crotchet (1/4) to a semiquaver triplet (1/16t). | 107 | - |
| arpOctaves | Arp octaves | How many octaves the arpeggio spreads the chord over, from one to three. | 72 | - |

### Perform › Clock

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| transportPlay | Bar | Stops the bar and silences the score; pressed again, starts it from the one and restarts the synced oscillators with it. | 120 | yes — the bar counts in fours and the score reads its columns from it; a device’s MIDI clock, Start, Stop and Continue drive it; the arpeggiator does not follow it |

### Perform › Morph

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| morphStoreA | Morph · store A | Stores every knob as the fader’s left end, and puts the fader there. Store, change the sound, store the other end, then slide. | 126 | - |
| morphPos | Morph | Slides the whole sound between the two stored ends: pitch by octaves, every other knob in a straight line. Menus, switches and the scope’s view stay. | 149 | yes — a knob turned by hand keeps its place until the fader moves; an LFO on it moves the whole sound; the ends are part of the setup code; the timebase, the zoom and the trigger are the view and stay where the player set them, the tempo is heard and slides (G8) |
| morphStoreB | Morph · store B | Stores every knob as the fader’s right end, and puts the fader there, so storing moves nothing you hear. | 104 | - |

### Perform › Key and tempo

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| keyRoot | Key | The page’s one key, which the quantiser and the score play in. | 62 | - |
| keyScale | Scale | Which notes of the key count: Chromatic (every semitone), major, minor or one of the modes. The quantiser and the score use it. | 127 | - |
| quantise | Quantise | Moves the generator’s pitch, after everything patched onto it, to the nearest note of the key: an LFO on the frequency plays a melody. | 134 | yes — a key played outside the scale moves too; it waits a tenth of a semitone past half-way and steps at most forty times a second, so a resting pitch does not flicker |
| quantiseGlide | Glide | How long the quantised pitch takes to slide to each new note, up to 300 ms; off, it steps. Only while Quantise is on. | 117 | - |
| tempo | Tempo | The page’s one tempo, 30 to 300 BPM: the arpeggiator, the score and every synced LFO or delay play at it. | 105 | yes — a device sending MIDI clock sets it while the clock runs and hands it back half a second after it stops |
| tempoTap | Tap tempo | Sets the tempo from your last four taps, and starts the synced oscillators on the beat you tapped. | 98 | - |

### Settings

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| menuClose | Close | Closes Settings. What is set here stays set when you load another sound. | 72 | - |

### Settings › MIDI

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| midiConnect | MIDI in | Asks the browser for MIDI, then listens to every keyboard connected. Needs a secure page; Safari has no Web MIDI. | 113 | yes — a page in an iframe needs the embedding page to allow MIDI, so the published artifact cannot, and the GitHub Pages copy can; setting up a Nord Electro |
| midiOut | MIDI out | A port to send the score’s and the arpeggiator’s notes to. With a synth on Local Off, the picture plays it. | 107 | yes — at most forty notes a second; every note is ended when the scope stops, the page is hidden or the port changes; the readout says sending |
| midiOutCh | MIDI out channel | The MIDI channel those notes go out on, one to sixteen. Changing it ends every note already sent. | 97 | - |

### A modulation card’s editor › The Photocell

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| photoButton | On | Puts a light sensor on the screen, landing on the figure; drag its reticle there to aim it. Off, it reads nought. | 113 | yes — how bright the screen is under it, a source that moves a control at most half way and no faster than two swings a second; Persistence is its memory |
| photoPlace | Place it on the figure | Moves the reticle to the nearest bright part of the figure, as switching it on does. Off, it switches it on. | 108 | - |

### Routings

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| routingsBySource | By source | Lists every routing under the card it comes from, each source with its switch. | 78 | - |
| routingsByDest | By destination | Lists every routing under the control it moves, to see all that is on one knob. | 79 | - |
| routingsClose | Close | Closes Routings and brings the tab back. Every routing and switch stays as set. | 79 | - |
| routingsAllOff | Switch all off | Silences every source’s routings and keeps them; pressed again, it puts them all back. | 86 | - |
| routingsClear | Clear every routing | Takes every routing off, from every source. Undo puts them back. | 64 | - |

### Routings › Fade

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| fadeMode | Fade | Whether modulation eases in and out rather than arriving at once: a routing patched or taken off, a note struck or let go. | 122 | yes — the envelope drawn under it and how to drag it; LFOs, the picture and knobs are not eased; a sound loaded (a preset, New, a code, undo) is never eased but lands at once, knobs and routings, whatever the fade (the owner's call, 11 Nov); kept in this browser, not in a setup code |
| fadeEditA | Fade · Lower (A) | Shows the lower hand’s fade envelope to draw, the upper’s faint behind. Each hand’s sound follows its own; only with two hands. | 127 | - |
| fadeEditB | Fade · Upper (B) | Shows the upper hand’s fade envelope to draw, the lower’s faint behind. Each hand’s sound follows its own; only with two hands. | 127 | - |
| fadeRestart | Restart | Runs the fade’s envelope again, from where it is, on every note you strike. | 75 | - |
| fadeLoop | Loop | Sends the fade’s attack and decay round again and again for as long as a note is held. | 86 | - |

### Settings › This window

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| helpFirst | Help sheet at first | Opens the help sheet over the instrument the first time it opens, in a browser or a host. The ? in the header opens it any time. | 128 | - |
| infoLineOn | Info line | Shows a line like this one along the foot, saying what the control you rest on does. Off hides it; this browser remembers. | 122 | - |
| sizeAuto | Size | 90% in a window under 1100 wide or 680 tall, 100% otherwise, so the plugin’s smallest window fits. Only the look changes. | 121 | - |
| size90 | Size | Everything on the face at 90%, whatever the window. This browser remembers it. | 78 | - |
| size100 | Size | Everything on the face at its own size, whatever the window. This browser remembers it. | 87 | - |
| size125 | Size | Everything on the face at 125%, whatever the window. This browser remembers it. | 79 | - |

### Settings › Input

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| srcTone | Source | Draws and plays the instrument’s own generator, the one your keys play. Where the instrument starts. | 100 | - |
| srcMic | Source | Draws what comes in at the audio input instead of the generator, a microphone or a line. Choose the device under Audio. | 119 | - |
| micWhole | Split | Draws the input as it arrives: one pair, left against right. | 60 | - |
| micBands | Split | Splits the input into four bands by pitch, so one instrument down one input draws four lanes and a figure that moves as you play. | 129 | yes — four crossovers, honest about it: a kick and a hi-hat part by frequency, not by being recognised; Lanes solos, mutes and lays them out; a band split is never monitored |

### Settings › Audio

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| device | Device | Which input Mic draws. The site’s choice only: in the plugin, the host’s input is used. | 87 | - |
| kindMic | Input is | Says a microphone is plugged in, so it is never sent to the speakers: it would hear them and feed back. | 103 | - |
| kindLine | Input is | Says a line input is plugged in, a keyboard or an interface, which has no ear, so it may be heard through the page. | 115 | yes — a claim you make that the browser cannot check; get it wrong with a microphone and the feedback loop is real |
| monitorLive | Hear it through the page | Plays a line input through the page, tens of milliseconds late. Only for a line; wear headphones the first time. | 112 | yes — the latency shown is the browser’s output side only, a floor; hearing the instrument directly and letting the page only look has none |

### Scope & measure

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| measureButton | Scope & measure | Opens the oscilloscope’s own tools over the screen: run, trigger, timebase, scale, the trace filter and the readouts. | 117 | - |
| measureClose | Close | Closes Scope & measure. Its settings stay as you left them, and the readouts stay if you switched them on. | 106 | - |

### Scope & measure › Run

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| run | Stop | Holds the trace where it is; press again to run. Stopping also silences the score and ends every note sent out over MIDI. | 121 | - |
| modeAuto | Auto | Draws whatever arrives, triggered or not, so the trace never stops. A grey trace is free-running, not a fault. | 110 | - |
| modeNormal | Normal | Holds the last triggered picture while nothing crosses the level, rather than drawing an untriggered one. | 105 | - |
| modeSingle | Single | Waits for one edge, draws it and stops: how to catch a transient. Run arms it again. | 84 | - |
| autoset | Autoset | Reads the signal and picks a timebase, a full scale for each lane and a trigger level to fit it, then runs in Auto. | 115 | - |

### Scope & measure › Trigger

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| edgeRising | Rising | Starts the trace where the signal crosses the level going up. | 61 | - |
| edgeFalling | Falling | Starts the trace where the signal crosses the level going down. | 63 | - |
| level | Trigger level | How high the signal must cross to start the trace, as a share of full scale: the dashed rose line on the screen. | 112 | - |
| trigSource0 | Source | Takes the trigger from the first lane. Every lane is cut at that lane’s edge, so they stay in step. | 99 | - |
| trigSource1 | Source | Takes the trigger from the second lane. Every lane is cut at that lane’s edge, so they stay in step. | 100 | - |
| position | Position | How much of the screen shows what came before the trigger. At 10%, a tenth; the marker at the top is the moment itself. | 119 | - |
| holdoff | Holdoff | Ignores an edge with another close behind it, up to 5 ms, which settles a wave that crosses the level twice a cycle. | 116 | - |

### Scope & measure › Time

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| timebase | Timebase | How much time the screen holds, from a millisecond to half a second across. In Y–T, longer shows more cycles of the wave. | 121 | yes — the longest settings depend on the converter’s rate (743 ms at 44.1 kHz, 341 at 96); past it the reading says past the buffer |
| zoom | Zoom | Magnifies: in Y–T a slice around the trigger, in X–Y the figure, on the spectrogram the band. The numbers still read it all. | 124 | - |

### Scope & measure › Lanes

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| layStack | Layout | In Y–T, each lane in its own strip with its name: what each part is doing. | 74 | - |
| layOver | Layout | In Y–T, every lane on one graticule: how the lanes line up against each other. | 78 | - |
| xyX | X–Y pair | Which lane is drawn across, the figure’s X. The goniometer follows the same pair. | 81 | - |
| xyY | X–Y pair | Which lane is drawn upward, the figure’s Y. One lane against itself draws a diagonal line. | 90 | - |

### Scope & measure › Filter

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| filterOn | Filter the trace | Filters the trace, and so what Scan reads from it: a low pass rounds a square towards a sine. Heard directly only on Shaped. | 124 | yes — it runs on the samples, not the audio graph; the screen’s and the speakers’ switches are separate, and straddle the filter, the AC coupling and the turn |
| filterType | Type | Which part the trace filter keeps: low pass the bottom, high pass the top, band pass a band; a notch carves one out. | 116 | - |
| filterCutoff | Cutoff | Where the trace filter acts, 20 Hz to 20 kHz. Lower on a low pass rounds the trace’s corners; a source on it sweeps. | 116 | - |
| filterRes | Resonance | A peak at the cutoff: nought is gentle, a hundred rings. High, it can push the trace past full scale and the readout says Clipping. | 131 | yes — nothing turns it down, since a compressor on the screen would lie about the level; lower Full scale or the amplitude |
| seeDry | Screen reads | The screen draws the signal as it came in, before the filter, the AC coupling and the turn. The readout says so. | 112 | - |
| seeWet | Screen reads | The screen draws the signal after the filter, the AC coupling and the turn. | 75 | - |
| hearDry | Speakers get | The speakers get the signal as it came in: the filter, the AC coupling and the turn change only the picture. | 108 | yes — the four combinations of the two switches and what each is for; anything reaching the speakers passes a limiter first |
| hearWet | Speakers get | The speakers get the signal after the filter, the AC coupling and the turn, so you hear what the screen shows shaped. | 117 | - |

### Scope & measure › Vertical

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| ch1On | Show | Draws this lane in Y–T and gives it a row in the readouts. | 58 | - |
| ch1Ac | AC | Blocks what is not moving, so a DC offset cannot push this lane off the screen. The speakers get it too on Shaped. | 114 | yes — a one-pole high pass at AC corner; the readouts are about the coupled signal and name the corner |
| ch1Scale | Full scale | The level that reaches the top of the screen, 0 to −50 dBFS. Lower it to open up a quiet signal; the numbers stay the same. | 123 | - |
| ch1Offset | Offset | Moves this lane’s trace up or down the screen, and in X–Y the figure along its axis. | 84 | - |
| ch2On | Show | Draws this lane in Y–T and gives it a row in the readouts. | 58 | - |
| ch2Ac | AC | Blocks what is not moving, so a DC offset cannot push this lane off the screen. The speakers get it too on Shaped. | 114 | yes — as ch1Ac |
| ch2Scale | Full scale | The level that reaches the top of the screen, 0 to −50 dBFS. Lower it to open up a quiet signal; the numbers stay the same. | 123 | - |
| ch2Offset | Offset | Moves this lane’s trace up or down the screen, and in X–Y the figure along its axis. | 84 | - |
| midSide | Mid / side | Draws the sum and the difference of a stereo pair in place of left and right: the figure turned 45°. Turns Lag X–Y off. | 119 | - |
| lagOn | Lag X–Y | Plots the signal against itself a moment later, so one input draws a loop shaped by its harmonics rather than a diagonal line. | 126 | yes — a phase portrait, not a Lissajous figure; Auto locks slowly so vibrato turns the loop; not offered on a band split |
| lagAuto | Delay | Sets the delay to a quarter of the note’s period, locked slowly, so a pure tone draws a circle and vibrato turns the loop. | 122 | - |
| lagManual | Delay | Holds the delay where its knob puts it, whatever the note. | 58 | - |
| lag | Delay | How far behind the delayed copy is, 0.1 to 40 ms. Only on Set; on Auto it shows what the lock found. | 100 | - |
| lagMix | Heard | How much of the delayed copy reaches the right speaker when the speakers get Shaped: a comb that follows the pitch. Up to 50%. | 126 | yes — 20% is mostly width; in headphones the top of the knob takes some harmonics out of the right ear entirely, on purpose |
| midiTruth | Lag and tuner from the note | Takes the pitch from the key you play, for the Auto lag and the tuner, rather than estimating it from the sound. | 112 | - |
| midiFollow | … and the timebase | Also sets the timebase from the note: about four periods of the lowest note held, so the wave keeps its size as you play. | 121 | - |
| acCorner | AC corner | Where AC coupling starts taking things away, 0.5 to 20 Hz. Ten removes a drift; twenty thins the bottom of a bass note too. | 123 | yes — at one hertz an asymmetric signal can read a third higher, which is AC coupling, not a fault; the corner reaches the speakers on Shaped |

### Scope & measure › Measure

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| readoutsOn | Readouts under the screen | Shows the numbers under the screen, a row per lane: peak, RMS, frequency, the nearest note, THD. Off to start. | 110 | yes — what each number means; the frequency is the sound’s period, and shows a dash rather than a guess |
| cursorsOn | Cursors | Two time and two level cursors to drag on the Y–T screen; the readout gives each pair’s difference, and Δt as a frequency. | 122 | - |
| measurePre | Numbers read | The numbers read the signal as it arrived, before the Plane’s Turn. | 67 | - |
| measurePost | Numbers read | The numbers read the signal after the Plane’s Turn, as the screen shows it. The level meter and Clipping stay on the signal. | 124 | - |
| saveReference | Save reference | Freezes the trace on screen and keeps it dashed behind the live one in Y–T, so you can see what a change did. | 109 | - |
| clearReference | Clear | Takes the saved reference trace off the screen. | 47 | - |

### Picture › Advanced › Panes

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| goniOn | Goniometer & correlation | A pane beside the screen: left against right turned 45°. Upright is mono, a circle is wide, flat means the channels fight. | 122 | - |
| spectrumOn | Spectrum | A pane beside the screen showing how much of the sound is at each frequency. | 76 | - |
| harmonicsOn | Harmonics & THD | A pane of the fundamental and its partials as bars, with the distortion they add up to. Needs a tone; noise gets no number. | 123 | - |
| tunerOn | Tuner | A pane naming the nearest note, with a needle for how many cents off; against the key you play, if there is one. | 112 | - |
| spectroSpan | Span | How many seconds the spectrogram shows across the screen, two to thirty. Only in the Spect display. | 99 | - |

### Find a control

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| benchSearch | Find a control | Finds any control by name, and by a few other words (adsr, lfo). Choosing a result opens whatever it is behind. Press / from anywhere. | 134 | - |

### Preset browser

| id | name | line | chars | paragraph |
|---|---|---|---|---|
| presetNew | New · a still sine | Loads the still sine the instrument opens on, with the picture at nought, and closes the browser: a start for a sound of your own. | 130 | - |
| presetClose | Close | Closes the browser and keeps what is loaded. Choosing a card loads nothing; Load or a double-click does. | 104 | - |
| presetLoad | Load | Loads the chosen sound and leaves the browser open, to compare it with another. Enter or a double-click loads and closes. | 121 | - |
| presetSaveOpen | Save this sound… | Opens a field to name the sound as it is now and keep it under Saved, in this browser, with its figure as the thumbnail. | 120 | - |
| presetName | Save this sound as | The name to keep the sound under; Enter saves. A name already saved is replaced without asking. | 95 | - |
| presetSave | Save | Keeps the sound under Saved in this browser, with what is sounding now as its figure. The setup code takes it elsewhere. | 120 | - |
| presetDelete | Delete saved | Deletes the saved sound chosen, or the saved one loaded, from this browser, without asking. The bank’s own cannot be deleted. | 125 | - |
| presetCode | Setup code | The whole setup as text: copy it to send a sound to someone, or paste one in and press Paste to load it. | 104 | yes — what a code holds and does not (the source, the fade, Settings), and that the site and the plugin read each other’s |
| presetCopy | Copy | Copies the setup code of the sound as it is now, for a message, another browser or the plugin. | 94 | - |
| presetPaste | Paste | Loads the code pasted into the field, or else the one on the clipboard if the browser hands it over. | 100 | - |
