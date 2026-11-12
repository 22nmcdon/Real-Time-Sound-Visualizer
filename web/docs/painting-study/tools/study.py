"""Make everything the study page shows, from the rendered phrases.

    python3 phrases.py     # first: the four phrases through the core (45 s)
    python3 study.py       # then: paintings, fades, Scan's read, results.json (a few minutes)
    python3 page.py        # and the page

What is rendered (not every combination - the brief asks for these):
  - physical paint first, the owner's priority (12 Nov): every phrase, with
    a detail crop at full resolution; Crossed hands in Earth, Night and
    Scroll; build-up animations for Crossed hands, the run and the chords;
    its cost per frame at three canvas sizes;
  - every phrase in every other style, Layered and Accumulate, in the house palette (12);
  - each style once in Earth and once in Night, on Crossed hands, the one
    phrase with two hands and so all six inks (6);
  - each style once in Scroll, on Crossed hands (3); Layered is the twelve;
  - a Fade animation for two phrases per style, with the phrase's audio (6);
  - what Scan would read off each style's Crossed hands painting: the
    finished painting held under a note, and the fading canvas read as it is
    painted, the phrase's length (6 sounds).
"""
import json, os, subprocess, sys, time
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import features, paint, palettes, physical  # noqa: E402

STUDY = os.path.dirname(HERE)
BUILD = os.path.join(STUDY, "build")
IMG = os.path.join(STUDY, "img")
ANIM = os.path.join(STUDY, "anim")
AUDIO = os.path.join(STUDY, "audio")
SIZE = {"layered": (1400, 1400), "scroll": (2400, 900)}
PHRASES = ("pad", "crossed", "run", "chords")
STYLES = ("ink", "gesture", "geometry")
FADES = {"ink": ("pad", "crossed"), "gesture": ("run", "crossed"), "geometry": ("chords", "run")}
PERSISTENCE = 4.0      # seconds for a mark to fade to a tenth, in Fade
FPS, ANIM_PX = 20, 600
SOFT = 3.0             # Scan's Softness, cells: the page's default
SCAN_NOTE, SCAN_DEPTH = 220.0, 0.6
PHYS = 1600                                  # physical paint's canvas, square
PHYS_BUILDS = ("crossed", "run", "chords")    # its build-up animations
PHYS_ANIM = 1000                              # simulated at this size for the animations, shown at 720

_cache = {}


def analysis(name):
    if name not in _cache: _cache[name] = features.analyse(name)
    return _cache[name]


def ops_for(name, style, layout):
    w, h = SIZE[layout]
    return paint.marks(analysis(name), style, layout, w, h)


def still(name, style, layout, pal):
    w, h = SIZE[layout]
    st = paint.accumulate(ops_for(name, style, layout), w, h)
    img = st.image(palettes.PALETTES[pal])
    path = os.path.join(IMG, f"{name}-{style}-{layout}-{pal}.jpg")
    Image.fromarray(img).save(path, quality=84, optimize=True, progressive=True)
    return st, os.path.relpath(path, STUDY)


def grid64(density):
    return np.asarray(Image.fromarray(density.astype(np.float32), "F").resize((64, 64), Image.BOX), np.float32)


def scan_tables(grids):
    src = os.path.join(BUILD, "grids.f32"); dst = os.path.join(BUILD, "tables.f32")
    np.asarray(grids, np.float32).tofile(src)
    subprocess.run([os.path.join(BUILD, "scanread"), src, str(SOFT), dst], check=True)
    rec = np.fromfile(dst, np.float32).reshape(len(grids), 4 + 512)
    return rec[:, 0] > 0, rec[:, 1:4], rec[:, 4:]


def play(tables, ok, rate_tables, seconds, rate=48000):
    """A held note at SCAN_NOTE whose wave is the sine mixed with Scan's
    table at SCAN_DEPTH, as the voice's scanMix does, the table moving to
    each new reading by a crossfade over its interval (the core fades over a
    tick); an unreadable (dark) grid holds the last table, as the core does."""
    n = int(seconds * rate)
    t = np.arange(n) / rate
    phase = (SCAN_NOTE * t) % 1.0
    ink = np.sin(2 * np.pi * phase)
    idx = phase * 512
    i0 = idx.astype(int) % 512; i1 = (i0 + 1) % 512; fr = idx - np.floor(idx)
    held, last = [], np.zeros(512, np.float32)
    for k in range(len(tables)):
        if ok[k]: last = tables[k]
        held.append(last)
    held = np.array(held)
    pos = np.minimum(t * rate_tables, len(held) - 1)
    a = np.floor(pos).astype(int); b = np.minimum(a + 1, len(held) - 1); x = pos - a
    va = held[a, i0] * (1 - fr) + held[a, i1] * fr
    vb = held[b, i0] * (1 - fr) + held[b, i1] * fr
    tab = va + (vb - va) * x
    out = ink + (tab - ink) * SCAN_DEPTH
    env = np.minimum(1, t / 0.05) * np.minimum(1, (seconds - t) / 0.3)
    return (0.35 * out * env).astype(np.float32)


def mp3(samples, path, rate=48000):
    raw = os.path.join(BUILD, "tmp.f32"); samples.tofile(raw)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(rate), "-ac", "1", "-i", raw,
                    "-b:a", "64k", path], check=True)


def harmonic_centroid(table):
    s = np.abs(np.fft.rfft(table))[1:65] ** 2
    return float((s * np.arange(1, 65)).sum() / max(s.sum(), 1e-12))


def fade(name, style):
    w, h = SIZE["layered"]
    s = ANIM_PX / w
    ops = ops_for(name, style, "layered")
    length = analysis(name)["length"]
    path = os.path.join(ANIM, f"{name}-{style}-fade.webm")
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{ANIM_PX}x{ANIM_PX}",
                           "-r", str(FPS), "-i", "-", "-i", os.path.join(AUDIO, name + ".mp3"),
                           "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "33", "-row-mt", "1", "-deadline", "good", "-cpu-used", "4",
                           "-c:a", "libopus", "-b:a", "48k", "-shortest", path], stdin=subprocess.PIPE)
    for st in paint.fade_frames(ops, w, h, s, FPS, length, PERSISTENCE):
        ff.stdin.write(st.image(palettes.PALETTES["brand"]).tobytes())
    ff.stdin.close(); ff.wait()
    return os.path.relpath(path, STUDY), None


def detail_box(rgb, size=520):
    """Where the brushwork is busiest: the window, on a coarse grid, whose
    luminance varies most - so the crop shows strokes meeting, not paper."""
    lum = rgb.astype(np.float32).mean(axis=2)
    h, w = lum.shape
    best, box = -1.0, (0, 0)
    for y in range(0, h - size, size // 4):
        for x in range(0, w - size, size // 4):
            v = float(lum[y:y + size:4, x:x + size:4].std())
            if v > best: best, box = v, (x, y)
    return box[0], box[1], box[0] + size, box[1] + size


def physical_still(name, layout, pal, w, h):
    a = analysis(name)
    out = {}
    cost = physical.run(a, layout, w, h, palettes.PALETTES[pal], [a["length"] + 0.5],
                        lambda rgb, cov: out.update(rgb=rgb.copy(), cov=cov.copy()))
    tag = f"{name}-physical-{'layered' if layout == 'wheel' else layout}-{pal}"
    path = os.path.join(IMG, tag + ".jpg")
    Image.fromarray(out["rgb"]).save(path, quality=86, optimize=True, progressive=True)
    rel = os.path.relpath(path, STUDY)
    crop = None
    if layout == "wheel" and pal == "brand":
        box = detail_box(out["rgb"])
        cpath = os.path.join(IMG, tag + "-detail.jpg")
        Image.fromarray(out["rgb"]).crop(box).save(cpath, quality=90, optimize=True)
        crop = os.path.relpath(cpath, STUDY)
    return out, rel, crop, cost


def parse_cost(line):
    p = line.split()
    d = {p[i]: p[i + 1] for i in range(0, len(p) - 1) if p[i] in ("steps", "brush_s", "frames", "render_s")}
    k = p.index("landed")
    return dict(steps=int(d["steps"]), brush_s=float(d["brush_s"]), frames=int(d["frames"]), render_s=float(d["render_s"]),
                wet=float(p[k + 2]), dry=float(p[k + 4]), bare=float(p[k + 6]))


def build_up(name):
    """The physical painting made in time with its sound, at 20 frames a
    second, simulated at PHYS_ANIM and shown at 720; and the brushwork's
    and the rendering's cost per frame."""
    a = analysis(name)
    n = int(a["length"] * FPS)
    times = [(f + 1) / FPS for f in range(n)]
    path = os.path.join(ANIM, f"{name}-physical-build.webm")
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{PHYS_ANIM}x{PHYS_ANIM}",
                           "-r", str(FPS), "-i", "-", "-i", os.path.join(AUDIO, name + ".mp3"), "-vf", "scale=720:720:flags=area",
                           "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "33", "-row-mt", "1", "-deadline", "good", "-cpu-used", "4",
                           "-c:a", "libopus", "-b:a", "48k", "-shortest", path], stdin=subprocess.PIPE)
    grids = []
    cost = physical.run(a, "wheel", PHYS_ANIM, PHYS_ANIM, palettes.PALETTES["brand"], times,
                        lambda rgb, cov: (ff.stdin.write(rgb.tobytes()), grids.append(grid64(cov))))
    ff.stdin.close(); ff.wait()
    return os.path.relpath(path, STUDY), parse_cost(cost), grids


def main():
    for d in (IMG, ANIM): os.makedirs(d, exist_ok=True)
    results = {"stills": [], "palettes": [], "scroll": [], "fades": [], "scan": [], "checks": {}, "physical": {}}
    t0 = time.time()
    physical.build()
    # Physical paint first: the owner's priority (12 Nov).
    phys = results["physical"]
    phys["stills"], phys["palettes"], phys["builds"], phys["costs"] = [], [], [], {}
    pdens = {}
    for name in PHRASES:
        out, rel, crop, cost = physical_still(name, "wheel", "brand", PHYS, PHYS)
        phys["stills"].append(dict(phrase=name, src=rel, detail=crop, landed=parse_cost(cost)))
        if name == "crossed": pdens["brand"] = out["cov"]
        print("physical", name, round(time.time() - t0))
    for pal in ("earth", "night"):
        out, rel, _, _ = physical_still("crossed", "wheel", pal, PHYS, PHYS)
        phys["palettes"].append(dict(phrase="crossed", palette=pal, src=rel))
        pdens[pal] = out["cov"]
    results["checks"]["physical_coverage_palette_max_difference"] = float(max(np.abs(pdens[p] - pdens["brand"]).max() for p in ("earth", "night")))
    assert results["checks"]["physical_coverage_palette_max_difference"] == 0.0, "the palette changed physical paint's coverage"
    _, rel, _, _ = physical_still("crossed", "scroll", "brand", 2400, 900)
    phys["scroll"] = dict(phrase="crossed", src=rel)
    for name in PHYS_BUILDS:
        rel, cost, grids = build_up(name)
        phys["builds"].append(dict(phrase=name, src=rel, cost=cost))
        print("physical build", name, round(time.time() - t0))
        if name == "crossed":
            ok, _, tabs = scan_tables(grids)
            fpath = os.path.join(AUDIO, "scan-physical-build.mp3"); mp3(play(tabs, ok, FPS, analysis(name)["length"]), fpath)
            ok2, _, tabs2 = scan_tables([grid64(pdens["brand"])])
            hpath = os.path.join(AUDIO, "scan-physical-held.mp3"); mp3(play(tabs2, ok2, 1, 4.0), hpath)
            hc = [harmonic_centroid(t) for t, k in zip(tabs, ok) if k]
            results["scan"].append(dict(style="physical", held=os.path.relpath(hpath, STUDY), fade=os.path.relpath(fpath, STUDY),
                                        held_centroid=round(harmonic_centroid(tabs2[0]), 2),
                                        fade_centroid_median=round(float(np.median(hc)), 2),
                                        fade_centroid_range=[round(float(np.percentile(hc, 10)), 2), round(float(np.percentile(hc, 90)), 2)],
                                        dark_frames=int((~ok).sum()), frames=len(ok)))
    # What a frame costs at the sizes a live version might run: Crossed hands,
    # the busiest phrase, rendered every frame at 20 a second.
    for size in (512, 1000, 1600):
        a = analysis("crossed")
        times = [(f + 1) / FPS for f in range(int(a["length"] * FPS))]
        c = parse_cost(physical.run(a, "wheel", size, size, palettes.PALETTES["brand"], times, lambda rgb, cov: None))
        phys["costs"][str(size)] = dict(brush_ms_per_frame=round(1000 * c["brush_s"] / c["frames"], 2),
                                        render_ms_per_frame=round(1000 * c["render_s"] / c["frames"], 2),
                                        steps=c["steps"], frames=c["frames"])
        print("cost", size, phys["costs"][str(size)])
    finals = {}
    for name in PHRASES:
        for style in STYLES:
            st, rel = still(name, style, "layered", "brand")
            finals[(name, style)] = st
            results["stills"].append(dict(phrase=name, style=style, src=rel))
            print("still", name, style, round(time.time() - t0))
    # The palette must not change what Scan reads: paint each style's Crossed
    # hands once per palette, from scratch, and compare the density to the
    # bit. The null beside it: lightness read off the coloured images, which
    # is what Scan would read if it read the picture rather than the ink,
    # differs between palettes - so the check can fail, and does for that.
    worst, null = 0.0, 0.0
    for style in STYLES:
        dens = {}
        for pal in ("brand", "earth", "night"):
            st, rel = still("crossed", style, "layered", pal) if pal != "brand" else (finals[("crossed", style)], None)
            dens[pal] = st.density
            if rel: results["palettes"].append(dict(phrase="crossed", style=style, palette=pal, src=rel))
            light = np.asarray(Image.open(os.path.join(STUDY, rel or f"img/crossed-{style}-layered-brand.jpg")).convert("L"), np.float32) / 255
            dens[pal + "_light"] = 1 - light if not palettes.PALETTES[pal]["dark"] else light
        for pal in ("earth", "night"):
            worst = max(worst, float(np.abs(dens[pal] - dens["brand"]).max()))
            null = max(null, float(np.abs(grid64(dens[pal + "_light"]) - grid64(dens["brand_light"])).max()))
        print("palettes", style, round(time.time() - t0))
    results["checks"]["density_palette_max_difference"] = worst
    results["checks"]["lightness_palette_max_difference_null"] = round(null, 3)
    assert worst == 0.0, "the palette changed the density"
    assert null > 0.05, "the null did not fail: the check cannot see a palette"
    for style in STYLES:
        _, rel = still("crossed", style, "scroll", "brand")
        results["scroll"].append(dict(phrase="crossed", style=style, src=rel))
        print("scroll", style, round(time.time() - t0))
    for style, names in FADES.items():
        for name in names:
            rel, _ = fade(name, style)
            results["fades"].append(dict(phrase=name, style=style, src=rel))
            print("fade", name, style, round(time.time() - t0))
    # Scan's read of each style's Crossed hands, as it is painted (the
    # fading canvas, a grid a frame) and once finished.
    for style in STYLES:
        name = "crossed"
        w, h = SIZE["layered"]
        grids = [grid64(st.density) for st in paint.fade_frames(ops_for(name, style, "layered"), w, h, ANIM_PX / w, FPS,
                                                                 analysis(name)["length"], PERSISTENCE)]
        if grids:
            ok, paths, tabs = scan_tables(grids)
            faded = play(tabs, ok, FPS, analysis(name)["length"])
            fpath = os.path.join(AUDIO, f"scan-{style}-fade.mp3"); mp3(faded, fpath)
            ok2, paths2, tabs2 = scan_tables([grid64(finals[("crossed", style)].density)])
            held = play(tabs2, ok2, 1, 4.0)
            hpath = os.path.join(AUDIO, f"scan-{style}-held.mp3"); mp3(held, hpath)
            hc = [harmonic_centroid(t) for t, k in zip(tabs, ok) if k]
            results["scan"].append(dict(style=style, held=os.path.relpath(hpath, STUDY), fade=os.path.relpath(fpath, STUDY),
                                        held_centroid=round(harmonic_centroid(tabs2[0]), 2),
                                        fade_centroid_median=round(float(np.median(hc)), 2) if hc else None,
                                        fade_centroid_range=[round(float(np.percentile(hc, 10)), 2), round(float(np.percentile(hc, 90)), 2)] if hc else None,
                                        dark_frames=int((~ok).sum()), frames=len(ok)))
    # The features each phrase measured, for the page and the write-up.
    results["phrases"] = {n: features.summary(analysis(n)) | {"preset": analysis(n)["meta"]["preset"],
                                                              "length": analysis(n)["length"]} for n in PHRASES}
    results["palette_measures"] = palettes.report()
    json.dump(results, open(os.path.join(STUDY, "results.json"), "w"), indent=1)
    print("done", round(time.time() - t0), "s")


if __name__ == "__main__":
    main()
