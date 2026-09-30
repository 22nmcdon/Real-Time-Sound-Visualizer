#pragma once

#include <array>
#include <atomic>
#include <cstddef>
#include <vector>

#include <juce_audio_processors/juce_audio_processors.h>

#include "scope/envelope.h"

// The processor. For the spike it plays the core's envelope on a sine, one
// note at a time with the envelope's legato rule, because the generator core
// is not ported yet (PLAN.md, stage 1); what the spike is for is the shape
// around it - notes in from the host, sound out, and the samples the page
// draws handed to the editor.
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
  bool producesMidi() const override { return false; }
  bool isMidiEffect() const override { return false; }
  double getTailLengthSeconds() const override { return 0.5; }

  int getNumPrograms() override { return 1; }
  int getCurrentProgram() override { return 0; }
  void setCurrentProgram(int) override {}
  const juce::String getProgramName(int) override { return {}; }
  void changeProgramName(int, const juce::String&) override {}

  void getStateInformation(juce::MemoryBlock&) override {}
  void setStateInformation(const void*, int) override {}

  /* The last `kPictureFrames` of what was played, left and right interleaved,
     for the page to draw: written by the audio thread, read by the editor's
     resource provider. The read can tear across a block boundary, which a
     picture redrawn sixty times a second survives and a measurement would
     not - the real channel (PLAN.md, stage 1) carries a frame count so the
     page can tell. */
  static constexpr std::size_t kPictureFrames = 2048;
  std::vector<float> pictureSnapshot() const;
  double sampleRateNow() const { return rate_.load(); }

 private:
  scope::EnvelopeTone tone_;
  std::unique_ptr<scope::Envelope> envelope_;
  double phase_ = 0;
  double hz_ = 220;
  int held_ = -1;
  std::atomic<double> rate_ { 48000.0 };

  std::array<float, kPictureFrames * 2> picture_ {};
  std::atomic<std::size_t> pictureAt_ { 0 };

  JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ScopeProcessor)
};
