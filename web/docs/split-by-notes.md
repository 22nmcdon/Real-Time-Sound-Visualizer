# Splitting the hands by notes

Asked for by the owner on 15 November, after playing the site: besides splitting
the keyboard at a key, a split by the notes held - the bottom few notes are the
lower hand and the rest the upper, or the other way round, with the count
chosen. Not built yet; it waits for the owner's list of fixes to land, so it is
written down here first.

## How it behaves

- **A note's hand is fixed when the note starts** (the owner's call, 15 Nov). A
  held note keeps the hand it began in until it is let go, so nothing jumps
  between hands, and between figures, in the middle of a chord. The other way -
  re-sorting the held notes every time one starts or stops - was rejected for
  exactly that jump.
- **Which end is counted.** *Lower: N notes* gives the lowest N notes held to
  the lower hand and the rest to the upper; *Upper: N notes* the other way
  round. A new note's rank is taken among the notes held when it starts.
- **Fewer notes held than the count.** They all go to the counted hand until the
  count is reached. (A lean, not yet confirmed by the owner.)
- **The control.** The split row gains *Split: by key · by notes*; with *by
  notes*, the key's point is replaced by the end counted and the count. (A lean.)
- **Stored.** In setups and presets like the key split. It is a new answer to
  "which hand does this note go to", so per CLAUDE.md it becomes a structure,
  with a version-tagged decode pass on both sides so that every code before it
  loads as a key split. The core's keyboard decides the hand, so the site and
  the plugin agree, and core_tests holds it with its nulls.
