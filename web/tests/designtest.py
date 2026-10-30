"""DESIGN.md's colour tables against the tokens the page actually paints with.

The design document sorts every colour into brand (the house this app shares
with the jazz and guitar apps) or product (the oscilloscope's own). A document
like that goes stale the first time someone adds a token to the page and not to
the table, and then it is believed. So this holds it to the source:

- every colour token in the page's :root is in a table, with the same value and
  a side of the line;
- a product row is a colour the page defines, because a product colour nobody
  paints with is not a decision any more, and a token removed from the page
  cannot linger in the doc;
- a brand row the page does not paint says so ("not used here"), and one that
  says so is not painted: the brand is the house's, so the page need not use all
  of it, but the table must not claim a colour is in use when it has gone, or
  unused when it is there. (The retired desktop build used to be a second copy of
  the palette to check against; the jazz app's document is the source now.)
- every var() the stylesheet uses is defined somewhere, because an undefined
  one is not an error: the property quietly takes its initial value. That is
  how the drop hint lost its wash;
- every rgba() outside :root is the charcoal shadow, since a colour spelled
  where it is used will not follow a light, and the house's shadows are ink;
- a radius outside the house's three - 1px, 20-30px, 50% - is on one of the
  instrument's own marks, named below, and never on the chrome.

No browser: both are text files. Each check is first fed a known-wrong
input below and has to report it, so none of them is believed before it has
been seen to fail.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()

HEX = r"#[0-9a-fA-F]{6}"

def page_tokens(html):
    # The first :root block is the stylesheet's. Later ones, if any, would be
    # inside the script or a comment, and the page has only the one light.
    start = html.index(":root {")
    block = html[start:html.index("\n}", start)]
    return {m.group(1): m.group(2).lower()
            for m in re.finditer(r"--([a-z0-9-]+):\s*(" + HEX + r")\s*;", block)}

def doc_rows(md):
    rows = {}
    for m in re.finditer(r"^\| `--([a-z0-9-]+)` \| `(" + HEX + r")` \| ([^|]+?) \|", md, re.M):
        rows[m.group(1)] = (m.group(2).lower(), m.group(3).strip())
    return rows

def undefined_vars(html):
    # The stylesheet only. The script builds `var(--ch' + (i + 1) + ')` by
    # concatenation, which a pattern over the whole file reads as a token
    # called --ch. A property the script sets with setProperty - the photocell's
    # --lit, a source chip's --pip - counts as defined.
    css = html[html.index("<style>"):html.index("</style>")]
    used = set(re.findall(r"var\(--([a-z0-9-]+)", css))
    defined = set(re.findall(r"(?<![a-z0-9(-])--([a-z0-9-]+)\s*:", css))
    defined |= set(re.findall(r"setProperty\(\s*[\"']--([a-z0-9-]+)", html))
    return used - defined

def stylesheet_rules(html):
    # Innermost rules only: a selector cannot hold a brace, so an @media
    # block's own opening never matches and the rules inside it do. After the
    # tag, or the first rule's selector is "<style> :root".
    css = html[html.index("<style>") + len("<style>"):html.index("</style>")]
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return [(m.group(1).strip(), m.group(2)) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css)]

def loose_rgba(html):
    out = []
    for selector, body in stylesheet_rules(html):
        if selector == ":root": continue   # tokens are where a colour is allowed to be spelled
        for m in re.finditer(r"rgba?\(([^)]*)\)", body):
            if not re.match(r"\s*36\s*,\s*31\s*,\s*29\s*,", m.group(1)):
                out.append("%s: %s" % (selector, m.group(0)))
    return out

BRAND_RADII = {"1px", "20px", "30px", "50%"}
# The instrument drawn on the paper, which the house leaves to the product as
# the guitar app rounds its fretboard (DESIGN.md, section 5): a piano key's
# rounded foot, a source's meter, and the modulation lane's marks. Chrome is
# not here, and a new entry wants a reason in DESIGN.md.
INSTRUMENT_MARKS = {".key", ".src-meter", ".mod-lane", ".lane-now", ".lane-cap"}

def off_brand_radii(html):
    out = []
    for selector, body in stylesheet_rules(html):
        for m in re.finditer(r"border-radius:\s*([^;]+);", body):
            value = m.group(1).strip()
            if all(part in BRAND_RADII or part == "0" for part in value.split()): continue
            if selector in INSTRUMENT_MARKS: continue
            out.append("%s: %s" % (selector, value))
    return out

def layer_of(text):
    return "brand" if text.startswith("Brand") else "product" if text.startswith("Product") else None

UNUSED = "not used here"

def problems(page, rows):
    out = []
    for name, value in sorted(page.items()):
        if name not in rows:
            out.append("--%s is painted by the page and sorted nowhere in DESIGN.md" % name)
        elif rows[name][0] != value:
            out.append("--%s is %s in the page and %s in DESIGN.md" % (name, value, rows[name][0]))
    for name, (value, layer) in sorted(rows.items()):
        kind = layer_of(layer)
        if kind is None:
            out.append("--%s has no side of the line (%r)" % (name, layer))
        if kind == "product" and name not in page:
            out.append("--%s is product and the page does not paint with it" % name)
        if kind == "brand" and name not in page and UNUSED not in layer:
            out.append("--%s is brand, not painted by the page, and not marked %r" % (name, UNUSED))
        if kind == "brand" and name in page and UNUSED in layer:
            out.append("--%s is marked %r and the page paints with it" % (name, UNUSED))
    return out

page = page_tokens(read("web", "scope.html"))
md = read("DESIGN.md")
rows = doc_rows(md)

print("\n--- what was read ---")
print("  page :root %d colours, DESIGN.md %d rows (%d brand, %d product)" % (
    len(page), len(rows),
    sum(layer_of(l) == "brand" for _, l in rows.values()),
    sum(layer_of(l) == "product" for _, l in rows.values())))
# A parser that found nothing would pass every check below vacuously.
check("the page's tokens were read: the ten core, three pigments and six inks",
      len(page) >= 19 and "ch6" in page and "unresolved" in page, "%d" % len(page))
check("DESIGN.md's rows were read", len(rows) >= 21 and "ch1" in rows, "%d" % len(rows))

print("\n--- null tests: each check fed something wrong on purpose ---")
def caught(name, p, r, needle):
    found = problems(p, r)
    check("caught: " + name, any(needle in f for f in found), "; ".join(found) or "nothing reported")

caught("a colour added to the page and not to the doc",
       {**page, "ch7": "#123456"}, rows, "--ch7 is painted by the page")
caught("a page colour changed and the doc left alone",
       {**page, "gold": "#b08d58"}, rows, "--gold is #b08d58 in the page")
caught("a row with no side of the line",
       page, {**rows, "sage": (rows["sage"][0], "Shared")}, "--sage has no side")
caught("a product row left behind after its colour went",
       {k: v for k, v in page.items() if k != "ch5"}, rows, "--ch5 is product and the page does not")
caught("a product colour nobody paints with",
       page, {**rows, "ch9": ("#000001", "Product")}, "--ch9 is product and the page does not")
caught("a brand colour gone from the page and still claimed in use",
       {k: v for k, v in page.items() if k != "rust"}, rows, "--rust is brand, not painted")
caught("a brand colour marked unused that the page paints",
       page, {**rows, "sage": (rows["sage"][0], "Brand (" + UNUSED + ")")}, "--sage is marked")

probe = "<style>\n.a { color: var(--nowhere); }\n.b { --here: 1; width: var(--here); }\n</style>"
check("caught: a var() of a token nobody defined", undefined_vars(probe) == {"nowhere"},
      repr(undefined_vars(probe)))
probe = ("<style>\n:root { --w: rgba(217, 166, 160, 0.16); }\n.s { box-shadow: 0 1px 2px rgba(36, 31, 29, 0.1); }\n"
         "@media (x) { .m { box-shadow: 0 1px 2px rgba(0,0,0,0.12); } }\n/* rgba(1,2,3,0.1) */\n</style>")
check("caught: a black shadow inside @media, and not a token or a comment", loose_rgba(probe) == [".m: rgba(0,0,0,0.12)"],
      repr(loose_rgba(probe)))
probe = ("<style>\n.a { border-radius: 1px; }\n.b { border-radius: 6px; }\n.key { border-radius: 0 0 4px 4px; }\n"
         "@media (x) { .c { border-radius: 0 0 4px 4px; } }\n.d { border-radius: 30px 30px 0 0; }\n</style>")
check("caught: chrome radii outside the three, inside @media too, and not the instrument's",
      off_brand_radii(probe) == [".b: 6px", ".c: 0 0 4px 4px"], repr(off_brand_radii(probe)))

print("\n--- the document against the page ---")
found = problems(page, rows)
for f in found: print("    " + f)
check("every colour in the page is in DESIGN.md, on one side of the line, at its value",
      not found, "%d problems" % len(found))
check("the lane inks are product and the core palette is brand",
      all(layer_of(rows["ch%d" % i][1]) == "product" for i in range(1, 7))
      and all(layer_of(rows[n][1]) == "brand" for n in
              ("cream", "cream-2", "paper", "charcoal", "text", "text-soft",
               "line", "blush", "blush-deep", "gold", "sage", "rust", "unresolved")))
html = read("web", "scope.html")
missing = undefined_vars(html)
check("every var() in the stylesheet is defined", not missing, ", ".join(sorted(missing)))
loose = loose_rgba(html)
check("every rgba() outside :root is the charcoal shadow", not loose, "; ".join(loose))
radii = off_brand_radii(html)
check("every radius is the house's three, or one of the instrument's marks", not radii, "; ".join(radii))
check("the instrument's marks are all still in the stylesheet",
      INSTRUMENT_MARKS <= {s for s, _ in stylesheet_rules(html)},
      ", ".join(sorted(INSTRUMENT_MARKS - {s for s, _ in stylesheet_rules(html)})))

# Not a value check: DESIGN.md names the brand's source, and if that ever
# changes the document should be read again, not just its tables.
check("DESIGN.md names the brand's source of truth",
      "jazz_learning_app/blob/main/docs/BRANDING.md" in md)

print()
if fails:
    print("FAILED: %d" % len(fails)); sys.exit(1)
print("all design checks pass")
