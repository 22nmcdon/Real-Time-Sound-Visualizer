"""Write core/include/scope/presets.h out from the page's preset library.

The header holds the library as the page evaluates it - JSON.stringify of
PRESETS, read off the page by restore_page.py - in pieces of 6000 characters,
since the whole is past what MSVC takes in one string literal. parity.py holds
the two together character for character, so a preset changed on the page and
not written out here is a failure there rather than a drift.

Until P8g this was done by hand at each change to the library; the bank is
now meant to be tuned in rounds, by ear, so it is a script.

    CHROME=/opt/pw-browsers/chromium python3 core/tests/tools/write_presets.py
"""
import os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
HEADER = os.path.join(HERE, "..", "..", "include", "scope", "presets.h")
PIECE = 6000


def main():
    text = subprocess.run([sys.executable, os.path.join(HERE, "restore_page.py"), "--library"],
                          check=True, capture_output=True, text=True).stdout.strip()
    if not text.startswith("[[") or ")preset\"" in text:
        sys.exit("the page's library did not come back as JSON: %r" % text[:80])
    with open(HEADER, encoding="utf-8") as f:
        header = f.read()
    start = header.index("    static const char* const pieces[] = {\n") + len("    static const char* const pieces[] = {\n")
    end = header.index("    };\n", start)
    pieces = "".join('      R"preset(%s)preset",\n' % text[i:i + PIECE] for i in range(0, len(text), PIECE))
    with open(HEADER, "w", encoding="utf-8") as f:
        f.write(header[:start] + pieces + header[end:])
    print("wrote %d characters in %d pieces to %s" % (len(text), -(-len(text) // PIECE), os.path.normpath(HEADER)))


if __name__ == "__main__":
    main()
