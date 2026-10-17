# Design

How the oscilloscope looks, and which parts of that are the **brand** - the house it
shares with the jazz and guitar learning apps - and which are the **product**, decisions
that belong to an oscilloscope and to nothing else. It covers all three builds: the page
(`web/scope.html`), the desktop build (`oscilloscope-poc/branding.py` and
`renderer.py`), and the plugin, whose interface *is* the page.

The brand has a source of truth, and it is not in this repository. It is
[`docs/BRANDING.md` in the jazz learning app](https://github.com/22nmcdon/jazz_learning_app/blob/main/docs/BRANDING.md),
which in turn says it follows the Milo McDonald portfolio. When this document and that one
disagree about the brand, that one wins and this one is out of date. What this document
owns is the second half: the oscilloscope's own decisions, and the list of places where
the oscilloscope currently departs from the brand.

## How the line was drawn

Three projects wear the brand: this one, the
[jazz learning app](https://github.com/22nmcdon/jazz_learning_app) and the
[guitar learning app](https://github.com/22nmcdon/guitar_learning_app). Every token,
rule and mannerism in this repository was compared against both, and sorted by one test:

- **Brand** - the same in all three, or written into `BRANDING.md` as a rule for any
  surface. Changing it here alone would make this the odd one out of the family.
- **Family mechanism** - all three do the same *kind* of thing, each its own way. The
  mechanism is brand; the particular values are product. The clearest case is the mode:
  every app may have a second light, and the brand says how one must work, but which
  colours it uses is each product's own.
- **Product** - only here. An oscilloscope has six lanes of ink, a graticule and a
  trigger; a lead sheet and a fretboard have none of them.

A useful shorthand: **the paper is the brand, and what is written on it is the product.**
Cream paper, charcoal ink, the pigments that each mean one thing, the type, the three
radii and the voice are the paper. The jazz app writes chords on it in a hand face, the
guitar app draws a rosewood neck on it, and this app writes traces on it with a graticule
for ruling.

---

# Part one: the brand

Everything in this part is shared. Each item says where it lives here, so it can be
checked, but it is not this repository's to change.

## 1. The idea

Each app is a sheet of paper that answers back. Printed where it tells you something
fixed, quiet everywhere else, so that the few colours that carry meaning are the loudest
things on the page. Each product chooses what the sheet is - a Real Book page, a neck
chart, a scope's screen - and that choice is product (see Part two, section 8).

## 2. Colour

### The core palette

Identical, hex for hex, in all three apps and in this repository's two builds.

| Token | Value | Layer | What it is |
|---|---|---|---|
| `--cream` | `#faf6f0` | Brand | The page. Warm, not white. |
| `--cream-2` | `#f2ebe1` | Brand | Anything under the page: the dock. |
| `--paper` | `#fffcf7` | Brand | The sheet laid on it, and every input. |
| `--charcoal` | `#241f1d` | Brand | Ink. Never pure black. |
| `--text` | `#3a332f` | Brand | Body copy. |
| `--text-soft` | `#6b615a` | Brand | Secondary copy, labels, hints. |
| `--line` | `#e4d9cc` | Brand | Every border and rule. |
| `--blush` | `#d9a6a0` | Brand | The accent at rest: hover borders, underlines. |
| `--blush-deep` | `#c07f79` | Brand | The accent doing work: focus, the active tab, the slider thumb. |
| `--gold` | `#b08d57` | Brand | Ready. Also a suggestion, a marker. |

### The pigments that mean one thing

These say the same thing in every mode of every app, which is why no mode moves them.

| Token | Value | Layer | Means, in the brand |
|---|---|---|---|
| `--sage` | `#6f7f63` | Brand | This matches. Good. |
| `--rust` | `#a4553f` | Brand | A problem. Outside. Armed. |
| `--unresolved` | `#b6afa4` | Brand | Open, undecided - deliberately not a verdict. |
| `--approach` | `#8fae6d` | Brand (jazz meaning) | An approach note. Nothing here means it, so the page does not define it; the desktop build keeps it in its block so the set stays whole. |
| `--enclosure` | `#3f8f88` | Brand (jazz meaning) | An enclosure. The guitar app reuses the hex as `--extension`. Not used here. |

What each one is *called on to mean* on a given surface is product: sage means "chord
tone" on the jazz app, "the third" on the guitar app and "trigger locked" here. Part two,
section 9 gives this app's readings. What is brand is the **direction** of each - sage is
never bad news, rust is never good news, and unresolved is never a verdict.

### Rules

- **Tokens, not literals.** A colour spelled as a hex or an `rgba()` at the call site will
  not follow the light. If it needs to, it is a token. The desktop build states the same
  rule at the top of `branding.py`: nothing below that file spells a hex digit.
- **Shadows and backdrops are charcoal at low alpha** - `rgba(36, 31, 29, a)` - never black.
- **The wash.** `--wash` and `--wash-strong` are the accent laid over something: hover,
  then selection. The mechanism is brand. The strong value has drifted across the family -
  `0.26` in the jazz app, the desktop build and the page, `0.3` in the guitar app.

## 3. Lights and modes

**A mode redefines tokens; it never restyles a component.** A second light is a change of
paper, not a dark theme, so it is never mapped onto `prefers-color-scheme`. That rule is
brand. Which second light, if any, is product:

| App | Its second light |
|---|---|
| Jazz | `body.soloing`: cooler paper, the rose accent becomes slate `#5c6488`. Every surface token moves. |
| Guitar | `body[data-mode="fretboard"]`: only `--accent` and the wash move, to teal `#35786f`. |
| This one | None, deliberately (the comment under `:root` in `scope.html`). |

## 4. Type

| Token | Stack | Layer |
|---|---|---|
| `--serif` | Playfair Display, Georgia, Times New Roman, serif | Brand |
| `--script` | Cormorant Garamond, Georgia, serif - italic only | Brand |
| `--sans` | Jost, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif | Brand |
| `--mono` | ui-monospace, Menlo, Consolas, monospace | Brand |
| `--hand` | Kalam, Bradley Hand, Segoe Print, cursive - chord symbols only | Product (jazz) |

Brand, all three apps:

- Body is Jost **300 at 16px / 1.65**, antialiased.
- Webfont weights: Playfair 500/600/700, Cormorant 500 roman and italic, Jost 300-600.
- **The eyebrow**: 11px, uppercase, `letter-spacing: 0.28em`, `--blush-deep`, weight 500.
- **The small-caps control**: 10.5px, uppercase, `0.14em`-`0.18em`, weight 500 (`.caps`
  here). Nothing shouts in large type; it whispers in wide-tracked small type.
- Headings in the serif at 600; the script for a credit or a lede, never for a control.
- **Webfonts are never render-blocking.** The `<link>` carries `data-href` and script
  promotes it when the page is served over the web. A webview that cannot reach the font
  server and is waiting on a stylesheet paints no text at all. The page promotes it on the
  site and never inside the plugin, as the guitar app does inside its own JUCE shell.

The desktop build has to fake two of these, because Qt has neither `text-transform` nor
`letter-spacing`: `small_caps()` in `branding.py` is the brand's small caps done by hand.

## 5. Shape, edge and depth

Three radii, each meaning one thing - this is brand for the **chrome** of every app:

- **`1px` - paper.** Inputs, selects, filled buttons.
- **`30px` - a state you are in** (the status chip, the mode switch, a menu button), and
  `20px` for a small chip.
- **`50%` - a dot.**

Brand, too:

- Borders are `1px solid var(--line)`.
- Depth is used once: the sheet takes
  `0 1px 0 var(--cream-2), 0 14px 34px rgba(36, 31, 29, 0.06)`. Here the sheet is the
  screen pane.
- State to be seen across the room is an **inset 3px rule** in its colour rather than a
  fill or a shadow.
- Buttons come in three weights: filled (charcoal, the one primary action), outlined pill
  (a mode or a menu), underlined (`.link-btn`, a 1px blush rule that thickens to 2px when
  pressed).

What the brand does not settle is the radius of the *instrument* drawn on the paper. The
guitar app rounds its fretboard and its finger dots at 6-14px, because a neck is not a
sheet of paper. By the same reasoning the radii of things drawn inside this app's screen
are product. Its chrome is not. The marks that keep radii of their own are the piano key's
rounded foot, a source's meter, and the modulation lane's span, now-mark and cap, and
`designtest.py` names them, so a rounded corner anywhere else fails the suite.

## 6. Motion

Almost nothing moves, which is what lets the few things that do move be noticed.

- The armed dot: `1.6s ease-in-out infinite`, `opacity: 0.25` at 50%.
- A waiting thing: `1.3s`, `0.45` at 50%.
- A mode flip: `280ms ease` on surfaces only.
- Every animation sits inside `prefers-reduced-motion: no-preference`.

## 7. Layout

- `padding-inline: 24px` (`--gutter` here).
- `--max: 1080px` in the jazz and guitar apps. This app is wider (Part three).
- **One breakpoint, at 760px**, below which a page stops being a screenful and becomes a
  page. Add another only where something actually collides, and check at 430px wide.
- Measures capped in `ch`: 62ch for ledes, 60ch for help copy.
- Anything that reserves height reserves it always; tap targets sized for touch at every
  width.
- `:focus-visible` is `2px solid var(--blush-deep)` at `2px` offset, everywhere.

## 8. Voice

1. **Name the thing; don't judge the person.** "Outside", never "wrong". Here: "Free run",
   never "no signal" or "error".
2. **A plain sentence, then the detail.**
3. **Labels are two or three words**, sentence case inside small caps. Middots separate;
   ampersands do not appear.

The house prose rules for code and docs - comments that explain why, British spelling,
ASCII hyphens in code comments - are in each repository's `CLAUDE.md`, and are the same
rules in all three.

---

# Part two: the product

Everything in this part is the oscilloscope's own. Another app in the family would not
inherit it, and changing it here needs no change anywhere else.

## 9. The idea: the screen is the sheet

The header comment of `scope.html` says it: the screen is the sheet, the graticule is the
ruling on it, and the traces are what is written. Two consequences follow, both product:

- **The screen fills the window** on a desktop, and nothing scrolls - not the page and not
  a Bench tab (CLAUDE.md, *Layout decisions already made*). The jazz and guitar apps are
  scrolling documents; an instrument is not.
- **There is one light.** The jazz app's second light exists because solo practice is a
  different activity from chord practice. Nothing an oscilloscope does is a different
  activity in that sense, so a second light would be decoration.

### What the brand's pigments mean on this surface

| Pigment | Here it means |
|---|---|
| `--sage` | The trigger is locked; in tune; channels in phase. The run button's live dot. |
| `--unresolved` | Free run. The trace goes this grey when nothing crosses the level, because a signal with no edge in it is not a fault. |
| `--rust` | Clipping, a level over, an input that would not open; and, as the house's armed, a scope stopped, recording or muted. A tuner's sharp or flat, which is "outside", never "wrong". |
| `--gold` | Ready (the status chip), and the cursors. |
| `--blush-deep` | The trigger line and its marker, the slider thumb, the selected tab: the accent doing work. |

## 10. Colour that is the oscilloscope's

### The lane inks

The house had one ink and a scope needs one per lane. Six, and the number is measured
rather than chosen: every lane is on screen at once and they cross each other, so the bar
is the all-pairs separation, and six is where the paper stops telling one trace from the
next. Six is also what the largest stem separator produces, which is why `MAX_LANES` is 6.

| Token | Value | Layer | Where it comes from |
|---|---|---|---|
| `--ch1` | `#241f1d` | Product | Charcoal - the brand's ink, and the left channel. |
| `--ch2` | `#5c6488` | Product | Slate, borrowed from the jazz app's solo light, so already in the family. The right channel. |
| `--ch3` | `#4c4921` | Product | Olive. |
| `--ch4` | `#6f9169` | Product | A lighter, greener sage than the brand's. |
| `--ch5` | `#72245e` | Product | Plum. |
| `--ch6` | `#a6552d` | Product | Terracotta - near rust, but a lane, never a verdict. The photocell's reticle. |

Worst all-pairs separation is 16.1 with normal vision and 8.8 under simulated colour
blindness, against bars of 15 and 8. Two of the usual checks are failed on purpose, and
the comment above the tokens says why: they are written for filled marks, and these are
thin strokes of ink on cream that clear 3:1. A seventh lane needs the measurement run
again, not a seventh colour picked by eye.

The same six inks are the modulation sources' colours: each source carries one
(`ink:` in its registration), and its chip, its meter and the lane it draws under a
control are painted in it. So the inks are a register the whole Bench draws from, not
only the traces' colours, and a source's ink says nothing about which lane it comes from.

### The spectrogram ramp

Built from brand tokens only - paper, cream-2, blush, blush-deep, rust, charcoal - with
the stops placed so OKLCH lightness falls at a steady rate per decibel (`RAMP_STOPS`). The
tokens are brand; the ramp, and the decision that a 10 dB step should look like 10 dB
anywhere on the scale, are product.

## 11. The screen

- **Graticule**: 10 divisions by 8 (`DIVS_X`, `DIVS_Y`), ruled in `--line` at 1px. The
  ruling on the sheet, so it is the quietest thing on it.
- **Traces**: 1.5px, in the lane's ink. A free-running trace goes `--unresolved`.
- **The trigger**: a dashed `--blush-deep` line in the trigger source's own band only,
  with its marker. Dashed because it is a line you set, not one the signal drew.
- **Cursors**: dotted `--gold`.
- **Goniometer and tuner**: sage for in phase and in tune.
- **Persistence**: a wash of the paper over the last frame, not a fade to black, because
  the screen is paper.

## 12. Controls

- **Sliders**: a 2px `--line` track and a 13px `--blush-deep` thumb that turns charcoal
  under the pointer. Full width up to 250px.
- **Readouts**: `font-variant-numeric: tabular-nums` everywhere a number changes, so a
  reading does not shuffle its neighbours while it moves.
- **The switch**: a 30px segmented pill; the chosen segment filled charcoal.
- **The run button**: a pill with a status dot - sage while running, breathing while
  armed, outlined rust when stopped.
- **Modulation**: chips are 30px pills, filled charcoal while armed because armed is a
  mode the whole Bench is in; a control's appearance does not depend on how many sources
  are on it (`patchtest.py` measures it).
- **Preset cards**: paper cards with the chosen one marked by the brand's inset-3px rule,
  turned to the left edge.
- **The on-screen keyboard**: a dock under the screen, on `--cream-2` like the brand's
  dock.

## 13. Layout

The brand's layout is a page; this is an instrument, so most of it is product. The
decisions, and the failures each one replaced, are in CLAUDE.md under *Layout decisions
already made*, and are not repeated here. In outline: a top bar, the screen, and a dock;
the Bench as six task tabs with a 160px rail and a 318px side column built from real
column elements; a Sources tab showing one family at a time; every section with one home.

Breakpoints beyond the brand's 760px, each added where something collided:

| Breakpoint | What collided |
|---|---|
| `max-width: 860px` | The screen and its side panes stop sitting side by side. |
| `max-width: 720px` | The keyboard's hint line and the height of its keys. |
| `max-width: 700px` | The preset browser's rail goes above its cards. |
| `pointer: coarse` | Modulation handles grow for a finger. |

## 14. Voice on this surface

The verdicts in the dock are a serif line in the pigment of their meaning: *Trigger
locked.* *Free run.* *Clipping.* *Waiting for an edge.* Each names what the scope sees.
None of them names what the person did. The cheat sheet inside `scope.html` is
user-facing documentation in the same voice, and it goes stale first.

## 15. The other two builds

- **The desktop build.** `oscilloscope-poc/branding.py` is the brand's drop-in block
  translated into the one form Qt can read - brand, kept hex for hex with the jazz app.
  Below it, marked off, are the page's six lane inks - product, and equal to the page's.
  `renderer.py` is product: ink for the left channel, slate for the right, the accent for
  the trigger line, as on the page.
- **The plugin.** Its interface is the page, served from JUCE's resource provider, so
  everything above applies unchanged. One brand rule matters more there than anywhere: a
  plugin window in a studio that is offline is exactly the webview the font rule is
  written for.

---

# Part three: where the oscilloscope departs from the brand

Writing this document found eleven places where the page or the desktop build departed
from the brand. Eight were fixed. Three stay, as decisions rather than oversights, and
are written down here and where they are set, so that nobody fixes them back by accident.

### Staying, on purpose

| Where | The brand says | Here, and why |
|---|---|---|
| `--max` | `1080px` | `1180px`. A preference, not a need: the screen is what is read, and on a wide window it is a tenth bigger. `fittest.py` passes at 1080 too, so this is the only cost-free one to reverse - one line. |
| `.run-btn` | A filled button is an action, square; a state is an outlined pill | A filled pill while running, outlined in rust when stopped. Running is a state you are in, so it is a pill, and the one pill that is filled, because a running scope is what has to be seen from across the room. |
| Rust | A problem; outside; armed | Clipping, a level over and an input that would not open are problems. A stopped, recording or muted scope is the brand's armed - a state to be seen from across the room. A tuner's sharp or flat is the jazz app's "outside, never wrong". A drawbar's brown is a drawing of a Hammond's drawbars, as the guitar app's rosewood is of a neck. Free run is none of these, and stays `--unresolved`. |

### Fixed

| What it was | What it is now |
|---|---|
| The drop hint painted `var(--wash-strong)`, which was never defined, so it drew no fill at all | `--wash` and `--wash-strong` are defined in `:root` at the house's values. |
| The webfonts were a render-blocking stylesheet in the head | `data-href`, promoted by script on the site and never inside the plugin, which sets the page in each stack's fallback faces until it carries the fonts itself. |
| The armed dot breathed to `0.2` | `0.25`, as the house has it. |
| `.run-btn`'s comment called it "the primary action" | It says it is a state, and why it is filled (above). |
| `.bench-results` had a black shadow | Charcoal at the same alpha. |
| The chrome had 2, 3, 4 and 6px corners (preset cards, the search box and its results, a found control's ring, a key hint) and a 5px "dot" | All 1px, and the dot `50%`. The instrument's own marks keep theirs: the piano key's foot, a source's meter and the modulation lane's marks (section 5). |
| The cheat sheet said "the only thing here painted in rust is clipping" | It lists what rust marks, and that free run is never one. |
| The desktop build drew its right channel in `BLUSH_DEEP`, its own trigger line's colour, under a docstring calling it the accent at rest | The page's lane inks are in `branding.py` as a product block, and the right channel and its legend are slate, `CH2`. |
| `branding.py` cited a `BRANDING.md` not in this repository | It names the jazz app's, and this document. |
| `.photo-reticle`'s fill was `--ch6` spelled out as an `rgba()` | `color-mix()` of `var(--ch6)`, so the reading still sets its strength. |

Two more belong to the brand rather than to this app, and are recorded here only because
they were found from here:

- `--wash-strong` is `0.26` in the jazz app and `0.3` in the guitar app.
- `BRANDING.md` describes neither the guitar app's accent-only mode nor its looser radii
  on the instrument; both are reasonable, and both are family mechanisms the brand
  document could name.

## Deciding where something new goes

1. Would the jazz or guitar app want it, unchanged, if they had the same need? Then it is
   brand: take it from `BRANDING.md`, or propose it there, rather than inventing it here.
2. Is it a new *value* for a mechanism the brand already has - a second light, a meaning
   for sage on a new surface? Then the mechanism is brand and the value is product: follow
   the rule and write the value down in Part two.
3. Otherwise it is product. Write it in Part two with its reason, and if it departs from
   a brand rule, add it to Part three's *Staying, on purpose* rather than leaving it to be
   found.

`web/tests/designtest.py` holds this document to the builds. A colour token in the page has
to be in one of the tables above, at its value, on one side of the line, and the desktop
build's copy of any colour must match. Every `var()` in the stylesheet must be defined;
every `rgba()` outside `:root` must be the charcoal shadow; and every radius must be one of
the house's three or sit on one of the instrument's marks, which the test names.
