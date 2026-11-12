"""The study's three palettes. Each is a ground and six inks in three roles a
hand: `main` (the hand's own ink, as its figure is drawn now), `related` (a
consonant tone against the bass) and `clash` (a dissonant one). The brand's
is the lane inks on the cream exactly as DESIGN.md has them, A taking its
figure's inks (ch1, its X lane, and ch2) and B its own (ch3 and ch4), with the
two remaining inks as the clashes. Earth and Night are proposals for a
product table, not tokens: nothing here is in DESIGN.md or the page. Their
inks were picked by eye and then moved as little as would clear DESIGN.md's
bars (`tune_palettes.py`, which starts from the picks).

    python3 palettes.py      # measure all three, as DESIGN.md measures the lane inks
"""
import json
from colour import measure

ROLES = ("a_main", "a_related", "a_clash", "b_main", "b_related", "b_clash")

PALETTES = {
    "brand": {
        "name": "The house",
        "ground": "#faf6f0",
        "dark": False,
        "inks": {"a_main": "#241f1d", "a_related": "#5c6488", "a_clash": "#a6552d",
                 "b_main": "#4c4921", "b_related": "#6f9169", "b_clash": "#72245e"},
        "names": {"a_main": "charcoal (ch1)", "a_related": "slate (ch2)", "a_clash": "terracotta (ch6)",
                  "b_main": "olive (ch3)", "b_related": "sage (ch4)", "b_clash": "plum (ch5)"},
    },
    "earth": {
        "name": "Earth",
        "ground": "#f0e7d6",
        "dark": False,
        "inks": {"a_main": "#33221a", "a_related": "#af3d0b", "a_clash": "#294e81",
                 "b_main": "#556d50", "b_related": "#a87f0f", "b_clash": "#6f2a4a"},
        "names": {"a_main": "burnt umber", "a_related": "burnt sienna", "a_clash": "smalt",
                  "b_main": "terre verte", "b_related": "yellow ochre", "b_clash": "madder"},
    },
    "night": {
        "name": "Night",
        "ground": "#151a24",
        "dark": True,
        "inks": {"a_main": "#ece3d0", "a_related": "#8ba4d6", "a_clash": "#e8734f",
                 "b_main": "#d8b349", "b_related": "#48c79f", "b_clash": "#bb65b0"},
        "names": {"a_main": "chalk", "a_related": "cerulean", "a_clash": "vermilion",
                  "b_main": "gold", "b_related": "jade", "b_clash": "orchid"},
    },
}


def report():
    out = {}
    for key, p in PALETTES.items():
        m = measure(p["inks"], p["ground"])
        out[key] = m
        print(key, "normal", m["worst"]["normal"], "simulated", m["simulated"],
              "\n   per deficiency", {k: v for k, v in m["worst"].items() if k != "normal"},
              "\n   contrast", m["contrast"], "\n   from ground", m["ground"], "\n   from ground simulated", m["ground_simulated"])
    return out


if __name__ == "__main__":
    json.dump(report(), open(__file__.replace("palettes.py", "palettes.json"), "w"), indent=1)
