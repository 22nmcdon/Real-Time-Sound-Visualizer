"""The hands (G6 of web/docs/the-face-second-pass.md): which hand the face
edits, and a link on each section that a hand can have its own of.

What would go wrong, and what is checked for it, each with a null:

- the selector shown with one hand, or named wrong: Lower and Upper on a
  split, A and B layered, and hidden with the layers off;
- a section without its link, or a link shown with one hand: one on each of
  the eleven the design lists, in the section it names;
- linked, a hand moved and the other left behind; unlinked, both moved. Read
  off each hand's settings as the face holds them (genSettings), not off the
  panel, which shows one;
- unlinking that does not start the other hand as a copy, or linking again
  that does not copy the hand on the face over the other;
- a new split starting with a section already parted, and a code from
  before G6 - every B value written - loading linked, which would make the
  first knob moved on it move the other hand too; and a code without B
  values loading parted;
- the Picture amount and Strike shared where the hands should each have
  their own: each hand's kept and shown, and carried by a code (what each
  is heard to do is parity's, below);
- a routing on a linked control moving one hand, or on an unlinked one
  moving both, and its row not saying which;
- the tab cards not saying what differs, or saying it with one hand.

On the default page since stage 5's step 3 (13 Nov); on ?brain=js until
then, where `genSettings(0/1)` were the page generator's two layers. Here they
are the page's mirror of the setup (makeGeneratorMirror), which the face
writes through the links and sends to the instrument: so these checks hold
the face's linked editing, and that the instrument links the same moves the
same way is core/tests/parity.py's "the hands on the panel (G6)", which plays
random hands through the page's handlers and the core's and compares them.
That is a narrower claim than "read off the generator", said so here rather
than left to look the same. Four checks of numbers went to parity's native
instrument then, as assertions on the core's own output ("Each hand's Picture
Amount and Strike"): the stage's routes pushing both hands at one Amount
linked and the upper not at all at its own nought (with their null), read
here off the page's route compiler with the stage's glow put in by hand; and
a note's strike at each hand's own Strike, read here off the page's scanStrike
with its picture's segment hooked. Neither runs on the default site.
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)
def null(name, red, detail=""):
    """A check's null: the same comparison fed a value it must reject."""
    check("null: " + name, red, detail)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text) if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html?picture=0"); p.wait_for_timeout(800)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)
    # Two hands want a keyboard and poly; each case starts from the base, linked throughout.
    p.evaluate("""() => {
      window.__layers = (mode) => { el.midiLayers.value = mode; el.midiLayers.dispatchEvent(new Event('change')); };
      window.__click = (id) => document.getElementById(id).click();
      window.__input = (id, v) => { el[id].value = String(v); el[id].dispatchEvent(new Event('input', { bubbles: true })); };
      window.__fresh = (mode) => { restore(BASE_SETUP); setScreenKeys(true); setMidiMode('poly'); __layers(mode); __click('editHandA'); };
    }""")

    print("\n--- the selector ---")
    sel = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const read = () => ({ shown: !document.getElementById('handsPick').hidden,
        names: [...document.querySelectorAll('#handsPick .hand-name')].map((n) => n.textContent),
        checked: ['editHandA', 'editHandB'].filter((id) => document.getElementById(id).getAttribute('aria-checked') === 'true') });
      __fresh('off'); await wait(50); const off = read();
      __layers('split'); await wait(50); const split = read();
      __click('editHandB'); await wait(50); const upper = Object.assign(read(), { edit: editLayer(), panel: panelLayer });
      __layers('layer'); await wait(50); const layer = read();
      __layers('off'); await wait(50); const offAgain = Object.assign(read(), { edit: editLayer() });
      return { off, split, upper, layer, offAgain, inHeader: !!document.querySelector('header #handsPick') };
    }""")
    check("the selector is in the header and hidden with one hand",
          sel["inHeader"] and not sel["off"]["shown"] and not sel["offAgain"]["shown"], str(sel["off"]))
    check("shown on a split, naming the hands Lower and Upper, the lower chosen",
          sel["split"] == {"shown": True, "names": ["Lower", "Upper"], "checked": ["editHandA"]}, str(sel["split"]))
    check("Upper chosen puts the upper hand on the panel",
          sel["upper"]["checked"] == ["editHandB"] and sel["upper"]["edit"] == 1 and sel["upper"]["panel"] == 1, str(sel["upper"]))
    check("layered, the hands are A and B", sel["layer"]["shown"] and sel["layer"]["names"] == ["A", "B"], str(sel["layer"]))
    null("the split's names are not the layered names", sel["split"]["names"] != sel["layer"]["names"])
    null("one hand is no hand to edit: the panel is the lower's with the layers off", sel["offAgain"]["edit"] == 0)

    print("\n--- a link on each section ---")
    links = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const where = (id) => {
        const b = document.getElementById(id);
        if (!b) return null;
        const group = b.closest('.menu-group, .fx-module, .picture-name');
        return group ? (group.dataset.fx || group.id || group.className) : null;
      };
      const ids = ['linkGen', 'linkAmpEnv', 'linkVcf', 'linkOsc', 'linkShp', 'linkPicture', 'linkPlane', 'linkPhaser',
                   'linkChorus', 'linkDelay', 'linkReverb'];
      __fresh('off'); await wait(50);
      const offShown = ids.filter((id) => !document.getElementById(id).hidden);
      __layers('split'); await wait(50);
      const onShown = ids.filter((id) => !document.getElementById(id).hidden);
      return { where: Object.fromEntries(ids.map((id) => [id, where(id)])), offShown, onShown,
               words: ids.map((id) => document.getElementById(id).textContent),
               keyboard: !!document.querySelector('#midiGroup .hand-link, #expressionGroup .hand-link') };
    }""")
    check("a link on the Generator, the Amp envelope and the Voice filter on Play, the Oscillator and Shaping on Ink, "
          "each rack module, and the Picture section",
          links["where"] == {"linkGen": "toneRows", "linkAmpEnv": "ampEnvGroup", "linkVcf": "vcfGroup", "linkOsc": "oscGroup",
                             "linkShp": "shpGroup", "linkPicture": "picture-name", "linkPlane": "plane", "linkPhaser": "phaser",
                             "linkChorus": "chorus", "linkDelay": "delay", "linkReverb": "reverb"}, str(links["where"]))
    check("and none on the Keyboard, which is both hands by nature", not links["keyboard"])
    check("each shown with two hands and saying the same in both", len(links["onShown"]) == 11
          and links["words"] == ["Same in both"] * 5 + ["Both"] * 6, str(links["words"]))
    null("with one hand none is shown", links["offShown"] == [], str(links["offShown"]))

    print("\n--- linked, both hands; unlinked, the one on the face ---")
    edit = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      __fresh('split'); await wait(50);
      const amps = () => [genSettings(0).amp, genSettings(1).amp];
      __click('editHandB'); __input('amp', 30); const linkedB = amps();
      __click('editHandA'); __input('amp', 40); const linkedA = amps();
      // The upper hand's own: the lower's start, then each its own.
      __click('editHandB'); __click('linkGen'); const afterUnlink = amps();
      const code = snapshot();
      __input('amp', 90); const ownB = amps();
      __click('editHandA'); __input('amp', 20); const ownA = amps();
      // Linked again from the upper: the upper's copied over the lower's.
      __click('editHandB'); __click('linkGen'); const relinked = amps();
      // And from the lower, as the null: the lower's over the upper's.
      __click('linkGen'); __input('amp', 70); __click('editHandA'); __click('linkGen'); const relinkedA = amps();
      return { linkedB, linkedA, afterUnlink, ownB, ownA, relinked, relinkedA, codeB: code.bAmp, codeA: code.amp };
    }""")
    check("linked, a knob moved on the upper hand moves both, and on the lower both",
          edit["linkedB"] == [0.3, 0.3] and edit["linkedA"] == [0.4, 0.4], "%r %r" % (edit["linkedB"], edit["linkedA"]))
    check("unlinked, the hand on the face alone", edit["ownB"] == [0.4, 0.9] and edit["ownA"] == [0.2, 0.9],
          "%r %r" % (edit["ownB"], edit["ownA"]))
    null("linked and unlinked differ", edit["ownB"] != [0.9, 0.9])
    check("unlinking starts the other hand as a copy, and a code then carries it as the hand's own",
          edit["afterUnlink"] == [0.4, 0.4] and edit["codeB"] == 40 and edit["codeA"] == 40, str(edit))
    check("linking again from the upper copies the upper over the lower", edit["relinked"] == [0.9, 0.9], str(edit["relinked"]))
    # The lower at 0.9 and the upper at 0.7 when it is linked from the lower: the lower's wins.
    null("from the lower, the lower over the upper", edit["relinkedA"] == [0.9, 0.9] and edit["relinkedA"] != [0.7, 0.7],
         str(edit["relinkedA"]))

    print("\n--- a new split, and codes from before ---")
    codes = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const own = () => HAND_SECTION_IDS.filter((s) => !linked(s));
      __fresh('split'); await wait(50); const fresh = own();
      // As every code before G6 had them: snapshotLayerB wrote every B field.
      restore({ layers: 'split', midiMode: 'poly', amp: 50, bAmp: 30, bShape: 'sine', bAtk: 8, bFm: 0, bDrive: 0, bVcf: 0, bScan: 0 });
      await wait(50); const old = own();
      const beforeMove = genSettings(0).amp;
      __click('editHandB'); __input('amp', 70); const oldMoved = [genSettings(0).amp, genSettings(1).amp];
      restore({ layers: 'split', midiMode: 'poly', amp: 50 }); await wait(50); const plain = own();
      // Every B value A's, as a code saved before G6 with the hands one wrote them; then one a step apart.
      const same = { layers: 'split', midiMode: 'poly', amp: 50, bAmp: 50, shape: 'ramp', bShape: 'ramp', atk: 8, bAtk: 8,
                     bFm: 0, bDrive: 0, bVcf: 0, bScan: 0, bPlane: true, delayMix: 20, bDelayMix: 20, bTwist: 0 };
      restore(same); await wait(30); const allSame = own();
      restore(Object.assign({}, same, { bAtk: 9 })); await wait(30); const oneApart = own();
      // A rack module's B fields count only with bPlane, as they always did.
      restore({ layers: 'split', midiMode: 'poly', bPlane: true, bDelayMix: 40 }); const rack = own();
      restore({ layers: 'split', midiMode: 'poly', bPlane: false, bDelayMix: 40 }); const rackOff = own();
      __click('editHandA');
      return { fresh, old, beforeMove, oldMoved, plain, rack, rackOff, allSame, oneApart };
    }""")
    check("a new split starts with everything linked", codes["fresh"] == [], str(codes["fresh"]))
    # The owner's call on G6: a section is the hand's own only where a B value
    # differs from A's. This code's level and shape differ; its attack,
    # FM, drive, filter and Scan are A's, as every code before G6 wrote them.
    check("a code with B values loads the hand's own only where they differ from A's, the rest linked",
          codes["old"] == ["gen"], str(codes["old"]))
    check("an old code whose every B value is A's loads linked throughout", codes["allSame"] == [], str(codes["allSame"]))
    null("one B value a step apart loads that section as the hand's own and the rest linked",
         codes["oneApart"] == ["ampEnv"], str(codes["oneApart"]))
    check("so moving the upper hand there leaves the lower as the code had it",
          codes["oldMoved"] == [0.5, 0.7] and codes["beforeMove"] == 0.5, str(codes["oldMoved"]))
    null("a code without B values loads linked", codes["plain"] == [], str(codes["plain"]))
    check("a rack module's B fields make it the hand's own with bPlane on, and not with it off",
          codes["rack"] == ["delay"] and codes["rackOff"] == [], "%r %r" % (codes["rack"], codes["rackOff"]))

    print("\n--- the Picture section, per hand ---")
    pic = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      __fresh('split'); await wait(50);
      __input('pictureAmount', 100);
      __click('editHandB'); __click('linkPicture');
      __input('pictureAmount', 0); __input('scanStrike', 0);
      const hands = pictureHands.map((h) => [h.amount, h.strike]);
      const title = el.pictureHandName.textContent;
      const shown = { amount: el.pictureAmount.value, strike: el.scanStrike.value };
      __click('editHandA'); const shownA = { amount: el.pictureAmount.value, strike: el.scanStrike.value };
      const code = snapshot();
      return { hands, title, shown, shownA,
               code: { a: code.pictureAmount, b: code.bPictureAmount, sa: code.scanStrike, sb: code.bScanStrike } };
    }""")
    # The stage's routes per hand at one Amount, and its null: parity's now (see the top).
    check("each hand keeps its own Amount and Strike, the sliders show the hand on the face, and the title says which",
          pic["hands"] == [[100, 50], [0, 0]] and pic["shown"] == {"amount": "0", "strike": "0"}
          and pic["shownA"] == {"amount": "100", "strike": "50"} and pic["title"] == " · Upper", str(pic))
    # A note's strike at each hand's own Strike: parity's now (see the top).
    check("and a code carries each hand's Amount and Strike", pic["code"] == {"a": 100, "b": 0, "sa": 50, "sb": 0}, str(pic["code"]))

    print("\n--- routings follow the link ---")
    rt = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      __fresh('split'); state.modRoutings = []; touchRoutings(); await wait(30);
      const route = (dest) => state.modRoutings.find((r) => r.sourceId === 'lfo1' && r.destId === dest);
      /* Each hand's depth as the face keeps it and a code carries it (mod,
         and modB for the upper's own), which is what the instrument is sent.
         On ?brain=js this read the page's route compiler for its own worklet
         (workletRoutes), which the default site never runs; the core's per-hand
         depth is the matrix's, held by parity. */
      const sent = (dest) => { const r = route(dest); return r ? [r.amount, r.amountB === undefined ? r.amount : r.amountB] : null; };
      const tags = () => { openModCard('lfo1'); const t = [...el.srcDetail.querySelectorAll('.mod-edit')].map((l) =>
        (l.querySelector('.hand-tag') || {}).textContent || ''); closeModCard(); return t; };
      __click('editHandB');
      addRouting('lfo1', 'gen.fm'); setDepth(route('gen.fm'), 40, true);
      const linkedFm = sent('gen.fm'), linkedTags = tags(), linkedB = route('gen.fm').amountB;
      __click('linkOsc');
      setDepth(route('gen.fm'), -20, true);
      const ownFm = sent('gen.fm'), ownTags = tags();
      // A new routing on an unlinked control, the upper hand on the face: the upper's alone.
      addRouting('lfo1', 'gen.drive'); __click('linkShp');
      state.modRoutings = state.modRoutings.filter((r) => r.destId !== 'gen.drive');
      addRouting('lfo1', 'gen.drive'); const driveB = [route('gen.drive').amount, route('gen.drive').amountB];
      const driveTags = tags();
      const code = snapshot();
      __click('editHandA'); const onLower = routingsFor('gen.drive').length, onUpper = (() => { __click('editHandB'); return routingsFor('gen.drive').length; })();
      __click('editHandA');
      return { linkedFm, linkedTags, linkedB, ownFm, ownTags, driveB, driveTags, mod: code.mod, modB: code.modB, onLower, onUpper };
    }""")
    check("a routing on a linked control moves both hands at one depth, and its row says Both",
          rt["linkedFm"] == [0.4, 0.4] and rt["linkedB"] is None and rt["linkedTags"] == ["· Both"], str(rt))
    check("on an unlinked one a depth set with the upper hand on the face is the upper's alone, and its rows say each hand",
          rt["ownFm"] == [0.4, -0.2] and sorted(rt["ownTags"]) == ["· Lower", "· Upper"], "%r %r" % (rt["ownFm"], rt["ownTags"]))
    null("the linked depths are not the unlinked", rt["linkedFm"] != rt["ownFm"])
    check("a routing added to an unlinked control with the upper on the face is the upper's alone, said so, and stored as modB",
          rt["driveB"][0] == 0 and rt["driveB"][1] > 0 and rt["driveTags"].count("· Upper") == 2
          and "lfo1>gen.drive@0.000" in rt["mod"] and "lfo1>gen.drive@" in rt["modB"] and "lfo1>gen.fm@-0.200" in rt["modB"],
          "%r %r %r" % (rt["driveB"], rt["mod"], rt["modB"]))
    check("and its knob has it on the upper hand and not the lower", rt["onUpper"] == 1 and rt["onLower"] == 0,
          "%r %r" % (rt["onLower"], rt["onUpper"]))

    print("\n--- the tab cards ---")
    cards = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const lines = () => { paintTabLines(); return ['play', 'ink', 'space'].map((id) => document.getElementById('benchLine-' + id).textContent); };
      __fresh('split'); state.modRoutings = []; touchRoutings(); await wait(30);
      const none = lines();
      __click('editHandB'); __click('linkGen'); __click('linkVcf'); const two = lines();
      __click('linkVcf'); const one = lines();
      __layers('off'); const off = lines();
      return { none, two, one, off };
    }""")
    check("a tab where the hands differ says so first, in the hand on the face's name: Play, Generator and Voice filter",
          cards["two"][0] == "Upper differs in 2" and "differs" not in cards["two"][1] and "differs" not in cards["two"][2], str(cards["two"]))
    check("and counts what differs", cards["one"][0] == "Upper differs in 1", str(cards["one"]))
    null("linked throughout, no tab says so", not any("differs" in l for l in cards["none"]), str(cards["none"]))
    null("with one hand, none says so", not any("differs" in l for l in cards["off"]), str(cards["off"]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the hands are each the face's to edit, and linked where they share")
