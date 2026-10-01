#include "PluginProcessor.h"

#include <cmath>
#include <cstdlib>

#include "PluginEditor.h"

ScopeProcessor::ScopeProcessor()
    : AudioProcessor(BusesProperties().withOutput("Output", juce::AudioChannelSet::stereo(), true)) {}

bool ScopeProcessor::isBusesLayoutSupported(const BusesLayout& layouts) const {
  return layouts.getMainOutputChannelSet() == juce::AudioChannelSet::stereo();
}

void ScopeProcessor::prepareToPlay(double sampleRate, int) {
  rate_.store(sampleRate);
  // Reset at nought, as the page resets an envelope that is about to be gated.
  envelope_ = std::make_unique<scope::Envelope>(sampleRate, tone_);
  envelope_->reset(0);
  phase_ = 0;
  held_ = -1;
  /* For measuring the spike without a keyboard: SCOPE_HOLD_NOTE=57 holds A3
     from the start, so the standalone has something to draw. Read once, here,
     and never on the audio thread. */
  if (const char* note = std::getenv("SCOPE_HOLD_NOTE")) {
    held_ = std::atoi(note);
    hz_ = juce::MidiMessage::getMidiNoteInHertz(held_);
    envelope_->gate(true, 1.0);
  }
}

void ScopeProcessor::processBlock(juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midi) {
  juce::ScopedNoDenormals noDenormals;
  const int frames = buffer.getNumSamples();
  auto* left = buffer.getWritePointer(0);
  auto* right = buffer.getNumChannels() > 1 ? buffer.getWritePointer(1) : nullptr;
  const double rate = rate_.load();

  auto events = midi.cbegin();
  for (int i = 0; i < frames; ++i) {
    // Each event at its own sample, not at the top of the block.
    for (; events != midi.cend() && (*events).samplePosition <= i; ++events) {
      const auto message = (*events).getMessage();
      if (message.isNoteOn()) {
        held_ = message.getNoteNumber();
        hz_ = juce::MidiMessage::getMidiNoteInHertz(held_);
        envelope_->gate(true, message.getFloatVelocity());
      } else if (message.isNoteOff() && message.getNoteNumber() == held_) {
        envelope_->gate(false, 0);
        held_ = -1;
      } else if (message.isAllNotesOff() || message.isAllSoundOff()) {
        envelope_->gate(false, 0);
        held_ = -1;
      }
    }
    const double level = envelope_->step();
    const float sample = static_cast<float>(0.3 * level * std::sin(phase_));
    phase_ += juce::MathConstants<double>::twoPi * hz_ / rate;
    if (phase_ > juce::MathConstants<double>::twoPi) phase_ -= juce::MathConstants<double>::twoPi;
    left[i] = sample;
    if (right) right[i] = sample;

    const std::size_t at = pictureAt_.load(std::memory_order_relaxed);
    picture_[at * 2] = sample;
    picture_[at * 2 + 1] = sample;
    pictureAt_.store((at + 1) % kPictureFrames, std::memory_order_release);
  }
}

std::vector<float> ScopeProcessor::pictureSnapshot() const {
  // Oldest first, so the page reads it as a window of time.
  std::vector<float> out(kPictureFrames * 2);
  const std::size_t at = pictureAt_.load(std::memory_order_acquire);
  for (std::size_t k = 0; k < kPictureFrames; ++k) {
    const std::size_t from = (at + k) % kPictureFrames;
    out[k * 2] = picture_[from * 2];
    out[k * 2 + 1] = picture_[from * 2 + 1];
  }
  return out;
}

juce::AudioProcessorEditor* ScopeProcessor::createEditor() { return new ScopeEditor(*this); }

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter() { return new ScopeProcessor(); }
