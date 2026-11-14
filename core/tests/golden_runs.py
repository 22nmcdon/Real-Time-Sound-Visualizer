"""Golden files: what the page's JavaScript answered for each scenario of the
port-is-the-original job, recorded while it still existed (stage 5, step 2),
and what the page's own `restore` left behind for every setup parity loads
(recorded in step 6, the day before the page's brain was deleted). They are
in core/tests/golden/, and they are what the core is held to now that there
is no JavaScript engine to compare it with. core/tests/golden/README.md is
the short version of what follows.

Each section of the core's tests that has a file names it (`section`), and
asks for each scenario's recorded answer by the tool that recorded it
(`recorded`): `recorded("envelope", path)` is what `envelope_js.mjs` printed
for that scenario, read from envelope.json.gz, in the place where the core's
tests used to run the JavaScript. The core's own tool is then run on the same
scenario as before, and the section's own comparison holds the two to 1e-12;
each such pair is also compared here, directly, so a difference is named by
scenario, line and value (`_against_core`).

Two modes, from the command line:

  (none)           the core against the files. A scenario the file has no run
                   for fails, naming it: either a check was changed, or the
                   sound is meant to change and the files are to be written.
  --write-golden --because "WHY"
                   the files written from the core's own answers, for a change
                   of sound that is meant. There is no page left to confirm
                   the new answers, as there was until step 6, so the guard is
                   this: the change must be named, and the name is kept - each
                   rewrite appends a line to the README's log with the date,
                   the reason and what moved - so a regenerated file is never
                   anonymous, and its reason sits beside it in the diff. A
                   section is refused if any of its own checks failed: with the
                   files out of the way those are the checks of what the sound
                   should be and their nulls, and a change that breaks one of
                   them is not the change that was meant. A section whose runs
                   did not move rewrites nothing.

The decision could have gone the other way - refusing a rewrite unless every
run in it moved by less than some bound, say - but a bound would stop the
changes worth making and pass the small wrong ones; a reason that has to be
written down puts the judgement where it belongs, with whoever meant the
change, and leaves it on the record.

A run is kept whole when its output is under SKETCH_OVER characters or
compresses to under KEEP_WHOLE times its sketch, and as a sketch otherwise
(`sketch`, below): the generator's 130 runs alone are 95 MB of digits. A run
kept as a sketch cannot be handed to a section's comparison as text, so for
those the core's own answer is compared with the sketch here and handed on,
and the section's comparison sees the core against itself: the sketched
sections rest wholly on the comparison here, which is why it is a check of
its own and null-tested at the end of every run.

A file is keyed by the recording tool and a hash of the scenario's text (with
the checkout's paths taken out, so it is the same file in any checkout), not
by the scenario's file name: the tests reuse names like `one.txt` for many
runs. The tools' names are those of the JavaScript runners that recorded them
(`envelope_js.mjs`, deleted in step 6) and `restore_page.py`, kept as they
were written so that no file had to be rewritten when the runners went.
"""
import gzip, hashlib, json, math, os, re, subprocess

_real_run = subprocess.run
SKETCH_OVER = 100_000     # characters: a run under this is kept whole
KEEP_WHOLE = 2            # and so is one that, gzipped, is under twice its sketch
BLOCK = 64
WHOLE_TOOLS = {"restore_page.py"}   # read field by field as JSON, so never a sketch

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
# A minus is the number's, a plus never is (`u+-0.0005` and `u+0.0005` must
# both be text `u+` and a number, or a minus nought on one side moves the
# text); and the C library's `-nan` is the JavaScript's `NaN`.
NUM = re.compile(r"(-?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?|-?NaN|-?Infinity|-?inf|-?nan)")
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

def canonical(text):
    """A run of JSON lines with each object's keys in order: the page wrote its
    restore's lines in the order its objects held their keys, restore_cpp in
    its own, and the restore sections read them field by field."""
    out = []
    for line in text.split("\n"):
        try: out.append(json.dumps(json.loads(line), sort_keys=True, separators=(",", ":"), ensure_ascii=False) if line.strip() else line)
        except ValueError: out.append(line)
    return "\n".join(out)

def against(entry, text, tol, inp=None):
    """A run's output against its golden entry, in whichever form it is kept."""
    if "output" in entry and entry.get("tool") in WHOLE_TOOLS: return diff(canonical(entry["output"]), canonical(text), tol, inp)
    if "output" in entry: return diff(entry["output"], text, tol, inp)
    return sketch_diff(entry["sketch"], text, tol, inp)

def stored(entry):
    """A run as it goes into a file: whole if short, else as its sketch."""
    out = entry["output"]
    keep = {k: v for k, v in entry.items() if k != "output"}
    if len(out) <= SKETCH_OVER or entry.get("tool") in WHOLE_TOOLS: keep["output"] = out; return keep
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
        self.mode = "write" if "--write-golden" in argv else "check"
        self.because = None
        if "--because" in argv:
            at = argv.index("--because")
            self.because = argv[at + 1].strip() if at + 1 < len(argv) else ""
        if self.mode == "write" and not self.because:
            raise SystemExit('--write-golden needs --because "what changed in the sound, and why": with no page left to '
                             "confirm the core's new answers, the reason is the guard, and it is kept in "
                             "core/tests/golden/README.md's log")
        self.tol, self.check, self.fails = tol, check, fails
        self.slug = None          # the golden file of the section now running, or None
        self.started = {}         # slug -> how many checks had failed when it began
        self.dirty = set()        # slugs a check failed in, which --write-golden refuses
        self.runs = {}            # slug -> {key: entry}, every run asked for this time, with the core's answer when written
        self.files = {}           # slug -> {key: entry}, as loaded
        self.cwrong = {}          # slug -> [what differed], the core against the file
        self.pairs = {}           # slug -> runs the core was compared with the file on directly
        self.served = {}          # input path -> (key, entry, scenario lines), for the core's run after
        self.core_seen = {}       # input path -> (tool, output), the core's last run, for a recorded run asked for after it
        subprocess.run = self.run

    # --- sections -----------------------------------------------------------
    def section(self, name, slug=None):
        """A section's heading. `slug` names the golden file its recorded runs
        are in; a section of the face-and-core job, or of the core's own
        numbers, has none."""
        if slug != self.slug: self._close()
        print("\n--- %s ---" % name)
        if slug and slug != self.slug:
            self.slug = slug
            self.started.setdefault(slug, len(self.fails))
            for d, v in ((self.runs, {}), (self.cwrong, []), (self.pairs, 0)): d.setdefault(slug, v)
            if slug not in self.files: self.files[slug] = self._load(slug)

    def _close(self):
        s = self.slug
        if not s: return
        self.slug = None
        if len(self.fails) > self.started[s]: self.dirty.add(s)
        if self.mode == "write": return
        runs, held = self.runs[s], self.files[s]
        unused = [k for k in held if k not in runs]
        named = lambda d, ks: ["%s on %s" % (d[k]["tool"], d[k]["input"]) for k in ks[:3]]
        self.check("%s: the golden file holds no run the tests no longer ask for (%d held)" % (s, len(held)), not unused,
                   "; ".join(named(held, unused)))
        self.check("%s: the core against the golden file, directly, on %d runs" % (s, self.pairs[s]),
                   self.pairs[s] > 0 and not self.cwrong[s], "; ".join(self.cwrong[s][:3]))

    def finish(self):
        """At the end of the core's tests: close the last section, and either
        null-test the comparison or, with --write-golden, write each clean
        section's file and log why."""
        self._close()
        if self.mode != "write":
            self._nulls(); return
        os.makedirs(self.dir, exist_ok=True)
        wrote = []
        for s, runs in self.runs.items():
            if s in self.dirty:
                print("  REFUSED  %s: a check of its own failed, so this is not the change that was meant; "
                      "its file is left as it was" % s)
                continue
            old = self.files.get(s, {})
            changed = [k for k in runs if k not in old or against(old[k], runs[k]["output"], 0.0) is not None]
            gone = [k for k in old if k not in runs]
            if not changed and not gone and os.path.exists(self._file(s)):
                print("  KEPT     %s: %d runs, unchanged" % (s, len(runs))); continue
            self._save(s, runs)
            wrote.append("%s (%d of %d runs new or changed, %d dropped)" % (s, len(changed), len(runs), len(gone)))
            print("  WROTE    %s: %d runs, %d new or changed, %d dropped, %d bytes"
                  % (s, len(runs), len(changed), len(gone), os.path.getsize(self._file(s))))
            for k in changed[:5]:
                said = against(old[k], runs[k]["output"], 0.0) if k in old else "new"
                print("             %s on %s: %s" % (runs[k]["tool"], runs[k]["input"], said))
        if wrote: self._log(wrote)

    def _log(self, wrote):
        """A line in the README's log for every rewrite: when, why, and what moved."""
        import datetime
        readme = os.path.join(self.dir, "README.md")
        with open(readme, encoding="utf-8") as f: text = f.read()
        mark = "## The log\n"
        if mark not in text: text = text.rstrip("\n") + "\n\n" + mark + "\n"
        line = "- %s: %s Rewrote %s.\n" % (datetime.date.today().isoformat(), self.because.rstrip(".") + ".", "; ".join(wrote))
        body = text.rstrip("\n")
        # A blank line after the log's heading paragraph, none between its entries.
        sep = "\n" if body.splitlines()[-1].startswith("- ") else "\n\n"
        with open(readme, "w", encoding="utf-8") as f: f.write(body + sep + line)
        print("  LOGGED   in core/tests/golden/README.md: " + line.strip())

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
            # A sketch has no text of its own: the core's answer on that run, which the sketch held.
            text = e and e.get("output") or run.get(key, {}).get("output")
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

    # --- a recorded run, and the core's after it ------------------------------
    def recorded(self, tool, path, core=None, core_out=None):
        """What `tool` recorded for the scenario in `path`, as a finished
        process whose stdout is that text: in the place where the tests ran
        the JavaScript. `tool` is the recording runner's stem ("envelope" for
        envelope_js.mjs) or its whole name ("restore_page.py"); `core` is the
        core's command on the same scenario, by default its _cpp tool on the
        path, or `core_out` its output already made. A run kept as a sketch is answered with the core's own output,
        held to the sketch here; a scenario the file has none of fails,
        naming it, and is answered with the core's so the section goes on."""
        s = self.slug
        assert s, "a recorded run outside a section with a golden file"
        name = tool if "." in tool else tool + "_js.mjs"
        key, h, text = self._key(name, path)
        entry = self.files[s].get(key)
        inp = text.split("\n")
        base = os.path.basename(path)
        cmd = core or [os.path.join(self.build, tool + "_cpp"), path]
        def own():
            if core_out is not None: return core_out, None
            c = _real_run(cmd, capture_output=True, text=True)
            return c.stdout if c.returncode == 0 else None, c
        if self.mode == "write":
            out, c = own()
            if out is None: raise SystemExit("the core's %s failed on %s: %s" % (cmd[0], base, c.stderr[-300:]))
            self.runs[s][key] = dict(tool=name, input=base, hash=h, output=out)
            return subprocess.CompletedProcess(cmd, 0, out, "")
        if entry is None:
            self.check("%s: the golden file has a run of %s on %s" % (s, name, base), False,
                       'the scenario is new or has changed: if the sound is meant to change, '
                       '--write-golden --because "why"')
            out, _ = own()
            self.runs[s][key] = dict(tool=name, input=base, hash=h, output=out or "")
            return subprocess.CompletedProcess(cmd, 0, out or "", "")
        if "output" in entry:
            self.runs[s][key] = dict(tool=name, input=base, hash=h)
            before = self.core_seen.pop(path, None)
            # Scan runs the core first and asks for the recorded run after, on the same file.
            if core is None and core_out is None and before and before[0] == tool and before[2] == key:
                self._pair(s, entry, tool + "_cpp", before[1], base, inp)
            elif core is None and core_out is None: self.served[path] = (key, entry, inp)
            else:
                # A core command of the caller's own (restore's, with the sources' file): run and paired here.
                out, c = own()
                self._pair(s, entry, os.path.basename(cmd[0]), out if out is not None else "the core failed: " + c.stderr[-200:], base, inp)
            return subprocess.CompletedProcess(cmd, 0, entry["output"], "")
        # A sketch cannot be handed to the section's comparison as text, so the
        # core's own answer is, and the sketch holds that answer here.
        out, c = own()
        said = against(entry, out, self.tol, inp) if out is not None else "the core's tool failed: " + c.stderr[-200:]
        self.pairs[s] += 1
        if said: self.cwrong[s].append("%s on %s: %s" % (os.path.basename(cmd[0]), base, said))
        self.runs[s][key] = dict(tool=name, input=base, hash=h, output=out or "")
        return subprocess.CompletedProcess(cmd, 0, out or "", "")

    def run(self, cmd, *args, **kw):
        """Every process the tests start, so the core's run on a scenario whose
        recorded run was just handed over is compared with the file directly."""
        r = _real_run(cmd, *args, **kw)
        self._against_core(self.slug, cmd, r)
        return r

    def _against_core(self, s, cmd, r):
        if not s or self.mode == "write" or not isinstance(cmd, (list, tuple)) or len(cmd) != 2: return
        if not isinstance(getattr(r, "stdout", None), str) or getattr(r, "returncode", 1) != 0: return
        path, exe = cmd[1], os.path.basename(str(cmd[0]))
        if not exe.endswith("_cpp"): return
        if path not in self.served:
            stem = exe[:-len("_cpp")]
            if os.path.isfile(path): self.core_seen = {path: (stem, r.stdout, self._key(stem + "_js.mjs", path)[0])}
            return
        key, entry, inp = self.served.pop(path)
        if key.split(":")[0] != exe[:-len("_cpp")] + "_js.mjs" or self._key(key.split(":")[0], path)[0] != key: return
        self._pair(s, entry, exe, r.stdout, os.path.basename(path), inp)

    def _pair(self, s, entry, exe, out, name, inp):
        self.pairs[s] += 1
        said = against(entry, out, self.tol, inp)
        if said: self.cwrong[s].append("%s on %s: %s" % (exe, name, said))
