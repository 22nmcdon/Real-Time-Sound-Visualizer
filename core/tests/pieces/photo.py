"""The photocell's reach ceiling, on the core: phototest.py's :338 and :343.

These were phototest.py's on its `?brain=js` leg until stage 5, step 3, batch
3 (13 Nov): `photo.value` forced to one by hand, a routing's amount written
past the ceiling round every setter, and the page's `applyModMatrix` read
back. Here the core's matrix (matrix_cpp): the photocell a scripted source
held at one, marked as the picture's, with the core's own reach
(`reach=photo`, kPhotoReach), on stand-in destinations of screen.h's spans.
Its neighbour, "and stored back within it, so the control says what
applies", is the face's and stays in the suite. Each check has its null.
"""
from pieces.loop import matrix, sources


def run(kit):
    check, null = kit.check, kit.null
    # The photocell at a half, not one: at one its push and the loop's total
    # are both a half, and a ceiling of three quarters would read the same
    # through the total (batch 3's mutation pass). The page read the ratio
    # of the offset to the value, as here.
    view = ["visual view.rotate 1 -2 2 0", "visual filter.res 50 0 100 20"]
    f = matrix(kit, sources(["photo.1"], 0.5) + view + ["route photo.1 view.rotate 1", "frame"])[0][0]
    check("an amount past the ceiling is held to it where it is used", abs(f["view.rotate"] / 0.5 - 0.5) < 1e-9,
          "applied %.4f of the value, of rotation's span" % (f["view.rotate"] / 0.5))
    o = matrix(kit, sources(["test.one"], 0.5, "1", "") + view + ["route test.one view.rotate 1", "frame"])[0][0]
    null("a source that is not the picture's is not held to it", abs(o["view.rotate"] / 0.5 - 0.5) > 0.1, "%.4f" % (o["view.rotate"] / 0.5))
    # A setup code carrying a routing past the ceiling, to the resonance.
    r = matrix(kit, sources(["photo.1"], 0.5) + view + ["load photo.1>filter.res@0.9", "frame"])[0][0]
    check("a routing that arrives in a code past the ceiling moves its destination no further than the ceiling",
          0 < r["filter.res"] <= 0.5 * 0.5 * 50 + 1e-9, str(r["filter.res"]))
    r2 = matrix(kit, sources(["test.one"], 0.5, "1", "") + view + ["load test.one>filter.res@0.9", "frame"])[0][0]
    null("the same code from a source that is not the picture's goes past it", r2["filter.res"] > 0.5 * 0.5 * 50, str(r2["filter.res"]))
