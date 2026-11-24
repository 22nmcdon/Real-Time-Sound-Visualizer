"""The sound audit's examples: short MP3s, so two controls the numbers call alike can be heard side by side.

Each clip is the phrase render.py measures (six notes, the last held), rendered
through the core as everything else here, matched in loudness within its pair or
set (the sustain's RMS, so a louder control is not heard as a better one), and
written at 64 kbps as the other listening pages' are (ffmpeg). The pairs are
chosen from analysis.json's findings and listed in SETS; the page reads
audio/index.json.

    python3 web/docs/listening/sound-audit/audio.py
"""
import json, os, subprocess, sys, wave
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "audio")

# (set title, what to listen for, [(file, label, base, patch, renderer)])
SETS = json.load(open(os.path.join(HERE, "sets.json")))

def clip(base, patch, renderer="core"):
    setup = R.BASES[base][1]
    code = R.code_of(setup)
    return R.run((renderer, R.phrase_script(code, patch, setup.get("layers") == "split"), 48000))

def main():
    os.makedirs(OUT, exist_ok=True)
    index = []
    for s in SETS:
        takes = [(f, label, clip(base, patch, renderer)) for f, label, base, patch, renderer in s["clips"]]
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
    json.dump(index, open(os.path.join(OUT, "index.json"), "w"), indent=1)

if __name__ == "__main__":
    main()
