#pragma once

#include <array>
#include <atomic>
#include <cstddef>
#include <optional>
#include <string>
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
// steps, the crossings' notes, the pluck's and the score's - each at the
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
     resource provider. */
  static constexpr std::size_t kPictureFrames = scope::Instrument::kPictureFrames;
  std::vector<float> pictureSnapshot() const { return instrument_.pictureSnapshot(); }
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
  int thresholdCount() const { return instrument_.thresholdCount(); }
  const scope::Hearing& hearing() const { return instrument_.hearing(); }
  const scope::Clock& clock() const { return instrument_.clock(); }
  const scope::ScoreState& score() const { return instrument_.score(); }
  const scope::PictureRun& picture() const { return instrument_.picture(); }
  const scope::Brain::ViewState& view() const { return instrument_.view(); }
  double lfoRate(int i) const { return instrument_.lfoRate(i); }
  // A hand on one of the panel's sliders, not remembered, and an end of the morph stored: the shell test's way in.
  void moveSlider(const std::string& id, double value) { instrument_.moveSlider(id, value); }
  void storeMorph(bool endB) { instrument_.storeMorph(endB); }

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
  // And the fade, which the page keeps in its own storage, sent whole as JSON when it is saved.
  void pageFade(std::string_view json);
  struct PageState { int version = 0; std::string code; };
  PageState pageState() const;
  double slider(const char* id) const { return instrument_.slider(id); }
  int learned() const { return instrument_.learned(); }

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
  std::vector<scope::Instrument::HostSlider> moved_;  // the parameters moved since the last block
  std::vector<scope::Instrument::Event> events_;      // the host's MIDI this block
  juce::SpinLock stateLock_;                   // a state loaded while the audio thread runs
  std::optional<scope::Json> pending_;         // waiting for the next block, or for prepareToPlay
  juce::SpinLock queueLock_;
  std::vector<scope::Instrument::Command> queue_, taken_;
  mutable juce::SpinLock publishLock_;
  PageState published_;
  std::atomic<double> rate_ { 48000.0 };
  juce::String pictureReport_;

  JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ScopeProcessor)
};
