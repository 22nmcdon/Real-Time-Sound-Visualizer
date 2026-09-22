#!/usr/bin/env python3
"""Every check, in one go.

    python3 web/tests/run.py            all of them
    python3 web/tests/run.py lag cap    just those

Needs Playwright and a Chromium. Point CHROME at one if the default is wrong.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUITES = [
    ("beam", ["node", "beam.test.mjs"], "the beam-intensity mapping, no browser"),
    ("lag", [sys.executable, "lagtest.py"], "lag X-Y: geometry, the lock, exclusivity"),
    ("cap", [sys.executable, "captest.py"], "what capture asks a source for"),
    ("live", [sys.executable, "livetest.py"], "live input: shared stream, wiring, crossovers"),
    ("regress", [sys.executable, "regress.py"], "presets, displays, source switching"),
    ("sources", [sys.executable, "sources.py"], "rack, file, tone, and a denied mic"),
]


def main(argv):
    want = set(argv[1:])
    # beam.test.mjs reads the shipped script, so it has to be extracted first.
    subprocess.run([sys.executable, "extract.py"], cwd=os.path.dirname(HERE), check=True)

    failed = []
    for name, cmd, blurb in SUITES:
        if want and name not in want:
            continue
        print("\n=== %s — %s ===" % (name, blurb), flush=True)
        if subprocess.run(cmd, cwd=HERE).returncode != 0:
            failed.append(name)

    print()
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print("everything passes")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
