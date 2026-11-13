"""Golden files: what the page's JavaScript produced for each parity scenario,
kept in core/tests/golden/ so the core can be held to it once the JavaScript
is gone (stage 5, step 2 of plugin/STAGE5-PLAN.md; core/tests/golden/README.md).

Parity runs the JavaScript the same way everywhere: `node tools/<x>_js.mjs
<scenario file>`, and the core's tool on the same file. So this sits at that
one point rather than at parity's two hundred comparisons: it is put in place
of `subprocess.run` for parity's run, sees every call, and acts only on the
JavaScript tools inside a section that has a golden file. The decision could
have gone the other way - a helper called by name at each of the 28 sites -
which reads more plainly but is 28 edits in a 6,900-line file, any of which
could be missed silently; a missed site here would show as a run the file has
never seen, which the three-way mode fails on.

Three modes, from parity's command line:

  (none)           all three: the page's JavaScript runs as before and parity
                   compares it with the core as before; every run is also
                   compared with its golden file, and the core's answer on the
                   same scenario is compared with the file directly.
  --golden         the core against the files: the JavaScript tools are not
                   run in a golden section, their golden output is handed to
                   parity's comparisons in their place, and the core is also
                   compared with the file directly.
  --write-golden   regenerate: as (none), then each section's file is written
                   only if every check in that section passed - that is, only
                   if the JavaScript and the core agree on it - so a
                   regenerated file is never merely believed.

A file is keyed by the tool and a hash of the scenario's text (with the
checkout's paths taken out, so it is the same file in any checkout), not by
the scenario's file name: parity reuses names like `one.txt` for many runs.
"""
import gzip, hashlib, json, math, os, subprocess

_real_run = subprocess.run

def _tokens_differ(p, q, tol):
    """None if two whitespace tokens are the same to parity's rule, else the gap.
    The rule is kdiff's: numbers to `tol` relative to the larger of one and the
    first; NaN against NaN the same; NaN against anything else a failure,
    never skipped (worst()'s rule); anything that is not a number exactly."""
    if p == q: return None
    try: fp, fq = float(p), float(q)
    except ValueError: return math.inf
    if math.isnan(fp) and math.isnan(fq): return None
    gap = abs(fp - fq)
    if math.isnan(gap): return math.inf
    return None if gap <= tol * max(1.0, abs(fp)) else gap

def diff(a, b, tol, inp=None):
    """Where two outputs first differ, with by how much, or None. `inp` is the
    scenario's lines: where the output has a line per input line, the input's
    line is named too, since 'line 4117' alone does not say which call it was."""
    la, lb = a.split("\n"), b.split("\n")
    if len(la) != len(lb): return "%d lines against %d" % (len(la), len(lb))
    for i, (x, y) in enumerate(zip(la, lb)):
        tx, ty = x.split(), y.split()
        if len(tx) != len(ty): return "line %d: %d values against %d" % (i + 1, len(tx), len(ty))
        for j, (p, q) in enumerate(zip(tx, ty)):
            gap = _tokens_differ(p, q, tol)
            if gap is None: continue
            said = "line %d, value %d: %s against %s (by %.3g)" % (i + 1, j + 1, p[:40], q[:40], gap)
            if inp is not None and len(inp) in (len(la), len(la) - 1) and i < len(inp):
                said += ", on: " + inp[i][:100]
            return said
    return None

class Golden:
    def __init__(self, here, argv, tol, check, fails):
        self.dir = os.path.join(here, "golden")
        self.paths = [os.path.dirname(here), here]   # core/, then core/tests/: the longer goes last so it is replaced first
        self.mode = "golden" if "--golden" in argv else "write" if "--write-golden" in argv else "three"
        self.tol, self.check, self.fails = tol, check, fails
        self.slug = None          # the golden file of the section now running, or None
        self.started = {}         # slug -> how many checks had failed when it began
        self.dirty = set()        # slugs a check failed in, which --write-golden refuses
        self.runs = {}            # slug -> {key: entry}, every JavaScript run this time
        self.files = {}           # slug -> {key: entry}, as loaded
        self.wrong = {}           # slug -> [what differed], file against the JavaScript
        self.cwrong = {}          # slug -> [what differed], the core against the file
        self.pairs = {}           # slug -> runs the core was compared with the file on directly
        self.served = {}          # input path -> (hash, golden text, scenario lines), for the core's run after
        self.direct = set()       # tools whose core output is in the JavaScript's own format
        self.probe = os.environ.get("GOLDEN_PROBE")
        self.tally = {}
        self.written = []
        subprocess.run = self.run

    # --- sections -----------------------------------------------------------
    def section(self, name, slug=None):
        """Parity's section heading. `slug` names the golden file the section's
        JavaScript runs belong to; a section of the face-and-core job has none."""
        if slug != self.slug: self._close()
        print("\n--- %s ---" % name)
        if slug and slug != self.slug:
            self.slug = slug
            self.started.setdefault(slug, len(self.fails))
            self.runs.setdefault(slug, {})
            self.wrong.setdefault(slug, []); self.cwrong.setdefault(slug, []); self.pairs.setdefault(slug, 0)
            self.files[slug] = self._load(slug)
        elif not slug:
            self.slug = None

    def _close(self):
        s = self.slug
        if not s: return
        if len(self.fails) > self.started[s]: self.dirty.add(s)
        runs, held = self.runs[s], self.files[s]
        if self.mode != "write":
            missing = [k for k in runs if k not in held]
            unused = [k for k in held if k not in runs]
            if self.mode == "three":
                self.check("%s: the golden file agrees with the page's JavaScript on all %d runs" % (s, len(runs)),
                           not self.wrong[s] and not missing,
                           "; ".join(self.wrong[s][:3] + ["no run of %s on %s in the file" % (runs[k]["tool"], runs[k]["input"])
                                                          for k in missing[:3]]))
            self.check("%s: and holds no run parity no longer makes (%d held)" % (s, len(held)), not unused,
                       "; ".join("%s on %s" % (held[k]["tool"], held[k]["input"]) for k in unused[:3]))
            self.check("%s: the core against the golden file, directly, on %d runs" % (s, self.pairs[s]),
                       self.pairs[s] > 0 and not self.cwrong[s], "; ".join(self.cwrong[s][:3]))
        self.slug = None

    def finish(self):
        """At the end of parity: close the last section and, with --write-golden,
        write each clean section's file."""
        self._close()
        if self.mode != "write": self._nulls()
        if self.probe:
            with open(self.probe, "w") as f: json.dump(self.tally, f, indent=1)
        if self.mode != "write": return
        os.makedirs(self.dir, exist_ok=True)
        for s, runs in self.runs.items():
            if s in self.dirty:
                print("  REFUSED  %s: a check failed in its section, so the JavaScript and the core do not agree; file left as it was" % s)
                continue
            old = self.files.get(s, {})
            changed = [k for k in runs if k not in old or old[k]["output"] != runs[k]["output"]]
            gone = [k for k in old if k not in runs]
            if not changed and not gone:
                print("  KEPT     %s: %d runs, unchanged" % (s, len(runs))); continue
            self._save(s, runs)
            print("  WROTE    %s: %d runs, %d new or changed, %d dropped" % (s, len(runs), len(changed), len(gone)))
            for k in changed[:5]:
                said = diff(old[k]["output"], runs[k]["output"], self.tol) if k in old else "new"
                print("             %s on %s: %s" % (runs[k]["tool"], runs[k]["input"], said))
            self.written.append(s)

    def _nulls(self):
        """The comparison's own nulls, on a real run from the files: one value
        changed, and a NaN put in, must each fail and be named by line and
        value; and a NaN in both, at the same place, is no difference (the
        worst() rule both ways)."""
        run = next((e for s in self.files.values() for e in s.values() if len(e["output"]) > 200), None)
        self.check("the golden files were read (one run of more than a few values found to null-test)", run is not None)
        if run is None: return
        out = run["output"]
        lines = out.split("\n")
        i = next(k for k, l in enumerate(lines) if any(self._num(t) for t in l.split()))
        toks = lines[i].split(); j = next(k for k, t in enumerate(toks) if self._num(t))
        def put(v):
            t = list(toks); t[j] = v
            return "\n".join(lines[:i] + [" ".join(t)] + lines[i + 1:])
        nudged = put(repr(float(toks[j]) + 1e-9 * max(1.0, abs(float(toks[j])))))
        said = diff(out, nudged, self.tol)
        where = "line %d, value %d:" % (i + 1, j + 1)
        self.check("null: one value in a golden file moved by a billionth fails, named by line and value (%s on %s)"
                   % (run["tool"], run["input"]), said is not None and said.startswith(where), said or "passed")
        said = diff(out, put("NaN"), self.tol)
        self.check("null: and a NaN put in its place fails too, either way round",
                   said is not None and said.startswith(where) and diff(put("NaN"), out, self.tol) is not None, said or "passed")
        self.check("and a NaN against a NaN at the same place is no difference", diff(put("NaN"), put("NaN"), self.tol) is None)
        self.check("and a value moved by less than the tolerance is none either",
                   diff(out, put(repr(float(toks[j]) * (1 + self.tol / 10))), self.tol) is None)

    @staticmethod
    def _num(t):
        try: return math.isfinite(float(t)) and float(t) != 0
        except ValueError: return False

    # --- the files ----------------------------------------------------------
    # One gzipped JSON file a section, a list of runs in the order parity made
    # them, each {tool, input, hash, output}, the output as the tool printed
    # it. Gzipped because the generator's and the picture's runs are tens of
    # megabytes of digits as text and compress about tenfold; the cost is that
    # a regeneration's diff is not readable in git, which is why
    # --write-golden prints where each changed run first moved.
    def _file(self, slug): return os.path.join(self.dir, slug + ".json.gz")
    def _load(self, slug):
        try:
            with gzip.open(self._file(slug), "rt", encoding="utf-8") as f: data = json.load(f)
        except FileNotFoundError: return {}
        return {e["tool"] + ":" + e["hash"]: e for e in data["runs"]}
    def _save(self, slug, runs):
        data = {"section": slug, "about": "core/tests/golden/README.md", "runs": list(runs.values())}
        text = json.dumps(data, indent=0, ensure_ascii=False, sort_keys=True)
        # mtime 0, so the same runs write the same bytes and git sees no change.
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
        s = self.slug
        env = kw.get("env")
        is_js = (s and isinstance(cmd, (list, tuple)) and len(cmd) == 3 and cmd[0] == "node"
                 and str(cmd[1]).endswith("_js.mjs") and not (env and env.get("CORE")))
        if not is_js:
            r = _real_run(cmd, *args, **kw)
            self._against_core(s, cmd, r)
            return r
        tool, path = os.path.basename(cmd[1]), cmd[2]
        key, h, text = self._key(tool, path)
        entry = self.files[s].get(key)
        inp = text.split("\n")
        if self.mode == "golden":
            if entry is None:
                self.check("%s: the golden file has a run of %s on %s" % (s, tool, os.path.basename(path)), False,
                           "the scenario is new or has changed: regenerate with parity.py --write-golden")
                r = _real_run(cmd, *args, **kw)
                out = r.stdout
            else:
                out = entry["output"]
                r = subprocess.CompletedProcess(cmd, 0, out, "")
            self.runs[s][key] = dict(tool=tool, input=os.path.basename(path), hash=h, output=out)
            self.served[path] = (key, out, inp)
            return r
        r = _real_run(cmd, *args, **kw)
        self.runs[s][key] = dict(tool=tool, input=os.path.basename(path), hash=h, output=r.stdout)
        if entry is not None:
            said = diff(entry["output"], r.stdout, self.tol, inp)
            if said: self.wrong[s].append("%s on %s: %s" % (tool, os.path.basename(path), said))
            self.served[path] = (key, entry["output"], inp)
        else:
            self.served[path] = (key, r.stdout, inp)
        return r

    def _against_core(self, s, cmd, r):
        """The core's run on a scenario the JavaScript (or its file) just
        answered: compared with the file directly, so a difference is named by
        scenario, line and value, not only by the section's own check. Only
        where the core's tool prints the JavaScript's format line for line,
        which is most of them; for the others parity's own comparison, against
        the file's text in --golden, is the check."""
        if not s or not isinstance(cmd, (list, tuple)) or len(cmd) < 2 or getattr(r, "returncode", 1) != 0: return
        if not isinstance(getattr(r, "stdout", None), str): return
        path = cmd[1] if len(cmd) == 2 else None
        if path not in self.served: return
        key, gold, inp = self.served.pop(path)
        tool = key.split(":")[0]
        if not self.probe and tool not in self.direct: return
        with open(path, encoding="utf-8") as f: now = f.read()
        if self._key(tool, path)[0] != key: return
        self.pairs[s] += 1
        said = diff(gold, r.stdout, self.tol, inp)
        t = self.tally.setdefault(tool, [0, 0, ""]); t[0] += 1
        if said: t[1] += 1; t[2] = t[2] or said
        if said: self.cwrong[s].append("%s on %s: %s" % (os.path.basename(cmd[0]), os.path.basename(path), said))
