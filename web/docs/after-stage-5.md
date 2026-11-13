# After stage 5

Agreed with the owner on 13 November: while stage 5 retires the page's engine
(`plugin/STAGE5-PLAN.md`), anything found along the way that can wait is written
down here instead of fixed, together with whatever the owner finds by playing it.
They are picked up once stage 5 is done, so the stage does not grow sideways and
nothing is lost. Each entry says who found it, when, and what is known so far.

## Defects on the site

- **Learn's split point does not reach the instrument.** On the default page,
  learning a split point moves the face's point only; the core keeps splitting at
  C4. Found by step 3's batch 2 (13 Nov), recorded in `STAGE5-INVENTORY.md`. A
  player would hit this.
- **A MIDI clock byte inside a note-on loses the note.** The page's `midiBytes`
  cuts at every status byte and the core's keyboard drops the half message.
  Web MIDI and the plugin's host hand over whole messages, so in practice this
  can hardly happen; low priority. Found by batch 2 (13 Nov).
- **Stop does not hold the instrument's picture, so Scan goes on moving with the
  screen stopped.** On the default page Stop (`setRunning(false)`) holds the
  face's screen and stops what the score and the arpeggiator sent, and tells
  the instrument nothing: it goes on drawing its own grid and Scan goes on
  reading it, so a scanned fifth's timbre keeps wandering under a stopped
  screen (0.0084 held against 0.0079 running, where the page's own brain
  holds still at 0.0001-0.0002). Scan's docstring, the first-minute test and
  striketest's description of Stop ("which holds the screen and so the
  tone") all say it should hold. Whether Stop should reach the instrument -
  freeze its grid, or its reading - is the owner's call, and the plugin,
  which has no Stop, may want the same answer. Found by step 3's batch 3 (13
  Nov); scantest.py's held run stays on `?brain=js&core=js` until then.
- **The generator still sounding 400 ms after it was set silent.** Strike's
  null once failed with readings reproduced exactly by a generator left
  audible, as if `genSet("amp", 0)` had not landed. It could be a race between
  the page and the audio engine; it did not recur in four runs alone. Found by
  the flaky-test pass (13 Nov).

## Sounds and presets

- **Bass under the tine piano and Bass under the pad sit on their headings'
  edges with the reverb switched on.** Rendered offline through the core, the
  tine piano reads 0.009 to 0.019 against Settled's 0.015 depending only on
  where the key lands, and the pad 0.020 to 0.025 against Breathing's 0.02
  floor. The test measures truly; the presets are the question. Parked with the
  owner's decision on the Tine piano (12 Nov). `core/tests/tools/honesty_cpp.cpp`
  measures it.

## Tests

- **The loop suite's fold check** passes only through its "saturated"
  exemption on the crossed split and the reverb at full, reading 0.032 to 0.043
  against a 0.05 bound, and goes red when a run misses saturation. It needs a
  better rule for what passing means, not a moved bound. Its Scan read-count
  check counts timer reads in real seconds and once failed at exactly its bound.
- **The hand suite's split fit** does not go red for the lower hand with the
  bass a semitone off (the upper hand's does): at 131 Hz a semitone moves the
  fit too little in a 10 ms window. Noted at the site by batch 1.

## Owner's list

- A few minor things from trying the click, swell and Width fixes on the testing
  site (13 Nov), to be written here.
- Offered and not yet answered: a small "Testing" label in the header shown only
  on the testing site, so the two pages can be told apart without reading the
  address.

## Already planned for after stage 5

- Each voice's real cycle sent from the core to the page, which is what brings
  the constellation back honestly (`ways-to-draw.md`, "The prototype's
  shortcut, and what fixes it").
- Closing the painting loop: Scan reading the painting live while the phrase
  plays, and the painting painted from the changed sound
  (`painting-the-sound.md`).
