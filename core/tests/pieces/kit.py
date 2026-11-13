"""What every module in core/tests/pieces/ is handed: a check, a way to build
one of parity's C++ tools, and a way to run one on a scenario.

The pieces are stage 5's step 3, the "numbers" rows of the web suites that
drove an engine piece directly from the page (waveAt, cycleTables,
makeGeneratorCore, scoreColumn, makePictureMeter, clockTap and so on) and so
needed the page's JavaScript under them. Here each claim is asserted against
the core's own output alone, through the tools parity already builds. There
is no second implementation to compare with, so every check is written with
its null - a known-wrong value seen red - as CLAUDE.md asks.

PIECES_INCLUDE points the build at another copy of core/include, so a
mutation pass can break a header in a scratch directory and watch a check go
red without leaving a diff in the repository; the tools are built into a
directory of their own for it, so a mutant never stands in for the real one.
"""
import hashlib, json, os, subprocess

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # core/tests
CORE = os.path.dirname(HERE)
INCLUDE = os.environ.get("PIECES_INCLUDE") or os.path.join(CORE, "include")
_tag = "" if INCLUDE == os.path.join(CORE, "include") else "-" + hashlib.sha1(INCLUDE.encode()).hexdigest()[:8]
BUILD = os.path.join(CORE, "build", "pieces" + _tag)


class Kit:
    def __init__(self, check):
        self.check = check
        self._built = {}

    def null(self, name, ok, detail=""):
        """A check that a known-wrong reading fails: `ok` is that it did."""
        self.check("null: " + name, ok, detail)

    def build(self, tool):
        """One of core/tests/tools/<tool>.cpp, built against INCLUDE, once a run."""
        if tool not in self._built:
            os.makedirs(BUILD, exist_ok=True)
            exe = os.path.join(BUILD, tool)
            subprocess.run(["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-I", INCLUDE,
                            os.path.join(HERE, "tools", tool + ".cpp"), "-o", exe], check=True)
            self._built[tool] = exe
        return self._built[tool]

    def run(self, tool, text, *args):
        """The tool's output on a scenario given as text (written to a file of its own)."""
        exe = self.build(tool)
        path = os.path.join(BUILD, "%s-%s.txt" % (tool, hashlib.sha1(text.encode()).hexdigest()[:12]))
        with open(path, "w") as f: f.write(text if text.endswith("\n") else text + "\n")
        return subprocess.run([exe, *args, path], check=True, capture_output=True, text=True).stdout

    def floats(self, tool, text, *args):
        return [float(v) for v in self.run(tool, text, *args).split()]

    def instrument(self, lines):
        """instrument_cpp on a script of JSON lines; its output's lines."""
        return self.run("instrument_cpp", "\n".join(json.dumps(l) for l in lines)).split("\n")

    def render(self, lines, raw=False):
        """render_cpp on a script of JSON lines (core/tests/tools/render_cpp.cpp
        lists its commands and readings): each reading's `at` as a dict of
        its readings' words, the time under "t" - or the text whole, `raw`.
        A table's two lines are "tableA" and "tableB"."""
        out = self.run("render_cpp", "\n".join(json.dumps(l) for l in lines))
        if raw: return out
        rows = []
        for line in out.split("\n"):
            w = line.split()
            if not w: continue
            if w[0] == "at": rows.append({"t": float(w[1])})
            elif w[0] == "no": raise RuntimeError("render_cpp refused: " + line)
            elif w[0] == "table": rows[-1]["table" + w[1]] = None if w[2] == "-" else [float(x) for x in w[3:]]
            elif rows: rows[-1][w[0]] = w[1:]
        return rows

    def slots(self):
        """The generator's slot numbers by name, as render_cpp prints them."""
        w = subprocess.run([self.build("render_cpp"), "--slots"], check=True, capture_output=True, text=True).stdout.split()
        return {w[i]: int(w[i + 1]) for i in range(0, len(w), 2)}

    def preset_codes(self):
        """Every bank preset's setup code, by name, as the instrument writes it."""
        exe = self.build("instrument_cpp")
        names = [n for n in subprocess.run([exe, "--names"], check=True, capture_output=True, text=True).stdout.split("\n") if n]
        codes = subprocess.run([exe, "--code", *names], check=True, capture_output=True, text=True).stdout.split("\n")
        return dict(zip(names, codes))
