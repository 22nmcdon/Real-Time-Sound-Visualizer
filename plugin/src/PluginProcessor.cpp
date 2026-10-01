#include "PluginProcessor.h"

#include <algorithm>
#include <cstdlib>

#include "PluginEditor.h"

ScopeProcessor::ScopeProcessor()
    : AudioProcessor(BusesProperties().withOutput("Output", juce::AudioChannelSet::stereo(), true)) {}

bool ScopeProcessor::isBusesLayoutSupported(const BusesLayout& layouts) const {
  return layouts.getMainOutputChannelSet() == juce::AudioChannelSet::stereo();
}

void ScopeProcessor::prepareToPlay(double sampleRate, int samplesPerBlock) {
  rate_.store(sampleRate);
  // The page's two LFOs as it starts them.
  lfos_.assign(2, scope::Lfo {});
  lfos_[0].rate = 0.2; lfos_[0].depth = 0.5;
  lfos_[1].rate = 0.5; lfos_[1].depth = 0.3;
  core_ = std::make_unique<scope::Generator>(sampleRate, scope::slot::Used, lfos_);
  // Gated, as the page's generator is once a keyboard drives it: silent
  // until a note.
  core_->setGated(true);
  const auto size = static_cast<std::size_t>(std::max(64, samplesPerBlock));
  pictureL_.assign(size, 0.0f); pictureR_.assign(size, 0.0f); spare_.assign(size, 0.0f);
  held_ = -1;
  /* For looking at it without a keyboard: SCOPE_HOLD_NOTE=57 holds A3 from
     the start, so the standalone has something to draw. Read once, here, and
     never on the audio thread. */
  if (const char* note = std::getenv("SCOPE_HOLD_NOTE")) {
    held_ = std::atoi(note);
    core_->set("freq", juce::MidiMessage::getMidiNoteInHertz(held_));
    core_->gate(true, 1.0);
  }
}

void ScopeProcessor::render(float* left, float* right, int from, int to) {
  // In pieces no longer than the buffers made for them: a host may hand over
  // a bigger block than it said it would.
  const int most = static_cast<int>(pictureL_.size());
  for (int at = from; at < to; at += most) {
    const int n = std::min(most, to - at);
    float* heardR = right ? right + at : spare_.data();
    core_->block(pictureL_.data(), pictureR_.data(), n, left + at, heardR);
    std::size_t ring = pictureAt_.load(std::memory_order_relaxed);
    for (int k = 0; k < n; ++k) {
      picture_[ring * 2] = pictureL_[static_cast<std::size_t>(k)];
      picture_[ring * 2 + 1] = pictureR_[static_cast<std::size_t>(k)];
      ring = (ring + 1) % kPictureFrames;
    }
    pictureAt_.store(ring, std::memory_order_release);
  }
}

void ScopeProcessor::processBlock(juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midi) {
  juce::ScopedNoDenormals noDenormals;
  const int frames = buffer.getNumSamples();
  auto* left = buffer.getWritePointer(0);
  auto* right = buffer.getNumChannels() > 1 ? buffer.getWritePointer(1) : nullptr;
  // Each event at its own sample, not at the top of the block: the generator
  // is run up to it, told, and run on.
  int done = 0;
  for (const auto event : midi) {
    const int at = std::clamp(event.samplePosition, done, frames);
    render(left, right, done, at);
    done = at;
    const auto message = event.getMessage();
    if (message.isNoteOn()) {
      held_ = message.getNoteNumber();
      core_->set("freq", juce::MidiMessage::getMidiNoteInHertz(held_));
      core_->gate(true, message.getFloatVelocity());
    } else if (message.isNoteOff() && message.getNoteNumber() == held_) {
      core_->gate(false, 0);
      held_ = -1;
    } else if (message.isAllNotesOff() || message.isAllSoundOff()) {
      core_->gate(false, 0);
      held_ = -1;
    }
  }
  render(left, right, done, frames);
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
