import rend, summ, meas, numpy as np, json, sys
B = "/tmp/claude-0/-home-user-Real-Time-Sound-Visualizer/fa175d99-1e8a-5677-be21-a0c5de1c3a3d/scratchpad/bin/"
D0 = dict(rend.HT, pictureAmount=0)
res = {}
for exe in ("render_cpp", "r-instep"):
    cohs = []
    for k in range(16):
        up_len = 1.0 + k * (1 / (4 * meas.hz(36))) / 16   # sixteen places across one turn of the drift (4 f, 3.8 ms)
        ev = [(0.2, 0x90, 36, 100), (0.8, 0x90, 64, 100), (0.8 + up_len, 0x80, 64, 0), (3.4, 0x80, 36, 0)]
        L, R, out = rend.render(D0, "sw", events=ev, exe=B + exe, every=0, end=3.5)
        tr = meas.track(L, R, meas.hz(36))
        im = summ.bass_image(tr, 0.8 + up_len + 0.2, 3.3)
        cohs.append((round(im["phase"]), round(im["coh"], 2)))
    res[exe] = cohs; print(exe, cohs, flush=True)
json.dump(res, open("sweep.json", "w"))
