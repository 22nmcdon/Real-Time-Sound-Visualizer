"""The preset library as it stood before P8g, kept as a corpus of real setups.

Until P8g the library was 268 presets in 30 sections, and a good many suites
used it as more than a list of sounds: as the widest set of real setups the
page had, walked whole to ask whether every one stays inside the voice budget,
keeps its routings, draws the same on the compiled site as on the page, and so
on. P8g replaced it with a small bank under four headings, which would have
quietly shrunk every one of those checks to a dozen setups. So the old library
is kept, exactly as the page evaluated it, in
core/tests/scenarios/library-p8f.json, which parity reads too; and the suites
that walked it walk it here, beside the new bank where the new bank is what is
being asked about.

A suite that opened one old preset by name to have a known sound under its
check opens it from here, so the check goes on reading the sound it was
written against however the bank changes.

    corpus.LIBRARY            [[section, [[name, setup, line], ...], kind], ...], PRESETS' shape
    corpus.setup(name)        one preset's setup, as a dict
    corpus.old_opening(page)  after the page has loaded: put it on what it opened on until
                              P8h - the defaults and a timebase, the Picture amount at its
                              default unless ?picture=N holds it - and send it to the site's
                              instrument, for a suite written against that opening
    corpus.held_tone(page)    after the page has loaded: a note held, so the generator sounds
                              at its controls as it did with no note until 10 Nov (Mono, A3
                              at full velocity, the Frequency slider put back where it was);
                              heldTone() in the page after install, for the same inside a probe
    corpus.install(page)      after the page has loaded: window.CORPUS (PRESETS' shape),
                              corpusSetup(name), and loadCorpus(name), which loads it as a
                              preset is loaded - restored, and sent to the site's
                              instrument - without marking a preset in use; through
                              the decode passes after version 7, so what was cut since
                              loads as a saved code from then would
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "..", "..", "core", "tests", "scenarios", "library-p8f.json")
with open(PATH, encoding="utf-8") as f:
    LIBRARY = json.load(f)


def setup(name):
    for _, entries, _ in LIBRARY:
        for entry in entries:
            if entry[0] == name:
                return dict(entry[1])
    raise KeyError("no preset called %r in the old library" % name)


INSTALL = """(library) => {
  window.CORPUS = library;
  window.corpusSetup = (name) => {
    for (const [, entries] of library) for (const [n, s] of entries) if (n === name) return s;
    throw new Error('no preset called ' + name + ' in the old library');
  };
  /* Through the decode passes after the corpus's own format, as a code saved
     at P8f would be: it was written at version 6 (the latch, 7, it never
     had), and since version 8 its kaleidoscopes load without one and a snap
     under five bits at five. Without this a preset's Snap of 3 restored as
     Off, which restore's menu check is right to do with a current setup. */
  // held_tone's, below, for a probe that loads a setup and wants it sounding.
  window.heldTone = HELD_TONE_FN;
  window.loadCorpus = (name) => {
    const s = migrateSetup(Object.assign({}, corpusSetup(name), { v: 7 }));
    hostQuietly(() => restore(s));
    hostSendSetup();
    return s;
  };
}"""


def install(page):
    page.evaluate(INSTALL.replace("HELD_TONE_FN", HELD_TONE), LIBRARY)


# Until P8h the page opened on Harmonic tone, which was the defaults and a
# timebase; it opens on the base now, a plain still sine in poly and X-Y. A
# suite whose checks were written against the old opening - dyad, the
# harmonic tone, Y-T, the stage at 60 - puts the page back there, rather than
# every such check learning a new starting point that is meant to change by
# ear. ?picture=N still holds the amount, as it held it through the old one.
OLD_OPENING = """() => {
  const s = Object.assign({}, DEFAULTS, { timebase: 3 });
  if (pictureHeldByLink !== null) s.pictureAmount = pictureHeldByLink;
  hostQuietly(() => restore(s));
  hostSendSetup();
}"""


def old_opening(page):
    page.evaluate(OLD_OPENING)


# Until 10 Nov the site's generator sounded with no note while nothing was
# plugged in: its pitch the Frequency slider, its second channel the Interval
# menu, its level the Level knob. It waits for a note now, as the plugin does,
# so a suite written against that sound holds one, by the means a player has:
# Mono by its button (which the site's instrument hears, where setMidiMode
# alone it does not), so that the slider moves the held note and the menu
# sets the interval as they set the sound before; A3, which is 220 Hz, the
# old opening's pitch and Harmonic tone's; at full velocity; and the slider
# put back where it was, since the note moves it. Not a switch back to the
# drone: the amp envelope still shapes the note, so its level is the Level
# knob times the sustain - unless `full` puts the sustain at full first,
# for a suite whose figures were placed at the drone's size - and a setup
# loaded after it sets the keyboard's mode again (Harmonic tone's is Dyad,
# where one held note is a unison).
HELD_TONE = """(note = 57, full = false) => {
  const hz = el.freq.value;
  // Full: the sustain at full first, so the level is the Level knob's, as the drone's was.
  if (full) { el.envSustain.value = '100'; el.envSustain.dispatchEvent(new Event('input')); }
  el.midiMono.click();
  midiNoteOn(note, 127);
  el.freq.value = hz; el.freq.dispatchEvent(new Event('input'));
}"""


def held_tone(page, note=57):
    page.evaluate(HELD_TONE, note)
