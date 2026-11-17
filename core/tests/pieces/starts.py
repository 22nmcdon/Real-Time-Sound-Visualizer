"""What the rack's switches start at (17 Nov).

Two of the rack's switches give a setting of their own when they have
nothing to put back: the Plane a Twist of 15 (PLANE_START) and the EQ the low
and high shelves up 3 dB (EQ_START), both read from the page here, so a start
changed on the page is a change seen here.

Until 17 Nov this also required each start to keep every Settled preset it
would switch on Settled, measured offline at five key landings. The owner
ruled that out the same day: a preset is held to its heading as shipped, and
a change it does not contain - a switch pressed on it - may move it under
another heading, which is not a fault ("reverb causing a preset to turn
breathing when turned on is totally acceptable because reverb was not
present in the preset"). The starts were still chosen by that measure
(web/docs/listening/plane-start/), so what they do to the bank is known; it
is no longer a requirement, and nothing here holds it.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "..", "..", "..", "web", "scope.html")


def starts():
    text = open(PAGE, encoding="utf-8").read()
    out = {}
    for name in ("PLANE_START", "EQ_START"):
        m = re.search(r"const %s = (\[\[.*?\]\]);" % name, text)
        out[name] = {k: float(v) for k, v in json.loads(m.group(1))} if m else None
    return out


def run(kit):
    check, null = kit.check, kit.null
    given = starts()
    check("the page's two starts read: the Plane's and the EQ's", given["PLANE_START"] == {"planeTwist": 15}
          and given["EQ_START"] == {"eqLow": 30, "eqMid": 0, "eqHigh": 30}, str(given))
    null("a start other than the page's is refused: the Plane at Twist 25 is not what the page gives",
         given["PLANE_START"] != {"planeTwist": 25}, str(given["PLANE_START"]))
