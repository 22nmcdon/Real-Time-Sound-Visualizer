# The Picture strip, readable

The build's spec for the third item of the owner's UI review (19 Nov). The mockup is
`web/docs/mockups/picture-strip/` (live; screenshots of testing's strip and the mockup's at
1400 × 900 and 960 × 600, and the longest line at 1100 × 860; `checks/strip_checks.py`, 32
checks with their nulls). It changes how the strip is laid out and what it says. Its controls,
their ids and what they do stay the same, and so does its height.

## What the owner saw

- *Heard / Drawn too*, with *Width on* under it, which read like a third option.
- The info line cut mid-sentence (*How much the light is blurred before Scan reads it….*).
- Both *Right-click for more* and *More*.
- Glow, Motion and Memory as three tiny pale slivers at the far right.

## What changes

- **The same height**: 90 px, and 80 compact. Nothing else in the window moves, so the strip
  costs the rest of the window nothing.
- **The strip runs the whole window's width**, not the page's 1180 px `.wrap`, with the brand's
  24 px gutters, as the modulation row above it already does. The info line gains the
  difference: it is 512 px wide at 1400 × 900, and 301 at 960 × 600.
- **Under 1100 px wide the fixed parts give way**: the knobs take the compact cell (50 px), the
  gaps tighten to 10, the name block narrows and the bars shorten to 40 px. Without that, the
  info line was 212 px at 1100 × 860.
- **The info line** has the name in the serif, the value, and the host's gold dot. The dot now
  comes first and keeps its place whether shown or not. **More** is at the right of that line,
  in a place of its own. Under them is the control's **whole line**: up to four lines at
  12.5 px, or three lines at 11.5 px compact, in Jost 400. The line is top-aligned, so a short
  sentence does not move the name. Every one of `CONTROL_WORDS` (391 lines, the longest 150
  characters) fits whole at all six windows. The check sets each in turn. Set the same way in
  testing's box at 1400 × 900, most of them are cut.
- **The Width switch**: **Width is** over **Only heard · Drawn too**. That is the label first,
  then the switch, read as a sentence. The ids are `widthHeard` and `widthDrawn`.
  `what-each-control-says.md` should name them *Only heard* and *Drawn too*; their lines need
  no change.
- **One way to more**: **More** (`infoMore`) opens the card, as now. *Right-click for more*
  (`infoMenu`) leaves the strip. Its job, telling someone who has never right-clicked a plugin
  that the controls have a menu, moves into More's title and the card's first line. G5b put that
  hint on the line on purpose: if the owner wants it kept, it can go back as More's caption
  and cost the line about 90 px.
- **The three reads**: each is a row. The name is 11 px (10.5 compact) in `--text`. The bar is
  64 px (52 compact, 40 under 1100 wide) and 6 px tall, filled in charcoal on `--line`
  (11.7:1). The reading is in per cent, tabular, in a column of one width. The `rust` held
  state (`data-held`) keeps its meaning on the bar's fill. `pictureReads` stays the element.
- **Not changed**: the seven knobs, their order and host dots, Advanced, the link pill with two
  hands, and the output meter beside the line.

## For the build

- `.picture-bar .picture-wrap`: let it span the window, as `.modrow` does. The knobs' place,
  measured from the window's left, moves by the gutter; nothing tests that place.
- The info line's markup splits into a top row (host dot, name, value, hand pill, More) and the
  words. Remove the clamp on the words (it is 2 today) and set it to 4 lines full and 3 compact.
  Keep `data-empty` and the hint for an empty line.
- `infoMenu`: remove it from the strip, or keep it unseen if a test reads it.
- The reads' drawing (`paintReads` or its kin) writes a width and a reading per row, rather
  than a height per sliver.
- Tests: `wordstest.py` (the two names), the info line's suite (it held the line to one row of
  words beside the name), `fittest.py`, `windowtest.py`, `headertest.py` (host dots),
  `layouttest.py`. The plugin's shell test sees the strip in WebKit: re-check the four lines
  there, since WebKit's clamp counts the same lines but its Jost metrics can differ by a pixel.

## Measured

At the six windows: the strip is testing's height; nothing in it overlaps, falls outside it or
is cut; all 391 lines fit whole; and nothing in it moves by half a pixel across pointing at
every control, the reads at 0 and 100 per cent, both Width settings, and the longest and
shortest lines. The nulls are taken from testing: its info box cuts the lines, its strip says
"more" twice and "right-click" once, its *Width on* sits under its switch, and its reads are
9 px bars named in 10.5 px of the soft ink. A reading column sized to its figures moves the
info line. `checks/results.json` has the rest.
