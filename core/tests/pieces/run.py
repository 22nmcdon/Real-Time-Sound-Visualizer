"""The pieces alone: python3 core/tests/pieces/run.py [name ...]. See __init__.py."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pieces

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

unknown = [n for n in sys.argv[1:] if n not in pieces.names()]
if unknown: print("no such piece: " + ", ".join(unknown)); sys.exit(2)
pieces.run_all(check, sys.argv[1:] or None)
print()
if fails: print("FAILED: " + ", ".join(fails)); sys.exit(1)
print("the pieces hold")
