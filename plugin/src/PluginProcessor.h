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

 private:
  scope::EnvelopeTone tone_;
  std::unique_ptr<scope::Envelope> envelope_;
  double phase_ = 0;
  double hz_ = 220;
  int held_ = -1;
  std::atomic<double> rate_ { 48000.0 };

  std::array<float, kPictureFrames * 2> picture_ {};
  juce::String pictureReport_;
  std::atomic<std::size_t> pictureAt_ { 0 };

  JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ScopeProcessor)
};
