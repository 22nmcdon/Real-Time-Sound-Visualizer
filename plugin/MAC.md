# The plugin on a Mac: the weekend's checklist

For the owner and a Claude session, the first time the plugin is built and
played on the owner's Mac (a Mac mini, Apple M4 Pro, Xcode installed) in
Logic Pro. The plugin had only been built on Linux before; what was done to
prepare it is in `PLAN.md`, stage 6. Each step says what it is for, so a step
that fails says where to look.

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
git fetch origin claude/mac-prep && git checkout claude/mac-prep    # or testing, once it is there
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
the page, and hands it the picture" or FAILED. Compare the count with the
Linux run's (the session that prepared this records it in its message and in
`PLAN.md`'s neighbourhood); a check that passes on Linux and fails here is
this weekend's real finding.

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
this order, writing down what happens at each:

1. **The face opens** and draws: the page, not the "no web view" sentence.
   The type is the fallback faces (Georgia and the system's sans), not the
   site's web fonts, by design; a tab that scrolls with them is a finding.
2. **Play** from a MIDI keyboard and from Logic's Musical Typing (Window →
   Show Musical Typing): sound, and the figure on the screen moving with it.
   With the face's window focused, do the computer's keys reach the page or
   Logic? (The page's own on-screen keys are the site's only, by design.)
3. **Ctrl-click and right-click a knob**: the page's own menu, never the
   web view's (Reload, Back). Over the setup code's text box, the web view's
   menu with Paste is right.
4. **Drag a knob**, and automate one of the gold-dotted ones in Logic: the
   knob moves with the automation, and a drag writes automation in Latch.
5. **Presets**: Logic's settings menu at the top of the plugin window lists
   the bank as factory programs; choosing one changes the face.
6. **Save the project, close Logic, open it again**: the sound, the face's
   size and the Output come back.
7. **Resize** the window, down to the minimum (960x600), and open it again.
8. **Side chain**: the plugin window's *Side Chain* menu set to an audio
   track or input, then the face's input source: the picture draws the
   host's input. (Logic takes the plugin's MIDI out only from MIDI FX, so the
   arpeggio's notes go nowhere here; that is Logic, not a fault.)
9. **Buffer size and rate**: Logic → Settings → Audio, 32 to 1024 samples,
   44.1 / 48 / 96 kHz; and **Bounce** a region offline. The sound and the
   picture should not care.
10. **Two instances**, each with its face open, and CPU in Logic's meter.
11. **The standalone**, `Scope.app`: macOS asks for the microphone once, with
    the plugin's sentence. Inside Logic the plugin never asks: Logic holds
    the microphone permission, with its own words, and the plugin gets
    audio only through its buses.

## What only the Mac can answer

The preparation was written and checked on Linux; these were not, and could
not be, and each is a question for the weekend:

- **That it compiles and links** under Apple clang with the owner's Xcode,
  universal. If the Xcode is newer than JUCE 8.0.15 knows (Xcode 26), expect
  warnings; an error there is a JUCE question first.
- **That the deployment target holds.** It is 13.3 because the core's
  `std::to_chars` for doubles is unavailable before that in Apple's libc++
  (`core/include/scope/chars.h`). If the compiler still calls it unavailable,
  the target did not reach the compile (check the configure was fresh: the
  architectures and target are cache variables, read once).
- **auval**: never run on this plugin. An instrument that also says it makes
  MIDI and has a stereo input off by default is unusual; auval's bus and
  MIDI-output checks are where to look first.
- **The face in WKWebView**: that the page loads from the binary through
  JUCE's `juce://` scheme handler, that the native functions answer, and that
  the picture's fetches (one `/picture.bin` and one `/lfos.bin` a frame,
  served on the main thread) keep up - the frame rate is the number to take
  home, beside stage 0's Linux table.
- **The browser storage** at the `juce://juce.backend` origin: whether
  WKWebView keeps it between openings (the Output, the tab, the Size). The
  plugin's own state goes through the host and does not depend on it.
- **Keyboard focus** between Logic and the web view, and Ctrl-click as a
  right-click, which on Linux was tested as a dispatched `contextmenu`
  only.
- **The fit** of every tab in the fallback fonts on a Retina screen, and the
  page's Auto size (a CSS zoom) under macOS's scaling.
- **The shell test's face checks** with WKWebView in place of WebKitGTK,
  both on the owner's Mac and on the GitHub runner.
- **Latency** told to Logic (0 to 62 samples by preset) being compensated,
  and the program list, side chain, offline bounce and a project's state
  coming back, as in the list above.

## The GitHub workflow

`.github/workflows/mac.yml`, run by hand: Actions → *Build the plugin for
macOS* → *Run workflow*, on `claude/mac-prep` or wherever it has gone. On a
macOS 14 runner (Apple Silicon) it reads the JUCE tag from the CMake file,
restores JUCE from the cache or clones it, configures and builds Release AU,
VST3 and the shell test universal, checks both slices and the deployment
target off the binaries, signs ad hoc, installs the AU and runs `auval -v
aumu Scop Rtsv` (the job fails if auval does), packs each bundle with `ditto`
into a zip (the artifact's own zipping would drop the execute bits) and
uploads them with auval's log, then runs the shell test, whose face checks
use the runner's desktop session. The artifact is unsigned: unzip it, copy
the bundles into place as in step 4, and run the `xattr` line there.
