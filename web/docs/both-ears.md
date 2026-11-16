# Both ears: hearing every note in both, and what it does to the picture

The owner, 16 Nov, after hearing options A to D of [`one-to-two-notes.md`](one-to-two-notes.md):
*"this didn't really fix the problem, it solved some of it, but the solutions given still have
the sounds jumping in and out of each ear. This is also especially prevalent with the new note
which only appears in one ear when played. Why can't the sound just reach both ears? Would that
affect the picture or cause the picture to not be true to sound?"*

The cause is the rule every earlier fix kept: the heard pair is the screen's X and Y, so a note's
place between the ears is its place on the screen, and a second note has to go somewhere on it.
A listening study, with takes on [`listening/both-ears/index.html`](listening/both-ears/index.html).
Nothing in the instrument has changed: both ways are compile-time switches in a scratch copy of
`core/include`, kept with the page's scripts in `listening/both-ears/make/`.

## The two ways

**Way 1: what is heard, apart from what is drawn.** The screen, Scan and every reading of the
loop are made from the voices' roles exactly as today. What comes out of the speakers is a second
mix of the same voices, each in both ears with an image of its own that never depends on what else
is held. Three widths were built:

- **(a) nearly mono:** each voice the same in both ears.
- **(b) gentle width:** each voice's left an *eighth* of its own period behind its right - half
  today's quarter turn - so a note is a little wide and centred at every pitch (its fundamental's
  coherence 0.71). A turn of the note's own period was chosen over a fixed Haas delay, since a
  fixed half a millisecond would leave a low C almost mono and comb-filter a high one.
- **(c) wide:** each voice its own quarter turn, which is a lone note today, for every note always.

In Poly each voice's heard image is a ring of its own beside the one the quarter turn already
keeps. In Dyad the heard mix treats the dyad as two voices, the lower note on the left phase and
the upper on a phase of its own kept from the right's while the interval is not a unison, each with
its own copy of the shaping, crush and filter; the upper note is faded in and out over 10 ms there,
since in the heard mix it can no longer turn into the lower note as the drawn right channel does.
The Phase knob sets the dyad's angle between the ears as it does today ((b) takes half of it). What is
heard goes through a second plane, set and stepped exactly as the first, so the effects and the
shaping act on it as on the picture.

**Way 2: heard and drawn stay one, every note on both sides.** That mix at (c) is what is drawn as
well: the one-to-two page's option D in Poly, carried to Dyad. The speakers are still the screen,
and the figure of one note drawn *against* another goes: the screen draws the notes' rings summed.

## What was measured

Two phrases through the core offline (`render_cpp`, 44.1 kHz). The owner's: Harmonic tone (Dyad),
C2 from 0.2 s, E4 added at 1.8 s and let go at 3.4 s, C2 alone until 5.2 s. And a chord on Tine
piano (Poly, Scan at 50): C3, then E3, G3 and C4 added at 0.9 s steps, let go from the top at 0.9 s
steps. Each note is read off its own fundamental by lock-in in each ear: its level in each, and the
coherence of the two (1 the same in both ears, 0 a quarter turn, -1 opposite). The owner's phrase
with the picture off, as the one-to-two page read it; the chord on Tine piano's voices made plain
(one sine each: its FM, Scan and routings off, held at full) so that every note's fundamental is its
own; and both with the limiter off, whose share is read apart.

### Each note at every entry and exit

| | C2 alone | C2 with the E | E4 | C2 alone again | C2 again, sixteen releases |
|---|---|---|---|---|---|
| Today | -10.4 / -10.4, 0.00 | -10.4 / gone, 0.00 | gone / -10.4 | -10.4 / -10.4, 0.99 | -0.99 to 0.99 |
| Way 1 (a) | -10.4 / -10.4, 1.00 | the same | the same | the same | 1.00 every time |
| Way 1 (b) | -10.4 / -10.4, 0.71 | the same | the same | the same | 0.71 every time |
| Way 1 (c), Way 2 | -10.4 / -10.4, 0.00 | the same | the same | the same | 0.00 every time |

Left and right in dB, then coherence; *gone* is more than 40 dB under the other ear (today's E4 is
92 dB under in the left: it is in the right ear only, as the owner heard). With the picture on, as
shipped, the bass's balance holds within 0.1 dB and its coherence within 0.06 in every way and
every span; today, while the E is held, what the picture puts back of the bass into the right ear
swings between 42 and 15 dB under the left.

On the chord, today, every change of the chord moves a note: the lowest and highest held lean 6 dB
to their sides and lose their width (coherence 1.00), an inner note sits in the middle with its
quarter turn. E3 arrives at the right edge (-13.3 / -7.3) and moves to the middle (-9.3 / -9.3,
0.00) when G3 arrives; G3 the same when C4 arrives, and back when C4 goes; the held C3 leans
(-7.3 / -13.3) from the second note until it is alone again. In every Way 1 width and in Way 2,
every note reads -7.3 dB in each ear in all seven spans, with one coherence throughout (1.00, 0.71,
0.00, 0.00).

### A second cause: the limiter

The limiter is last of all, on what is heard, and pulls the whole sound down as it gets loud, so a
held note gets quieter as others join it, in both ears alike. On the plain chord held at full the
held C3 is 1.8 dB under its level alone with three notes and 3.1 with four, today; with every note
in both ears at full the pair is louder in each ear and it pulls 3.3 and 4.3 dB (Way 1 (b)), 3.4 and
4.5 (Way 2). Tine piano itself decays to a quarter while held and the limiter does much less; on the
owner's phrase its share is under 0.3 dB, the same in every version. Ways 1 and 2 are 1.0 dB louder
than today overall on the owner's phrase and 1.5 dB on the chord; a build would take that back with
the level.

## Way 1 leaves the picture and Scan unchanged, to the bit

Each Way 1 build against the core, on both phrases, byte for byte: the six drawn lanes at every
sample (264,600 and 321,930), the shown grid at every hundredth of a second (9.8 and 12.0 MB), and
7,800 and 9,490 reading lines - Scan's table, the picture's six sources and reads, every routing's
depth, the stages, the meters and their verdicts. All the same, in all three widths. The nulls: the
copy with every switch off renders the core's heard pair to the bit as well, so the copy is the
core; every Way 1 build's heard pair differs from today's, so the comparison sees a difference where
there is one; and Way 2 fails the drawn comparison, lanes, grid and readings.

**What Way 1 changes about honesty to the sound.** The speakers are no longer the screen: a real
oscilloscope fed the output draws a different figure from the one on the screen (the page draws
both). Every note heard is still drawn and everything drawn is heard, which is the rule
`making-it-one-instrument.md` kept in its Question 2 (*"kept as coherence rather than identity:
nothing is heard that is not drawn"*); what goes is P4's *"a voice is heard where it is drawn"*.
Everything the loop does is unchanged: the picture, its reads, Scan's table and every depth are
today's, and they act on the heard notes as on the drawn ones. One thread runs from the heard pair
back into the loop: the limiter's reduction is handed to the picture meter, whose *running away*
verdict trips past 6 dB of it, and Way 1, louder in each ear, works the limiter harder on a loud
held chord (6.1 dB at most on the plain chord against 4.3 today). It changed no verdict in any run
here; a build would either accept it or hand the meter the limiting the drawn pair would have needed.

## What each costs

- **Way 1** costs the heard pair being X and Y, and processing: what is heard goes through a second
  plane (the phaser, chorus, delay and reverb, and the oversampled shaping stage, run twice: the
  governor has to count it), and a dyad's two notes need two voice chains each where they had one.
  Poly's per-voice image is one more read of a ring per voice. The picture loses nothing. Its three
  widths differ only in the ear: (a) is the steadiest and least spacious, and drops the Phase knob's
  effect on what is heard (the Phase is the angle between the ears); (c) is a lone note today, for
  every note; (b) is between, and safer summed to mono.
- **Way 2** costs the figure: a dyad no longer draws its X-against-Y figure and a chord's outer
  notes are no longer the figure's axes - harmony as geometry, the first feature the plan ranks,
  loses the figure it is built on. Scan reads the new figure, so every Poly preset's sound changes
  and is measured again (`honestytest.py`), and the bank's thumbnails are drawn again.

## Recommendation

**Way 1, at (b) or (c) as the ear says.** It answers the question as it was asked: the sound
reaches both ears and the picture is not touched. Way 2 keeps the speakers and the screen one by
giving up the two-note figure. Between the widths, (c) is what one note already sounds like, so
nothing changes until a second note arrives; (b) keeps a chord narrower. The one-to-two page's
option A is still worth having for the picture's sake: the drawn dyad still comes back at whatever
angle a release catches, and the picture shapes the sound.

What building Way 1 would take: a heard mix beside `c.mix` in `sound` (`scope/voices.h`) and in
`Generator::block`'s Dyad path (`scope/generator.h`), on the oscillator's and the noise's paths as
well as the plain wave's, which is all the prototype covers, and for layer B; a second plane, set
and ticked with the first; the governor's cost for both; and the limiter-to-meter thread decided.
It means the sound to change, so the golden recordings of anything played are rewritten with
`--write-golden --because`; `core/tests/pieces/` grows a check that the drawn lanes, grid and Scan's
table are the same to the bit with the heard mix on and off (its null: Way 2), and one that a held
note's image does not move as notes join it (its null: today's core); and the controls' words for
Quarter turn, Phase and the Width say what they do to what is heard.
