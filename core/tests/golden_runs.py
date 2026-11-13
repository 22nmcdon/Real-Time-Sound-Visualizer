"""Golden files: what the page's JavaScript produced for each parity scenario,
kept in core/tests/golden/ so the core can be held to it once the JavaScript
is gone (stage 5, step 2 of plugin/STAGE5-PLAN.md; core/tests/golden/README.md).

Parity runs the JavaScript the same way everywhere: `node tools/<x>_js.mjs
<scenario file>`, and the core's tool `<x>_cpp` on the same file. So this sits
at that one point rather than at parity's two hundred comparisons: it is put in
place of `subprocess.run` for parity's run, sees every call, and acts only on
the JavaScript tools inside a section that has a golden file. The decision
could have gone the other way - a helper called by name at each of the 28
sites - which reads more plainly but is 28 edits in a 6,900-line file, any of
which could be missed silently; a missed site here shows as a run the file has
never seen, which the three-way mode fails on.

Three modes, from parity's command line:

  (none)           all three: the page's JavaScript runs as before and parity
                   compares it with the core as before; every run is also
                   compared with its golden file, and the core's answer on the
                   same scenario is compared with the file directly.
  --golden         the core against the files: the JavaScript tools are not
                   run in a golden section; parity's comparisons are handed
                   the file's text in their place, or, for a run kept as a
                   sketch, the core's own answer, which the sketch then holds.
  --write-golden   regenerate: as (none), then each section's file is written
                   only if every check in that section passed - that is, only
                   if the JavaScript and the core agree on it - so a
                   regenerated file is never merely believed.

A run is kept whole when its output is under SKETCH_OVER characters or
compresses to under KEEP_WHOLE times its sketch, and as a sketch otherwise (`sketch`, below): the generator's 130 runs alone are 95 MB of
digits, and whole the files came to 75 MB gzipped.

A file is keyed by the tool and a hash of the scenario's text (with the
checkout's paths taken out, so it is the same file in any checkout), not by
the scenario's file name: parity reuses names like `one.txt` for many runs.
Runs on a page parity broke on purpose (SCOPE_PAGE) or on the compiled module
(CORE) pass through untouched: the first are nulls of the JavaScript
comparison and go with it, the second are the face-and-core job.
"""
import gzip, hashlib, json, math, os, re, subprocess

_real_run = subprocess.run
SKETCH_OVER = 100_000     # characters: a run under this is kept whole
KEEP_WHOLE = 2            # and so is one that, gzipped, is under twice its sketch
BLOCK = 64

def _tokens_differ(p, q, tol):
    """None if two numbers are the same to parity's rule, else the gap. The
    rule is kdiff's: to `tol` relative to the larger of one and the first; NaN
    against NaN the same; NaN against anything else a failure, never skipped
    (worst()'s rule); anything that is not a number exactly."""
    if p == q: return None
    try: fp, fq = float(p), float(q)
    except ValueError: return math.inf
    if math.isnan(fp) and math.isnan(fq): return None
    if fp == fq: return None          # an infinity against itself, however spelt
    gap = abs(fp - fq)
    if math.isnan(gap): return math.inf
    return None if gap <= tol * max(1.0, abs(fp)) else gap

# A number wherever it appears, so that `45/0.551+76/1.000000000000` and
# `45/0.551+76/1`, which the JavaScript and the core print for the same
# keyboard state, are the same; the text around the numbers is compared exactly.
NUM = re.compile(r"([-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?|NaN|-?Infinity|-?inf|nan)")
def split(line):
    """A line as (text, numbers): the text with each number replaced by `#`."""
    parts = NUM.split(line)
    return "#".join(parts[0::2]), parts[1::2]

def _input_line(inp, n, i):
    if inp is not None and len(inp) in (n, n - 1) and i < len(inp): return ", on: " + inp[i][:100]
    return ""

def diff(a, b, tol, inp=None):
    """Where two outputs first differ, with by how much, or None. `inp` is the
    scenario's lines: where the output has a line per input line, the input's
    line is named too, since 'line 4117' alone does not say which call it was."""
    la, lb = a.split("\n"), b.split("\n")
    if len(la) != len(lb): return "%d lines against %d" % (len(la), len(lb))
    for i, (x, y) in enumerate(zip(la, lb)):
        (sx, tx), (sy, ty) = split(x), split(y)
        if sx != sy or len(tx) != len(ty): return "line %d: %s | %s" % (i + 1, x[:80], y[:80]) + _input_line(inp, len(la), i)
        for j, (p, q) in enumerate(zip(tx, ty)):
            gap = _tokens_differ(p, q, tol)
            if gap is None: continue
            return ("line %d, value %d: %s against %s (by %.3g)" % (i + 1, j + 1, p[:40], q[:40], gap)
                    + _input_line(inp, len(la), i))
    return None

# --- the sketch ---------------------------------------------------------------
# A long run is kept as, per line, its text with the numbers taken out, and
# per block of BLOCK numbers three figures: their sum, their sum weighted by
# place (1 to BLOCK), and the largest of them in size, to two figures; with any
# number that is not finite kept as it was, by place, and left out of the sums.
#
# What it can see. One value moved by g moves the sum by g, held to tol times
# max(1, the block's largest) - the whole-text rule's tolerance for the value
# that moved, when it is the largest; stricter than it, for any other. Two
# values swapped, or a run a sample late, leave the sum and move the weighted
# sum, held to BLOCK times that. And where one value moved, the weighted sum
# over the sum is its place, so a mismatch names the line, the block, the value
# and by how much, as the whole text does. What it cannot see: two or more
# values moved within one block so that both sums cancel to under the
# tolerance - two changes of opposite sign and in the ratio of their places -
# which no plausible fault does and a deliberate one could. And a NaN appears
# by place, so it is never summed away. The decision could have gone the other
# way, to keep everything whole at 75 MB a regeneration, or to keep fewer
# digits (13 are needed for 1e-12, so a third smaller at best); a sketch of
# BLOCK 64 keeps the files at a few megabytes.
def sketch(text):
    out = []
    for line in text.split("\n"):
        skel, nums = split(line)
        blocks = []
        for b in range(0, len(nums), BLOCK):
            s = w = m = 0.0; odd = []
            for k, t in enumerate(nums[b:b + BLOCK]):
                v = float(t)
                if not math.isfinite(v): odd.append([k, t]); continue
                s += v; w += (k + 1) * v; m = max(m, abs(v))
            blocks.append([s, w, float("%.2g" % m)] + ([odd] if odd else []))
        out.append([skel, len(nums), blocks])
    return out

def sketch_diff(gold, text, tol, inp=None):
    """Where a run's output first differs from a sketch, or None."""
    mine = sketch(text)
    if len(mine) != len(gold): return "%d lines against %d" % (len(gold), len(mine))
    for i, ((gs, gn, gb), (ms, mn, mb)) in enumerate(zip(gold, mine)):
        where = _input_line(inp, len(gold), i)
        if gs != ms or gn != mn: return "line %d: its text or count of values differs (%d against %d)" % (i + 1, gn, mn) + where
        for b, (g, m) in enumerate(zip(gb, mb)):
            first = b * BLOCK + 1
            span = "line %d, values %d to %d" % (i + 1, first, first + min(BLOCK, gn - b * BLOCK) - 1)
            godd, modd = (g[3] if len(g) > 3 else []), (m[3] if len(m) > 3 else [])
            if [k for k, _ in godd] != [k for k, _ in modd] or any(_tokens_differ(p, q, tol) is not None for (_, p), (_, q) in zip(godd, modd)):
                return "%s: not finite at %s against %s" % (span, godd, modd) + where
            scale = max(1.0, g[2], m[2])
            if m[0] == g[0] and m[1] == g[1]: continue   # an overflowed sum is the same only to the bit
            ds, dw = m[0] - g[0], m[1] - g[1]
            if math.isnan(ds) or math.isnan(dw): ds = dw = math.inf
            if abs(ds) <= tol * scale and abs(dw) <= BLOCK * tol * scale: continue
            said = "%s: the sum off by %.3g, the weighted sum by %.3g" % (span, ds, dw)
            if abs(ds) > tol * scale:
                at = dw / ds
                if abs(at - round(at)) < 1e-3 and 1 <= round(at) <= BLOCK:
                    said += " - if one value moved, value %d, by %.3g" % (first + round(at) - 1, ds)
            else:
                said += " - values moved within the block, as by a swap or a shift"
            return said + where
    return None

def against(entry, text, tol, inp=None):
    """A run's output against its golden entry, in whichever form it is kept."""
    if "output" in entry: return diff(entry["output"], text, tol, inp)
    return sketch_diff(entry["sketch"], text, tol, inp)

def stored(entry):
    """A run as it goes into a file: whole if short, else as its sketch."""
    out = entry["output"]
    keep = {k: v for k, v in entry.items() if k != "output"}
    if len(out) <= SKETCH_OVER: keep["output"] = out; return keep
    sk = sketch(out)
    whole = len(gzip.compress(out.encode("utf-8")))
    if whole <= KEEP_WHOLE * len(gzip.compress(json.dumps(sk).encode("utf-8"))): keep["output"] = out
    else: keep["sketch"] = sk; keep["chars"] = len(out)
    return keep

class Golden:
    def __init__(self, here, argv, tol, check, fails):
        self.dir = os.path.join(here, "golden")
        self.build = os.path.join(os.path.dirname(here), "build", "parity")
        self.paths = [os.path.dirname(here), here]
        self.off = os.environ.get("GOLDEN_OFF") == "1"   # time parity as it was: headers only, no file work
        self.mode = "golden" if "--golden" in argv else "write" if "--write-golden" in argv else "three"
        self.tol, self.check, self.fails = tol, check, fails
        self.slug = None          # the golden file of the section now running, or None
        self.started = {}         # slug -> how many checks had failed when it began
        self.dirty = set()        # slugs a check failed in, which --write-golden refuses
        self.runs = {}            # slug -> {key: entry}, every JavaScript run this time, whole
        self.files = {}           # slug -> {key: entry}, as loaded
        self.wrong = {}           # slug -> [what differed], the file against the JavaScript
        self.cwrong = {}          # slug -> [what differed], the core against the file
        self.pairs = {}           # slug -> runs the core was compared with the file on directly
        self.served = {}          # input path -> (key, entry or None, scenario lines), for the core's run after
        self.core_seen = {}       # input path -> (key, tool, output), for a JavaScript run after the core's
        subprocess.run = self.run

    # --- sections -----------------------------------------------------------
    def section(self, name, slug=None):
        if self.off: print("\n--- %s ---" % name); return
        """Parity's section heading. `slug` names the golden file the section's
        JavaScript runs belong to; a section of the face-and-core job has none."""
        if slug != self.slug: self._close()
        print("\n--- %s ---" % name)
        if slug and slug != self.slug:
            self.slug = slug
            self.started[slug] = len(self.fails)
            for d, v in ((self.runs, {}), (self.wrong, []), (self.cwrong, []), (self.pairs, 0)): d.setdefault(slug, v)
            self.files[slug] = self._load(slug)

    def _close(self):
        s = self.slug
        if not s: return
        self.slug = None
        if len(self.fails) > self.started[s]: self.dirty.add(s)
        if self.mode == "write": return
        runs, held = self.runs[s], self.files[s]
        missing = [k for k in runs if k not in held]
        unused = [k for k in held if k not in runs]
        named = lambda d, ks: ["%s on %s" % (d[k]["tool"], d[k]["input"]) for k in ks[:3]]
        if self.mode == "three":
            self.check("%s: the golden file agrees with the page's JavaScript on all %d runs" % (s, len(runs)),
                       not self.wrong[s] and not missing,
                       "; ".join(self.wrong[s][:3] + ["not in the file: " + n for n in named(runs, missing)]))
        self.check("%s: and holds no run parity no longer makes (%d held)" % (s, len(held)), not unused,
                   "; ".join(named(held, unused)))
        self.check("%s: the core against the golden file, directly, on %d runs" % (s, self.pairs[s]),
                   self.pairs[s] > 0 and not self.cwrong[s], "; ".join(self.cwrong[s][:3]))

    def finish(self):
        if self.off: return
        """At the end of parity: close the last section, null-test the
        comparison and, with --write-golden, write each clean section's file."""
        self._close()
        if self.mode != "write":
            self._nulls(); return
        os.makedirs(self.dir, exist_ok=True)
        for s, runs in self.runs.items():
            if s in self.dirty:
                print("  REFUSED  %s: a check failed in its section, so the JavaScript and the core do not agree "
                      "on it; its file is left as it was" % s)
                continue
            old = self.files.get(s, {})
            changed = [k for k in runs if k not in old or against(old[k], runs[k]["output"], 0.0) is not None]
            gone = [k for k in old if k not in runs]
            if not changed and not gone and os.path.exists(self._file(s)):
                print("  KEPT     %s: %d runs, unchanged" % (s, len(runs))); continue
            self._save(s, runs)
            print("  WROTE    %s: %d runs, %d new or changed, %d dropped, %d bytes"
                  % (s, len(runs), len(changed), len(gone), os.path.getsize(self._file(s))))
            for k in changed[:5]:
                said = against(old[k], runs[k]["output"], 0.0) if k in old else "new"
                print("             %s on %s: %s" % (runs[k]["tool"], runs[k]["input"], said))

    def _nulls(self):
        """The comparison's own nulls, on real runs from the files: one value
        moved, and a NaN put in its place, must each fail and be named by line
        and value, in a run kept whole and in one kept as a sketch; a NaN against
        a NaN is no difference (worst()'s rule both ways); and a value moved by
        less than the tolerance is none either."""
        def num(t):
            try: return math.isfinite(float(t)) and float(t) != 0
            except ValueError: return False
        for form in ("output", "sketch"):
            e = next((e for f in self.files.values() for e in f.values() if form in e and len(e.get("output", "x" * 300)) > 200), None)
            run = self.runs.get(next((s for s, f in self.files.items() if e and e in f.values()), None), {})
            key = e and e["tool"] + ":" + e["hash"]
            if self.mode == "three": text = run.get(key, {}).get("output")
            else: text = e and e.get("output") or run.get(key, {}).get("output")
            self.check("null: the files hold a run kept %s to null-test, and its text is at hand"
                       % ("whole" if form == "output" else "as a sketch"), text is not None)
            if text is None: continue
            lines = text.split("\n")
            i = next(k for k, l in enumerate(lines) if any(num(t) for t in split(l)[1]))
            skel, toks = split(lines[i])
            j = next(k for k, t in enumerate(toks) if num(t))
            def put(v):
                t = list(toks); t[j] = v
                parts = skel.split("#")
                line = parts[0] + "".join(n + p for n, p in zip(t, parts[1:]))
                return "\n".join(lines[:i] + [line] + lines[i + 1:])
            v = float(toks[j])
            where = "line %d, value %d" % (i + 1, j + 1)
            said = against(e, put(repr(v + 1e-9 * max(1.0, abs(v)))), self.tol)
            self.check("null: one value moved by a billionth fails, named by line and value (%s on %s, kept %s)"
                       % (e["tool"], e["input"], "whole" if form == "output" else "as a sketch"),
                       said is not None and (where in said or "value %d," % (j + 1) in said), said or "passed")
            said = against(e, put("NaN"), self.tol)
            self.check("null: and a NaN put in its place fails too", said is not None, said or "passed")
            self.check("and the run itself, and a value moved by a tenth of the tolerance, are no difference",
                       against(e, text, self.tol) is None and against(e, put(repr(v * (1 + self.tol / 10))), self.tol) is None)
        self.check("and a NaN against a NaN at the same place is no difference, and against a number is",
                   diff("1 NaN", "1 NaN", self.tol) is None and diff("1 NaN", "1 2", self.tol) is not None
                   and diff("1 2", "1 NaN", self.tol) is not None
                   and sketch_diff(sketch("1 NaN"), "1 NaN", self.tol) is None and sketch_diff(sketch("1 NaN"), "1 2", self.tol) is not None
                   and sketch_diff(sketch("1 2"), "1 NaN", self.tol) is not None)
        self.check("and the sketch sees two values swapped, and a block a value late",
                   sketch_diff(sketch("0.1 0.2 0.3"), "0.2 0.1 0.3", self.tol) is not None
                   and sketch_diff(sketch("0.1 0.2 0.3 0.4"), "0.1 0.1 0.2 0.3", self.tol) is not None)

    # --- the files ----------------------------------------------------------
    # One gzipped JSON file a section, the runs in the order parity made them,
    # each {tool, input, hash} with `output`, the text as the tool printed it,
    # or `sketch` and `chars`. Gzipped and so not readable as a diff in git,
    # which is why --write-golden prints where each changed run first moved.
    def _file(self, slug): return os.path.join(self.dir, slug + ".json.gz")
    def _load(self, slug):
        try:
            with gzip.open(self._file(slug), "rt", encoding="utf-8") as f: data = json.load(f)
        except FileNotFoundError: return {}
        return {e["tool"] + ":" + e["hash"]: e for e in data["runs"]}
    def _save(self, slug, runs):
        data = {"section": slug, "about": "core/tests/golden/README.md", "block": BLOCK,
                "runs": [stored(e) for e in runs.values()]}
        text = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        # mtime 0 and no name, so the same runs write the same bytes and git sees no change.
        with open(self._file(slug), "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, filename="") as f:
            f.write(text.encode("utf-8"))

    def _key(self, tool, path):
        with open(path, encoding="utf-8") as f: text = f.read()
        norm = text
        for p in sorted(self.paths, key=len, reverse=True): norm = norm.replace(p, "<" + os.path.basename(p) + ">")
        h = hashlib.sha256(norm.encode("utf-8")).hexdigest()[:20]
        return tool + ":" + h, h, text

    # --- the one point every run goes through --------------------------------
    def run(self, cmd, *args, **kw):
        if self.off: return _real_run(cmd, *args, **kw)
        s = self.slug
        env = kw.get("env")
        is_js = (s and isinstance(cmd, (list, tuple)) and len(cmd) == 3 and cmd[0] == "node"
                 and str(cmd[1]).endswith("_js.mjs")
                 and not (env and (env.get("CORE") or env.get("SCOPE_PAGE"))))
        if not is_js:
            r = _real_run(cmd, *args, **kw)
            self._against_core(s, cmd, r)
            return r
        before = self.core_seen.pop(cmd[2], None)
        tool, path = os.path.basename(cmd[1]), cmd[2]
        key, h, text = self._key(tool, path)
        entry = self.files[s].get(key)
        inp = text.split("\n")
        name = os.path.basename(path)
        if self.mode == "golden":
            core = os.path.join(self.build, tool[:-len("_js.mjs")] + "_cpp")
            if entry is None:
                self.check("%s: the golden file has a run of %s on %s" % (s, tool, name), False,
                           "the scenario is new or has changed: regenerate with parity.py --write-golden")
                r = _real_run(cmd, *args, **kw)
            elif "output" in entry:
                r = subprocess.CompletedProcess(cmd, 0, entry["output"], "")
                self.served[path] = (key, entry, inp)
                if before and before[0] == key: self._pair(s, entry, before[1], before[2], name, inp)
            else:
                # A sketch cannot be handed to parity's comparison as text, so the
                # core's own answer is, and the sketch holds that answer here: for
                # this run parity's comparison is the core against itself, and
                # what parity reads of the run's meaning it reads of the core's.
                c = _real_run([core, path], capture_output=True, text=True)
                said = against(entry, c.stdout, self.tol, inp) if c.returncode == 0 else "the core's tool failed: " + c.stderr[-200:]
                self.pairs[s] += 1
                if said: self.cwrong[s].append("%s on %s: %s" % (os.path.basename(core), name, said))
                r = subprocess.CompletedProcess(cmd, 0, c.stdout, "")
            self.runs[s][key] = dict(tool=tool, input=name, hash=h, output=r.stdout)
            return r
        r = _real_run(cmd, *args, **kw)
        self.runs[s][key] = dict(tool=tool, input=name, hash=h, output=r.stdout)
        if entry is not None:
            said = against(entry, r.stdout, self.tol, inp)
            if said: self.wrong[s].append("%s on %s: %s" % (tool, name, said))
        self.served[path] = (key, entry, inp)
        # Scan runs the core first and the JavaScript after, on the same file.
        if before and before[0] == key: self._pair(s, entry, before[1], before[2], name, inp)
        return r

    def _against_core(self, s, cmd, r):
        """The core's run on a scenario the JavaScript (or its file) just
        answered: compared with the file directly, so a difference is named by
        scenario, line and value, not only by the section's own check."""
        if not s or not isinstance(cmd, (list, tuple)) or len(cmd) != 2 or not isinstance(getattr(r, "stdout", None), str): return
        path = cmd[1]
        if getattr(r, "returncode", 1) != 0: return
        exe = os.path.basename(str(cmd[0]))
        if not exe.endswith("_cpp"): return
        tool = exe[:-len("_cpp")] + "_js.mjs"
        if path not in self.served:
            if os.path.isfile(path): self.core_seen = {path: (self._key(tool, path)[0], exe, r.stdout)}
            return
        key, entry, inp = self.served.pop(path)
        if key.split(":")[0] != tool or self._key(tool, path)[0] != key: return
        self._pair(s, entry, exe, r.stdout, os.path.basename(path), inp)

    def _pair(self, s, entry, exe, out, name, inp):
        if entry is None: return
        self.pairs[s] += 1
        said = against(entry, out, self.tol, inp)
        if said: self.cwrong[s].append("%s on %s: %s" % (exe, name, said))
