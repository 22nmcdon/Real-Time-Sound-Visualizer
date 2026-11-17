# The instrument as a plugin: the core (../core) behind a JUCE processor, and
# the page (../web/scope.html) as its UI in a web view. See PLAN.md.
#
#   cmake -B build -G Ninja [-DSCOPE_JUCE_DIR=/path/to/JUCE]
#   cmake --build build
#
# JUCE is fetched at the tag below when no checkout is given. On Linux the
# web view needs WebKitGTK 4.1 and GTK 3 (and ALSA for the standalone); on
# macOS it is WKWebView, in the system, and the build wants Xcode's tools and
# nothing else (MAC.md, the weekend's checklist).
cmake_minimum_required(VERSION 3.22)

# macOS only, and read only there: these have to be set before project(), and
# are cache defaults so a command line wins (-DCMAKE_OSX_ARCHITECTURES=arm64
# halves a local build's time on the owner's Mac).
#
# Both architectures, so Logic on an Intel Mac, or under Rosetta, finds it too,
# and an Apple Silicon Logic never has to host it out of process.
#
# 13.3, not the 11.0 a universal binary could go down to: the core writes
# every number through std::to_chars with a precision (core/include/scope/
# chars.h, locale-proof since the outside review), and Apple's libc++ marks
# the floating-point to_chars unavailable before macOS 13.3, so a lower
# target does not compile. The cost is Monterey and earlier, and with them
# Logic 10.7 and 10.8 there; Logic 11 needs Sonoma (14.4) anyway.
# Rewriting the core's writer to reach further back was the alternative and
# was turned down: it is the one place every recording's numbers go through.
set(CMAKE_OSX_ARCHITECTURES "arm64;x86_64" CACHE STRING "macOS: the architectures built")
set(CMAKE_OSX_DEPLOYMENT_TARGET "13.3" CACHE STRING "macOS: the oldest system the plugin loads on")

# The plugin's version, which every release raises (PLAN.md, "Releasing"):
# Logic caches what an AU said of itself by its version, so a build that
# changes the parameters, the buses or the name under an unchanged version can
# be shown to Logic as the old one until its cache is reset.
project(ScopeInstrument VERSION 0.2.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(SCOPE_JUCE_DIR "" CACHE PATH "A JUCE checkout to build against; fetched when empty")
# The cloud environment's setup script clones JUCE at the tag below into
# /opt/juce-<tag>, read from this file, so a new session builds without
# fetching it again (11 Nov). Used only when nothing was given and that
# checkout exists; a tag moved below finds no checkout and fetches as before.
if(NOT SCOPE_JUCE_DIR AND EXISTS "/opt/juce-8.0.15/CMakeLists.txt")
  set(SCOPE_JUCE_DIR "/opt/juce-8.0.15")
endif()
if(SCOPE_JUCE_DIR)
  add_subdirectory(${SCOPE_JUCE_DIR} juce)
else()
  include(FetchContent)
  FetchContent_Declare(juce GIT_REPOSITORY https://github.com/juce-framework/JUCE.git
                            GIT_TAG 8.0.15 GIT_SHALLOW TRUE)
  FetchContent_MakeAvailable(juce)
endif()

add_subdirectory(../core core)

juce_add_plugin(ScopeInstrument
  PRODUCT_NAME "Scope"
  COMPANY_NAME "Real-Time Sound Visualizer"
  # The two codes are the plugin's identity to every host - an AU is found as
  # `aumu Scop Rtsv`, a VST3's id is made from them - and a project saved with
  # the plugin in it finds it again by them. Never change either; the bundle id
  # likewise. JUCE wants the manufacturer code to have a capital (Apple keeps
  # all-lower-case for itself).
  PLUGIN_MANUFACTURER_CODE Rtsv
  PLUGIN_CODE Scop
  BUNDLE_ID com.realtimesoundvisualizer.scope
  # An instrument: AU type 'aumu' (kAudioUnitType_MusicDevice, which IS_SYNTH
  # makes the default; said here so nobody wonders), on an instrument track in
  # Logic. Its stereo input is off by default and reaches Logic as the
  # instrument's side chain, which is how the host's input gets to the picture
  # there. The MIDI it sends (the arpeggio, the score) an aumu cannot hand on
  # in Logic, which takes MIDI out only from a MIDI FX ('aumi'); other hosts
  # take it from the VST3.
  AU_MAIN_TYPE kAudioUnitType_MusicDevice
  IS_SYNTH TRUE
  NEEDS_MIDI_INPUT TRUE
  NEEDS_MIDI_OUTPUT TRUE
  IS_MIDI_EFFECT FALSE
  EDITOR_WANTS_KEYBOARD_FOCUS TRUE
  # The page is the UI: WebKitGTK on Linux, WKWebView on macOS (the page served
  # from the binary through a juce:// scheme handler there, as through
  # WebKitGTK's custom scheme here), WebView2 linked statically on Windows.
  NEEDS_WEB_BROWSER TRUE
  NEEDS_WEBVIEW2 TRUE
  # Only the standalone opens an input itself, so only its plist's sentence is
  # ever shown. A plugin cannot ask: macOS asks once for the app that holds the
  # microphone - Logic, with Logic's own words - and a plugin inside it gets the
  # host's input through its buses or nothing. JUCE writes the key into every
  # format's plist, where in a .component or .vst3 it is read by no one.
  MICROPHONE_PERMISSION_ENABLED TRUE
  MICROPHONE_PERMISSION_TEXT "Scope draws what it hears: your microphone or instrument, on its screen."
  FORMATS VST3 AU Standalone)

# The page, built into the binary, so the plugin serves its own UI and never
# reaches for the network or the file system to draw itself.
juce_add_binary_data(ScopePage SOURCES ../web/scope.html)

target_sources(ScopeInstrument PRIVATE src/PluginProcessor.cpp src/PluginEditor.cpp)

target_compile_definitions(ScopeInstrument PUBLIC
  JUCE_WEB_BROWSER=1
  JUCE_USE_CURL=0
  JUCE_USE_WIN_WEBVIEW2_WITH_STATIC_LINKING=1
  JUCE_VST3_CAN_REPLACE_VST2=0
  JUCE_DISPLAY_SPLASH_SCREEN=0)

target_link_libraries(ScopeInstrument
  PRIVATE ScopePage scope_core juce::juce_audio_utils juce::juce_gui_extra
  PUBLIC juce::juce_recommended_config_flags juce::juce_recommended_lto_flags
         juce::juce_recommended_warning_flags)

# The shell's own test: the processor and the resource provider, run with
# neither a host nor a web view. `ctest` or run it directly.
juce_add_console_app(ScopeShellTest PRODUCT_NAME "ScopeShellTest" NEEDS_WEB_BROWSER TRUE)
target_sources(ScopeShellTest PRIVATE tests/ShellTest.cpp src/PluginProcessor.cpp src/PluginEditor.cpp)
# Modal loops, for the test alone: it opens the face and waits on the message
# thread for the page to answer (the right-click, G5b).
target_compile_definitions(ScopeShellTest PRIVATE JucePlugin_Name="Scope" JUCE_WEB_BROWSER=1 JUCE_USE_CURL=0
                           JUCE_MODAL_LOOPS_PERMITTED=1)
# The preset library before P8g, which the shell test opens the presets it was
# written against from: the bank the plugin ships is eleven since then.
target_compile_definitions(ScopeShellTest PRIVATE
  SCOPE_CORPUS="${CMAKE_CURRENT_SOURCE_DIR}/../core/tests/scenarios/library-p8f.json")
target_link_libraries(ScopeShellTest PRIVATE ScopePage scope_core juce::juce_audio_utils juce::juce_gui_extra
                      juce::juce_recommended_config_flags juce::juce_recommended_warning_flags)
enable_testing()
add_test(NAME shell COMMAND ScopeShellTest)
