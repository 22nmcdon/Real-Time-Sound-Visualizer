#pragma once

#include <array>
#include <atomic>
#include <cstddef>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include <juce_audio_processors/juce_audio_processors.h>

#include "scope/instrument.h"
#include "scope/presets.h"

// The processor is the instrument (scope::Instrument) behind JUCE: the core's
// generator, and over it the brain - the keyboard, the matrix and its
// sources, the clock, the score, the hearing, the picture the photocell
// reads - which the site's worklet runs too, compiled, so the two are one
// instrument. What is the processor's own is what only a host has: the
// host's MIDI, handed to the instrument byte for byte at its sample, and its
// MIDI out, which gets what the page would send to a port - the arpeggio's
// steps and the score's notes - each at the
// sample of what sent it; the host's transport; eight parameters, each one
// of the panel's sliders; the page's commands, queued under a lock for the
// top of the next block; and the state, saved as a setup code - the setup it
// was loaded with, the hands on it since, and the controllers it has learned.
class ScopeProcessor final : public juce::AudioProcessor {
 public:
  ScopeProcessor();

  void prepareToPlay(double sampleRate, int samplesPerBlock) override;
  void releaseResources() override {}
  bool isBusesLayoutSupported(const BusesLayout& layouts) const override;
  void processBlock(juce::AudioBuffer<float>&, juce::MidiBuffer&) override;
  using AudioProcessor::processBlock;

  juce::AudioProcessorEditor* createEditor() override;
  bool hasEditor() const override { return true; }

  const juce::String getName() const override { return JucePlugin_Name; }
  bool acceptsMidi() const override { return true; }
  bool producesMidi() const override { return true; }
  bool isMidiEffect() const override { return false; }
  /* How long it goes on after the last note: the longer release of the two
     layers, and the echo's repeats until they are 60 dB down. It was half a
     second whatever the echo did, so a host that stops processing a silent
     track cut the echoes off. Worked out on the audio thread as the setup
     changes (`tailFor`) and read from wherever the host asks. A known limit:
     layer B's own echo, and a loop that keeps itself going under Scan, are
     not counted; the second has no end to report. */
  double getTailLengthSeconds() const override { return tail_.load(); }
  static double tailFor(const scope::Tone& a, const scope::LayerSettings& b);

  /* The bank as the host's programs (6 Nov): the plain sine the plugin opens
     on, then the bank in the browser's order. A program chosen is a state
     handed over, as a project's is. The one already chosen chosen again is
     nothing: some hosts set the current program straight after restoring a
     project, which would otherwise put the project back to the plain sine. */
  int getNumPrograms() override { return 1 + static_cast<int>(scope::presets().size()); }
  int getCurrentProgram() override { return program_.load(); }
  void setCurrentProgram(int index) override;
  const juce::String getProgramName(int index) override;
  void changeProgramName(int, const juce::String&) override {}

  /* The face's window: the size it was last left at, kept with the project
     ("pluginWindow" in the state, which the instrument never sees). */
  static constexpr int kWindowW = 1200, kWindowH = 680;  // inside a 1366x768 laptop with a host's frame
  void setWindowSize(int w, int h) { windowW_.store(w); windowH_.store(h); }
  std::pair<int, int> windowSize() const { return { windowW_.load(), windowH_.load() }; }

  /* The plugin's state is a setup code, the thing the page shares: the
     setup it was loaded with, and over it what has moved since - every
     slider moved, by the host's parameters or the page, every menu, switch
     and button the page has sent and its routings, and the controllers
     learned. */
  void getStateInformation(juce::MemoryBlock&) override;
  void setStateInformation(const void*, int) override;

  /* The last `kPictureFrames` of what was played, left and right interleaved,
     for the page to draw: written by the audio thread, read by the editor's
     resource provider. */
  static constexpr std::size_t kPictureFrames = scope::Instrument::kPictureFrames;
  std::vector<float> pictureSnapshot() const { return instrument_.pictureSnapshot(); }
  std::vector<float> pictureServed() const { return instrument_.pictureServed(); }
  // The oscillators as they stood at the picture's newest frame: phase, held and value, each of two.
  std::array<double, 6> lfosServed() const { return instrument_.lfosServed(); }
  bool bands() const { return instrument_.bands(); }
  int lanes() const { return instrument_.lanes(); }
  double bandGain(int lane) const { return instrument_.bandGain(lane); }
  double sampleRateNow() const { return rate_.load(); }

  /* What the page last said about how the picture is getting through: frames
     a second and how long its fetches take. Kept for whoever asks, and
     printed when SCOPE_REPORT is set - which is how the spike measures the
     path. Written from the message thread, read from it too. */
  void setPictureReport(const juce::String& json) { pictureReport_ = json; }
  juce::String pictureReport() const { return pictureReport_; }

  // What the shell test reads, from the instrument.
  const scope::Tone& tone() const { return instrument_.tone(); }
  const scope::LayerSettings& toneB() const { return instrument_.toneB(); }
  scope::Keyboard::Settings keys() const { return instrument_.keyboard().settings(); }
  // The routings, for the shell test to set. Not to be touched while the audio thread runs.
  scope::Matrix& matrix() { return instrument_.matrix(); }
  double level() const { return instrument_.level(); }
  const scope::Hearing& hearing() const { return instrument_.hearing(); }
  const scope::Clock& clock() const { return instrument_.clock(); }
  const scope::ScoreState& score() const { return instrument_.score(); }
  const scope::PictureRun& picture() const { return instrument_.picture(); }
  const scope::Brain::ViewState& view() const { return instrument_.view(); }
  double lfoRate(int i) const { return instrument_.lfoRate(i); }
  bool drawsInput() const { return instrument_.drawsInput(); }
  int pictureLanes() const { return instrument_.pictureLanes(); }
  // A hand on one of the panel's sliders, not remembered, and an end of the morph stored: the shell test's way in.
  void moveSlider(const std::string& id, double value) { instrument_.moveSlider(id, value); }
  void storeMorph(bool endB) { instrument_.storeMorph(endB); }

  /* The host's parameters (P8a): the loop's own controls in the main bank,
     then the morph's fader in a group of its own. Each is one of the panel's
     sliders by id and in its units, so a host moving one is a hand on that
     slider, and a hand on the slider moves the parameter.

     The main bank is the picture's amount, Scan's depth, the screen's
     persistence, the bend, the voice filter's cutoff, the level and the echo.
     The phaser's amount takes the eighth place when the phaser is built,
     inserted before the morph. The macros were four of the first eight and
     are not parameters any more: nobody had saved a project, so nothing was
     mapped across (plugin/PLAN.md, P8a).

     Hosts that bind automation by id (VST3 and AU here, JUCE's default ids)
     keep the morph's automation when the phaser is inserted; what moves is
     its index, so a controller mapped by position would find it one along.
     Reserving the place now with an inert parameter was the alternative,
     and was turned down: a knob in a host's list that does nothing is worse
     than an index that moves once, before anyone has saved anything.

     `version` is the plugin version a parameter arrived in, which AU hosts
     use to order and JUCE asks for: the level, cutoff, echo and morph were
     the first plugin's, the four loop controls this one's. A layer's
     controls - Scan's depth, the bend, the cutoff, the level - address the
     layer the panel shows, as the slider does for a hand (`readBack`). */
  struct HostKnob { const char* id; const char* name; const char* slider; int version; bool main; };
  static constexpr std::array<HostKnob, 9> kKnobs { {
    { "picture", "Picture", "pictureAmount", 2, true }, { "scan", "Scan", "oscScan", 2, true },
    { "persistence", "Persistence", "scanMemory", 2, true }, { "bend", "Warp", "oscBend", 2, true },
    { "cutoff", "Cutoff", "vcfCut", 1, true }, { "level", "Level", "amp", 1, true },
    { "echo", "Echo", "delayMix", 1, true },
    // P8e: the eighth knob of the bank, which P8a kept for it. Morph moves from
    // index 7 to 8, and its automation stays with it, being bound to its id.
    { "phaser", "Phaser", "phaserMix", 2, true },
    { "morph", "Morph", "morphPos", 1, false },
  } };
  juce::AudioParameterFloat* knob(std::size_t i) const { return knobs_[i]; }
  // By the parameter's id, which outlives its index: the shell test's way to a knob.
  juce::AudioParameterFloat* knob(std::string_view id) const {
    for (std::size_t i = 0; i < kKnobs.size(); ++i)
      if (id == kKnobs[i].id) return knobs_[i];
    return nullptr;
  }

  /* The page as the plugin's face (stage 3), through the editor's native
     functions, on the message thread. A slider moved on the page is a hand
     on that slider here; a setup loaded on the page - a preset, a code - is
     loaded here as it was there. Both wait in a queue for the top of the
     next block, where the audio thread does what it does with everything
     else. And the state for the page to show: the setup code the plugin
     would save, with how many changes in it came from the host rather than
     the page, so the page applies only those and never echoes its own. */
  void pageSlider(const std::string& id, const std::u16string& text);
  bool pageSetup(std::string_view code);
  /* And a menu, a switch or a text box changed (its value as the browser
     holds it, or a switch's state as true or false), a button pressed, and
     the routings as an edit there left them, every depth to the last digit.
     Each is the
     page's handler, ported (scope::controlChange, controlClick and
     Matrix::setRoutings). */
  void pageControl(const std::string& id, scope::Json value);
  void pageClick(const std::string& id);
  void pageRoutings(std::string_view text);
  // And the fade, which the page keeps in its own storage, sent whole as JSON when it is saved.
  void pageFade(std::string_view json);
  // The state for the page: its host count, how many of those were loads, the
  // sliders the host has moved since the last, and the code (hostPull on the page).
  struct PageState { int version = 0; int loads = 0; std::string moved; std::string code; };
  PageState pageState() const;
  double slider(const char* id) const { return instrument_.slider(id); }

 private:
  // A command from the page, waiting for the next block; or refused, and false.
  bool queue(std::optional<scope::Instrument::Command> command);
  // The page's queue, applied; and the state, published for the page if it changed.
  void takePage();
  void publish(bool wait);

  scope::Instrument instrument_;
  juce::MidiBuffer outgoing_;  // what the out sent this block, handed over at its end
  std::array<juce::AudioParameterFloat*, kKnobs.size()> knobs_ {};
  std::array<float, kKnobs.size()> applied_ {};  // each parameter as last applied
  int panelLayer_ = 0;                          // the layer the panel showed at the last block
  // The parameters not moved by the host, read back from their sliders: a setup loaded, or the panel's layer changed.
  void readBack(bool unmovedOnly);
  std::vector<scope::Instrument::HostSlider> moved_;  // the parameters moved since the last block
  std::vector<scope::Instrument::Event> events_;      // the host's MIDI this block
  std::vector<float> inL_, inR_;                      // the host's input this block, copied out of the buffer
  juce::SpinLock stateLock_;                   // guards the hand-over of pending_ only, never the instrument
  std::optional<scope::Json> pending_;         // waiting for the next block, or for prepareToPlay
  juce::SpinLock queueLock_;
  std::vector<scope::Instrument::Command> queue_, taken_;
  mutable juce::SpinLock publishLock_;
  PageState published_;
  std::atomic<double> rate_ { 48000.0 };
  std::atomic<double> tail_ { 0.5 };
  std::atomic<int> program_ { 0 };
  std::atomic<int> windowW_ { kWindowW }, windowH_ { kWindowH };
  juce::String pictureReport_;

  JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ScopeProcessor)
};
