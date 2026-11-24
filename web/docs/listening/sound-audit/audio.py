"""The sound audit's examples: short MP3s, so two controls the numbers call alike can be heard side by side.

Each clip is the phrase render.py measures (six notes, the last held), rendered
through the core as everything else here, matched in loudness within its pair or
set (the sustain's RMS, so a louder control is not heard as a better one), and
written at 64 kbps as the other listening pages' are (ffmpeg). The pairs are
chosen from analysis.json's findings and listed in SETS; the page reads
audio/index.json.

    python3 web/docs/listening/sound-audit/audio.py
    python3 web/docs/listening/sound-audit/audio.py --followup   the follow-up's sets: sets-followup.json to audio/followup.json

A clip may name its script after its renderer: "phrase" (the default), or "chord", the
held A3 with a major third over it in just tuning, three seconds and let go, as the
follow-up's Chord measure hears it.
"""
import json, os, subprocess, sys, wave
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "audio")

# (set title, what to listen for, [(file, label, base, patch, renderer)])
FOLLOW = "--followup" in sys.argv
SETS = json.load(open(os.path.join(HERE, "sets-followup.json" if FOLLOW else "sets.json")))

def clip(base, patch, renderer="core", script="phrase"):
    setup = R.BASES[base][1]
    code = R.code_of(setup)
    if script == "chord":
        notes, _ = R.notes_of(setup)
        p = patch if "just" in patch else dict(patch, just=True)
        return R.run((renderer, R.held_script(code, p, sorted(notes + [n + 4 for n in notes])), 48000))
    return R.run((renderer, R.phrase_script(code, patch, setup.get("layers") == "split"), 48000))

def main():
    os.makedirs(OUT, exist_ok=True)
    index = []
    for s in SETS:
        takes = [(c[0], c[1], clip(*c[2:])) for c in s["clips"]]
        # matched in loudness: each to the set's quietest RMS, then one gain so the loudest peak is 0.9
        rms = [float(np.sqrt(np.mean(x[int(0.2 * 48000):] ** 2))) for _, _, x in takes]
        target = min(r for r in rms if r > 1e-6)
        scaled = [(f, label, x * (target / r if r > 1e-6 else 1)) for (f, label, x), r in zip(takes, rms)]
        g = 0.9 / max(float(np.abs(x).max()) for _, _, x in scaled)
        for f, label, x in scaled:
            wav = os.path.join(R.BUILD, f + ".wav")
            with wave.open(wav, "wb") as w:
                w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
                w.writeframes((np.clip(x * g, -1, 1) * 32767).astype("<i2").tobytes())
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-codec:a", "libmp3lame", "-b:a", "64k",
                            os.path.join(OUT, f + ".mp3")], check=True)
            os.remove(wav)
        index.append({"title": s["title"], "listen": s["listen"], "clips": [{"file": "audio/%s.mp3" % f, "label": l} for f, l, _ in scaled]})
        print(s["title"], [f for f, _, _ in scaled])
    json.dump(index, open(os.path.join(OUT, "followup.json" if FOLLOW else "index.json"), "w"), indent=1)

if __name__ == "__main__":
    main()
