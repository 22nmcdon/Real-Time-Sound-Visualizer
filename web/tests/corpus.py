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
    corpus.install(page)      after the page has loaded: window.CORPUS (PRESETS' shape),
                              corpusSetup(name), and loadCorpus(name), which loads it as a
                              preset is loaded - restored, and sent to the site's
                              instrument - without marking a preset in use
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
  window.loadCorpus = (name) => {
    const s = corpusSetup(name);
    hostQuietly(() => restore(s));
    hostSendSetup();
    return s;
  };
}"""


def install(page):
    page.evaluate(INSTALL, LIBRARY)
