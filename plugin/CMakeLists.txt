# The instrument as a plugin: the core (../core) behind a JUCE processor, and
# the page (../web/scope.html) as its UI in a web view. See PLAN.md.
#
#   cmake -B build -G Ninja [-DSCOPE_JUCE_DIR=/path/to/JUCE]
#   cmake --build build
#
# JUCE is fetched at the tag below when no checkout is given. On Linux the
# web view needs WebKitGTK 4.1 and GTK 3 (and ALSA for the standalone).
cmake_minimum_required(VERSION 3.22)
project(ScopeInstrument VERSION 0.1.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(SCOPE_JUCE_DIR "" CACHE PATH "A JUCE checkout to build against; fetched when empty")
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
  PLUGIN_MANUFACTURER_CODE Rtsv
  PLUGIN_CODE Scop
  IS_SYNTH TRUE
  NEEDS_MIDI_INPUT TRUE
  NEEDS_MIDI_OUTPUT FALSE
  IS_MIDI_EFFECT FALSE
  EDITOR_WANTS_KEYBOARD_FOCUS TRUE
  # The page is the UI: WebKitGTK on Linux, WebView2 linked statically on Windows.
  NEEDS_WEB_BROWSER TRUE
  NEEDS_WEBVIEW2 TRUE
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
target_compile_definitions(ScopeShellTest PRIVATE JucePlugin_Name="Scope" JUCE_WEB_BROWSER=1 JUCE_USE_CURL=0)
target_link_libraries(ScopeShellTest PRIVATE ScopePage scope_core juce::juce_audio_utils juce::juce_gui_extra
                      juce::juce_recommended_config_flags juce::juce_recommended_warning_flags)
enable_testing()
add_test(NAME shell COMMAND ScopeShellTest)
