"""The setup's table of fields, SETUP_FIELDS: one place for what a setup holds.

What would go wrong, and what is checked for it:

- a field in the setup and not the table, or in the table and never in the
  setup: snapshot() and the table are held to each other key for key, with
  layer B's own plane and echo on so that their fields are written too. A
  field the table keeps and snapshot never writes has to be one read only
  from old codes ("read");
- a rule that disagrees with its control: every menu in the table is its
  control's options, as a set, and every range its slider's min and max - so
  a menu changed on the page (the kaleidoscope's Snap, cut to 0, 5 and 6) and
  not in the table, which is what the core reads by, fails here rather than
  in parity's random setups by luck, which is how layer B's snap was found
  still offering 1 to 4 bits in the core (7 Nov). The fields whose control is
  under another id are named here, and a ruled field with no control found
  at all fails, so a new one has to be looked at;
- a default its own rule refuses, which would make "else the default" a
  value the field may not have;
- the readers: a value the rule refuses comes back as the default, one it
  takes comes back held, layer B's twin falls back to A's value as it
  stands, and B's own delay sync, unknown, is A's (the one reading that
  changed with the table);
- each of those checks fed a wrong table on purpose (the null at each), so
  that none of them is known only to pass.

That the core reads by the same table is parity's: core/tests/parity.py
holds core/include/scope/schema.h to this table character for character,
and its random setups load to the same instrument on both sides.
"""
# On the default page since stage 5's step 3 (13 Nov). It opened ?brain=js
# until then with no reason given, and nothing in it needed the page's brain:
# the table, snapshot(), the markup's controls and the readers are the face's
# and the codec's, and restore() writes the plane and echo objects read below
# whatever plays the sound (scope.html's restore, not the brain). Each check
# read the same page code on ?brain=js as it reads here, which the restore
# check's null below now proves by breaking the reader restore goes through.
import json, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def null(name, red, detail=""):
    check("null: " + name, red, detail)


# The fields whose control is under another id. A ruled field neither under
# its own id nor named here fails the check below, so that a new field is
# looked at rather than skipped.
CONTROL = {
    "bendRange": "midiBendRange", "wheelTo": "midiWheelTo", "pressureTo": "midiPressureTo",
    "layers": "midiLayers", "layerPair": "midiLayerPair",
    # One menu shows whichever layer is on the panel.
    "midiDrawWhichB": "midiDrawWhich",
    # Button groups, a button a value, in the menu's order: the group must
    # have no other button, so one added without its value fails.
    "midiMode": ["midiDyad", "midiMono", "midiPoly"],
    "planeOS": ["planeOS1", "planeOS2", "planeOS4"],
    # The beam's ink, a swatch an ink.
    "beamInk": ["inkAccent", "inkCh1", "inkCh2", "inkCh3", "inkCh4", "inkCh5"],
    "trace": "traceWidth",
}
# Ruled fields with no control of their own, and why.
NO_CONTROL = {
}

# The judgments, as functions of the page's own table, so that each can be
# fed a wrong one (the nulls).
JUDGE = """(args) => {
  const [fields, control, noControl] = args;
  const rows = Object.entries(fields);
  const options = (id) => Array.from(el[id].options).map((o) => o.value);
  const bad = { rule: [], menu: [], range: [], missing: [] };
  for (const [key, [dflt, rule]] of rows) {
    if (!rule) continue;
    const kind = rule[0];
    if (dflt !== null) {
      if (kind === "menu" && !rule[1].includes(dflt)) bad.rule.push(key);
      if (kind === "within" && !(typeof dflt === "number" && dflt >= rule[1] && dflt <= rule[2])) bad.rule.push(key);
      if (kind === "flag" && typeof dflt !== "boolean") bad.rule.push(key);
    }
    if (kind !== "menu" && kind !== "within") continue;
    if (dflt === null) continue;
    const id = control[key] || key;
    if (Array.isArray(id)) {
      // A group of buttons: one a value, and the group has no others.
      const buttons = id.map((b) => document.getElementById(b));
      const group = buttons[0] ? buttons[0].parentElement.querySelectorAll("button[role=radio]").length : 0;
      if (kind !== "menu" || buttons.some((x) => !x) || buttons.length !== rule[1].length || group !== rule[1].length) {
        bad.menu.push(key + ": " + rule[1] + " against " + group + " buttons");
      }
      continue;
    }
    if (!el[id]) { if (!noControl.includes(key)) bad.missing.push(key); continue; }
    if (kind === "within" && el[id].tagName === "SELECT") {
      // A range shown as a menu of whole numbers: its lowest and highest.
      const values = options(id).map(Number);
      if (Math.min(...values) !== rule[1] || Math.max(...values) !== rule[2]) {
        bad.range.push(key + ": " + rule[1] + "-" + rule[2] + " against options " + values);
      }
      continue;
    }
    if (kind === "menu") {
      const want = rule[1].map(String).sort(), have = options(id).sort();
      if (JSON.stringify(want) !== JSON.stringify(have)) bad.menu.push(key + ": " + want + " against " + have);
    } else if (Number(el[id].min) !== rule[1] || Number(el[id].max) !== rule[2]) {
      bad.range.push(key + ": " + rule[1] + "-" + rule[2] + " against " + el[id].min + "-" + el[id].max);
    }
  }
  return bad;
}"""

COVER = """(fields) => {
  /* Every section the upper hand's own (G6), so that snapshot writes every B
     field - linked, a section writes none; until G6 B's voice was written
     always and its plane and echo while planeB.own was on. */
  const was = Object.assign({}, handLinks);
  for (const sec of HAND_SECTION_IDS) handLinks[sec] = false;
  planeB.own = true;
  const route = { sourceId: "lfo1", destId: "gen.fm", amount: 0.4, amountB: -0.2 };
  state.modRoutings.push(route);
  const snap = snapshot();
  state.modRoutings.splice(state.modRoutings.indexOf(route), 1);
  Object.assign(handLinks, was);
  planeB.own = !linked("plane");
  const table = new Set(Object.keys(fields)), wrote = new Set(Object.keys(snap));
  return {
    notInTable: [...wrote].filter((k) => !table.has(k)),
    neverWritten: [...table].filter((k) => !wrote.has(k) && (fields[k][1] || [])[0] !== "read"),
    readOnly: [...table].filter((k) => (fields[k][1] || [])[0] === "read"),
    count: wrote.size,
  };
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()
    p.wait_for_timeout(200)

    fields = p.evaluate("() => SETUP_FIELDS")
    ruled = [k for k, row in fields.items() if len(row) > 1]
    print("    %d fields, %d of them ruled" % (len(fields), len(ruled)))

    print("\n--- the table and the setup, both ways ---")
    cover = p.evaluate(COVER, fields)
    print("    %s" % cover)
    check("every field snapshot writes is in the table, with layer B's own plane and echo on",
          not cover["notInTable"] and cover["count"] > 200, str(cover["notInTable"]))
    check("and every field in the table is written, but those read only from old codes",
          not cover["neverWritten"] and sorted(cover["readOnly"]) == ["l0d", "l1d"], str(cover["neverWritten"]))
    # The nulls: a field snapshot writes, gone from the table; a field the
    # table has, never written.
    gone = dict(fields); del gone["planeSnap"]
    added = dict(fields); added["planeKaleido"] = [0, ["menu", [0, 3, 6]]]
    cg, ca = p.evaluate(COVER, gone), p.evaluate(COVER, added)
    check("null: a table without planeSnap is caught, and one with the kaleidoscope back",
          cg["notInTable"] == ["planeSnap"] and ca["neverWritten"] == ["planeKaleido"], "%s %s" % (cg, ca))

    print("\n--- each rule against its control and its default ---")
    judged = p.evaluate(JUDGE, [fields, CONTROL, list(NO_CONTROL)])
    print("    %s" % judged)
    check("every default is one its own rule takes", not judged["rule"], str(judged["rule"]))
    check("every menu is its control's options", not judged["menu"], str(judged["menu"]))
    check("every range is its slider's", not judged["range"], str(judged["range"]))
    check("every ruled field has a control, or a reason it has none", not judged["missing"], str(judged["missing"]))
    wrong = json.loads(json.dumps(fields))
    wrong["planeSnap"][1][1] = [0, 1, 2, 3, 4, 5, 6]
    wrong["planeRadius"][1][2] = 99
    wrong["delayMix"][0] = 140
    wrong["scanSoft"] = [30, ["within", 0, 60]]
    wrong["oddField"] = [1, ["menu", [1, 2]]]
    wrong["planeOS"][1][1] = [1, 2]
    wrong["arpOctaves"][1][2] = 4
    # The one this suite's first run would have caught on its own: the scale
    # menu written into the table with the first eight of its thirteen.
    wrong["keyScale"][1][1] = wrong["keyScale"][1][1][:8]
    jw = p.evaluate(JUDGE, [wrong, CONTROL, list(NO_CONTROL)])
    print("    null: %s" % jw)
    check("null: Snap offering 1 to 4 bits again, a radius to 99, a default outside its range, a field with no control, a button group a value short, a menu range one long and the scale menu cut short are each caught",
          any(m.startswith("planeSnap") for m in jw["menu"]) and any(r.startswith("planeRadius") for r in jw["range"])
          and "delayMix" in jw["rule"] and "oddField" in jw["missing"]
          and any(m.startswith("planeOS") for m in jw["menu"]) and any(r.startswith("arpOctaves") for r in jw["range"])
          and any(m.startswith("keyScale") for m in jw["menu"]), str(jw))

    print("\n--- the readers ---")
    read = p.evaluate("""() => {
      const s = (o) => Object.assign({}, DEFAULTS, o);
      return {
        snapRefused: setupField(s({ planeSnap: 3 }), "planeSnap"),
        snapText: setupField(s({ planeSnap: "5" }), "planeSnap"),
        snapTaken: setupField(s({ planeSnap: 5 }), "planeSnap"),
        radiusHeld: setupField(s({ planeRadius: 400 }), "planeRadius"),
        radiusText: setupField(s({ planeRadius: "30" }), "planeRadius"),
        radiusJunk: setupField(s({ planeRadius: "wide" }), "planeRadius"),
        truthOff: setupField(s({ midiTruth: false }), "midiTruth"),
        truthJunk: setupField(s({ midiTruth: 0 }), "midiTruth"),
        holdJunk: setupField(s({ midiHold: 1 }), "midiHold"),
        bSnapOwn: setupOwn({ bSnap: 6 }, "bSnap"),
        bSnapRefused: setupOwn({ bSnap: 3 }, "bSnap"),
        bSnapMissing: setupOwn({}, "bSnap"),
        bTurnHeld: setupOwn({ bTurn: -80 }, "bTurn"),
      };
    }""")
    print("    %s" % read)
    check("a value the rule refuses is the default, and one it takes comes back as given or held",
          read["snapRefused"] == 0 and read["snapText"] == 0 and read["snapTaken"] == 5 and read["radiusHeld"] == 100
          and read["radiusText"] == 30 and read["radiusJunk"] == 40, str(read))
    check("a switch is on only for true, or off only for false where its default is on",
          read["truthOff"] is False and read["truthJunk"] is True and read["holdJunk"] is False, str(read))
    check("layer B's own is read by A's rule, and is nothing where it is refused or missing",
          read["bSnapOwn"] == 6 and read["bSnapRefused"] is None and read["bSnapMissing"] is None
          and read["bTurnHeld"] == -50, str(read))

    print("\n--- through restore ---")
    loaded = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      restore({ planeSnap: 3, planeRadius: 400, delaySync: "1/5" }); await wait(30);
      const a = { snap: plane.snap, radius: plane.radius, sync: echo.sync };
      restore({ planeSnap: 5, delaySync: "1/4", bPlane: true, bSnap: 3, bRadius: 30, bDelaySync: "1/5" }); await wait(30);
      const bOwn = { snap: planeB.snap, radius: planeB.radius, sync: echoB.sync };
      restore({}); await wait(30);
      return { a, bOwn };
    }""")
    print("    %s" % loaded)
    check("restore reads A's plane and echo by the table: a cut snap and an unknown sync are the defaults, a radius held",
          loaded["a"] == {"snap": 0, "radius": 1, "sync": ""}, str(loaded["a"]))
    check("and B's own falls back to A's as it stands - its snap of 3 bits is A's 5, its unknown sync A's 1/4",
          loaded["bOwn"] == {"snap": 5, "radius": 0.3, "sync": "1/4"}, str(loaded["bOwn"]))
    # The null, added as the suite moved to the default: restore with the
    # table's reader made to take any value, so the cut snap and the unknown
    # sync come through as given. Were restore on this page not reading by
    # the table - a second restore somewhere, or plane written from elsewhere -
    # the check above would pass either way; this shows it reading the rule.
    loose = p.evaluate("""async () => {
      const wait = (ms) => new Promise((r) => setTimeout(r, ms));
      const real = setupField;
      setupField = (s, key) => (s[key] !== undefined ? s[key] : SETUP_FIELDS[key][0]);
      try { restore({ planeSnap: 3, planeRadius: 400, delaySync: "1/5" }); await wait(30); }
      finally { setupField = real; }
      const a = { snap: plane.snap, radius: plane.radius, sync: echo.sync };
      restore({}); await wait(30);
      return a;
    }""")
    null("with the table's reader made to take anything, restore keeps the cut snap and the unknown sync, and the check above fails",
         loose != {"snap": 0, "radius": 1, "sync": ""} and loose["snap"] == 3, str(loose))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print()
if fails:
    print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the setup's fields are one table, and every menu and range in it is its control's")
