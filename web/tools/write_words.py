"""Write what each control says (the info line) from the doc into web/scope.html.

The words live in one place: web/docs/what-each-control-says.md, a table per
section with a row per control - its id (or, for a control with no id, the
key in its `data-say`), the name the line shows, and the line. Change a row
there, run this, reload:

    python3 web/tools/write_words.py            # write the page
    python3 web/tools/write_words.py --check    # say whether the page agrees

The page carries them as one object, CONTROL_WORDS, which nothing but this
script should edit; `--check` exits 1 when the page and the doc differ, and
wordstest.py runs it, so a hand edit to either side is found rather than
believed. A row whose line is `removed (...)` or `??` is left out: a control
the doc says is going has no words to show, and one nobody could describe
should show none rather than a guess.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
DOC = os.path.join(ROOT, "web", "docs", "what-each-control-says.md")
PAGE = os.path.join(ROOT, "web", "scope.html")
BLOCK = re.compile(r"const CONTROL_WORDS = \{.*?\n\};\n", re.S)


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse(text):
    """The doc's tables as {key: [name, line]}, in the doc's order.

    A table counts when its header names `id` (or `key`), `name` (or `what`)
    and `line`; the questions and anything else in prose are left alone."""
    words, cols = {}, None
    for raw in text.split("\n"):
        if not raw.startswith("|"):
            cols = None
            continue
        row = cells(raw)
        if cols is None:
            head = [c.lower() for c in row]
            key = "id" if "id" in head else "key" if "key" in head else None
            name = "name" if "name" in head else "what" if "what" in head else None
            cols = (head.index(key), head.index(name), head.index("line")) if key and name and "line" in head else False
            continue
        if not cols or set(raw.replace("|", "").strip()) <= set("-: "):
            continue
        k, n, l = (row[i] if i < len(row) else "" for i in cols)
        if not k or l.startswith("removed") or l.startswith("??") or not l:
            continue
        if k in words:
            raise SystemExit("%s: %s appears twice; a control has one line" % (os.path.relpath(DOC, ROOT), k))
        words[k] = [n, l]
    return words


def block(words):
    rows = ",\n".join("  %s: %s" % (json.dumps(k), json.dumps(v, ensure_ascii=False)) for k, v in words.items())
    return ("const CONTROL_WORDS = {\n"
            "  /* Written by web/tools/write_words.py from web/docs/what-each-control-says.md:\n"
            "     edit the doc and run it, not this. */\n" + rows + "\n};\n")


def main():
    words = parse(open(DOC, encoding="utf-8").read())
    page = open(PAGE, encoding="utf-8").read()
    if not BLOCK.search(page):
        raise SystemExit("web/scope.html has no CONTROL_WORDS block to write into")
    new = BLOCK.sub(lambda m: block(words), page, count=1)
    if "--check" in sys.argv:
        same = new == page
        print("the page says what the doc says (%d controls)" % len(words) if same
              else "the page and web/docs/what-each-control-says.md differ: run python3 web/tools/write_words.py")
        sys.exit(0 if same else 1)
    if new != page:
        open(PAGE, "w", encoding="utf-8").write(new)
    print("wrote %d controls' words into web/scope.html" % len(words))


if __name__ == "__main__":
    main()
