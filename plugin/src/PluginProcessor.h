#pragma once

#include <array>
#include <atomic>
#include <cstddef>
#include <optional>
#include <string>
#include <vector>

#include <juce_audio_processors/juce_audio_processors.h>

#include "scope/generator.h"
#include "scope/hearing.h"
#include "scope/keyboard.h"
#include "scope/lfo.h"
#include "scope/matrix.h"
#include "scope/presets.h"
#include "scope/restore.h"
#include "scope/sources.h"

// The processor plays the core's generator (scope::Generator, the page's
// `makeGeneratorCore` ported): what the speakers get is its heard pair, and
// what the page draws is its picture pair. The host's MIDI reaches it through
// the core's keyboard (scope::Keyboard, the page's `midi` functions ported),
// byte for byte as a port's reach the page: the stack, the pedal, the dyad,
// mono and chords on two layers. The routings reach it through the core's
// matrix (scope::Matrix), compiled and faded at the top of every block, from
// the sources ported so far, and the morph steps after it, as the page's
// frame has it. Before all of it the clock (scope::Clock, the page's
// `transport`): the host's tempo, play and position where the host gives
// them, a MIDI clock's otherwise, and the slider's when neither. Until the
// rest of the brain moves into the core (PLAN.md, stage 2) it starts as the
// page starts - on the "Harmonic tone" preset, loaded through the core's
// `restoreSetup` - and nothing yet moves it from there but the host's notes,
// its clock and the matrix. What the page sends to a MIDI port - the
// arpeggio's steps, the crossings' notes, the pluck's and the score's - goes
// to the host's MIDI out (scope::MidiOut), each at the sample of what sent it.
// The host sees eight parameters, each one of the panel's sliders, and saves
// the plugin as a setup code: the setup it was loaded with, the parameters
// over it, and the controllers it has learned.
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
  double getTailLengthSeconds() const override { return 0.5; }

  int getNumPrograms() override { return 1; }
  int getCurrentProgram() override { return 0; }
  void setCurrentProgram(int) override {}
  const juce::String getProgramName(int) override { return {}; }
  void changeProgramName(int, const juce::String&) override {}

  /* The plugin's state is a setup code, the thing the page shares: the
     setup it was loaded with, and over it what has moved since - every
     slider moved, by the host's parameters or the page, every menu, switch
     and button the page has sent and its routings, and the controllers
     learned. */
  void getStateInformation(juce::MemoryBlock&) override;
  void setStateInformation(const void*, int) override;

  /* The last `kPictureFrames` of what was played, left and right interleaved,
     for the page to draw: written by the audio thread, read by the editor's
     resource provider. The read can tear across a block boundary, which a
     picture redrawn sixty times a second survives and a measurement would
     not - the real channel (PLAN.md, stage 1) carries a frame count so the
     page can tell. */
  /* About 170 ms at 48 kHz: enough for the scope's longer timebases and for
     the readout's analysis, at 64 KB a fetch. 2048 was a twentieth of a
     second, shorter than a 5 ms/div screen. */
  static constexpr std::size_t kPictureFrames = 8192;
  std::vector<float> pictureSnapshot() const;
  double sampleRateNow() const { return rate_.load(); }

  /* What the page last said about how the picture is getting through: frames
     a second and how long its fetches take. Kept for whoever asks, and
     printed when SCOPE_REPORT is set - which is how the spike measures the
     path. Written from the message thread, read from it too. */
  void setPictureReport(const juce::String& json) { pictureReport_ = json; }
  juce::String pictureReport() const { return pictureReport_; }

  // The tone and the keyboard's settings, for the shell test to read.
  const scope::Tone& tone() const { return core_->tone(); }
  scope::Keyboard::Settings keys() const { return keyboard_->settings(); }
  // The routings, for whoever sets them: the shell test now, the brain's
  // setup later. Not to be touched while the audio thread runs.
  scope::Matrix& matrix() { return *matrix_; }
  // The level, the threshold's count and the learned controllers, for the shell test to read.
  double level() const { return sources_->level().value(); }
  int thresholdCount() const { return brain_->thresh.count; }
  const scope::Hearing& hearing() const { return hearing_->hearing(); }
  // The clock and an oscillator's rate, for the shell test to read.
  const scope::Clock& clock() const { return brain_->clock; }
  const scope::ScoreState& score() const { return brain_->score; }
  double lfoRate(int i) const { return lfos_[static_cast<std::size_t>(i)].rate; }
  /* A hand on one of the panel's sliders, and an end of the morph stored: what
     the page will send over the bridge once it is the plugin's face. Until
     then, the shell test's way in. */
  void moveSlider(const std::string& id, double value);
  void storeMorph(bool endB) { scope::morphStore(*brain_, endB); }

  /* The host's parameters: the four macros, the morph's fader, and three of
     the main knobs, each one of the panel's sliders by id and in its units.
     A curated few rather than every control, as the plan has it. */
  struct HostKnob { const char* id; const char* name; const char* slider; };
  static constexpr std::array<HostKnob, 8> kKnobs { {
    { "macro1", "Macro 1", "macro1" }, { "macro2", "Macro 2", "macro2" }, { "macro3", "Macro 3", "macro3" },
    { "macro4", "Macro 4", "macro4" }, { "morph", "Morph", "morphPos" }, { "level", "Level", "amp" },
    { "cutoff", "Cutoff", "vcfCut" }, { "echo", "Echo", "delayMix" },
  } };
  juce::AudioParameterFloat* knob(std::size_t i) const { return knobs_[i]; }

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
  struct PageState { int version = 0; std::string code; };
  PageState pageState() const;
  double slider(const char* id) const { return brain_->panel.range(id); }
  int learned() const { return static_cast<int>(keyboard_->controllers().size()); }

 private:
  // A setup loaded as a preset is: the core restored, the sliders it moved
  // since put back, and the parameters read back from the panel.
  void load(const scope::Json& setup, bool fromHost);
  // A slider moved, by the host's parameter or the page, and remembered as
  // moved since the setup was loaded.
  void moveTo(const std::string& id, const std::u16string& text, bool fromHost);
  // The page's other hands: done here, and remembered if they did anything.
  void change(const std::string& id, const scope::Json& value);
  void click(const std::string& id);
  void routings(const std::string& text);
  // A hand put back from a saved state, as the page sends it.
  void replay(const scope::Json& hand);
  // A hand remembered, in place of an earlier one it makes redundant.
  void remember(std::string key, scope::Json hand);
  // The setup code of everything that can have changed: the setup loaded,
  // the hands on it since, the controllers learned.
  std::string stateCode() const;
  // The page's queue, applied; and the state, published for the page if it changed.
  void takePage();
  void publish(bool wait);
  // Each parameter the host has moved since the last block, to its slider.
  void applyKnobs();

  // Render [from, to) of the block into the output and the picture ring.
  void render(float* left, float* right, int from, int to);
  // The last of the picture, the page's screen, for the level and the hearing
  // to read: its left channel for both, and its right for the hearing's width.
  void window(std::vector<float>& left, std::vector<float>* right) const;
  static constexpr std::size_t kLevelFrames = 2048;
  std::vector<float> levelLane_, hearL_, hearR_;
  std::unique_ptr<scope::HearingSources> hearing_;  // what it hears of itself, as sources

  std::vector<scope::Lfo> lfos_;
  std::unique_ptr<scope::Generator> core_;
  std::unique_ptr<scope::GeneratorNotes> notes_;
  std::unique_ptr<scope::Keyboard> keyboard_;
  std::unique_ptr<scope::Matrix> matrix_;
  std::unique_ptr<scope::CoreSources> sources_;
  std::unique_ptr<scope::Brain> brain_;  // what a setup sets beyond the generator
  std::unique_ptr<scope::ClockIn> clockIn_;  // MIDI's real-time bytes, to the brain's clock
  std::unique_ptr<scope::BrainSources> brainSources_;  // the macros, the morph's fader and the pluck as destinations
  std::unique_ptr<scope::MidiOut> midiOut_;  // to the host's MIDI out, through `outgoing_`
  scope::Strike strike_;  // the score's notes, struck in the generator's score voice
  juce::MidiBuffer outgoing_;  // what the out sent this block, at `outAt_`, handed over at its end
  int outAt_ = 0;
  std::array<juce::AudioParameterFloat*, kKnobs.size()> knobs_ {};
  std::array<float, kKnobs.size()> applied_ {};  // each parameter as last applied
  scope::Json setup_;                          // the setup the plugin was loaded with
  juce::SpinLock stateLock_;                   // a state loaded while the audio thread runs
  std::optional<scope::Json> pending_;         // waiting for the next block, or for prepareToPlay
  /* Every hand on the setup since it was loaded, in order: a slider, a menu,
     a switch, a button, the routings. Saved with it as `pluginHands`, each
     [kind, id, value], and put back in order when the state is loaded. A
     hand on a control already in the list takes the earlier one's place at
     the end - unless a hand between them is one whose handler reads it. */
  struct Hand { std::string key; scope::Json hand; };
  std::vector<Hand> hands_;
  struct PageCommand {
    enum Kind { Slider, Setup, Control, Click, Routings } kind;
    std::string id; std::u16string text; scope::Json value; std::optional<scope::Json> setup;
  };
  juce::SpinLock queueLock_;
  std::vector<PageCommand> queue_, taken_;
  mutable juce::SpinLock publishLock_;
  PageState published_;
  int hostVersion_ = 0;      // changes that came from the host: a load, a parameter moved
  bool changed_ = false;
  std::size_t learnedSeen_ = 0;
  double nowMs_ = 0, lastBlockMs_ = 0;  // the matrix's clock: audio time, not the wall's
  std::vector<float> pictureL_, pictureR_, spare_;  // a block's worth, made in prepareToPlay
  std::atomic<double> rate_ { 48000.0 };

  std::array<float, kPictureFrames * 2> picture_ {};
  juce::String pictureReport_;
  std::atomic<std::size_t> pictureAt_ { 0 };

  JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ScopeProcessor)
};
