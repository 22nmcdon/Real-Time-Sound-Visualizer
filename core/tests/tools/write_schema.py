"""Write core/include/scope/schema.h out from the page's SETUP_FIELDS.

The table is read the way parity reads DEFAULTS - lifted out of
web/scope.html by setup_js.mjs, and stringified as the page evaluates it -
and written in pieces of 6000 characters, as presets.h is, since the whole
may outgrow what MSVC takes in one string literal. parity.py holds the
compiled header to the page character for character, so a field, default or
rule changed on the page and not written out here is a failure there rather
than a drift.

    python3 core/tests/tools/write_schema.py           write it
    python3 core/tests/tools/write_schema.py --check   say whether it is current
"""
import os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HEADER = os.path.join(HERE, "..", "..", "include", "scope", "schema.h")
PIECE = 6000

TOP = """// The setup's fields: SETUP_FIELDS in web/scope.html as the page evaluates
// it - each field's default (null for layer B's, which have none: a field a
// code lacks is A's) and the rule restore reads it by. The page says what
// each rule means, beside the table; setup.h reads them the same way.
//
// Written out by core/tests/tools/write_schema.py, never by hand, and held
// to the page character for character by core/tests/parity.py. That is what
// it is for: the menus and ranges were written into restore.h once each,
// beside the page's, and after the kaleidoscope's removal layer B's snap
// here still offered 1 to 4 bits that the page had dropped (7 Nov).

#pragma once

namespace scope {

inline const char* const kSetupFieldsPieces[] = {
"""
BOTTOM = """};

}  // namespace scope
"""


def page_fields():
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("fields\n")
        path = f.name
    try:
        out = subprocess.run(["node", os.path.join(HERE, "setup_js.mjs"), path], check=True,
                             capture_output=True, text=True).stdout.strip()
    finally:
        os.unlink(path)
    if not out.startswith("{") or ")fields\"" in out:
        sys.exit("the page's SETUP_FIELDS did not come back as JSON: %r" % out[:80])
    return out


def header_for(text):
    pieces = "".join('  R"fields(%s)fields",\n' % text[i:i + PIECE] for i in range(0, len(text), PIECE))
    return TOP + pieces + BOTTOM


def main():
    want = header_for(page_fields())
    if "--check" in sys.argv:
        have = open(HEADER, encoding="utf-8").read() if os.path.exists(HEADER) else ""
        print("current" if have == want else "stale")
        sys.exit(0 if have == want else 1)
    with open(HEADER, "w", encoding="utf-8", newline="\n") as f:
        f.write(want)
    print("wrote %s" % os.path.normpath(HEADER))


if __name__ == "__main__":
    main()
