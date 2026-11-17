"""Every info line holds to what the control was measured to do to the sound.

web/tools/reach_audit.py measures, for every control on the face, whether
moving it changes the sound - most of all the view's and the look's, which
reach it through the picture Scan reads (the zoom, the timebase, the turn, the
beam) - and writes the classes into web/docs/what-reaches-the-sound.table.json
beside the table in web/docs/what-reaches-the-sound.md. This holds the words
(web/docs/what-each-control-says.md, the info line's source) to that table:

- a control measured to reach the sound through the picture says so: its
  line names the sound, the tone, Scan or what is heard, and does not call
  itself only the look or say it changes nothing in the sound;
- a control measured look-only does not claim the sound moves with it;
- every control the info line describes that is on the face is in the table,
  so a control added since the audit fails here until it is measured.

Each rule is seen red first on a line made wrong on purpose (the nulls below),
as CLAUDE.md asks of every new check. No browser: it reads two files.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "web", "tools"))
import write_words  # noqa: E402

TABLE = os.path.join(ROOT, "web", "docs", "what-reaches-the-sound.table.json")
REACHES = "REACHES THE SOUND THROUGH THE PICTURE"

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

# What a line has to say to tell the player the sound moves with it.
# The speakers alone are not enough: "the speakers get it on Shaped" is a
# claim about the direct path, which the instrument does not take (the table's
# hearWet), and says nothing of the picture's.
# And "a pure tone" is not the tone changing: Scan, or the sound or the tone by name.
SAYS_SOUND = re.compile(r"\bScan\b|\bthe (sound|tone)\b", re.I)
# And what a line says when it claims the sound does not.
SAYS_LOOK = re.compile(r"only the look|nothing it does changes the sound|never reaches the sound|"
                       r"the sound is the same|changes? only the picture", re.I)


def says_reach(line):
    return bool(SAYS_SOUND.search(line)) and not SAYS_LOOK.search(line)


def says_still(line):
    """A line claiming the sound moves with it: names the sound changing, not only Scan."""
    return bool(re.search(r"(changes|moves|turns|reaches) the (sound|tone)|the sound (changes|turns|moves)", line, re.I)) \
        and not SAYS_LOOK.search(line)


def wrong(rows, words):
    """Each row whose line breaks the table: (id, why)."""
    out = []
    for r in rows:
        line = (words.get(r["id"]) or [None, ""])[1]
        if not line: continue
        if r["class"] == REACHES and not says_reach(line):
            out.append((r["id"], "reaches the sound through the picture, and its line does not say so"))
        if r["class"] == "look-only" and says_still(line):
            out.append((r["id"], "reads nought, and its line says the sound moves with it"))
    return out


rows = json.load(open(TABLE))
# REACH_WORDS reads another copy of the words, for the null against the lines as they stood before the audit.
words = write_words.parse(open(os.environ.get("REACH_WORDS") or write_words.DOC, encoding="utf-8").read())
by_id = {r["id"]: r for r in rows}

print("\n--- the info lines against what was measured ---")
bad = wrong(rows, words)
check("every control that reaches the sound through the picture says so in its line, and no look-only one claims it",
      not bad, "; ".join("%s: %s" % b for b in bad) or "%d reach, %d look-only" % (
          sum(r["class"] == REACHES for r in rows), sum(r["class"] == "look-only" for r in rows)))

# The nulls: each rule fed a line made wrong, which it must find.
zoom = dict(by_id.get("zoom") or {"id": "zoom", "class": REACHES})
check("null: a reaching control whose line says only the look is found",
      wrong([dict(zoom, **{"class": REACHES})], {"zoom": ["Zoom", "Magnifies the figure. Only the look."]}) != [])
check("null: and one whose line never names the sound, the tone or Scan",
      wrong([dict(zoom, **{"class": REACHES})], {"zoom": ["Zoom", "Magnifies the figure on the screen."]}) != [])
check("null: a look-only control claiming the sound turns with it is found",
      wrong([{"id": "graticuleOn", "class": "look-only"}], {"graticuleOn": ["Graticule", "Rules the screen; the sound turns with it."]}) != [])
check("null: a line that names only a pure tone is not taken for one saying the tone changes",
      wrong([dict(zoom, **{"class": REACHES})], {"zoom": ["Zoom", "A pure tone draws a circle."]}) != [])
check("null: and the line that passes is passed, so the rule is not red on everything",
      wrong([dict(zoom, **{"class": REACHES})], {"zoom": ["Zoom", "Magnifies the figure, and so what Scan reads."]}) == [])

# Coverage: every control the words describe that the audit found on the
# face is in the table. The words also describe controls with no id (by
# their data-say key) - those are not in the table and not asked for.
on_face = set(by_id)
missing = [k for k in words if k in on_face and not by_id[k].get("class")]
check("every described control in the table has a class", not missing, ", ".join(missing))
# The EQ's editor and switch (17 Nov) came after the audit: each in the table, by hand, with why.
EQ_IDS = ("eqOn", "eqEditorOn", "eqThumb", "eqEditorClose", "eqLow", "eqLowFreq", "eqMid", "eqMidFreq", "eqMidWidth",
          "eqHigh", "eqHighFreq", "linkEq")
eq_missing = [k for k in EQ_IDS if not (by_id.get(k) or {}).get("class")]
check("the EQ's controls, its switch and its editor's included, are each in the table with a class", not eq_missing, ", ".join(eq_missing))
check("null: a table without the switch's row fails that", "eqOn" in [k for k in EQ_IDS if k not in {r["id"] for r in rows if r["id"] != "eqOn"}])
SUSPECTS = ("zoom", "timebase", "level", "position", "holdoff", "rotate", "midSide", "lagOn", "beamLevel", "beamXY",
            "traceWidth", "filterOn", "ch1Scale", "dispXY", "dispYT", "pictureOnly", "enlargeButton", "enlargeTrail",
            "graticuleOn", "inkAccent")
def holds_suspects(table):
    ids = {r["id"] for r in table if r.get("class") and r["class"] != "not moved"}
    return [k for k in SUSPECTS if k not in ids]
check("the table measures every control the audit's suspects list names", not holds_suspects(rows),
      ", ".join(holds_suspects(rows)))
check("null: a table without the zoom's row fails that", holds_suspects([r for r in rows if r["id"] != "zoom"]) == ["zoom"])

print("\n%d failed" % len(fails) if fails else "\nall passed")
sys.exit(1 if fails else 0)
