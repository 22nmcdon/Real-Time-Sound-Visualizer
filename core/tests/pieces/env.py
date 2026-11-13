"""The gate and the envelope, on the core: envtest.py's numbers rows.

These were envtest.py's on ?brain=js until stage 5, step 3, batch 4 (13
Nov): a `makeGeneratorCore` built in the page and stepped by hand
(`core.gate`, `core.envelope`, `core.block`), and the generator's worklet
rendered in an `OfflineAudioContext` from `generatorModuleSource()` with no
`wasm` in its options - the page's JavaScript engine both ways. Here the
core's own generator (generator_cpp: `gated`, `gate`, `set`, the heard lane,
and after the samples the envelope and the source `env.note` reads), with
the measurements the suite made - 10 ms peak windows, the steepest step, the
pitch by zero crossings - written again in Python. The rest of envtest.py,
the keyboard end to end and the readout's line, is the face's and the
instrument's and stays in the suite, on the default page. Each check has
its null beside it.
"""
import math

RATE = 44100
N = 128
AMP = 0.55


def run(kit):
    check, null = kit.check, kit.null

    def render(samples, events, lfo="lfo0=sine,0.2 lfo1=sine,0.5"):
        """The left lane, and the envelope and env.note's reading as the run left them."""
        blocks = -(-samples // N) * N
        out = kit.floats("generator_cpp", "run rate=%r slots=32 seed=3 samples=%d %s\n%s\nend"
                         % (float(RATE), blocks, lfo, "\n".join("at %d %s" % e for e in events)))
        left = out[0:blocks * 6:6][:samples]
        tail = out[blocks * 6:]
        return left, tail[0], tail[-3]

    def envelope_of(samples, ms=10):
        per = max(8, round(ms * RATE / 1000))
        return [max(abs(v) for v in samples[at:at + per]) for at in range(0, len(samples) - per + 1, per)]

    def worst_step(s, frm, to):
        worst, at = 0, -1
        for i in range(max(1, frm), min(len(s), to)):
            d = abs(s[i] - s[i - 1])
            if d > worst: worst, at = d, i
        return worst, at

    def pitch(s):
        """Hz by rising zero crossings, interpolated, first to last."""
        at = [k - 1 + s[k - 1] / (s[k - 1] - s[k]) for k in range(1, len(s)) if s[k - 1] < 0 <= s[k]]
        return (len(at) - 1) * RATE / (at[-1] - at[0]) if len(at) > 2 else None

    # --- it is not there until it is asked for (envtest :126, :128) ---
    # A core nobody has gated: its envelope one and its source nought (the
    # source reads the envelope only when gated, sources.h), and its peak the
    # amplitude from the first 10 ms to the last.
    base = [(0, "set shape sine"), (0, "set amp 0.9")]
    left, envelope, source = render(4410, base)
    early, late = max(abs(v) for v in left[:441]), max(abs(v) for v in left[-441:])
    check("a core nobody has gated is wide open and says so: envelope one, and env.note reads nought",
          envelope == 1 and source == 0, "envelope %r, env.note %r" % (envelope, source))
    check("and its amplitude is the slider, from the first sample to the last",
          abs(early - 0.9) < 1e-3 and abs(late - 0.9) < 1e-3, "%.4f then %.4f against 0.9" % (early, late))
    gl, genv, gsrc = render(4410, base + [(0, "gated 1")])
    null("a core gated with no note is not wide open, and is silent",
         not (genv == 1 and gsrc == 0) and max(abs(v) for v in gl) < 1e-6, "envelope %r, peak %.2e" % (genv, max(abs(v) for v in gl)))

    # --- the shape, off the samples the generator made (envtest :197 to :250) ---
    # As the suite's offline render: gated from the start, a sine at 220 and
    # 0.55, the gate opened at 128 and closed at 0.45 s on a block's edge.
    def staged(attack=50, decay=100, sustain=0.5, release=200, hold=0.45, seconds=1.0):
        on, off = 128, round(hold * RATE / 128) * 128
        ev = [(0, "set shape sine"), (0, "set freq 220"), (0, "set amp %r" % AMP), (0, "set interval 0"),
              (0, "set attackMs %r" % attack), (0, "set decayMs %r" % decay), (0, "set sustain %r" % sustain),
              (0, "set releaseMs %r" % release), (0, "gated 1"), (on, "gate 1 1"), (off, "gate 0 0")]
        left = render(round(RATE * seconds), ev)[0]
        return left, on, off

    def shape(left, on, off, attack=50, decay=100, sustain=0.5, release=200):
        env = envelope_of(left)
        at = lambda ms: env[int(ms / 10)] / AMP
        peak_at = max(range(len(env)), key=lambda i: env[i])
        settled = next((i for i in range(len(env)) if abs(env[i] / AMP - sustain) < 0.02), None)
        silent = next((i for i in range(int(off / RATE * 100), len(env)) if env[i] / AMP < 0.01), None)
        on_ms, off_ms = on / RATE * 1000, off / RATE * 1000
        return {
            "starts": at(0) < 0.35,
            "open": env[peak_at] / AMP > 0.9 and peak_at * 10 <= attack + 20,
            "sustain": abs(at(300) - sustain) < 0.04 and abs(at(440) - sustain) < 0.04,
            "gone": at(off_ms + release + 50) < 0.02,
            "attack": abs(peak_at * 10 - (on_ms + attack)) <= 12,
            "decay": settled is not None and abs(settled * 10 - (on_ms + attack + decay)) <= 25,
            "release": silent is not None and abs(silent * 10 - (off_ms + release)) <= 30,
            "detail": "peak %.3f at %d ms, sustain %.3f at 300 and %.3f at 440, %.4f %d ms after the release; "
                      "settled %s ms, silent %s ms" % (env[peak_at] / AMP, peak_at * 10, at(300), at(440),
                                                       at(off_ms + release + 50), release + 50,
                                                       settled * 10 if settled is not None else "never",
                                                       silent * 10 if silent is not None else "never"),
        }
    left, on, off = staged()
    got = shape(left, on, off)
    check("it starts from nothing", got["starts"], got["detail"])
    check("and is open within the attack it was given", got["open"], got["detail"])
    check("then falls to the sustain it was given", got["sustain"], got["detail"])
    check("and is gone within the release it was given", got["gone"], got["detail"])
    check("the attack takes the time it says, not a time constant", got["attack"], got["detail"])
    check("and the decay arrives at the sustain when it said it would", got["decay"], got["detail"])
    check("and the release is over when it said it would be", got["release"], got["detail"])
    # The nulls: each reading against a render whose envelope is not the one
    # asked of it - the same samples judged against twice the attack, the
    # decay and the release, and a sustain of 0.7.
    wrong = shape(left, on, off, attack=100, decay=200, sustain=0.7, release=400)
    null("the same samples judged against twice the times and a sustain of 0.7 fail the timings and the sustain",
         not wrong["attack"] and not wrong["decay"] and not wrong["release"] and not wrong["sustain"], wrong["detail"])
    ungated = render(RATE, [(0, "set shape sine"), (0, "set freq 220"), (0, "set amp %r" % AMP)])[0]
    null("and an ungated core does not start from nothing", not shape(ungated, on, off)["starts"])

    first = max(abs(v) for v in left[on:on + 128])
    check("a note-on is doing something inside the block after it", first > 1e-4, "peak %.5f in the 128 frames after the gate" % first)
    null("and the block before it is silent", max(abs(v) for v in left[:on]) < 1e-9)

    # --- no step at any edge (envtest :267, :270) ---
    slope = AMP * 2 * math.pi * 220 / RATE
    onset, release, = worst_step(left, 0, 4410 + 128), worst_step(left, off - 441, off + 4410)
    check("the gate opening is not a step", onset[0] < slope * 1.2, "%.4f at sample %d, the sine's own %.4f" % (onset + (slope,)))
    check("nor the gate closing", release[0] < slope * 1.2, "%.4f at sample %d" % release)
    # The null: an envelope that cuts. A 1 ms attack and release are the
    # quickest the panel offers, and on the peak of a cosine they jump.
    cut, con, coff = staged(attack=0, release=0)
    null("an attack and release of nothing are steps the same reading sees",
         worst_step(cut, 0, 4410 + 128)[0] > slope * 1.2 or worst_step(cut, coff - 441, coff + 4410)[0] > slope * 1.2,
         "%.4f, %.4f" % (worst_step(cut, 0, 4410 + 128)[0], worst_step(cut, coff - 441, coff + 4410)[0]))

    # --- legato, and what is not legato (envtest :314 to :326) ---
    # The page stepped one core by hand and read its envelope between steps;
    # here each reading is its own run of the same script cut at that moment,
    # on blocks' edges: a key, a second key 200 ms in, both up 6 ms after,
    # and the second key again from silence 300 ms after that.
    LEG = [(0, "set shape sine"), (0, "set amp %r" % AMP), (0, "set attackMs 20"), (0, "set decayMs 40"), (0, "set sustain 0.5"),
           (0, "set releaseMs 60"), (0, "gated 1"), (0, "gate 1 1")]
    two, up, again = 8832, 9088, 22400       # 200 ms, 206 ms and 508 ms, on block edges
    def env_at(samples, extra, script=LEG):
        return render(samples, script + extra)[1]
    held = env_at(two, [])
    overlaid = env_at(two + 256, [(two, "gate 1 0.25")])
    after = env_at(again, [(two, "gate 1 0.25"), (up, "gate 0 0")])
    renewed_left, renewed, _ = render(again + 4480, LEG + [(two, "gate 1 0.25"), (up, "gate 0 0"), (again, "gate 1 0.25")])
    detail = "sustain %.4f, after a second key %.4f, released %.4f, retriggered %.4f" % (held, overlaid, after, renewed)
    check("a second key over a held one does not restart the envelope", abs(overlaid - held) < 0.02, detail)
    check("and does not take its velocity either", overlaid > 0.4, detail)
    check("a release runs all the way out", after == 0, detail)
    check("and the next key starts it again, at its own velocity", abs(renewed - 0.5 * 0.25) < 0.005, detail)
    # And what is heard is that level, not only what the envelope reports:
    # the mutation pass (batch 4) found the samples could drop the velocity
    # with every reading above still right. The last 10 ms of the run, 100
    # ms after the key, past its 20 ms attack and 40 ms decay.
    heard = max(abs(v) for v in renewed_left[-441:]) / AMP
    check("and it is heard at that level: the sustain at a quarter velocity", abs(heard - 0.125) < 0.01, "%.4f of the amplitude" % heard)
    held_left = render(two, LEG)[0]
    null("the first key, at full velocity, is heard at the sustain, not a quarter of it",
         abs(max(abs(v) for v in held_left[-441:]) / AMP - 0.125) >= 0.01, "%.4f" % (max(abs(v) for v in held_left[-441:]) / AMP))
    # The nulls: the second key struck from silence restarts it at its
    # velocity (so "does not take its velocity" can fail), and a release cut
    # short is not nought.
    fresh = env_at(two + 2688, [(128, "gate 0 0"), (two, "gate 1 0.25")])
    null("a key struck from silence does take its velocity", not fresh > 0.4, "%.4f" % fresh)
    short = env_at(up + 1024, [(two, "gate 1 0.25"), (up, "gate 0 0")])
    null("and 23 ms into a 60 ms release it is not yet nought", short != 0, "%.4f" % short)

    # --- the glide's own time (envtest :358) ---
    # poleFor was once shared with the envelope and scaled by its stage, so a
    # glide under a note took another time than one on an ungated core.
    def glided(gated, glide=200, jump=4480):
        ev = [(0, "set shape sine"), (0, "set glideMs %r" % glide), (0, "set sustain 1"), (0, "set attackMs 1"),
              (0, "set decayMs 1"), (0, "set freq 220"), (0, "set interval 0"), (jump, "set freq 440")]
        if gated: ev += [(0, "gated 1"), (0, "gate 1 1")]
        left = render(jump + 2205, ev)[0]
        return pitch(left[jump + 441:jump + 2205])
    open_, under = glided(False), glided(True)
    check("a glide takes the same time whether a note is holding or not",
          open_ is not None and under is not None and abs(open_ - under) < 8, "%.1f Hz ungated, %.1f under a note" % (open_, under))
    quicker = glided(True, glide=100)
    null("and a glide of 100 ms under a note is told from 200 ungated", abs(open_ - quicker) >= 8, "%.1f against %.1f" % (quicker, open_))

    # --- with no glide and with one (envtest :398, :401) ---
    def jumped(glide):
        ev = [(0, "set shape sine"), (0, "set glideMs %r" % glide), (0, "set freq 220"), (0, "set interval 0"),
              (2304, "set freq 440")]
        left = render(2304 + 2205, ev)[0]
        return pitch(left[2304 + 441:2304 + 2205])
    off_, on_ = jumped(0), jumped(200)
    check("with no glide the pitch is simply the new one", off_ is not None and abs(off_ - 440) < 12, "%.1f" % off_)
    check("and with a glide it is still on its way there", on_ is not None and on_ < 400, "%.1f" % on_)
    null("the glide's pitch is not simply the new one, nor the jump's on its way",
         abs(on_ - 440) >= 12 and not off_ < 400, "%.1f, %.1f" % (on_, off_))
