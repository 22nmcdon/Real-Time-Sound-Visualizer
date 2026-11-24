"""Scan's read at a picture frame, made cheaper to the bit (24 Nov).

The owner's unison report found the frame's Scan work - the whole 64 by 64
grid blurred, then read round the path, then each table level summed in a
pass of its own - was the block every sixtieth that ran past its deadline in
the page's worklet, even at a unison of one. ScanReader now blurs only the
cells the read touches (scanBlurRead) and writes every level in one pass,
each a prefix of the richest's sum (scanTables). Held here against the old
ways, kept word for word in core/tests/tools/scanread_cpp.cpp: every reading
and every table value the same in every bit, over grids from blank to the
edge and softness from none to past the widest. The null makes the
reference's blur a millionth wider and adds its harmonics from the top, and
must be seen to differ. And the cost, on the thread's own clock: the new way
under half the old (it measured about 0.3).
"""


def run(kit):
    check, null = kit.check, kit.null

    def go(*args):
        out = {}
        for line in kit.run_args("scanread_cpp", *args).strip().split("\n"):
            w = line.split()
            out[w[0]] = [float(v) for v in w[1:]]
        return out

    r = go("400", "1")
    print("    over 400 frames: %s" % r)
    check("the read round the path is the same to the bit as the whole grid blurred", r["reads"][0] == 0, str(r["reads"]))
    check("the tables are the same to the bit as a pass a level", r["tables"][0] == 0, str(r["tables"]))
    w = go("400", "1", "wrong")
    null("a blur a millionth wider is seen in the read", w["reads"][0] > 0, str(w["reads"]))
    null("the harmonics added from the top are seen in the tables", w["tables"][0] > 0, str(w["tables"]))
    old, new = r["time"][0], r["time"][1]
    check("a frame's read and tables cost under half what they did", new < 0.5 * old, "%.1f against %.1f ms" % (new, old))
    null("and the same bound read the other way round goes red", not (old < 0.5 * new), "%.1f against %.1f ms" % (old, new))
