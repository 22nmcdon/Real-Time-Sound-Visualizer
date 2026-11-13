"""The engine's pieces, held by their own numbers (stage 5, step 3).

Runs every module in core/tests/pieces/ (each a web suite's "numbers" rows,
moved off the page's JavaScript; see pieces/kit.py), or those named:

    python3 core/tests/pieces/run.py                 # all, in seconds
    python3 core/tests/pieces/run.py alias pulse # just those
    PIECES_INCLUDE=/tmp/x/include python3 core/tests/pieces/run.py alias   # against a mutated copy of the core

Parity runs them all as one of its sections, so a full parity run holds them.
A piece that needs the whole instrument playing - a setup with the loop
closed, an input, readings over seconds of audio - renders it with
`kit.render` (core/tests/tools/render_cpp.cpp; core/tests/golden/README.md
says how), which pieces/render.py proves deterministic first.
No browser and no JavaScript: what each asserts is the core's output alone.
"""
import glob, importlib, os

from pieces.kit import Kit

HERE = os.path.dirname(os.path.abspath(__file__))


def names():
    return sorted(os.path.basename(p)[:-3] for p in glob.glob(os.path.join(HERE, "*.py"))
                  if os.path.basename(p)[:-3] not in ("__init__", "kit", "run"))


def run_all(check, only=None):
    kit = Kit(check)
    for name in only or names():
        print("\n--- %s's numbers, on the core (pieces/%s.py) ---" % (name, name))
        importlib.import_module("pieces." + name).run(kit)
