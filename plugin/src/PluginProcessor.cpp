#include "PluginProcessor.h"

#include <algorithm>
#include <cmath>
#include <cstdlib>

#include "PluginEditor.h"

ScopeProcessor::ScopeProcessor()
    : AudioProcessor(BusesProperties().withOutput("Output", juce::AudioChannelSet::stereo(), true)) {
  for (std::size_t i = 0; i < kKnobs.size(); ++i) {
    const auto* spec = scope::rangeSpec(kKnobs[i].slider);
    knobs_[i] = new juce::AudioParameterFloat(juce::ParameterID { kKnobs[i].id, 1 }, kKnobs[i].name,
                                              juce::NormalisableRange<float>(static_cast<float>(spec->min), static_cast<float>(spec->max),
                                                                             static_cast<float>(spec->step)),
                                              static_cast<float>(spec->value));
    addParameter(knobs_[i]);
  }
  moved_.reserve(kKnobs.size());
  // What the out sends goes to the host's MIDI out, at its sample.
  instrument_.hooks.midiOut = [this](const std::uint8_t* bytes, int length, int sample) { outgoing_.addEvent(bytes, length, sample); };
  // A slider moved on the page: the host's parameter for it follows.
  instrument_.hooks.sliderMoved = [this](const std::string& id, double value) {
    for (std::size_t i = 0; i < kKnobs.size(); ++i) {
      if (id != kKnobs[i].slider) continue;
      knobs_[i]->setValueNotifyingHost(knobs_[i]->convertTo0to1(static_cast<float>(value)));
      applied_[i] = knobs_[i]->get();
    }
  };
  // A setup loaded: the parameters read back from the panel, so the host shows what it set.
  instrument_.hooks.loaded = [this] {
    for (std::size_t i = 0; i < kKnobs.size(); ++i) {
      const auto v = static_cast<float>(instrument_.slider(kKnobs[i].slider));
      knobs_[i]->setValueNotifyingHost(knobs_[i]->convertTo0to1(v));
      applied_[i] = knobs_[i]->get();
    }
  };
}

bool ScopeProcessor::queue(std::optional<scope::Instrument::Command> command) {
  if (!command) return false;
  const juce::SpinLock::ScopedLockType lock(queueLock_);
  queue_.push_back(std::move(*command));
  return true;
}

void ScopeProcessor::pageSlider(const std::string& id, const std::u16string& text) { queue(scope::Instrument::slider(id, text)); }
void ScopeProcessor::pageControl(const std::string& id, scope::Json value) { queue(scope::Instrument::control(id, std::move(value))); }
void ScopeProcessor::pageClick(const std::string& id) { queue(scope::Instrument::click(id)); }
void ScopeProcessor::pageFade(std::string_view json) { queue(scope::Instrument::fade(json)); }
void ScopeProcessor::pageRoutings(std::string_view text) { queue(scope::Instrument::routings(text)); }
bool ScopeProcessor::pageSetup(std::string_view code) { return queue(scope::Instrument::setup(code)); }

ScopeProcessor::PageState ScopeProcessor::pageState() const {
  const juce::SpinLock::ScopedLockType lock(publishLock_);
  return published_;
}

void ScopeProcessor::takePage() {
  {
    // Not waited for: a page mid-push leaves its commands for the next block.
    const juce::SpinLock::ScopedTryLockType lock(queueLock_);
    if (!lock.isLocked()) return;
    std::swap(queue_, taken_);
  }
  for (const auto& command : taken_) instrument_.apply(command);
  taken_.clear();
}

void ScopeProcessor::publish(bool wait) {
  if (!instrument_.changed()) return;
  std::string code = instrument_.stateCode();
  if (wait) {
    const juce::SpinLock::ScopedLockType lock(publishLock_);
    published_ = { instrument_.hostVersion(), std::move(code) };
  } else {
    const juce::SpinLock::ScopedTryLockType lock(publishLock_);
    if (!lock.isLocked()) return;  // the page is reading it; again next block
    published_ = { instrument_.hostVersion(), std::move(code) };
  }
  instrument_.published();
}

void ScopeProcessor::getStateInformation(juce::MemoryBlock& out) {
  const juce::SpinLock::ScopedLockType lock(stateLock_);
  if (!instrument_.prepared()) return;
  const std::string code = instrument_.stateCode();
  out.append(code.data(), code.size());
}

void ScopeProcessor::setStateInformation(const void* data, int size) {
  const auto decoded = scope::decodeSetup(std::string_view(static_cast<const char*>(data), static_cast<std::size_t>(size)));
  if (decoded.kind != scope::DecodedSetup::Kind::Read) return;
  const juce::SpinLock::ScopedLockType lock(stateLock_);
  pending_ = decoded.setup;
}

bool ScopeProcessor::isBusesLayoutSupported(const BusesLayout& layouts) const {
  return layouts.getMainOutputChannelSet() == juce::AudioChannelSet::stereo();
}

void ScopeProcessor::prepareToPlay(double sampleRate, int samplesPerBlock) {
  rate_.store(sampleRate);
  outgoing_.clear();
  outgoing_.ensureSize(2048);
  /* The sound the page opens on: its boot preset, loaded as the page loads
     it. SCOPE_PRESET names another, for looking at one in the standalone;
     read once, here, and never on the audio thread. */
  const char* wanted = std::getenv("SCOPE_PRESET");
  const scope::Preset* preset = wanted ? scope::findPreset(wanted) : nullptr;
  if (!preset) preset = scope::findPreset("Harmonic tone");
  {
    // A state the host handed over before there was a core to give it to wins.
    const juce::SpinLock::ScopedLockType lock(stateLock_);
    instrument_.prepare(sampleRate, samplesPerBlock, pending_ ? *pending_ : preset ? preset->setup : scope::Json::object());
    pending_.reset();
  }
  publish(true);  // for a page that asks before the first block
  /* For looking at it without a keyboard: SCOPE_HOLD_NOTE=57 holds A3 from
     the start, and SCOPE_HOLD_NOTE=57,64 a fifth on it, so the standalone has
     something to draw. Read once, here, and never on the audio thread. */
  if (const char* held = std::getenv("SCOPE_HOLD_NOTE")) {
    for (const auto& note : juce::StringArray::fromTokens(held, ",", ""))
      instrument_.keyboard().noteOn(note.getIntValue(), 127);
  }
}

void ScopeProcessor::processBlock(juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midi) {
  juce::ScopedNoDenormals noDenormals;
  /* A state being loaded from the message thread: this block is silence
     rather than a wait; one waiting for this thread is loaded here, which
     allocates, as a preset's load does. */
  const juce::SpinLock::ScopedTryLockType lock(stateLock_);
  if (!lock.isLocked()) { buffer.clear(); midi.clear(); return; }
  if (pending_) { instrument_.load(*pending_, true); pending_.reset(); }
  takePage();
  // The host's transport, where it gives one.
  std::optional<scope::Instrument::Transport> transport;
  if (auto* head = getPlayHead()) {
    if (const auto position = head->getPosition()) {
      if (const auto bpm = position->getBpm()) {
        const auto ppq = position->getPpqPosition();
        transport = scope::Instrument::Transport { *bpm, ppq.hasValue() ? std::optional<double>(*ppq) : std::nullopt,
                                                   position->getIsPlaying() };
      }
    }
  }
  // Each parameter the host has moved since the last block, to its slider.
  moved_.clear();
  for (std::size_t i = 0; i < kKnobs.size(); ++i) {
    const float v = knobs_[i]->get();
    if (v == applied_[i]) continue;
    applied_[i] = v;
    moved_.push_back({ kKnobs[i].slider, v });
  }
  /* The host's MIDI, as bytes at their samples, not JUCE's reading of them:
     the keyboard is the page's `midiBytes` ported. Collected first, as the
     instrument runs the generator up to each. */
  events_.clear();
  for (const auto event : midi)
    events_.push_back({ event.samplePosition, event.data, static_cast<std::size_t>(event.numBytes) });
  const int frames = buffer.getNumSamples();
  auto* right = buffer.getNumChannels() > 1 ? buffer.getWritePointer(1) : nullptr;
  instrument_.block(buffer.getWritePointer(0), right, frames, events_.data(), events_.size(), transport ? &*transport : nullptr,
                    moved_.data(), moved_.size());
  // The host's notes are spent; what goes back is what the out sent.
  midi.swapWith(outgoing_);
  outgoing_.clear();
  publish(false);
}

juce::AudioProcessorEditor* ScopeProcessor::createEditor() { return new ScopeEditor(*this); }

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter() { return new ScopeProcessor(); }
