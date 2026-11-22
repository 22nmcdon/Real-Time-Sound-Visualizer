# The plugin on a Mac: the checklist

For the owner and a Claude session, the first time the plugin is built and
played on the owner's Mac (a Mac mini, Apple M4 Pro, Xcode installed) in
Logic Pro. The plugin had only been built on Linux and on GitHub's macOS
runner before; what was done to prepare it is in `PLAN.md`, stage 6. Each step
says what it is for, so a step that fails says where to look, and *If
something fails*, at the end, says what to bring back to the session.

Written on 17 Nov and brought up to date on 22 Nov, at `testing` 722da4c:
since the first version the instrument has gained the drawn envelopes on
Play's figures, the keyboard band, Ink's figures, the drawn LFOs, the Paint
view and the player's controllers on its brush, and Scope & measure, the
Picture strip and Perform as the UI review laid them out.

## 0. Connect the Mac to the session

On the Mac, in the Claude desktop app: **Settings → Claude Code → Remote
Control**, turn it on and share a folder - the checkout of this repository
(clone it first if there is none: step 1). A cloud session can then run the
commands below on the Mac and read what they print. A folder under a hidden
directory in your home (one whose name starts with a dot), your home itself
or `~/Library` cannot be shared, so keep the checkout somewhere like
`~/Code/Real-Time-Sound-Visualizer`.

## 1. What the Mac needs

```sh
xcode-select -p                      # Xcode's tools are found (else: xcode-select --install)
sudo xcodebuild -license accept      # once, if Xcode has never been opened
brew install cmake ninja             # CMake 3.22 or later; Ninja is optional but quicker
cmake --version
git clone https://github.com/22nmcdon/real-time-sound-visualizer.git ~/Code/Real-Time-Sound-Visualizer
cd ~/Code/Real-Time-Sound-Visualizer
git fetch origin testing && git checkout testing     # testing is what to build; main moves only on the owner's word
git log --oneline -1                                 # 722da4c or later
```

JUCE is fetched by CMake at the tag the plugin pins (8.0.15) on the first
configure. To keep one checkout across build folders instead:

```sh
git clone --depth 1 --branch 8.0.15 https://github.com/juce-framework/JUCE.git ~/Code/JUCE-8.0.15
# and add -DSCOPE_JUCE_DIR=$HOME/Code/JUCE-8.0.15 to the configure lines below
```

## 2. Configure and build

Quick, for trying things (Apple Silicon only, half the compile):

```sh
cmake -S plugin -B plugin/build-mac -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_OSX_ARCHITECTURES=arm64
cmake --build plugin/build-mac --target ScopeInstrument_AU ScopeInstrument_VST3 ScopeInstrument_Standalone ScopeShellTest
```

As shipped (universal, arm64 and x86_64, which is the CMake file's default):

```sh
cmake -S plugin -B plugin/build-universal -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build plugin/build-universal --target ScopeInstrument_AU ScopeInstrument_VST3
```

Without Ninja, leave out `-G Ninja` and add `-j 12` to the build line. The
bundles land in `plugin/build-mac/ScopeInstrument_artefacts/Release/`:
`AU/Scope.component`, `VST3/Scope.vst3`, `Standalone/Scope.app`. Check them:

```sh
B=plugin/build-mac/ScopeInstrument_artefacts/Release
lipo -archs $B/AU/Scope.component/Contents/MacOS/Scope        # arm64 (and x86_64 for the universal build)
vtool -show-build $B/AU/Scope.component/Contents/MacOS/Scope   # minos 13.3
```

## 3. The shell test

```sh
plugin/build-mac/ScopeShellTest_artefacts/Release/ScopeShellTest | tee shell-mac.log
grep -c '  PASS  ' shell-mac.log; grep '  FAIL  ' shell-mac.log
```

No xvfb on a Mac: its face checks open a real window on the desktop for a
few seconds (leave the Mac unlocked). It ends with "the shell plays, serves
the page, and hands it the picture" or FAILED. On Linux under `xvfb-run -a`
it is 233 checks passed and none failed at 722da4c (22 Nov); a check that
passes there and fails here is the day's real finding. (GitHub's macOS
runner also read 233 and none failed on 22 Nov, so a failure here would be
this Mac's, not macOS's.) The paint check prints a
line of its own, `(the face in WebKitGTK, painting: {...})` - the label is the
Linux one, but on the Mac it is WKWebView's answer: `"mode":"gpu"` is the
painting on the graphics card, `"mode":"plain"` with a `why` is the fallback,
and `fps` the face's frame rate while it painted. Keep that line whatever it
says.

## 4. Install

```sh
B=plugin/build-mac/ScopeInstrument_artefacts/Release
mkdir -p ~/Library/Audio/Plug-Ins/Components ~/Library/Audio/Plug-Ins/VST3
rm -rf ~/Library/Audio/Plug-Ins/Components/Scope.component ~/Library/Audio/Plug-Ins/VST3/Scope.vst3
cp -R $B/AU/Scope.component ~/Library/Audio/Plug-Ins/Components/
cp -R $B/VST3/Scope.vst3   ~/Library/Audio/Plug-Ins/VST3/
killall -9 AudioComponentRegistrar 2>/dev/null; true    # the system's AU list, read again
```

Remove the old copy before copying, as above: `cp -R` onto an existing bundle
puts the new one inside the old.

**Signing.** A copy built on this Mac needs none: the linker signs each
binary ad hoc, which is all Apple Silicon asks of code built where it runs,
and a file made locally carries no quarantine. A bundle **downloaded** (the
GitHub workflow's artifact, below) is quarantined, and macOS will refuse to
load it, often with no more than Logic saying it failed validation. Take the
quarantine off after copying it into place:

```sh
xattr -dr com.apple.quarantine ~/Library/Audio/Plug-Ins/Components/Scope.component ~/Library/Audio/Plug-Ins/VST3/Scope.vst3
```

(The right-click → Open route is for apps: it works for the standalone
`Scope.app`, not for a plugin bundle, which is never opened from the Finder.
If a load was refused, System Settings → Privacy & Security may offer *Open
Anyway* once.) Signing with a Developer ID and notarising, so nobody has to
do this, is stage 6's remaining work and needs the owner's Apple developer
account.

## 5. auval

```sh
auval -a | grep Rtsv                 # listed: aumu Scop Rtsv - Real-Time Sound Visualizer: Scope
auval -v aumu Scop Rtsv              # ends "AU VALIDATION SUCCEEDED."
```

`aumu` is the type (an instrument), `Scop` the plugin's code, `Rtsv` the
manufacturer's. If it is not listed, run the `killall` again and wait a few
seconds. If it fails, the lines before the failure name the test; keep the
whole output.

## 6. Logic

Open **Logic Pro → Settings → Plug-in Manager**, find *Real-Time Sound
Visualizer*, and if Scope is there with a failure, select it and **Reset &
Rescan Selection** (Logic runs its own auval). If Logic insists on an old
result after a rebuild, reset the cache with Logic closed:

```sh
killall -9 AudioComponentRegistrar
rm -f ~/Library/Caches/AudioUnitCache/com.apple.audiounits.cache
```

and open Logic again. The cure that lasts is the rule in `PLAN.md`
("Releasing"): every build handed over raises the version, which is what
tells Logic to look again.

Then, on a new **Software Instrument** track, instrument slot → *AU
Instruments → Real-Time Sound Visualizer → Scope*. What to try, roughly in
this order, writing down what happens at each.

**The host's knobs.** Eighteen, in four groups, in this order (the plugin's
`kKnobs`; a gold dot before the name marks each on the face):

| Group | Knobs | On the face |
|---|---|---|
| Instrument | Picture, Scan, Strike, Softness, Persistence, Output, Width | the Picture strip along the bottom |
| | Level, Cutoff, Warp, Twist | Play's Wave header; Play's Filter; Ink's Oscillator; the rack's Plane |
| | Delay mix, Phaser mix, Reverb mix | Space & Memory's rack |
| Setups | Morph | Perform's crossfader |
| Amp envelope | Attack, Release | Play's Amp figure |
| LFO 1 | LFO 1 rate | LFO 1's card, its editor's Rate |

Persistence is the trace's in Trace and the painting's own in Paint (the knob
reads back when the view changes). Output and Width are what is heard alone
and no setup's: a preset or the morph never moves them, the project does.

1. **The face opens** and draws: the page, not the "no web view" sentence.
   The type is the fallback faces (Georgia and the system's sans), not the
   site's web fonts, by design; a tab that scrolls with them is a finding.
2. **Play** from a MIDI keyboard and from Logic's Musical Typing (Window →
   Show Musical Typing): sound, and the figure on the screen moving with it.
   With the face's window focused, do the computer's keys reach the page or
   Logic? (The page's on-screen keys are the site's only, by design: their
   row is hidden and M does nothing.) The keyboard band's keys light with each
   held note in its hand's ink.
3. **Ctrl-click and right-click a knob**: the page's own menu, never the
   web view's (Reload, Back). Over the setup code's text box, the web view's
   menu with Paste is right.
4. **Drag a knob**, and automate a gold-dotted one in Logic - Cutoff on
   Play's Filter, Attack on the Amp figure, LFO 1 rate (open LFO 1's card to
   see its Rate turn): the knob moves with the automation, the Amp figure's
   drawing stretches with Attack, and a drag writes automation in Latch.
   Logic shows them in the plugin window's controls view by group, as in the
   table.
5. **Undo and redo.** The page's own: Cmd-Z, Shift-Cmd-Z or Cmd-Y with the
   face focused, and its header's arrows. Logic's: Cmd-Z with the track or
   the arrange window focused, and Edit → Undo. Turn a knob, wait half a
   second, then try each. Write down which history Cmd-Z reaches with the
   face focused (the page's, Logic's, or both - JUCE hands the web view key
   equivalents first, but Logic's menu may take Cmd-Z before it), and whether
   Logic's undo of a host knob's move puts the face's knob back. Two
   histories that undo one move twice, or a Cmd-Z that does nothing with the
   face focused, is the finding.
6. **Presets**: Logic's settings menu at the top of the plugin window lists
   the bank as factory programs; choosing one changes the face, and the
   header's preset name and the browser's (Browse) agree.
7. **Save the project, close Logic, open it again**: the sound, the face's
   size and the Output and Width come back; and a setup with Paint shown
   opens in Paint.
8. **The face at 960x600 and in the fallback fonts.** Resize the window down
   to the minimum (it opens at 1200x680, will not go under 960x600, and is
   the compact face there, at Auto's 90 per cent). At 960x600 and again at
   1200x680, open each and look for a cut word, an overlap, a scrollbar or a
   box that moves when something is chosen:
   - **Play's keyboard band**: Dyad · Mono · Poly, *Two hands* and the split
     row (Key · Notes · Layer, *Split at*, *learn from a key* - press a key on
     the controller), the three octaves of keys and the one line under them
     on one line.
   - **Play's figure area**: the Amp, Filter and Wave subtabs; drag a point
     on the Amp envelope and on the Filter's (the drawing follows the pointer,
     the knobs under it turn with it), *Sustain here* and *No sustain* from a
     point's menu; each Filter type; Wave across a few shapes, the drawbars
     and the Drawn cycle's band.
   - **Ink's figures**: Oscillator (both channels drawn, Wave · Figure) and
     Shaping; with Unison on, *Hold to watch it drift* moves it only while
     held.
   - **The drawn LFOs**: press LFO 1's card; the shape the editor's width,
     drag a point, the Grid, a shape from the seven, Rate through the note
     values with Tempo on; the card's dot follows.
   - **Scope & measure** (the toolbar over the screen): Run, Auto · Normal ·
     Single and Autoset on top, and the four subtabs, Trigger, Time,
     Vertical and Measure, each in one box with nothing scrolling.
   - **The Picture strip's info line**: point at a strip knob; the top row
     (gold dot, name, value, More) and its lines fit over the strip, and More
     opens the rest. *Draw width* switches and Width's reading follows.
   - **Perform** (the header's menu): Pattern, Step and Octaves over their
     menus, the bar of what a held chord plays, the clock's sentence and its
     Start or Stop, the morph's crossfader with its ends named. With Logic
     playing, does the clock follow the host's tempo and transport?
   Then close and open the face: it opens at the size left.
9. **Paint, in WKWebView.** The display switch above the screen: Y–T · X–Y ·
   Spect · **Paint**. Play a chord and hold it.
   - *Does it draw, and how?* The painting on the graphics card is in the
     lane inks - charcoal, slate and terracotta for the lower hand, olive,
     sage and plum for the upper - with wet paint glossy and drying. The
     fallback, where WKWebView gives no WebGL 2 or no float (or half-float)
     render target, is the core's map plain: charcoal on the paper and
     nothing else. It still plays, since the map is the sound. Either is a
     finding; the shell test's paint line (step 3) says which and why, in
     words.
   - *At what frame rate?* Hold a chord for ten seconds and watch the
     painting build: smooth or stepping. The shell test's line gives the
     face's `fps` and the cost of a paint frame (`ms`, `worst`); Linux's
     software renderer is the floor to beat.
   - *Clear* (above the screen) empties the painting at once, and a note
     after it starts on clean paper.
   - *Persistence* on the Picture strip, in Paint, is the painting's own
     half-life (16 s to start): at the bottom it holds, turned up it fades
     faster. Switch to Y–T and back: the trace's Persistence and the
     painting's are kept apart.
   - *Scan reads the painting*: with the Picture strip's Amount and Scan up
     and a chord held in Paint, the sound changes as the paint builds, and
     after a Clear it goes back towards the plain chord and changes again.
10. **The controllers on the brush**, in Paint, from a MIDI keyboard through
    Logic (Musical Typing has velocity but no wheel or pressure):
    - a **hard strike** (from about a third of full impact up) throws drops
      round where the brush lands; a soft one does not;
    - the **mod wheel**, at the bottom, leaves the brush as it was; up, it
      loads it - heavier, wider marks that last longer;
    - **pressure** (aftertouch, if the keyboard sends it) presses the brush
      wider while held;
    - the **pitch wheel**'s bend moves the stroke with the pitch and pushes
      the wet paint aside the way it went, like a palette knife;
    - the **sustain pedal** joins a hand's notes into one stroke while down,
      and does nothing else to the brush;
    - on Expression (Play), the wheel's and pressure's menus set to
      **Nothing** leave them painting only: the sound does not change as
      they move, and the brush still does.
11. **Side chain**: the plugin window's *Side Chain* menu set to an audio
    track or input, then the face's input source: the picture draws the
    host's input. (Logic takes the plugin's MIDI out only from MIDI FX, so the
    arpeggio's notes go nowhere here; that is Logic, not a fault.)
12. **Buffer size and rate**: Logic → Settings → Audio, 32 to 1024 samples,
    44.1 / 48 / 96 kHz; and **Bounce** a region offline. The sound and the
    picture should not care, in Trace or Paint; a bounce of a Paint project
    with Scan up should sound as it played.
13. **Two instances**, each with its face open, one in Paint, and CPU in
    Logic's meter.
14. **The standalone**, `Scope.app`: macOS asks for the microphone once, with
    the plugin's sentence. Inside Logic the plugin never asks: Logic holds
    the microphone permission, with its own words, and the plugin gets
    audio only through its buses.

## What only the Mac can answer

The preparation was written and checked on Linux; these were not, and could
not be, and each is a question for the day:

- **That it compiles and links** under Apple clang with the owner's Xcode,
  universal. If the Xcode is newer than JUCE 8.0.15 knows (Xcode 26), expect
  warnings; an error there is a JUCE question first.
- **That the deployment target holds.** It is 13.3 because the core's
  `std::to_chars` for doubles is unavailable before that in Apple's libc++
  (`core/include/scope/chars.h`). If the compiler still calls it unavailable,
  the target did not reach the compile (check the configure was fresh: the
  architectures and target are cache variables, read once).
- **auval** on the owner's Mac. On the GitHub runner (macOS 15) the first
  build passed everything but "parameters retain value across reset and
  initialization", which was a real bug - prepare threw away the host's
  values - fixed since (`PLAN.md`, "Found on the way"). **Settled on the
  runner on 22 Nov** (run 6, `claude/mac-build` at 722da4c, macOS 15, Apple
  Silicon): the universal build, both slices and the 13.3 target, auval with
  all eighteen knobs, and the shell test at 233 passed and none failed, its
  face checks in WKWebView included - Play's band and figures, Ink's figures,
  the right-click, the drag's gestures, Learn from a host's note and the
  Envelope card's dot. What the runner cannot say is the owner's Xcode, the
  owner's Mac and Logic.
- **The face in WKWebView**: that the page loads from the binary through
  JUCE's `juce://` scheme handler, that the native functions answer, and that
  the picture's fetches (one `/picture.bin` and one `/lfos.bin` a frame, and
  in Paint `/paint/COUNT.bin` for the strokes since the last, all served on
  the main thread) keep up - the frame rate is the number to take home,
  beside stage 0's Linux table.
- **Paint on WKWebView's graphics.** Partly settled on the runner on 22
  Nov: WKWebView gives WebGL 2 with a float render target, and the shell
  test's line read `"mode":"gpu"`, 0.145 ms a paint frame and 2 ms at worst,
  against WebKitGTK's software renderer here at 9.3 ms and 358 ms. Its `fps`
  (34 there, 32 here) is the shell test's own loop pacing the page, not the
  face's rate. Still open: the frame rate in Logic on the M4 Pro, with the
  face in a real window and a host playing, and whether a painting held for
  minutes stays smooth (step 6, Paint). Plain on the owner's Mac, where the
  runner had the graphics card, would be a finding about that Mac.
- **The controllers through Logic**: whether the mod wheel, channel
  pressure, the pitch wheel and the pedal arrive as the page and the core
  expect them, or Logic turns pressure into polyphonic aftertouch or eats
  the pedal for its own sustain handling.
- **Two undo histories**, Logic's and the page's, and which one Cmd-Z
  reaches with the face focused (step 6's fifth item).
- **The host's tempo and transport** reaching Perform's clock and the LFOs'
  Tempo, which on Linux was the shell test's fake transport only.
- **The browser storage** at the `juce://juce.backend` origin: whether
  WKWebView keeps it between openings (the Output, the tab, the Size). The
  plugin's own state goes through the host and does not depend on it.
- **Keyboard focus** between Logic and the web view, and Ctrl-click as a
  right-click, which on Linux was tested as a dispatched `contextmenu`
  only.
- **The fit** of every tab, figure area and subtab in the fallback fonts on
  a Retina screen, and the page's Auto size (a CSS zoom) under macOS's
  scaling. `fittest.py` and `patchtest.py` measured them in Chromium with
  the web fonts; nothing has measured them in WKWebView with Georgia.
- **The shell test's face checks** with WKWebView in place of WebKitGTK,
  both on the owner's Mac and on the GitHub runner.
- **Latency** told to Logic (0 to 62 samples by preset) being compensated,
  and the program list, side chain, offline bounce and a project's state
  coming back, as in the list above.

## The GitHub workflow

`.github/workflows/mac.yml`, run by hand: Actions → *Build the plugin for
macOS* → *Run workflow* once it is on `main` (GitHub offers the button only
for a workflow the default branch carries), or a push to `claude/mac-build`
runs it from that branch. On a macOS 15 runner (Apple Silicon; the macos-14
jobs were never given a runner) it reads the JUCE tag from the CMake file,
restores JUCE from the cache or clones it, configures and builds Release AU,
VST3 and the shell test universal, checks both slices and the deployment
target off the binaries, signs ad hoc, installs the AU and runs `auval -v
aumu Scop Rtsv` (the job fails if auval does), packs each bundle with `ditto`
into a zip (the artifact's own zipping would drop the execute bits) and
uploads them with auval's log, then runs the shell test, whose face checks
use the runner's desktop session. The artifact is unsigned: unzip it, copy
the bundles into place as in step 4, and run the `xattr` line there.

## If something fails

Bring the whole of it back to the session rather than a summary: the line
before a failure is usually the one that names it.

- **The build**: the first `error:` and the twenty lines above it, and
  `cmake --version`, `xcodebuild -version`.
- **The shell test**: `shell-mac.log` (step 3), whole, and the two `grep`
  lines under it. A face check that fails with "no web view" means WKWebView
  was not reached at all; one that fails after the face opened is a
  difference between WKWebView and WebKitGTK, which is what the test is for.
- **auval**: the whole output of `auval -v aumu Scop Rtsv > auval.log 2>&1`.
  The failing test is named a few lines above "AU VALIDATION FAILED".
- **Logic's Plug-in Manager**: select Scope, and copy the message in the
  lower pane word for word (or a screenshot of it); say whether it was the
  first scan or a *Reset & Rescan*.
- **The face**: a screenshot (Shift-Cmd-4, then Space, then click the plugin
  window), and the window's size.
- **The Web Inspector**, for a blank face, a control that does nothing or a
  Paint mode to read. In the Release build WKWebView is not inspectable.
  Build Debug once (`cmake -S plugin -B plugin/build-debug -G Ninja
  -DCMAKE_BUILD_TYPE=Debug -DCMAKE_OSX_ARCHITECTURES=arm64`, then the same
  build line with `build-debug`, and install that bundle in place of the
  Release one, step 4): JUCE turns on WebKit's developer extras there, so
  the web view's own menu - over the setup code's text box, the one place
  the page lets it show - offers *Inspect Element*. If it does not (macOS
  13.3 and later also ask an app to mark a web view inspectable, which JUCE
  8.0.15 does not), the standalone `Scope.app` from the Debug build is the
  same face and the same web view, and Safari → Settings → Advanced → *Show
  features for web developers*, then Develop → this Mac, may list it.
  In the console, copy any red line, and these:

  ```js
  JSON.stringify({ mode: paintView.mode, why: paintView.why, fps: Math.round(state.fps),
    frames: paintView.timing.frames, msPerFrame: paintView.timing.ms / paintView.timing.frames })
  ```

  Put the Release build back afterwards: the Debug one is several times
  slower and its CPU figures mean nothing.
- **The standalone from Terminal**, when the face shows nothing and no
  inspector can be had: `SCOPE_REPORT=1 plugin/build-mac/ScopeInstrument_artefacts/Release/Standalone/Scope.app/Contents/MacOS/Scope`
  prints the page's reports to the terminal, which at least says whether the
  page ran.
- **Logic's own crash report**, if Logic quits: the dialog's *Report…*
  text, or `~/Library/Logs/DiagnosticReports/Logic Pro*` newest first.
